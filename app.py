"""
Talk to Your Data – AI Analyst (Text-to-SQL System)
Flask API for natural language database queries
"""
import time
import csv
import io
import json
import pandas as pd
from dotenv import load_dotenv

# Load environment variables first
load_dotenv()

from flask import Flask, request, jsonify, send_from_directory, send_file
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from config import get_config
import llm
import executor
import validator
import explainer
import rbac
import logs as logs_module
from schema import introspect_schema, format_schema_for_prompt, get_allowed_tables, SchemaCache
from auth import require_auth, require_role, get_auth_from_header, generate_token
from saved_queries import get_saved_query_store
from analytics import record_query, get_analytics
from caching import get_cached, set_cache, get_cache


app = Flask(__name__)
config = get_config()

# Initialize rate limiter
limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["200 per hour", "50 per minute"],
    storage_uri="memory://"
)

# Global service instances
db_engine = None
genai_client = None
schema_cache = None


def init_services():
    """Initialize all services: database, LLM client, schema cache."""
    global db_engine, genai_client, schema_cache
    
    # Initialize database engine
    if not config.DATABASE_URL:
        print("WARNING: DATABASE_URL not configured")
    else:
        try:
            db_engine = executor.init_engine(
                config.DATABASE_URL,
                statement_timeout_ms=config.STATEMENT_TIMEOUT_MS,
                readonly=config.READONLY,
            )
            print(f"✓ Database initialized: {config.DATABASE_URL[:50]}...")
        except Exception as e:
            print(f"✗ Database init failed: {e}")
    
    # Initialize LLM client
    if not config.GEMINI_API_KEY:
        print("WARNING: GEMINI_API_KEY not configured")
    else:
        try:
            genai_client = llm.init_genai_client(config.GEMINI_API_KEY)
            print(f"✓ LLM client initialized: {config.GENAI_MODEL_ID}")
        except Exception as e:
            print(f"✗ LLM init failed: {e}")
    
    # Initialize schema cache
    if config.ENABLE_SCHEMA_CACHE:
        schema_cache = SchemaCache(ttl_seconds=config.SCHEMA_CACHE_TTL_S)
        print(f"✓ Schema cache enabled (TTL={config.SCHEMA_CACHE_TTL_S}s)")


@app.route("/", methods=["GET"])
def root():
    """Serve the enhanced web UI."""
    return send_from_directory("static", "index_enhanced.html")


@app.route("/classic", methods=["GET"])
def classic():
    """Serve the classic web UI."""
    return send_from_directory("static", "index.html")


@app.route("/static/<path:path>", methods=["GET"])
def static_files(path):
    """Serve static files (CSS, JS, etc)."""
    return send_from_directory("static", path)


@app.route("/health", methods=["GET"])
def health():
    """Health check endpoint reporting service readiness."""
    status = {
        "status": "ok" if (db_engine and genai_client) else "degraded",
        "timestamp": time.time(),
        "config": {
            "database_url": bool(config.DATABASE_URL),
            "gemini_api_key": bool(config.GEMINI_API_KEY),
            "dev_fallback_mode": config.DEV_FALLBACK_MODE,
        },
        "services": {
            "database": db_engine is not None,
            "genai_client": genai_client is not None,
            "schema_cache": schema_cache is not None,
        },
        "features": {
            "rbac": config.ENABLE_RBAC,
            "logging": config.ENABLE_LOGGING,
            "schema_cache": config.ENABLE_SCHEMA_CACHE,
        },
    }
    
    # Try a trivial DB query if engine exists
    if db_engine:
        try:
            executor.execute_query(db_engine, "SELECT 1")
            status["services"]["database"] = True
        except Exception as e:
            status["services"]["database"] = False
            status["db_error"] = str(e)
    
    return jsonify(status)


@app.route("/query", methods=["POST"])
@limiter.limit("20 per minute")
def query_data():
    """
    Process a natural language question and return SQL results.
    
    Request JSON:
        {
            "question": "What are total sales by region?",
            "user_id": "user_1" (optional, for RBAC)
        }
    
    Response JSON (success):
        {
            "question": "...",
            "generated_sql": "SELECT ...",
            "columns": ["col1", "col2"],
            "rows": [{"col1": "val1", "col2": "val2"}, ...],
            "explanation": "...",
            "latency_ms": 123,
        }
    
    Response JSON (error):
        {
            "error": "Error message",
            "details": "Additional context",
            "generated_sql": "..." (if available)
        }
    """
    query_start = time.time()
    
    # Parse request
    try:
        data = request.get_json() or {}
        question = data.get("question", "").strip()
        user_request_context = {
            "user_id": data.get("user_id", "user_1"),
            "username": data.get("username", "analyst"),
            "role": data.get("role", "analyst"),
        }
    except Exception as e:
        return jsonify({"error": "Invalid request body", "details": str(e)}), 400
    
    if not question:
        return jsonify({"error": "Question is required"}), 400
    
    # Lazy Init: Try to connect if not connected
    if not db_engine:
        init_services()
    
    # Check service readiness
    if not db_engine:
        return jsonify({"error": "Database not configured"}), 503
    if not genai_client and not config.DEV_FALLBACK_MODE:
        return jsonify({"error": "LLM client not configured"}), 503
    
    try:
        # 1. Get user and check permissions
        if config.ENABLE_RBAC:
            user = rbac.get_user_from_request(user_request_context)
        else:
            user = rbac.User(user_id="system", username="system", role="admin")
        
        # 2. Introspect schema and filter by user permissions
        try:
            schema_dict = introspect_schema(db_engine, schema_cache if config.ENABLE_SCHEMA_CACHE else None)
        except Exception as e:
            return jsonify({"error": "Schema introspection failed", "details": str(e)}), 500
        
        # Get allowed tables for user
        allowed_tables = rbac.get_allowed_resources(user)
        if allowed_tables != ["*"]:
            schema_dict = get_allowed_tables(schema_dict, allowed_tables)
        
        if not schema_dict:
            return jsonify({"error": "No accessible tables for this user"}), 403
        
        # 3. Prepare schema context for LLM
        schema_str = format_schema_for_prompt(schema_dict)
        
        # 4. Generate SQL using LLM
        if config.DEV_FALLBACK_MODE:
            # Fallback: use simple template-based SQL for common queries
            print(f"ℹ Using fallback SQL generation (not calling LLM)")
            generated_sql = _dev_fallback_sql(question, list(schema_dict.keys()))
        else:
            try:
                generated_sql = llm.generate_sql(
                    client=genai_client,
                    model_id=config.GENAI_MODEL_ID,
                    question=question,
                    schema_context=schema_str,
                    temperature=config.LLM_TEMPERATURE,
                    timeout_seconds=config.LLM_TIMEOUT_S,
                )
            except Exception as e:
                # Fallback Strategy: If AI fails (404, 429, 500, etc), use Regex SQL
                # Detailed error logging for admin/logs
                print(f"⚠ LLM Generation Failed: {e}")
                
                # Generate "Smart" Offline SQL
                generated_sql = _dev_fallback_sql(question, list(schema_dict.keys()), schema_dict)
                
                # User-facing warning in explanation
                error_short = str(e).split(']')[0] if ']' in str(e) else str(e)[:50]
                explanation = f"⚠ AI Unavailable ({error_short}). showing result based on keywords."
        
        # 5. Validate SQL
        try:
            list_of_allowed = list(schema_dict.keys())
            safe_sql = validator.sanitize_and_validate_sql(
                generated_sql,
                allowed_tables=list_of_allowed,
                max_limit=config.MAX_LIMIT,
            )
        except ValueError as e:
            logs_module.log_query(
                user_id=user.user_id,
                question=question,
                generated_sql=generated_sql,
                status="error",
                latency_ms=(time.time() - query_start) * 1000,
                error_message=f"SQL validation failed: {e}",
            )
            return jsonify({
                "error": "Generated SQL did not pass safety checks",
                "details": str(e),
                "generated_sql": generated_sql,
            }), 400
        
        # 6. Execute query
        try:
            columns, rows = executor.execute_query(db_engine, safe_sql)
        except Exception as e:
            logs_module.log_query(
                user_id=user.user_id,
                question=question,
                generated_sql=safe_sql,
                status="error",
                latency_ms=(time.time() - query_start) * 1000,
                error_message=f"Query execution failed: {e}",
            )
            return jsonify({"error": "Query execution failed", "details": str(e)}), 500
        
        # 7. Generate explanation
        explanation = None
        if config.DEV_FALLBACK_MODE:
            # Fallback: generate explanation from results instead of calling LLM
            num_rows = len(rows) if rows else 0
            num_cols = len(columns) if columns else 0
            col_summary = ", ".join(columns[:3]) + ("..." if num_cols > 3 else "")
            explanation = f"Retrieved {num_rows} record(s) with columns: {col_summary}."
            print(f"ℹ Using fallback explanation (not calling LLM)")
        else:
            try:
                explanation = explainer.generate_explanation(
                    client=genai_client,
                    model_id=config.GENAI_MODEL_ID,
                    question=question,
                    sql=safe_sql,
                    sample_rows=rows,
                    temperature=config.LLM_TEMPERATURE,
                    timeout_seconds=config.LLM_TIMEOUT_S,
                )
            except Exception as e:
                # Graceful fallback: generate basic explanation from results
                print(f"⚠ Explanation generation failed: {e}, using fallback")
                num_rows = len(rows) if rows else 0
                num_cols = len(columns) if columns else 0
                col_summary = ", ".join(columns[:3]) + ("..." if num_cols > 3 else "")
                explanation = f"Retrieved {num_rows} record(s) with columns: {col_summary}."
        
        # 8. Log successful query
        latency_ms = (time.time() - query_start) * 1000
        if config.ENABLE_LOGGING:
            logs_module.log_query(
                user_id=user.user_id,
                question=question,
                generated_sql=safe_sql,
                status="success",
                latency_ms=latency_ms,
                rows_returned=len(rows),
            )
        
        # Record in analytics
        record_query(user.user_id, question, safe_sql, latency_ms, len(rows))
        
        # Try to cache result
        try:
            set_cache(user.user_id, question, columns, rows, explanation)
        except:
            pass  # Cache failures are non-blocking
        
        return jsonify({
            "question": question,
            "generated_sql": safe_sql,
            "columns": columns,
            "rows": rows,
            "explanation": explanation,
            "latency_ms": round(latency_ms, 2),
        })
    
    except Exception as e:
        latency_ms = (time.time() - query_start) * 1000
        if config.ENABLE_LOGGING:
            logs_module.log_query(
                user_id=user_request_context.get("user_id", "unknown"),
                question=question,
                generated_sql="",
                status="error",
                latency_ms=latency_ms,
                error_message=str(e),
            )
        return jsonify({"error": "Internal server error", "details": str(e)}), 500


@app.route("/logs", methods=["GET"])
def get_query_logs():
    """
    Retrieve recent query logs (admin only in production).
    Query params:
        - limit: number of recent logs to return (default: 50)
    """
    limit = request.args.get("limit", 50, type=int)
    recent_logs = logs_module.get_logs(limit=limit)
    return jsonify({"logs": recent_logs, "count": len(recent_logs)})


def _dev_fallback_sql(question: str, available_tables: list, schema_dict: dict = None) -> str:
    """
    Robust Rule-Based SQL Generator (No AI Required).
    Parses natural language to Generate valid SQL for common patterns.
    """
    import re
    q = question.lower().strip()
    table = available_tables[0] if available_tables else "unknown_table"
    
    # 0. Table Selection (if multiple tables exist)
    if len(available_tables) > 1:
        for t in available_tables:
            if t.lower() in q:
                table = t
                break

    # 1. Aggregations (Count)
    if re.search(r"\b(count|how many|total number)\b", q):
        return f"SELECT COUNT(*) FROM {table}"
        
    # 2. Aggregations (Sum/Avg) - Requires finding a numeric column
    agg_match = re.search(r"\b(sum|total|average|avg)\b", q)
    if agg_match and schema_dict and table in schema_dict:
        agg_func = "AVG" if agg_match.group(1) in ["average", "avg"] else "SUM"
        # Find a numeric column mentioned in query, or default to first numeric
        # For now, just look for any column name in query
        for col in schema_dict[table]:
            if col.lower() in q:
                return f"SELECT {agg_func}({col}) FROM {table}"

    # 3. Specific Columns Selection
    selected_cols = []
    if schema_dict and table in schema_dict:
        # Sort columns by length desc to match longest names first (e.g. 'user_id' before 'id')
        all_cols = sorted(schema_dict[table], key=len, reverse=True)
        for col in all_cols:
            # Check for column name in query
            # Use word boundary to avoid partial matches (e.g. 'id' inside 'width')
            if re.search(r"\b" + re.escape(col.lower()) + r"\b", q):
                selected_cols.append(col)
    
    # 4. Limit logic
    limit = 100
    limit_match = re.search(r"\b(top|limit)\s+(\d+)", q)
    if limit_match:
        limit = int(limit_match.group(2))
    elif "top" in q: 
        limit = 10
        
    # 5. Filtering (WHERE clause)
    where_clause = ""
    # Look for 'value' or "value"
    quote_match = re.search(r"['\"](.*?)['\"]", question)
    if quote_match and schema_dict and table in schema_dict:
        val = quote_match.group(1)
        safe_val = val.replace("'", "''") # SQL Escape
        
        # Determine which column this value belongs to
        # 1. Check if column name is mentioned near the value
        target_col = None
        for col in schema_dict[table]:
            if col.lower() in q:
                target_col = col
                break
        
        # 2. If no column mentioned, fallback to first text column (heuristic)
        if not target_col:
             # Just pick the first column that isn't ID? 
             # Safer to just not filter if we don't know the column to avoid errors.
             pass
        else:
            where_clause = f" WHERE {target_col} = '{safe_val}'"

    # Construct Final Query
    cols_sql = "*"
    if selected_cols:
        cols_sql = ", ".join(selected_cols)
    
    # If using specific columns, maybe don't limit unless asked? 
    # Let's keep limit for safety, but increase it.
    if selected_cols and limit == 100:
        limit = 1000

    return f"SELECT {cols_sql} FROM {table}{where_clause} LIMIT {limit}"


@app.route("/auth/token", methods=["POST"])
def get_token():
    """Generate JWT token for user."""
    data = request.get_json() or {}
    user_id = data.get("user_id", "user_1")
    username = data.get("username", "analyst")
    role = data.get("role", "analyst")
    
    token = generate_token(user_id, username, role)
    return jsonify({
        "token": token,
        "user_id": user_id,
        "username": username,
        "role": role,
    })


@app.route("/saved-queries", methods=["GET", "POST"])
def saved_queries():
    """List or save queries."""
    auth = get_auth_from_header()
    if not auth:
        return jsonify({"error": "Unauthorized"}), 401
    
    store = get_saved_query_store()
    
    if request.method == "POST":
        # Save new query
        data = request.get_json() or {}
        name = data.get("name", "").strip()
        question = data.get("question", "").strip()
        generated_sql = data.get("generated_sql", "").strip()
        
        if not (name and question and generated_sql):
            return jsonify({"error": "name, question, and generated_sql are required"}), 400
        
        try:
            saved = store.save(auth["user_id"], name, question, generated_sql)
            return jsonify({
                "message": "Query saved",
                "query": saved.to_dict(),
            }), 201
        except ValueError as e:
            return jsonify({"error": str(e)}), 400
    
    else:
        # List user's saved queries
        limit = request.args.get("limit", 50, type=int)
        queries = store.list_user_queries(auth["user_id"], limit)
        return jsonify({
            "queries": [q.to_dict() for q in queries],
            "count": len(queries),
        })


@app.route("/saved-queries/search", methods=["GET"])
def search_saved_queries():
    """Search saved queries by keyword."""
    auth = get_auth_from_header()
    if not auth:
        return jsonify({"error": "Unauthorized"}), 401
    
    keyword = request.args.get("q", "").strip()
    if not keyword:
        return jsonify({"error": "q parameter is required"}), 400
    
    store = get_saved_query_store()
    results = store.search(auth["user_id"], keyword)
    return jsonify({
        "keyword": keyword,
        "results": [q.to_dict() for q in results],
        "count": len(results),
    })


@app.route("/saved-queries/<query_id>", methods=["GET", "DELETE"])
def saved_query_detail(query_id):
    """Get or delete a saved query."""
    auth = get_auth_from_header()
    if not auth:
        return jsonify({"error": "Unauthorized"}), 401
    
    store = get_saved_query_store()
    
    if request.method == "GET":
        saved = store.get(query_id)
        if not saved:
            return jsonify({"error": "Query not found"}), 404
        if saved.user_id != auth["user_id"]:
            return jsonify({"error": "Forbidden"}), 403
        
        return jsonify(saved.to_dict())
    
    else:  # DELETE
        saved = store.get(query_id)
        if not saved:
            return jsonify({"error": "Query not found"}), 404
        if saved.user_id != auth["user_id"]:
            return jsonify({"error": "Forbidden"}), 403
        
        store.delete(query_id)
        return jsonify({"message": "Query deleted"})


@app.route("/analytics/dashboard", methods=["GET"])
def analytics_dashboard():
    """Get analytics dashboard statistics."""
    analytics = get_analytics()
    stats = analytics.get_dashboard_stats()
    return jsonify({
        "timestamp": time.time(),
        "stats": stats,
    })


@app.route("/analytics/slowest", methods=["GET"])
def analytics_slowest():
    """Get slowest queries."""
    limit = request.args.get("limit", 10, type=int)
    analytics = get_analytics()
    slowest = analytics.get_slowest_queries(limit)
    return jsonify({
        "slowest_queries": slowest,
        "count": len(slowest),
    })


@app.route("/cache/stats", methods=["GET"])
def cache_stats():
    """Get cache statistics."""
    cache = get_cache()
    stats = cache.get_stats()
    return jsonify({
        "cache_stats": stats,
    })


@app.route("/cache/clear", methods=["POST"])
def cache_clear():
    """Clear all cache (admin only)."""
    auth = get_auth_from_header()
    if not auth or auth.get("role") != "admin":
        return jsonify({"error": "Admin only"}), 403
    
    cache = get_cache()
    cache.clear()
    return jsonify({"message": "Cache cleared"})


@app.route("/query/export", methods=["POST"])
def export_query_results():
    """Export query results as CSV or JSON."""
    data = request.get_json() or {}
    columns = data.get("columns", [])
    rows = data.get("rows", [])
    format_type = data.get("format", "csv").lower()
    
    if not (columns and rows):
        return jsonify({"error": "columns and rows are required"}), 400
    
    if format_type == "json":
        # JSON export
        output = io.StringIO()
        json.dump(rows, output, indent=2, default=str)
        output.seek(0)
        return send_file(
            io.BytesIO(output.getvalue().encode()),
            mimetype="application/json",
            as_attachment=True,
            download_name="query_results.json"
        )
    
    else:  # CSV
        # CSV export
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)
        output.seek(0)
        return send_file(
            io.BytesIO(output.getvalue().encode()),
            mimetype="text/csv",
            as_attachment=True,
            download_name="query_results.csv"
        )


@app.route("/upload", methods=["POST"])
def upload_csv():
    """Upload a CSV file and convert it to a database table."""
    auth = get_auth_from_header()
    # In production, require admin/analyst role
    # if not auth: return jsonify({"error": "Unauthorized"}), 401
    
    # Lazy Init: Try to connect if not connected
    if not db_engine:
        init_services()

    if "file" not in request.files:
        return jsonify({"error": "No file part"}), 400
    
    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "No selected file"}), 400
    
    if not file.filename.endswith(".csv"):
        return jsonify({"error": "Only CSV files are allowed"}), 400
    
    try:
        # 1. Read CSV into DataFrame (Try UTF-8 first, then Latin-1 for Excel)
        try:
            df = pd.read_csv(file)
        except UnicodeDecodeError:
            file.seek(0)  # Reset file pointer
            df = pd.read_csv(file, encoding='latin-1')
        
        # 2. Sanitize table name (use filename, alphanumeric only)
        table_name = "".join(c for c in file.filename.split(".")[0] if c.isalnum() or c == "_").lower()
        if not table_name:
            table_name = "uploaded_data"
            
        # 3. Write to database (replace if exists)
        if db_engine:
            df.to_sql(table_name, db_engine, if_exists="replace", index=False)
            
            # 4. Clear schema cache so new table is visible
            if schema_cache:
                schema_cache.clear()
            
            # 5. Get column info for response
            columns = list(df.columns)
            row_count = len(df)
            
            return jsonify({
                "message": f"Successfully uploaded '{file.filename}' to table '{table_name}'",
                "table": table_name,
                "rows": row_count,
                "columns": columns
            })
        else:
            return jsonify({"error": "Database not configured"}), 503
            
    except Exception as e:
        print(f"❌ Upload error: {str(e)}")  # Print to server logs
        return jsonify({"error": "Upload failed", "details": str(e)}), 500


if __name__ == "__main__":
    # Initialize services on startup
    init_services()
    print("\n" + "=" * 70)
    print("Talk to Your Data – AI Analyst (Enhanced)")
    print("=" * 70)
    print(f"Config: DEV_FALLBACK_MODE={config.DEV_FALLBACK_MODE}")
    print("\nAPI Endpoints:")
    print("  Core:")
    print("    GET  /              - Web UI")
    print("    POST /query         - Execute NL query")
    print("    GET  /health        - Health check")
    print("    GET  /logs          - Query logs")
    print("\n  Authentication:")
    print("    POST /auth/token    - Generate JWT token")
    print("\n  Saved Queries:")
    print("    GET  /saved-queries                - List user's saved queries")
    print("    POST /saved-queries                - Save new query")
    print("    GET  /saved-queries/search         - Search saved queries")
    print("    GET  /saved-queries/<id>           - Get saved query")
    print("    DEL  /saved-queries/<id>           - Delete saved query")
    print("\n  Analytics:")
    print("    GET  /analytics/dashboard          - Dashboard stats")
    print("    GET  /analytics/slowest            - Slowest queries")
    print("\n  Cache:")
    print("    GET  /cache/stats                  - Cache statistics")
    print("    POST /cache/clear                  - Clear cache (admin)")
    print("\n  Data Export:")
    print("    POST /query/export                 - Export as CSV/JSON")
    print("    POST /upload                       - Upload CSV to Database")
    print("=" * 70 + "\n")
    
    # Run Flask development server
    app.run(host="127.0.0.1", port=5000, debug=False)

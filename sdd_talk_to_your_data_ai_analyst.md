# SOFTWARE DESIGN DESCRIPTION (SDD)

## for
**Talk to Your Data – AI Analyst (Text-to-SQL System)**  
Version 1.0

---

## 1. Introduction
This document describes the system design of the Talk to Your Data AI Analyst, covering architecture, data design, algorithms, and interfaces.

---

## 2. Design Methodology and Software Process Model

### Design Methodology
An **Object-Oriented Design (OOD)** approach is used to promote modularity, extensibility, and maintainability.

### Software Process Model
An **Iterative and Incremental** development model is followed to allow continuous evaluation of LLM behavior and system reliability.

---

## 3. System Overview

### 3.1 Architectural Design
The system follows a **Client–Server layered architecture** with 13 modular Python components:

| Layer | Module | Purpose |
|-------|--------|---------|
| Configuration | config.py | Centralized configuration with 13+ settings |
| Data Access | executor.py | Safe query execution with read-only + timeouts |
| Data Access | schema.py | Schema introspection & TTL-based caching |
| Validation | validator.py | SQL injection prevention with actionable errors |
| AI Reasoning | llm.py | Google Gemini integration with fallback |
| AI Reasoning | explainer.py | Result summarization via LLM |
| API | app.py | Flask orchestration with 17 endpoints |
| Security | rbac.py | Role-based access control (3 roles) |
| Security | auth.py | JWT authentication & authorization |
| Audit | logs.py | In-memory query audit trail |
| Performance | caching.py | Result caching with TTL (5min default) |
| Analytics | analytics.py | Query performance tracking & dashboard |
| Query Management | saved_queries.py | Save, search, and manage user queries |
| UI | static/index_enhanced.html | Modern UI with sidebar & tabs |
| UI | static/app_enhanced.js | Frontend with Chart.js visualization |

**Major Modules:**
- User Interface Layer
- API Layer
- AI Reasoning Layer
- Validation & Guardrails Layer
- Data Access Layer


### 3.2 Process Flow Representation
1. User submits natural language query via enhanced web UI
2. Rate limiter checks request limits (20/min per IP)
3. Cache checks if identical query exists (5-min TTL)
4. If cache miss, API extracts user context (role, permissions)
5. RBAC module checks table access permissions
6. Schema cache retrieves filtered database schema
7. SQL generation: LLM or template-based fallback (when `DEV_FALLBACK_MODE=true` or LLM failure)
8. Validator applies injection prevention with helpful error messages
9. Executor runs query with read-only + 5s timeout
10. Explanation generation: LLM or row/column-based fallback summary (no external API required)
11. Analytics module records query metrics (latency, status)
12. Cache stores result for future requests
13. Logs module records audit trail
14. Results, SQL, explanation, latency, and chart data returned to UI
15. UI renders tabbed views (table, chart, SQL, explanation)

---

## 4. Design Models

### 4.1 Class Diagram (Conceptual)
Key classes:
- User (rbac.py)
- QuerySession (logs.py)
- SchemaMetadata (schema.py)
- SQLGenerator (llm.py)
- SQLValidator (validator.py)
- QueryExecutor (executor.py)
- ResultExplainer (explainer.py)
- AuthToken (auth.py)
- SavedQuery (saved_queries.py)
- QueryCache (caching.py)
- AnalyticsDashboard (analytics.py)

### 4.2 Sequence Diagram (Enhanced Query Flow)
User → UI → RateLimiter → Cache → API → Auth → SQLGenerator → SQLValidator → QueryExecutor → ResultExplainer → Analytics → Cache → UI

### 4.3 Data Flow Diagram (DFD – Level 1)
- Input: Natural language query
- Process: Query translation and execution
- Data Store: Relational Database
- Output: Results + Explanation

---

## 5. Data Design

### 5.1 Data Storage
- User metadata (role-based permissions)
- Query audit logs (in-memory, max 1000 entries)
- Schema metadata cache (TTL: 3600s default)
- Saved queries (in-memory, per-user storage)
- Query result cache (in-memory, 5-min TTL)
- Analytics metrics (in-memory, aggregate stats)
- Sample database: PostgreSQL 'talk_to_data' with 'sales' table (130 rows, 5 regions)

### 5.2 Data Dictionary

**User (rbac.py)**
- user_id (string)
- username (string)
- role (string: analyst | finance | admin)
- allowed_tables (list of table names)

**QuerySession (logs.py)**
- user_id (string)
- question (string)
- generated_sql (string)
- execution_status (string: success | failed)
- latency_ms (float)
- rows_returned (int)
- error_message (string or null)
- timestamp (datetime)

**SchemaMetadata (schema.py)**
- table_name (string)
- columns (dict: column_name → data_type)
- last_updated (timestamp)
- ttl_seconds (int: 3600)

**SavedQuery (saved_queries.py)**
- query_id (string: UUID)
- user_id (string)
- name (string)
- question (string)
- description (string)
- created_at (datetime)
- usage_count (int)

**CachedResult (caching.py)**
- cache_key (string: hash of question)
- columns (list of strings)
- rows (list of dicts)
- generated_sql (string)
- explanation (string)
- cached_at (timestamp)
- ttl_seconds (int: 300)

**AnalyticsMetrics (analytics.py)**
- total_queries (int)
- successful_queries (int)
- failed_queries (int)
- total_latency_ms (float)
- avg_latency_ms (float)
- slowest_queries (list of QuerySession)

**AuthToken (auth.py)**
- token (string: JWT)
- user_id (string)
- username (string)
- role (string)
- exp (timestamp: expiration)

**Sample Data (sales table)**
```
CREATE TABLE sales (
    id SERIAL PRIMARY KEY,
    amount NUMERIC NOT NULL,
    region TEXT NOT NULL,
    created_at DATE NOT NULL
);
```
Current data: 130 rows across 5 regions (US, EU, APAC, LATAM, CANADA)

---

## 6. Algorithm & Implementation

### 6.1 Natural Language to SQL Generation
Pseudo Code:
- Receive user query
- Load allowed schema context (filtered by RBAC)
- Generate SQL via LLM **or** template-based fallback when `DEV_FALLBACK_MODE=true` or LLM errors
- Enforce output schema and normalize SQL
- If LLM unavailable, continue with fallback-generated SQL

### 6.2 SQL Validation Algorithm (validator.py)
Input: Generated SQL, allowed_tables list, max_limit
Output: Sanitized SQL or raises PermissionError

Validation Steps:
1. Check for forbidden keywords (INSERT, UPDATE, DELETE, DROP, ALTER, TRUNCATE, CREATE, GRANT, REVOKE, COPY, VACUUM, ANALYZE, LOCK)
2. Check for forbidden patterns (semicolons, block/inline comments, UNION, INTERSECT, EXCEPT, CTEs, INTO, FOR UPDATE)
3. Extract all table references from query
4. Verify all tables exist in allowed_tables list
5. Verify max_limit >= query LIMIT clause (or inject default 100)
6. Return sanitized SQL with auto-injected LIMIT

Security Features:
- Regex-based pattern detection
- Allowlist-based table validation
- Prevents LIMIT injection bypass
- Provides actionable error messages

### 6.3 Result Explanation
- Summarize rows and metrics
- Generate human-readable insights; when LLM is unavailable, produce fallback summary from returned rows/columns (no external API call)

### 6.4 Caching Algorithm (caching.py)
Input: Question string
Output: Cached result or None

Algorithm:
1. Hash question text to generate cache key
2. Check if key exists in cache
3. If exists and not expired (TTL < 300s), return cached result
4. If miss or expired, return None (triggering fresh query)
5. After query execution, store result in cache with timestamp

### 6.5 Rate Limiting (Flask-Limiter)
- Track requests per IP address
- Global limits: 200/hour
- Query endpoint: 20/minute
- Return 429 status code when exceeded

### 6.6 Authentication Flow (auth.py)
1. User requests token via POST /auth/token with credentials
2. Server generates JWT with user_id, username, role, exp
3. Client stores token and includes in Authorization header
4. Server validates token signature and expiration on protected endpoints
5. Extract user context from token for RBAC checks

---

## 7. Software Requirements Traceability Matrix

| Req ID | Design Component | Implementation | File |
|--------|------------------|-----------------|------|
| FR-1 | User Input | Accept query via POST /query | app.py, index.html |
| FR-2 | LLM Integration | generate_sql(question, schema) | llm.py |
| FR-3 | SQL Validator | sanitize_and_validate_sql() | validator.py |
| FR-4 | Query Executor | execute_query(engine, sql) | executor.py |
| FR-5 | Result Display | buildTable(columns, rows) | static/app.js |
| FR-6 | Result Explainer | generate_explanation() | explainer.py |
| FR-7 | RBAC | User model + authorize_tables() | rbac.py |
| FR-8 | Query Logging | QueryLogger.log_query() | logs.py |
| FR-9 | Schema Cache | SchemaCache with TTL | schema.py |
| FR-10 | Fallback Mode | _dev_fallback_sql() | app.py |
| FR-11 | JWT Auth | generate_token(), require_auth() | auth.py |
| FR-12 | Saved Queries | SavedQueryStore.save_query() | saved_queries.py |
| FR-13 | Query Search | search_queries(keyword) | saved_queries.py |
| FR-14 | Analytics Tracking | record_query() | analytics.py |
| FR-15 | Analytics Dashboard | get_analytics() | analytics.py |
| FR-16 | Query History | get_recent_logs(limit) | logs.py |
| FR-17 | Result Caching | get_cached(), set_cache() | caching.py |
| FR-18 | Cache Stats | get_cache_stats() | caching.py |
| FR-19 | Rate Limiting | @limiter.limit() decorator | app.py + flask-limiter |
| FR-20 | Data Export | POST /query/export | app.py |
| FR-21 | Data Visualization | Chart.js integration | app_enhanced.js |
| FR-22 | Tabbed Views | showTab() function | index_enhanced.html |
| NFR-1 | SQL Injection Prevention | 13-point validation | validator.py |
| NFR-2 | Read-Only Enforcement | SET SESSION CHARACTERISTICS | executor.py |
| NFR-3 | Statement Timeout | SET statement_timeout | executor.py |
| NFR-4 | Caching Performance | Hash-based in-memory cache | caching.py |
| NFR-5 | Rate Limiting | Flask-Limiter middleware | app.py |
| NFR-6 | Error Messages | Actionable validation errors | validator.py |

---

## 8. Human Interface Design

### 8.1 Screen Layout (Enhanced UI - index_enhanced.html)
**Main Layout:**
- **Sidebar** (300px):
  - Query History panel (last 10 queries, one-click reload)
  - Saved Queries panel (bookmarked queries with names)
  - Quick Stats panel (total queries, avg latency, success rate)
- **Main Content Area**:
  - Header: Purple gradient banner with "Talk to Your Data" title
  - Query Input Section: Textarea with Submit/Clear/Save buttons
  - Status Bar: Real-time messages (loading, success, error)
  - Tabbed Results Section:
    - 📋 Table Tab: Sortable data table with export buttons (CSV/JSON)
    - 📊 Chart Tab: Auto-generated bar charts using Chart.js
    - 💻 SQL Tab: Generated SQL with syntax highlighting
    - 💡 Explanation Tab: AI-generated insights

**Classic UI** (index.html):
- **Header**: Purple gradient banner with title "Talk to Your Data"
- **Query Section**: Textarea for natural language question + Submit/Clear buttons
- **Status Bar**: Real-time status messages (loading, success, error)
- **Results Section** (collapsible):
  - **Explanation Panel**: AI-generated summary of results
  - **SQL Panel**: Generated SQL query with syntax highlighting
  - **Data Table**: Results rendered as sortable HTML table

### 8.2 Screen Objects and Actions (Enhanced UI)
- **#question (textarea)**: Accept user input; Ctrl+Enter submits query
- **#submitBtn (button)**: onclick=submitQuery() POST to /query with rate limiting
- **#clearBtn (button)**: Clear textarea and results
- **saveQueryBtn (button)**: onclick=saveCurrentQuery() bookmark current query
- **#status (div)**: Display messages ("Loading...", "Success", errors)
- **#queryHistory (div)**: Sidebar panel showing last 10 queries (clickable)
- **#savedQueries (div)**: Sidebar panel showing bookmarked queries
- **#quickStats (div)**: Sidebar panel showing analytics (total, latency, success rate)
- **Tab buttons**: Switch between Table/Chart/SQL/Explanation views
- **#resultsTable (div)**: Dynamic HTML table with export buttons
- **#resultChart (canvas)**: Chart.js bar chart visualization
- **#generatedSql (code)**: Display generated SQL with syntax highlighting
- **#explanation (div)**: Display AI-generated explanation
- **exportData(format) (function)**: Download results as CSV or JSON

### 8.3 API Endpoints (Complete List)
| Method | Endpoint | Parameters | Response |
|--------|----------|------------|----------|
| GET | / | - | Serve enhanced UI (index_enhanced.html) |
| GET | /classic | - | Serve classic UI (index.html) |
| GET | /static/<path> | path: string | Serve CSS/JS/assets |
| POST | /query | question, user_id, username, role | {columns, rows, generated_sql, explanation, latency_ms} |
| GET | /health | - | {status, timestamp, config:{database_url, gemini_api_key, dev_fallback_mode}, services:{database, genai_client, schema_cache}, features:{rbac, logging, schema_cache}} |
| GET | /logs | limit: int (default 50) | [{user_id, question, sql, status, latency_ms, timestamp}...] |
| POST | /auth/token | user_id, username, role | {token: JWT string} |
| GET | /saved-queries | user_id: string | {queries: [SavedQuery...]} |
| POST | /saved-queries | user_id, name, question, description | {query_id, message} |
| GET | /saved-queries/search | q: keyword, user_id: string | {queries: [SavedQuery...]} |
| GET | /saved-queries/<id> | - | {SavedQuery} |
| DELETE | /saved-queries/<id> | - | {message} |
| GET | /analytics/dashboard | - | {analytics: {total, successful, failed, avg_latency}} |
| GET | /analytics/slowest | limit: int (default 10) | {slowest_queries: [QuerySession...]} |
| GET | /cache/stats | - | {hits, misses, size, hit_rate} |
| POST | /cache/clear | - | {message} (requires admin auth) |
| POST | /query/export | format (csv\|json), columns[], rows[] (from prior /query) | Binary file download (CSV/JSON) |

## 9. Configuration Design (config.py)

| Setting | Type | Default | Purpose |
|---------|------|---------|---------|
| DATABASE_URL | str | (env var) | PostgreSQL connection string |
| READONLY | bool | True | Force read-only transactions |
| STATEMENT_TIMEOUT_MS | int | 5000 | Max query execution time |
| GEMINI_API_KEY | str | (env var) | Google Gemini API key |
| GENAI_MODEL_ID | str | gemini-2.0-flash-exp | LLM model to use (configurable) |
| LLM_TIMEOUT_S | float | 10.0 | LLM response timeout |
| LLM_TEMPERATURE | float | 0.2 | LLM creativity (lower = more deterministic) |
| LLM_MAX_OUTPUT_TOKENS | int | 1024 | Max tokens in LLM response |
| MAX_LIMIT | int | 1000 | Enforce upper limit on LIMIT clause |
| DEFAULT_LIMIT | int | 100 | Auto-inject LIMIT if not specified |
| ENABLE_RBAC | bool | True | Enable role-based access control |
| ENABLE_LOGGING | bool | True | Enable query audit trail |
| ENABLE_SCHEMA_CACHE | bool | True | Enable schema caching |
| SCHEMA_CACHE_TTL_S | int | 3600 | Cache expiry in seconds |
| DEV_FALLBACK_MODE | bool | false | Use template-based SQL + result-based explanations when LLM unavailable or for offline/quota-safe mode |

## 10. Security Architecture

### 10.1 Defense Layers
1. **Input Validation**: User question sanitized for length
2. **RBAC**: User role checked before schema introspection
3. **Schema Filtering**: Only allowed tables included in LLM context
4. **LLM Guard**: Output normalization (strip code fences, comments)
5. **SQL Validation**: 13-point injection prevention checklist
6. **Database Enforcement**: Read-only session + statement timeout
7. **Error Masking**: Generic error messages to prevent information leakage
8. **Audit Logging**: All queries logged for compliance

### 10.2 Threat Model
| Threat | Mitigation |
|--------|-----------|
| SQL Injection via NL | Keyword/pattern blocking + table allowlist |
| Destructive Queries | Forbidden keywords (INSERT, DELETE, etc.) |
| Runaway Queries | Statement timeout + LIMIT auto-injection |
| Unauthorized Data Access | RBAC + table-level permissions |
| Privilege Escalation | User role from request header |
| API Abuse | Rate limiting (future enhancement) |
| Data Exfiltration | Read-only sessions enforce non-modification |

## 11. Testing & Validation Summary
- Automated edge-case suites executed (`quick_test.py`, `test_edge_cases.py`, `test_validator.py`)
- Coverage: empty/missing fields, malformed JSON, long queries (3000+ chars), cache hit/miss timing, rate limiting, CSV export contract, analytics dashboard, health check
- Security validation: 13/13 injection and system access attempts blocked by `validator.py`
- Performance: ~9ms average latency; cache improves repeated queries (~7% measured); fallback SQL/explanations operate without LLM/API calls
- Reliability: Fallback mode verified (DEV_FALLBACK_MODE=true) with template SQL + row/column-based explanations when LLM unavailable

## 12. Appendix I
- UML modeling guidelines
- Secure SQL execution best practices
- LLM integration patterns for safety


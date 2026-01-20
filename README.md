## Talk to Your Data – Complete Project

A production-ready Flask API for natural language database queries using AI-generated SQL. Query your PostgreSQL database in plain English, get back results with explanations, and enjoy enterprise-grade safety guardrails.

### Features

**Core:**
✅ **Natural Language to SQL**: Ask questions in English, get SQL and results  
✅ **Safety Guardrails**: Read-only, SQL injection prevention, statement timeouts  
✅ **Result Explanations**: AI-generated summaries of query results  
✅ **RBAC**: Role-based table access control  
✅ **Query Logging**: Audit trail of all executed queries  
✅ **Schema Introspection**: Automatic database schema discovery  
✅ **Web UI**: Interactive chat-style interface  
✅ **Modular Architecture**: Clean separation: 12+ focused modules  

**Enhanced (New):**
✅ **JWT Authentication**: Secure token-based access  
✅ **Saved Queries**: Bookmark and organize frequently used queries  
✅ **Query Analytics**: Dashboard with stats, trends, slowest queries  
✅ **Result Caching**: Instant results for repeated questions  
✅ **Data Export**: Download results as CSV or JSON  
✅ **Better Error Messages**: Actionable validation feedback  

For detailed feature documentation, see [FEATURES.md](FEATURES.md)  

---

## Quick Start (Windows)

### 1) Prerequisites

- Python 3.10+  
- PostgreSQL running locally  
- Google Gemini API key  

### 2) Create Virtual Environment

Open PowerShell in the project directory:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 3) Configure Environment

Copy `.env.example` to `.env` and fill in your values:

```bash
cp .env.example .env
```

Edit `.env` with your database connection and API key:

```
DATABASE_URL=postgresql+psycopg2://user:password@localhost:5432/dbname
GEMINI_API_KEY=your_api_key_here
GENAI_MODEL_ID=gemini-2.0-flash-exp
DEV_FALLBACK_MODE=false
```

**NOTE: Never commit .env to version control. Use .env.example as a template.**

### 4) Database Setup

Ensure PostgreSQL is running and create a database:

```sql
CREATE DATABASE talk_to_data;
```

To populate with sample data (130 sales records), run:

```bash
python populate_db.py
```

### 5) Run the Application

```powershell
.\.venv\Scripts\Activate
python app.py
```

Server runs at: http://127.0.0.1:5000

### 6) Access the UI

- Enhanced UI: http://127.0.0.1:5000/
- Classic UI: http://127.0.0.1:5000/classic
- Health check: http://127.0.0.1:5000/health
- API docs: See Endpoints section below


```
DATABASE_URL=postgresql+psycopg2://postgres:your_password@localhost:5432/talk_to_data
GEMINI_API_KEY=your_google_gemini_api_key
GENAI_MODEL_ID=gemini-1.5-flash
DEV_FALLBACK_MODE=false
```

**Or set in PowerShell (no .env file):**

```powershell
$env:DATABASE_URL = "postgresql+psycopg2://postgres:password@localhost:5432/talk_to_data"
$env:GEMINI_API_KEY = "YOUR_API_KEY"
```

### 4) Setup Database

If you haven't created the database yet, open psql and run:

```sql
CREATE DATABASE talk_to_data;
CREATE TABLE sales (
    id SERIAL PRIMARY KEY,
    amount NUMERIC,
    region TEXT,
    created_at DATE
);

INSERT INTO sales (amount, region, created_at) VALUES
(1200, 'US', '2024-01-01'),
(900, 'EU', '2024-01-02'),
(1500, 'US', '2024-01-03');
```

### 5) Run the Server

```powershell
python app.py
```

You should see:
```
============================================================
Talk to Your Data – AI Analyst
============================================================
Config: DEV_FALLBACK_MODE=False
Available endpoints: GET / POST /query GET /health GET /logs
============================================================
```

### 6) Open Web UI

Open your browser and go to:

```
http://127.0.0.1:5000
```

You should see an interactive chat interface. Try asking:

```
What is the total sales amount by region?
```

---

## Testing Locally (Dev/Debug Mode)

### Use Fallback Mode (No LLM Required)

Set in `.env` or PowerShell:

```
DEV_FALLBACK_MODE=true
```

This uses simple template-based SQL for common queries (total, region, sum). Great for testing without an API key.

### Run Tests

```powershell
pip install pytest pytest-cov
pytest tests/ -v
```

Or run a specific test:

```powershell
pytest tests/test_validator.py -v
```

---

## API Endpoints

### `POST /query`

Submit a natural language question.

**Request:**
```json
{
  "question": "What are total sales by region?",
  "user_id": "user_1",
  "role": "analyst"
}
```

**Response (Success):**
```json
{
  "question": "What are total sales by region?",
  "generated_sql": "SELECT region, SUM(amount) as total FROM sales GROUP BY region LIMIT 1000",
  "columns": ["region", "total"],
  "rows": [
    {"region": "US", "total": 2700},
    {"region": "EU", "total": 900}
  ],
  "explanation": "The sales are distributed across two regions...",
  "latency_ms": 234.5
}
```

**Response (Error):**
```json
{
  "error": "Generated SQL did not pass safety checks",
  "details": "Forbidden keyword detected: DELETE",
  "generated_sql": "DELETE FROM sales"
}
```

### `GET /health`

Check service status.

```json
{
  "status": "ok",
  "timestamp": 1705674000.5,
  "config": {
    "database_url": true,
    "gemini_api_key": true,
    "dev_fallback_mode": false
  },
  "services": {
    "database": true,
    "genai_client": true,
    "schema_cache": true
  },
  "features": {
    "rbac": true,
    "logging": true,
    "schema_cache": true
  }
}
```

### `GET /logs?limit=50`

Retrieve recent query logs (admin access).

```json
{
  "logs": [
    {
      "timestamp": "2026-01-19T16:30:00.123456",
      "user_id": "user_1",
      "question": "Total sales by region",
      "generated_sql": "SELECT region, SUM(amount) FROM sales GROUP BY region LIMIT 1000",
      "status": "success",
      "latency_ms": 234.5,
      "rows_returned": 2,
      "error_message": null
    }
  ],
  "count": 1
}
```

---

## Architecture

### Modules

| Module | Component | Purpose |
|--------|-----------|---------|
| `config.py` | Config | Environment & app settings |
| `schema.py` | SchemaMetadata | Database introspection & caching |
| `validator.py` | SQLValidator | SQL safety checks & normalization |
| `llm.py` | SQLGenerator | LLM calls for SQL generation |
| `explainer.py` | ResultExplainer | AI-generated result explanations |
| `executor.py` | QueryExecutor | Safe query execution |
| `rbac.py` | RBAC | Role-based access control |
| `logs.py` | QueryLogger | Audit & query logging |
| `app.py` | Flask | HTTP API & UI serving |

### Flow

```
User Question
    ↓
API (/query) → RBAC Check
    ↓
Schema Introspection → Filter by Role
    ↓
LLM Generate SQL
    ↓
Validator (Safety Checks)
    ↓
Executor (Run Query)
    ↓
Explainer (AI Summary)
    ↓
Logger (Audit Trail)
    ↓
Response (JSON)
```

---

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | (required) | PostgreSQL connection string |
| `GEMINI_API_KEY` | (required) | Google Gemini API key |
| `GENAI_MODEL_ID` | `gemini-1.5-flash` | LLM model ID |
| `LLM_TIMEOUT_S` | `10.0` | LLM request timeout (seconds) |
| `MAX_LIMIT` | `1000` | Max rows to return per query |
| `STATEMENT_TIMEOUT_MS` | `5000` | Database query timeout (ms) |
| `ENABLE_RBAC` | `true` | Enable role-based access |
| `ENABLE_LOGGING` | `true` | Log all queries |
| `ENABLE_SCHEMA_CACHE` | `true` | Cache schema (TTL 3600s) |
| `DEV_FALLBACK_MODE` | `false` | Use template SQL (no LLM) |

---

## Development

### Adding New Tables

1. Create the table in PostgreSQL
2. (Optional) Add role permissions in `rbac.py`
3. Restart the server—schema is auto-introspected

### Extending RBAC

Edit `rbac.py` > `ROLE_TABLE_PERMISSIONS`:

```python
ROLE_TABLE_PERMISSIONS = {
    "analyst": ["sales", "users", "orders"],
    "finance": ["sales", "invoices"],
    "admin": ["*"],
}
```

### Customizing Validation

Edit `validator.py`:

- Add forbidden keywords to `FORBIDDEN_KEYWORDS`
- Add patterns to `FORBIDDEN_PATTERNS`
- Adjust `MAX_LIMIT` in `config.py`

### Fallback SQL Templates

Edit `app.py` > `_dev_fallback_sql()` to add more templates for common questions.

---

## Production Deployment

### Use WSGI Server

Do NOT use Flask's development server in production:

```powershell
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

### Enable HTTPS

Use a reverse proxy (nginx, Traefik) to terminate TLS.

### Security Checklist

- [ ] Set `DEBUG=false` in config
- [ ] Use strong `GEMINI_API_KEY` (rotate regularly)
- [ ] Restrict `DATABASE_URL` credentials (use DB roles)
- [ ] Enable RBAC; audit logs regularly
- [ ] Rate-limit `/query` endpoint
- [ ] Use environment variables, never hardcode secrets
- [ ] Add authentication middleware (JWT, OAuth2)
- [ ] Monitor LLM cost (rate limit API calls)

---

## Troubleshooting

### "Database not configured" Error

Ensure `DATABASE_URL` is set and PostgreSQL is running:

```powershell
psql -U postgres -d talk_to_data -c "SELECT 1"
```

### "LLM client not configured" Error

Ensure `GEMINI_API_KEY` is set and valid:

```powershell
$env:GEMINI_API_KEY = "sk_..."
python app.py
```

### "Access to table denied" Error

Check user role and `ROLE_TABLE_PERMISSIONS` in `rbac.py`.

### Slow Query Execution

- Check `STATEMENT_TIMEOUT_MS` (increase if needed)
- Check database indexes
- Check LLM latency (usually 2–5s)

### Tests Fail

Ensure pytest is installed:

```powershell
pip install pytest pytest-cov
```

---

## License

MIT

---

## Support

For issues or questions, refer to the SRS/SDD documents or see the module docstrings for detailed API reference.


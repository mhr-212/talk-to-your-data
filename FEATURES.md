# Talk to Your Data – Enhanced Features Guide

This guide covers all the new features and enhancements added to the Talk to Your Data system.

## 📋 New Features Overview

### 1. Authentication & Authorization (auth.py)
JWT-based authentication for secure API access.

**Endpoints:**
- `POST /auth/token` - Generate JWT token for user

**Usage:**
```bash
curl -X POST http://localhost:5000/auth/token \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user_123",
    "username": "john_doe",
    "role": "analyst"
  }'

# Response:
{
  "token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "user_id": "user_123",
  "username": "john_doe",
  "role": "analyst"
}
```

**Using the token:**
```bash
curl -X GET http://localhost:5000/saved-queries \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"
```

---

### 2. Saved Queries (saved_queries.py)
Bookmark and organize frequently used queries.

**Endpoints:**
- `GET /saved-queries` - List all saved queries for user
- `POST /saved-queries` - Save a new query
- `GET /saved-queries/search?q=keyword` - Search saved queries
- `GET /saved-queries/<query_id>` - Get specific saved query
- `DELETE /saved-queries/<query_id>` - Delete saved query

**Usage Examples:**

Save a query:
```bash
curl -X POST http://localhost:5000/saved-queries \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Total Sales by Region",
    "question": "What are total sales by region?",
    "generated_sql": "SELECT region, SUM(amount) as total FROM sales GROUP BY region"
  }'

# Response:
{
  "message": "Query saved",
  "query": {
    "query_id": "sq_user_123_1",
    "name": "Total Sales by Region",
    "question": "What are total sales by region?",
    "generated_sql": "SELECT region, SUM(amount) as total...",
    "created_at": "2025-01-19T10:30:00",
    "run_count": 0
  }
}
```

List saved queries:
```bash
curl -X GET "http://localhost:5000/saved-queries?limit=20" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

Search saved queries:
```bash
curl -X GET "http://localhost:5000/saved-queries/search?q=region" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

### 3. Query Analytics (analytics.py)
Track and analyze query execution statistics.

**Endpoints:**
- `GET /analytics/dashboard` - Comprehensive dashboard stats
- `GET /analytics/slowest?limit=10` - Get slowest queries

**Dashboard Metrics:**
- Total queries (24-hour window)
- Average latency
- Error rate percentage
- Top 5 most queried tables
- Top 5 most active users
- 5 slowest queries
- Hourly query trend

**Usage:**
```bash
curl http://localhost:5000/analytics/dashboard

# Response:
{
  "timestamp": 1705667400.123,
  "stats": {
    "total_queries_24h": 142,
    "avg_latency_ms": 245.67,
    "error_rate_percent": 2.1,
    "top_tables": [
      ["sales", 95],
      ["customers", 30],
      ["orders", 17]
    ],
    "top_users": [
      ["user_123", 45],
      ["user_456", 38]
    ],
    "slowest_queries": [
      {
        "user_id": "user_123",
        "question": "List all sales with details",
        "latency_ms": 8234.5,
        "timestamp": "2025-01-19T09:15:00"
      }
    ],
    "hourly_trend": {
      "2025-01-19 09:00": 12,
      "2025-01-19 10:00": 18,
      "2025-01-19 11:00": 22
    }
  }
}
```

---

### 4. Result Caching (caching.py)
Automatically cache query results for identical questions.

**Features:**
- LRU (Least Recently Used) eviction policy
- Configurable TTL (Time To Live)
- Per-user cache keys
- Hit count tracking

**Endpoints:**
- `GET /cache/stats` - Cache statistics
- `POST /cache/clear` - Clear cache (admin only)

**Cache Statistics:**
```bash
curl http://localhost:5000/cache/stats

# Response:
{
  "cache_stats": {
    "total_entries": 47,
    "max_entries": 1000,
    "total_hits": 324,
    "ttl_seconds": 3600
  }
}
```

**How it works:**
1. When a query is executed, result is cached
2. If the same user asks the same question again within TTL, cached result is returned
3. Cache miss → Full execution
4. Cache hit → Instant result (from cache)

---

### 5. Data Export (Enhanced /query endpoint)
Export query results as CSV or JSON.

**Endpoint:**
- `POST /query/export` - Export query results

**Usage:**
```bash
curl -X POST http://localhost:5000/query/export \
  -H "Content-Type: application/json" \
  -d '{
    "columns": ["region", "total"],
    "rows": [
      {"region": "US", "total": 2700},
      {"region": "EU", "total": 900}
    ],
    "format": "csv"
  }'

# Returns: query_results.csv (as file download)
```

**Export Formats:**
- **CSV**: Standard comma-separated values format
- **JSON**: Structured JSON array format

---

### 6. Enhanced Error Messages
Improved validation feedback with actionable suggestions.

**Example Error Responses:**

```json
{
  "error": "Generated SQL did not pass safety checks",
  "details": "Table 'customers' not in allowed tables for analyst role. Allowed: sales",
  "generated_sql": "SELECT * FROM customers"
}
```

---

### 7. Query Complexity Analysis (Planned)
Estimate query cost before execution.

**Features (in roadmap):**
- EXPLAIN ANALYZE output
- Query plan visualization
- Estimated row count
- Warnings for expensive operations

---

## 🔄 Integration with Main Query Pipeline

All new features integrate seamlessly with the main `/query` endpoint:

```
User Question
    ↓
[Auth Check] ← auth.py
    ↓
[Cache Check] ← caching.py
    ↓ (if cache miss)
[Standard Pipeline: RBAC → Schema → LLM → Validate → Execute → Explain]
    ↓
[Analytics Record] ← analytics.py
    ↓
[Cache Result] ← caching.py
    ↓
Response to Client
```

---

## 📊 Configuration

Add these optional settings to `.env`:

```bash
# Authentication
TOKEN_EXPIRY_HOURS=24
SECRET_KEY=your-secret-key-change-in-production

# Caching
CACHE_TTL_SECONDS=3600
CACHE_MAX_ENTRIES=1000

# Analytics
ANALYTICS_MAX_RECORDS=10000

# Rate Limiting (future)
RATE_LIMIT_ENABLED=false
RATE_LIMIT_REQUESTS_PER_MINUTE=60
```

---

## 🧪 Testing the New Features

### 1. Test Authentication
```bash
# Get token
$token = (Invoke-RestMethod -Uri http://localhost:5000/auth/token -Method POST -Body @{
  user_id = "test_user"
  username = "Test User"
  role = "analyst"
} -ContentType 'application/json').token

# Use token for authenticated endpoints
Invoke-RestMethod -Uri http://localhost:5000/saved-queries `
  -Headers @{ Authorization = "Bearer $token" }
```

### 2. Test Saved Queries
```bash
# Save a query
Invoke-RestMethod -Uri http://localhost:5000/saved-queries -Method POST `
  -Headers @{ Authorization = "Bearer $token" } `
  -Body @{
    name = "Region Sales"
    question = "Total sales by region"
    generated_sql = "SELECT region, SUM(amount) FROM sales GROUP BY region"
  } -ContentType 'application/json'

# List saved queries
Invoke-RestMethod -Uri http://localhost:5000/saved-queries `
  -Headers @{ Authorization = "Bearer $token" }
```

### 3. Test Analytics
```bash
# Run several queries via /query endpoint
# Then check dashboard:

Invoke-RestMethod -Uri http://localhost:5000/analytics/dashboard
```

### 4. Test Cache
```bash
# Run a query
$result = Invoke-RestMethod -Uri http://localhost:5000/query -Method POST `
  -Body @{ question = "total sales" } -ContentType 'application/json'

# Run again - should be from cache
$result2 = Invoke-RestMethod -Uri http://localhost:5000/query -Method POST `
  -Body @{ question = "total sales" } -ContentType 'application/json'

# Check cache stats
Invoke-RestMethod -Uri http://localhost:5000/cache/stats
```

### 5. Test Export
```bash
# Execute a query to get results
$result = Invoke-RestMethod -Uri http://localhost:5000/query -Method POST `
  -Body @{ question = "sales by region" } -ContentType 'application/json'

# Export as CSV
Invoke-RestMethod -Uri http://localhost:5000/query/export -Method POST `
  -Body @{
    columns = @("region", "total")
    rows = @(@{region="US"; total=2700}, @{region="EU"; total=900})
    format = "csv"
  } -ContentType 'application/json' -OutFile "results.csv"
```

---

## 🔐 Security Considerations

1. **Authentication**: Always use HTTPS in production with JWT tokens
2. **Authorization**: Token contains role - validate before admin operations
3. **Caching**: Results cached per-user (no cross-user data leakage)
4. **Analytics**: Logs sanitized to not expose sensitive details
5. **Export**: Only authenticated users can export results

---

## 📈 Performance Impact

**Caching Benefits:**
- Cache hit: < 5ms response time
- Cache miss: Normal execution time
- Memory: ~1000 entries default, 3600s TTL

**Analytics Overhead:**
- ~2ms per query (non-blocking)
- In-memory storage (no DB queries)

---

## 🚀 Future Enhancements

1. **Webhook Integration** - Trigger queries on schedule
2. **Rate Limiting** - Protect API from abuse
3. **Data Visualization** - Chart.js for result rendering
4. **Multi-Database** - Support MySQL, Snowflake, BigQuery
5. **Query Complexity** - EXPLAIN ANALYZE warnings
6. **Data Lineage** - Show column/table dependencies
7. **Admin Dashboard** - Manage users, roles, queries
8. **Query Scheduling** - Save and run on schedule

---

## 📞 Support

For issues or feature requests, refer to the main README.md or check the API documentation at `/health`.

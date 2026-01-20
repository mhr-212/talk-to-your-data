"""Analytics module - query statistics and insights."""
from datetime import datetime, timedelta
from typing import Dict, List
from collections import defaultdict
import time


class QueryAnalytics:
    """Track and analyze query statistics."""
    
    def __init__(self, max_records: int = 10000):
        self.max_records = max_records
        self.queries: List[Dict] = []
    
    def record(self, user_id: str, question: str, generated_sql: str, 
               latency_ms: float, rows_returned: int, error: str = None):
        """Record a query execution."""
        record = {
            "user_id": user_id,
            "question": question,
            "sql": generated_sql,
            "latency_ms": latency_ms,
            "rows_returned": rows_returned,
            "error": error,
            "timestamp": datetime.utcnow(),
        }
        self.queries.append(record)
        
        # Keep memory bounded
        if len(self.queries) > self.max_records:
            self.queries = self.queries[-self.max_records:]
    
    def get_total_queries(self, hours: int = 24) -> int:
        """Get total queries in last N hours."""
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        return sum(1 for q in self.queries if q["timestamp"] >= cutoff)
    
    def get_avg_latency(self, hours: int = 24) -> float:
        """Get average query latency."""
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        queries = [q for q in self.queries if q["timestamp"] >= cutoff and not q["error"]]
        if not queries:
            return 0.0
        return sum(q["latency_ms"] for q in queries) / len(queries)
    
    def get_error_rate(self, hours: int = 24) -> float:
        """Get error rate percentage."""
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        queries = [q for q in self.queries if q["timestamp"] >= cutoff]
        if not queries:
            return 0.0
        errors = sum(1 for q in queries if q["error"])
        return (errors / len(queries)) * 100
    
    def get_top_tables(self, limit: int = 10) -> List[tuple]:
        """Get most frequently queried tables."""
        table_counts = defaultdict(int)
        for q in self.queries:
            sql = q["sql"].upper()
            if "FROM" in sql:
                # Simple extraction: FROM table_name
                parts = sql.split("FROM")
                if len(parts) > 1:
                    table_name = parts[1].split()[0].strip()
                    table_counts[table_name] += 1
        
        sorted_tables = sorted(table_counts.items(), key=lambda x: x[1], reverse=True)
        return sorted_tables[:limit]
    
    def get_top_users(self, limit: int = 10) -> List[tuple]:
        """Get most active users."""
        user_counts = defaultdict(int)
        for q in self.queries:
            user_counts[q["user_id"]] += 1
        
        sorted_users = sorted(user_counts.items(), key=lambda x: x[1], reverse=True)
        return sorted_users[:limit]
    
    def get_slowest_queries(self, limit: int = 10) -> List[Dict]:
        """Get slowest queries."""
        sorted_queries = sorted(self.queries, key=lambda x: x["latency_ms"], reverse=True)
        result = []
        for q in sorted_queries[:limit]:
            result.append({
                "user_id": q["user_id"],
                "question": q["question"],
                "latency_ms": q["latency_ms"],
                "timestamp": q["timestamp"].isoformat(),
            })
        return result
    
    def get_hourly_trend(self, hours: int = 24) -> Dict[str, int]:
        """Get queries per hour for trend analysis."""
        trend = defaultdict(int)
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        
        for q in self.queries:
            if q["timestamp"] >= cutoff:
                hour = q["timestamp"].strftime("%Y-%m-%d %H:00")
                trend[hour] += 1
        
        return dict(sorted(trend.items()))
    
    def get_dashboard_stats(self) -> Dict:
        """Get comprehensive dashboard statistics."""
        return {
            "total_queries_24h": self.get_total_queries(24),
            "avg_latency_ms": round(self.get_avg_latency(24), 2),
            "error_rate_percent": round(self.get_error_rate(24), 2),
            "top_tables": self.get_top_tables(5),
            "top_users": self.get_top_users(5),
            "slowest_queries": self.get_slowest_queries(5),
            "hourly_trend": self.get_hourly_trend(24),
        }


# Global instance
_analytics = QueryAnalytics()


def record_query(user_id: str, question: str, sql: str, latency_ms: float, 
                 rows_returned: int, error: str = None):
    """Record a query in analytics."""
    _analytics.record(user_id, question, sql, latency_ms, rows_returned, error)


def get_analytics() -> QueryAnalytics:
    """Get the global analytics instance."""
    return _analytics

"""Query logging and audit module."""
import json
import time
from datetime import datetime
from typing import Optional


class QueryLogger:
    """Simple in-memory query logger for audit trail."""
    
    def __init__(self, max_entries: int = 1000):
        self.max_entries = max_entries
        self.logs: list = []
    
    def log_query(
        self,
        user_id: str,
        question: str,
        generated_sql: str,
        status: str,
        latency_ms: float,
        rows_returned: int = 0,
        error_message: Optional[str] = None,
    ) -> None:
        """
        Log a query execution.
        
        Args:
            user_id: User who ran the query
            question: Original natural language question
            generated_sql: Generated SQL query (may be redacted in production)
            status: "success" or "error"
            latency_ms: Execution latency in milliseconds
            rows_returned: Number of rows returned
            error_message: Error details (if status="error")
        """
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "user_id": user_id,
            "question": question,
            "generated_sql": generated_sql,
            "status": status,
            "latency_ms": latency_ms,
            "rows_returned": rows_returned,
            "error_message": error_message,
        }
        
        self.logs.append(log_entry)
        
        # Keep only recent entries
        if len(self.logs) > self.max_entries:
            self.logs = self.logs[-self.max_entries:]
    
    def get_recent_logs(self, limit: int = 100) -> list:
        """Retrieve the most recent log entries."""
        return self.logs[-limit:]
    
    def clear_logs(self) -> None:
        """Clear all logs."""
        self.logs.clear()


# Global logger instance
_logger = QueryLogger()


def log_query(**kwargs) -> None:
    """Log a query to the global logger."""
    _logger.log_query(**kwargs)


def get_logs(limit: int = 100) -> list:
    """Get recent logs."""
    return _logger.get_recent_logs(limit)


def clear_logs() -> None:
    """Clear all logs."""
    _logger.clear_logs()

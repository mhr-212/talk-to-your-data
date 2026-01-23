"""Database execution module."""
from typing import List, Dict, Any
from sqlalchemy import create_engine, text, event, Engine


def init_engine(database_url: str, statement_timeout_ms: int = 5000, readonly: bool = True) -> Engine:
    """
    Initialize a SQLAlchemy engine with read-only session and statement timeout.
    
    Args:
        database_url: SQLAlchemy database URL
        statement_timeout_ms: PostgreSQL statement timeout in milliseconds
        readonly: Whether to enforce read-only transactions
    
    Returns:
        Configured SQLAlchemy Engine
    """
    # Heroku compatibility: Fix "postgres://" -> "postgresql://"
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql://", 1)
        
    # SSL configuration for Heroku
    connect_args = {}
    if "localhost" not in database_url and "127.0.0.1" not in database_url:
        connect_args["sslmode"] = "require"

    engine = create_engine(database_url, connect_args=connect_args, pool_pre_ping=True)
    
    @event.listens_for(engine, "connect")
    def set_session_settings(dbapi_connection, connection_record):
        """Set read-only and timeout on each connection."""
        cur = dbapi_connection.cursor()
        try:
            if readonly:
                cur.execute("SET SESSION CHARACTERISTICS AS TRANSACTION READ ONLY;")
            cur.execute(f"SET statement_timeout TO {statement_timeout_ms};")
        except Exception:
            # MySQL, SQLite, etc. may not support these settings
            pass
        finally:
            cur.close()
    
    return engine


def execute_query(engine: Engine, sql: str) -> tuple[List[str], List[Dict[str, Any]]]:
    """
    Execute a SELECT query on the database.
    
    Args:
        engine: SQLAlchemy Engine
        sql: SQL query string
    
    Returns:
        Tuple of (column_names, rows_as_dicts)
    
    Raises:
        Exception: If query execution fails
    """
    with engine.connect() as conn:
        result = conn.execute(text(sql))
        columns = list(result.keys())
        raw_rows = result.fetchall()
        
        # Convert rows to list of dicts for JSON serialization
        rows = [dict(zip(columns, row)) for row in raw_rows]
    
    return columns, rows

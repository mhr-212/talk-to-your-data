"""Schema introspection and formatting module."""
from typing import Dict, List, Optional
from sqlalchemy import inspect, Engine
import time


class SchemaCache:
    """In-memory cache for database schema with TTL."""
    
    def __init__(self, ttl_seconds: int = 3600):
        self.ttl_seconds = ttl_seconds
        self.cache: Dict[str, tuple] = {}  # {key: (data, timestamp)}
    
    def get(self, key: str) -> Optional[dict]:
        """Get cached value if not expired."""
        if key in self.cache:
            data, timestamp = self.cache[key]
            if time.time() - timestamp < self.ttl_seconds:
                return data
            del self.cache[key]
        return None
    
    def set(self, key: str, value: dict) -> None:
        """Cache a value with current timestamp."""
        self.cache[key] = (value, time.time())
    
    def clear(self) -> None:
        """Clear all cached entries."""
        self.cache.clear()


def introspect_schema(engine: Engine, cache: Optional[SchemaCache] = None) -> Dict[str, List[str]]:
    """
    Introspect the database schema and return a dict of {table: [columns]}.
    Uses cache if provided and available.
    """
    cache_key = "schema_metadata"
    
    if cache:
        cached = cache.get(cache_key)
        if cached:
            return cached
    
    schema_dict = {}
    inspector = inspect(engine)
    
    for table_name in inspector.get_table_names():
        columns = [col["name"] for col in inspector.get_columns(table_name)]
        schema_dict[table_name] = columns
    
    if cache:
        cache.set(cache_key, schema_dict)
    
    return schema_dict


def format_schema_for_prompt(schema_dict: Dict[str, List[str]]) -> str:
    """
    Format schema dict as a readable string for LLM prompts.
    Example output:
    
    sales(id, amount, region, created_at)
    users(user_id, name, email)
    """
    lines = []
    for table, columns in sorted(schema_dict.items()):
        col_list = ", ".join(columns)
        lines.append(f"{table}({col_list})")
    return "\n".join(lines)


def get_allowed_tables(schema_dict: Dict[str, List[str]], allowed_list: List[str]) -> Dict[str, List[str]]:
    """
    Filter schema dict to only include allowed tables.
    """
    return {
        table: cols
        for table, cols in schema_dict.items()
        if table.lower() in {t.lower() for t in allowed_list}
    }

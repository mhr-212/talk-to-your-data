"""Query Caching module - cache identical queries for faster results."""
import hashlib
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple, List


class CachedResult:
    """Cached query result."""
    
    def __init__(self, columns: List[str], rows: List[Dict], explanation: str):
        self.columns = columns
        self.rows = rows
        self.explanation = explanation
        self.created_at = datetime.utcnow()
        self.hit_count = 0
    
    def is_expired(self, ttl_seconds: int = 3600) -> bool:
        """Check if cache entry is expired."""
        age = (datetime.utcnow() - self.created_at).total_seconds()
        return age > ttl_seconds


class QueryCache:
    """LRU-style cache for query results."""
    
    def __init__(self, max_entries: int = 1000, ttl_seconds: int = 3600):
        self.max_entries = max_entries
        self.ttl_seconds = ttl_seconds
        self.cache: Dict[str, CachedResult] = {}
        self.access_order: List[str] = []
    
    def _make_key(self, user_id: str, question: str) -> str:
        """Generate cache key from user ID and question."""
        # Use question text as key (same question = same result)
        content = f"{user_id}:{question}"
        return hashlib.md5(content.encode()).hexdigest()
    
    def get(self, user_id: str, question: str) -> Optional[Tuple[List[str], List[Dict], str]]:
        """Get cached result if available and not expired."""
        key = self._make_key(user_id, question)
        
        if key not in self.cache:
            return None
        
        cached = self.cache[key]
        
        # Check expiration
        if cached.is_expired(self.ttl_seconds):
            del self.cache[key]
            self.access_order.remove(key) if key in self.access_order else None
            return None
        
        # Update access order
        if key in self.access_order:
            self.access_order.remove(key)
        self.access_order.append(key)
        
        # Increment hit count
        cached.hit_count += 1
        
        return (cached.columns, cached.rows, cached.explanation)
    
    def set(self, user_id: str, question: str, columns: List[str], 
            rows: List[Dict], explanation: str):
        """Cache a query result."""
        key = self._make_key(user_id, question)
        
        # If exists, update
        if key in self.cache:
            self.access_order.remove(key)
            self.cache[key] = CachedResult(columns, rows, explanation)
        else:
            # Check if we need to evict
            if len(self.cache) >= self.max_entries:
                # Remove least recently used
                if self.access_order:
                    lru_key = self.access_order.pop(0)
                    del self.cache[lru_key]
            
            self.cache[key] = CachedResult(columns, rows, explanation)
        
        # Track access order
        self.access_order.append(key)
    
    def clear(self):
        """Clear all cache."""
        self.cache.clear()
        self.access_order.clear()
    
    def get_stats(self) -> Dict:
        """Get cache statistics."""
        total_hits = sum(c.hit_count for c in self.cache.values())
        return {
            "total_entries": len(self.cache),
            "max_entries": self.max_entries,
            "total_hits": total_hits,
            "ttl_seconds": self.ttl_seconds,
        }


# Global instance
_cache = QueryCache()


def get_cached(user_id: str, question: str) -> Optional[Tuple]:
    """Get cached result if available."""
    return _cache.get(user_id, question)


def set_cache(user_id: str, question: str, columns: List[str], 
              rows: List[Dict], explanation: str):
    """Cache a query result."""
    _cache.set(user_id, question, columns, rows, explanation)


def get_cache() -> QueryCache:
    """Get the global cache instance."""
    return _cache

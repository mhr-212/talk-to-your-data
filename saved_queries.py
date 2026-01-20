"""Saved Queries module - bookmark and persist frequently used queries."""
import json
from datetime import datetime
from typing import List, Dict, Optional


class SavedQuery:
    """Represents a saved query."""
    
    def __init__(self, query_id: str, user_id: str, name: str, question: str, 
                 generated_sql: str, created_at: datetime = None):
        self.query_id = query_id
        self.user_id = user_id
        self.name = name
        self.question = question
        self.generated_sql = generated_sql
        self.created_at = created_at or datetime.utcnow()
        self.run_count = 0
    
    def to_dict(self):
        return {
            "query_id": self.query_id,
            "user_id": self.user_id,
            "name": self.name,
            "question": self.question,
            "generated_sql": self.generated_sql,
            "created_at": self.created_at.isoformat(),
            "run_count": self.run_count,
        }


class SavedQueryStore:
    """In-memory store for saved queries (can be upgraded to database)."""
    
    def __init__(self, max_queries: int = 500):
        self.queries: Dict[str, SavedQuery] = {}
        self.max_queries = max_queries
        self._counter = 0
    
    def save(self, user_id: str, name: str, question: str, generated_sql: str) -> SavedQuery:
        """Save a new query."""
        if len(self.queries) >= self.max_queries:
            raise ValueError(f"Max saved queries ({self.max_queries}) reached")
        
        self._counter += 1
        query_id = f"sq_{user_id}_{self._counter}"
        
        saved_query = SavedQuery(query_id, user_id, name, question, generated_sql)
        self.queries[query_id] = saved_query
        return saved_query
    
    def get(self, query_id: str) -> Optional[SavedQuery]:
        """Get a saved query by ID."""
        return self.queries.get(query_id)
    
    def list_user_queries(self, user_id: str, limit: int = 50) -> List[SavedQuery]:
        """List all saved queries for a user."""
        user_queries = [q for q in self.queries.values() if q.user_id == user_id]
        return sorted(user_queries, key=lambda q: q.created_at, reverse=True)[:limit]
    
    def delete(self, query_id: str) -> bool:
        """Delete a saved query."""
        if query_id in self.queries:
            del self.queries[query_id]
            return True
        return False
    
    def increment_run_count(self, query_id: str):
        """Increment run count for a query."""
        if query_id in self.queries:
            self.queries[query_id].run_count += 1
    
    def search(self, user_id: str, keyword: str) -> List[SavedQuery]:
        """Search saved queries by name or question."""
        keyword = keyword.lower()
        user_queries = [q for q in self.queries.values() if q.user_id == user_id]
        return [q for q in user_queries if keyword in q.name.lower() or keyword in q.question.lower()]
    
    def get_stats(self, user_id: str) -> Dict:
        """Get statistics for user's saved queries."""
        user_queries = [q for q in self.queries.values() if q.user_id == user_id]
        return {
            "total_saved": len(user_queries),
            "most_used": sorted(user_queries, key=lambda q: q.run_count, reverse=True)[:5] if user_queries else [],
            "recent": sorted(user_queries, key=lambda q: q.created_at, reverse=True)[:5] if user_queries else [],
        }


# Global instance
_saved_query_store = SavedQueryStore()


def get_saved_query_store() -> SavedQueryStore:
    """Get the global saved query store."""
    return _saved_query_store

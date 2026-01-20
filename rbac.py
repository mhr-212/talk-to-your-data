"""Role-based access control (RBAC) module."""
from typing import List, Dict, Optional
from dataclasses import dataclass


@dataclass
class User:
    """Represents an authenticated user with a role."""
    user_id: str
    username: str
    role: str = "analyst"  # Default role
    allowed_tables: List[str] = None
    
    def __post_init__(self):
        if self.allowed_tables is None:
            # Default: all tables allowed
            self.allowed_tables = []


# Simple in-memory role-to-table mapping
ROLE_TABLE_PERMISSIONS = {
    "analyst": ["sales", "users", "orders"],
    "admin": ["*"],  # Access to all tables
    "readonly": ["sales", "users"],  # Limited read-only user
}


def get_user_from_request(request_context: Optional[Dict] = None) -> User:
    """
    Extract user information from request context.
    For now, returns a default analyst user.
    In production, implement JWT/session-based extraction.
    """
    # Placeholder: check request headers for user_id, role, etc.
    # For MVP, use a default user
    user_id = "user_1"
    username = "analyst"
    role = "analyst"
    
    if request_context:
        user_id = request_context.get("user_id", user_id)
        username = request_context.get("username", username)
        role = request_context.get("role", role)
    
    allowed_tables = ROLE_TABLE_PERMISSIONS.get(role, [])
    return User(user_id=user_id, username=username, role=role, allowed_tables=allowed_tables)


def get_allowed_resources(user: User) -> List[str]:
    """
    Return list of tables the user is allowed to access.
    If user role is "admin", return ["*"] (all tables).
    """
    if not user.allowed_tables:
        return ROLE_TABLE_PERMISSIONS.get(user.role, [])
    return user.allowed_tables


def authorize_tables(user: User, table_names: List[str]) -> None:
    """
    Verify that all requested tables are accessible by the user.
    Raises PermissionError if any table is not allowed.
    """
    allowed = get_allowed_resources(user)
    
    # Admin has access to everything
    if allowed == ["*"]:
        return
    
    allowed_lower = {t.lower() for t in allowed}
    
    for table in table_names:
        if table.lower() not in allowed_lower:
            raise PermissionError(f"User '{user.username}' is not authorized to access table '{table}'")

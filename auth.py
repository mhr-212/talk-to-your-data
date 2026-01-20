"""Authentication module for Talk to Your Data."""
import os
import jwt
from datetime import datetime, timedelta
from functools import wraps
from flask import request, jsonify, current_app


SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
TOKEN_EXPIRY_HOURS = int(os.getenv("TOKEN_EXPIRY_HOURS", "24"))


def generate_token(user_id: str, username: str, role: str) -> str:
    """Generate JWT token for user."""
    payload = {
        "user_id": user_id,
        "username": username,
        "role": role,
        "iat": datetime.utcnow(),
        "exp": datetime.utcnow() + timedelta(hours=TOKEN_EXPIRY_HOURS),
    }
    token = jwt.encode(payload, SECRET_KEY, algorithm="HS256")
    return token


def verify_token(token: str) -> dict:
    """Verify and decode JWT token."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        return payload
    except jwt.ExpiredSignatureError:
        raise ValueError("Token has expired")
    except jwt.InvalidTokenError:
        raise ValueError("Invalid token")


def get_auth_from_header():
    """Extract user info from Authorization header or return default."""
    auth_header = request.headers.get("Authorization", "")
    
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]
        try:
            payload = verify_token(token)
            return {
                "user_id": payload.get("user_id"),
                "username": payload.get("username"),
                "role": payload.get("role"),
            }
        except ValueError:
            return None
    
    # Dev mode: allow header-based user info
    user_id = request.headers.get("X-User-ID", "user123")
    username = request.headers.get("X-Username", "demo_user")
    role = request.headers.get("X-Role", "analyst")
    
    return {
        "user_id": user_id,
        "username": username,
        "role": role,
    }


def require_auth(f):
    """Decorator to require authentication."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user = get_auth_from_header()
        if not user:
            return jsonify({"error": "Unauthorized"}), 401
        return f(*args, **kwargs)
    return decorated_function


def require_role(*allowed_roles):
    """Decorator to require specific roles."""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            user = get_auth_from_header()
            if not user:
                return jsonify({"error": "Unauthorized"}), 401
            if user.get("role") not in allowed_roles:
                return jsonify({"error": "Forbidden: insufficient permissions"}), 403
            return f(*args, **kwargs)
        return decorated_function
    return decorator

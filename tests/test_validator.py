"""Unit tests for the validator module."""
import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from validator import (
    sanitize_and_validate_sql,
    extract_table_references,
    has_limit_clause,
    inject_limit,
)


def test_basic_select_allowed():
    """Test that a simple SELECT passes validation."""
    sql = "SELECT * FROM sales"
    result = sanitize_and_validate_sql(sql, allowed_tables=["sales"])
    assert "SELECT * FROM sales" in result
    assert "LIMIT" in result


def test_select_with_limit_not_duplicated():
    """Test that LIMIT is not duplicated if already present."""
    sql = "SELECT * FROM sales LIMIT 10"
    result = sanitize_and_validate_sql(sql, allowed_tables=["sales"])
    assert result.count("LIMIT") == 1


def test_forbidden_keyword_insert():
    """Test that INSERT is blocked."""
    sql = "INSERT INTO sales (amount) VALUES (100)"
    with pytest.raises(ValueError, match="Forbidden keyword"):
        sanitize_and_validate_sql(sql, allowed_tables=["sales"])


def test_forbidden_keyword_update():
    """Test that UPDATE is blocked."""
    sql = "UPDATE sales SET amount = 200 WHERE id = 1"
    with pytest.raises(ValueError, match="Forbidden keyword"):
        sanitize_and_validate_sql(sql, allowed_tables=["sales"])


def test_forbidden_keyword_delete():
    """Test that DELETE is blocked."""
    sql = "DELETE FROM sales WHERE id = 1"
    with pytest.raises(ValueError, match="Forbidden keyword"):
        sanitize_and_validate_sql(sql, allowed_tables=["sales"])


def test_semicolon_not_allowed():
    """Test that semicolons are blocked."""
    sql = "SELECT * FROM sales; DROP TABLE users;"
    with pytest.raises(ValueError):
        sanitize_and_validate_sql(sql, allowed_tables=["sales", "users"])


def test_table_not_in_allowlist():
    """Test that access to non-allowed tables is blocked."""
    sql = "SELECT * FROM secret_data"
    with pytest.raises(ValueError, match="not permitted"):
        sanitize_and_validate_sql(sql, allowed_tables=["sales"])


def test_multiple_tables_mixed_allowed():
    """Test that only allowed tables can be joined."""
    sql = "SELECT s.amount, u.name FROM sales s JOIN users u ON s.user_id = u.id"
    result = sanitize_and_validate_sql(sql, allowed_tables=["sales", "users"])
    assert "LIMIT" in result


def test_multiple_tables_one_not_allowed():
    """Test that one disallowed table in JOIN fails."""
    sql = "SELECT s.amount FROM sales s JOIN forbidden f ON s.id = f.id"
    with pytest.raises(ValueError, match="not permitted"):
        sanitize_and_validate_sql(sql, allowed_tables=["sales"])


def test_extract_table_references():
    """Test table reference extraction from SQL."""
    sql = "SELECT * FROM sales WHERE id = 1"
    tables = extract_table_references(sql)
    assert "sales" in tables


def test_extract_table_references_multiple():
    """Test extraction of multiple table references."""
    sql = "SELECT * FROM sales JOIN users ON sales.user_id = users.id"
    tables = extract_table_references(sql)
    assert "sales" in tables
    assert "users" in tables


def test_has_limit_clause():
    """Test LIMIT clause detection."""
    assert has_limit_clause("SELECT * FROM sales LIMIT 100")
    assert not has_limit_clause("SELECT * FROM sales")


def test_inject_limit():
    """Test LIMIT injection."""
    sql = "SELECT * FROM sales"
    result = inject_limit(sql, 500)
    assert "LIMIT 500" in result


def test_inline_comment_blocked():
    """Test that inline comments are blocked."""
    sql = "SELECT * FROM sales -- this is a comment"
    with pytest.raises(ValueError):
        sanitize_and_validate_sql(sql, allowed_tables=["sales"])


def test_block_comment_blocked():
    """Test that block comments are blocked."""
    sql = "SELECT * FROM sales /* dangerous */"
    with pytest.raises(ValueError):
        sanitize_and_validate_sql(sql, allowed_tables=["sales"])


def test_union_blocked():
    """Test that UNION is blocked."""
    sql = "SELECT * FROM sales UNION SELECT * FROM users"
    with pytest.raises(ValueError):
        sanitize_and_validate_sql(sql, allowed_tables=["sales", "users"])


def test_max_limit_enforced():
    """Test that MAX_LIMIT is respected."""
    sql = "SELECT * FROM sales"
    result = sanitize_and_validate_sql(sql, allowed_tables=["sales"], max_limit=50)
    assert "LIMIT 50" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

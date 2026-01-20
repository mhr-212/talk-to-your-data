"""SQL validation and sanitization module."""
import re
from typing import List


FORBIDDEN_KEYWORDS = {
    "INSERT", "UPDATE", "DELETE", "DROP",
    "ALTER", "TRUNCATE", "CREATE", "GRANT", "REVOKE",
    "COPY", "VACUUM", "ANALYZE", "LOCK",
}

FORBIDDEN_PATTERNS = [
    (r";", "Multi-statement queries (semicolon) are not allowed"),
    (r"--", "Inline comments are not allowed"),
    (r"/\*", "Block comments are not allowed"),
    (r"\bUNION\b", "UNION queries are not allowed"),
    (r"\bINTERSECT\b", "INTERSECT queries are not allowed"),
    (r"\bEXCEPT\b", "EXCEPT queries are not allowed"),
    (r"\bWITH\s*\(", "Complex CTEs are not allowed"),
    (r"\bINTO\b", "SELECT INTO is not allowed"),
    (r"\bFOR\s+UPDATE\b", "FOR UPDATE clauses are not allowed"),
    (r"\bINFORMATION_SCHEMA\b", "System schema access is not allowed"),
    (r"\bpg_\w+\b", "PostgreSQL system objects are not allowed"),
]


def ensure_single_statement(sql: str) -> None:
    """Verify SQL contains only one statement."""
    # Count semicolons (naive but effective for basic cases)
    if sql.count(";") > 1:
        raise ValueError("Only single SQL statements are allowed")


def ensure_select_only(sql: str) -> None:
    """Verify SQL is a SELECT statement."""
    s_upper = sql.upper().strip()
    if not s_upper.startswith("SELECT"):
        raise ValueError(
            "Only SELECT statements are allowed. "
            "This system is read-only and cannot modify data. "
            "Try rephrasing your question to retrieve data instead of changing it."
        )


def check_forbidden_keywords(sql: str) -> None:
    """Check for forbidden SQL keywords."""
    s_upper = sql.upper()
    for kw in FORBIDDEN_KEYWORDS:
        if re.search(rf"\b{kw}\b", s_upper):
            raise ValueError(
                f"Forbidden keyword detected: {kw}. "
                f"This system is read-only and only supports SELECT queries. "
                f"Please rephrase your question to retrieve information instead of modifying data."
            )


def check_forbidden_patterns(sql: str) -> None:
    """Check for forbidden SQL patterns."""
    s_upper = sql.upper()
    for pattern, reason in FORBIDDEN_PATTERNS:
        if re.search(pattern, s_upper):
            raise ValueError(f"Unsafe SQL pattern: {reason}")


def extract_table_references(sql: str) -> List[str]:
    """
    Extract table names from FROM and JOIN clauses.
    Returns a list of plain table names (lowercased).
    """
    s_upper = sql.upper()
    # Simple regex to find table names after FROM/JOIN
    matches = re.findall(
        r"\b(?:FROM|JOIN|INNER\s+JOIN|LEFT\s+JOIN|RIGHT\s+JOIN|FULL\s+JOIN)\s+([a-zA-Z0-9_\.]+)",
        s_upper
    )
    # Strip schema prefix if present
    plain_names = []
    for match in matches:
        plain = match.split(".")[-1]
        plain_names.append(plain.lower())
    return list(set(plain_names))  # Deduplicate


def has_limit_clause(sql: str) -> bool:
    """Check if SQL includes a LIMIT clause."""
    return bool(re.search(r"\bLIMIT\s+\d+", sql.upper()))


def inject_limit(sql: str, limit: int) -> str:
    """Append LIMIT clause if not present."""
    if not has_limit_clause(sql):
        return f"{sql.rstrip(';')} LIMIT {limit}"
    return sql


def sanitize_and_validate_sql(
    sql: str,
    allowed_tables: List[str],
    max_limit: int = 1000,
) -> str:
    """
    Validate and sanitize SQL query.
    
    Returns the sanitized SQL (with LIMIT injected if needed).
    Raises ValueError with clear error message if validation fails.
    """
    s = sql.strip()
    
    # Core checks
    try:
        ensure_single_statement(s)
        ensure_select_only(s)
        check_forbidden_keywords(s)
        check_forbidden_patterns(s)
    except ValueError:
        raise
    
    # Table allowlist enforcement
    table_refs = extract_table_references(s)
    allowed_lower = {t.lower() for t in allowed_tables}
    
    for table in table_refs:
        if table not in allowed_lower:
            available_tables = ", ".join(sorted(allowed_lower))
            raise ValueError(
                f"Access to table '{table}' is not permitted. "
                f"Available tables: {available_tables}. "
                f"Please use one of the available tables in your question."
            )
    
    # Inject LIMIT if missing
    s = inject_limit(s, max_limit)
    
    return s

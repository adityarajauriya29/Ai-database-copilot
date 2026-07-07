import re
from typing import Tuple, List
import sqlparse

DDL_TYPES = {"CREATE", "ALTER", "DROP"}
MUTATION_TYPES = {"INSERT", "UPDATE", "DELETE"}
READ_TYPES = {"SELECT"}
ABSOLUTELY_BLOCKED_KEYWORDS = [
    "TRUNCATE", "GRANT", "REVOKE", "EXEC", "EXECUTE", "MERGE", "CALL", "ATTACH", "DETACH",
]

DANGEROUS_PATTERNS = [
    r"\bDROP\s+DATABASE\b",
    r"\bDROP\s+SCHEMA\b",
    r"\bTRUNCATE\s+TABLE\b",
    r"\bGRANT\b|\bREVOKE\b",
    r"\bEXEC\b|\bEXECUTE\b|\bCALL\b",
    r"\bxp_cmdshell\b",
    r"'\s*OR\s*'1'\s*=\s*'1",
    r'"\s*OR\s*"1"\s*=\s*"1',
    r"\bOR\s+1\s*=\s*1\b",
    r"'\s*;\s*--",
]

SAFE_DDL_PATTERNS = [
    r"^CREATE\s+TABLE\s+(IF\s+NOT\s+EXISTS\s+)?[a-zA-Z_][\w]*\s*\(",
    r"^CREATE\s+INDEX\s+(IF\s+NOT\s+EXISTS\s+)?[a-zA-Z_][\w]*\s+ON\s+[a-zA-Z_][\w]*\s*\(",
    r"^CREATE\s+UNIQUE\s+INDEX\s+(IF\s+NOT\s+EXISTS\s+)?[a-zA-Z_][\w]*\s+ON\s+[a-zA-Z_][\w]*\s*\(",
    r"^CREATE\s+VIEW\s+[a-zA-Z_][\w]*\s+AS\s+SELECT\s+",
    r"^ALTER\s+TABLE\s+[a-zA-Z_][\w]*\s+(ADD\s+COLUMN|RENAME\s+TO|RENAME\s+COLUMN)",
    r"^DROP\s+TABLE\s+(IF\s+EXISTS\s+)?[a-zA-Z_][\w]*$",
]


def _normalize_sql(sql: str) -> str:
    return " ".join(sql.strip().split())


def _split_statements(sql: str) -> List[str]:
    return [str(stmt).strip().rstrip(";").strip() for stmt in sqlparse.parse(sql) if str(stmt).strip()]


def _get_statement_type(sql: str) -> str:
    parsed = sqlparse.parse(sql)
    if not parsed:
        return "UNKNOWN"
    stmt_type = parsed[0].get_type() or "UNKNOWN"
    if stmt_type == "UNKNOWN":
        match = re.match(r"^\s*(CREATE|ALTER|DROP|INSERT|UPDATE|DELETE|SELECT)\b", sql, re.IGNORECASE)
        if match:
            return match.group(1).upper()
    return stmt_type.upper()


def _has_where_clause(sql: str) -> bool:
    return bool(re.search(r"\bWHERE\b", sql, re.IGNORECASE))


def _has_limit_clause(sql: str) -> bool:
    return bool(re.search(r"\b(LIMIT|TOP|FETCH\s+FIRST)\b", sql, re.IGNORECASE))


def _is_safe_ddl(stmt: str) -> bool:
    clean = _normalize_sql(stmt).rstrip(";")
    upper = clean.upper()
    if any(re.search(rf"\b{kw}\b", upper) for kw in ABSOLUTELY_BLOCKED_KEYWORDS):
        return False
    if re.search(r"\bDROP\s+(DATABASE|SCHEMA)\b", upper):
        return False
    return any(re.search(pattern, clean, re.IGNORECASE) for pattern in SAFE_DDL_PATTERNS)


def validate_sql(sql: str, is_readonly: bool = True) -> Tuple[bool, str, List[str]]:
    if not sql or not sql.strip():
        return False, "Empty SQL query", []

    warnings: List[str] = []
    statements = _split_statements(sql)
    if not statements:
        return False, "Could not parse SQL", []

    for pattern in DANGEROUS_PATTERNS:
        if re.search(pattern, sql, re.IGNORECASE | re.MULTILINE | re.DOTALL):
            return False, "Blocked: dangerous SQL pattern detected", []

    stmt_types = [_get_statement_type(stmt) for stmt in statements]

    if is_readonly and any(t != "SELECT" for t in stmt_types):
        return False, "Connection is in read-only mode. Only SELECT queries are allowed.", []

    if len(statements) > 1:
        if not all(t in DDL_TYPES for t in stmt_types):
            return False, "Multiple SQL statements are allowed only for safe DDL schema creation.", []
        if not all(_is_safe_ddl(stmt) for stmt in statements):
            return False, "Only safe CREATE TABLE/INDEX/VIEW or limited ALTER/DROP TABLE DDL is allowed.", []
        warnings.append("Multiple DDL statements detected. They will be executed in order.")
        return True, "OK", warnings

    stmt = statements[0]
    stmt_type = stmt_types[0]
    stmt_upper = _normalize_sql(stmt).upper()

    if any(re.search(rf"\b{kw}\b", stmt_upper) for kw in ABSOLUTELY_BLOCKED_KEYWORDS):
        return False, "Blocked keyword found in SQL", []

    if stmt_type in DDL_TYPES:
        if not _is_safe_ddl(stmt):
            return False, "DDL statement is not permitted or is considered unsafe", []
        warnings.append("DDL query detected. Review carefully before execution.")
        return True, "OK", warnings

    if stmt_type == "UPDATE" and not _has_where_clause(stmt):
        return False, "UPDATE without WHERE clause is not allowed", []

    if stmt_type == "DELETE" and not _has_where_clause(stmt):
        return False, "DELETE without WHERE clause is not allowed", []

    if stmt_type == "SELECT":
        if re.search(r"\bSELECT\s+\*", stmt_upper):
            warnings.append("Avoid SELECT *. Select only required columns for better performance.")
        if not _has_limit_clause(stmt_upper):
            warnings.append("Consider adding LIMIT to avoid very large result sets.")
        if "CROSS JOIN" in stmt_upper:
            warnings.append("CROSS JOIN may create a very large result set.")

    return True, "OK", warnings


def estimate_risk(sql: str) -> Tuple[str, float, List[str]]:
    sql_clean = _normalize_sql(sql)
    sql_upper = sql_clean.upper()
    reasons: List[str] = []
    score = 0.0
    statements = _split_statements(sql)
    stmt_types = [_get_statement_type(stmt) for stmt in statements] or ["UNKNOWN"]

    if len(statements) > 1:
        score += 0.25
        reasons.append("Multiple statements will be executed in sequence.")

    for stmt_type in stmt_types:
        if stmt_type == "DELETE":
            score += 0.65
            reasons.append("DELETE operation can permanently remove data.")
        if stmt_type == "UPDATE":
            score += 0.55
            reasons.append("UPDATE operation modifies existing records.")
        if stmt_type == "INSERT":
            score += 0.25
            reasons.append("INSERT operation adds new records.")
        if stmt_type == "CREATE":
            score += 0.35
            reasons.append("CREATE operation changes database structure.")
        if stmt_type == "ALTER":
            score += 0.65
            reasons.append("ALTER operation modifies database structure.")
        if stmt_type == "DROP":
            score += 0.9
            reasons.append("DROP operation removes database objects.")

    if any(t in ("DELETE", "UPDATE") for t in stmt_types) and not _has_where_clause(sql_clean):
        score += 0.4
        reasons.append("No WHERE clause detected; operation may affect all rows.")

    if "JOIN" in sql_upper:
        score += 0.1
        reasons.append("JOIN may be expensive on large tables.")
    if "CROSS JOIN" in sql_upper:
        score += 0.25
        reasons.append("CROSS JOIN may generate a large result set.")
    if re.search(r"\bSELECT\s+\*", sql_upper):
        score += 0.05
        reasons.append("SELECT * returns all columns and may use more memory.")
    if not _has_limit_clause(sql_upper) and "SELECT" in stmt_types:
        score += 0.05
        reasons.append("SELECT query has no LIMIT clause.")

    score = min(score, 1.0)
    if score >= 0.85:
        level = "critical"
    elif score >= 0.55:
        level = "high"
    elif score >= 0.25:
        level = "medium"
    else:
        level = "low"
    return level, score, reasons

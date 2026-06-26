import re
from typing import Tuple, List
import sqlparse


BLOCKED_KEYWORDS = [
    "DROP",
    "TRUNCATE",
    "ALTER",
    "CREATE",
    "GRANT",
    "REVOKE",
    "EXEC",
    "EXECUTE",
    "MERGE",
    "CALL",
]


DANGEROUS_PATTERNS = [
    r"\bDROP\s+(TABLE|DATABASE|SCHEMA|INDEX|VIEW)\b",
    r"\bTRUNCATE\s+TABLE\b",
    r"\bALTER\s+TABLE\b",
    r"\bCREATE\s+(TABLE|DATABASE|SCHEMA|INDEX|VIEW)\b",
    r"\bGRANT\b|\bREVOKE\b",
    r"\bEXEC\b|\bEXECUTE\b|\bCALL\b",
    r"\bxp_cmdshell\b",
    r"--.*$",
    r"/\*.*?\*/",
    r";\s*(DROP|TRUNCATE|ALTER|CREATE|GRANT|REVOKE|EXEC|EXECUTE)\b",
    r"'\s*OR\s*'1'\s*=\s*'1",
    r'"\s*OR\s*"1"\s*=\s*"1',
    r"\bOR\s+1\s*=\s*1\b",
    r"'\s*;\s*--",
]


def _normalize_sql(sql: str) -> str:
    return " ".join(sql.strip().split())


def _get_statement_type(sql: str) -> str:
    parsed = sqlparse.parse(sql)
    if not parsed:
        return "UNKNOWN"
    return parsed[0].get_type() or "UNKNOWN"


def _has_where_clause(sql: str) -> bool:
    return bool(re.search(r"\bWHERE\b", sql, re.IGNORECASE))


def _has_limit_clause(sql: str) -> bool:
    return bool(re.search(r"\b(LIMIT|TOP|FETCH\s+FIRST)\b", sql, re.IGNORECASE))


def validate_sql(sql: str, is_readonly: bool = True) -> Tuple[bool, str, List[str]]:
    if not sql or not sql.strip():
        return False, "Empty SQL query", []

    sql_clean = _normalize_sql(sql)
    sql_upper = sql_clean.upper()
    warnings: List[str] = []

    parsed = sqlparse.parse(sql_clean)
    if not parsed:
        return False, "Could not parse SQL", []

    if len(parsed) > 1:
        return False, "Multiple SQL statements are not allowed", []

    for pattern in DANGEROUS_PATTERNS:
        if re.search(pattern, sql_clean, re.IGNORECASE | re.MULTILINE | re.DOTALL):
            return False, "Blocked: dangerous SQL pattern detected", []

    stmt_type = _get_statement_type(sql_clean)

    if stmt_type in BLOCKED_KEYWORDS:
        return False, f"{stmt_type} statement is not permitted", []

    if any(re.search(rf"\b{kw}\b", sql_upper) for kw in BLOCKED_KEYWORDS):
        return False, "Blocked keyword found in SQL", []

    if is_readonly and stmt_type != "SELECT":
        return False, "Connection is in read-only mode. Only SELECT queries are allowed.", []

    if stmt_type == "UPDATE" and not _has_where_clause(sql_clean):
        return False, "UPDATE without WHERE clause is not allowed", []

    if stmt_type == "DELETE" and not _has_where_clause(sql_clean):
        return False, "DELETE without WHERE clause is not allowed", []

    if stmt_type == "SELECT":
        if re.search(r"\bSELECT\s+\*", sql_upper):
            warnings.append("Avoid SELECT *. Select only required columns for better performance.")

        if not _has_limit_clause(sql_upper):
            warnings.append("Consider adding LIMIT to avoid very large result sets.")

        if "CROSS JOIN" in sql_upper:
            warnings.append("CROSS JOIN may create a very large result set.")

    return True, "OK", warnings


def estimate_risk(sql: str) -> Tuple[str, float, List[str]]:
    sql_clean = _normalize_sql(sql)
    sql_upper = sql_clean.upper()
    reasons: List[str] = []
    score = 0.0

    try:
        stmt_type = _get_statement_type(sql_clean)
    except Exception:
        stmt_type = "UNKNOWN"

    if stmt_type == "DELETE":
        score += 0.65
        reasons.append("DELETE operation can permanently remove data.")

    if stmt_type == "UPDATE":
        score += 0.55
        reasons.append("UPDATE operation modifies existing records.")

    if stmt_type == "INSERT":
        score += 0.25
        reasons.append("INSERT operation adds new records.")

    if stmt_type in ("DROP", "TRUNCATE", "ALTER", "CREATE"):
        score += 1.0
        reasons.append("DDL operation changes database structure.")

    if stmt_type in ("DELETE", "UPDATE") and not _has_where_clause(sql_clean):
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

    if not _has_limit_clause(sql_upper) and stmt_type == "SELECT":
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
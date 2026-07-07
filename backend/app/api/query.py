from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from datetime import datetime
import secrets
import json
import re
import time
import sqlparse
from sqlalchemy import create_engine, text

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.query import QueryHistory, DatabaseConnection
from app.schemas.schemas import QueryRequest, QueryResponse, ExecuteRequest, ExecuteResponse
from app.services.ai_service import generate_sql, get_relevant_schema_context
from app.services.sql_firewall import validate_sql, estimate_risk
from app.services.db_connector import execute_query, decrypt_password, build_connection_url, get_schema
from app.services.audit_service import write_audit_log

router = APIRouter()

SCHEMA_CHANGE_TYPES = {"CREATE", "ALTER", "DROP"}


def _get_connection(connection_id: int, user_id: int, db: Session) -> DatabaseConnection:
    conn = (
        db.query(DatabaseConnection)
        .filter(
            DatabaseConnection.id == connection_id,
            DatabaseConnection.user_id == user_id,
            DatabaseConnection.is_active == True,
        )
        .first()
    )

    if not conn:
        raise HTTPException(status_code=404, detail="Database connection not found")

    return conn


def _get_connection_url(conn: DatabaseConnection) -> str:
    if conn.connection_string:
        return conn.connection_string

    password = ""
    if conn.encrypted_password:
        password = decrypt_password(conn.encrypted_password)

    return build_connection_url(
        conn.db_type,
        conn.host,
        conn.port,
        conn.database,
        conn.username,
        password,
    )


def _detect_query_type(sql: str, fallback: str = "SELECT") -> str:
    text = (sql or "").strip().upper()
    match = re.match(r"^(SELECT|INSERT|UPDATE|DELETE|CREATE|ALTER|DROP)\b", text)
    if match:
        return match.group(1)
    return (fallback or "SELECT").upper()


def _split_sql_statements(sql: str) -> list[str]:
    return [str(stmt).strip().rstrip(";").strip() for stmt in sqlparse.parse(sql or "") if str(stmt).strip()]


def _execute_sql_statements(connection_url: str, sql: str):
    statements = _split_sql_statements(sql)
    if not statements:
        raise ValueError("No SQL statements to execute")

    engine = create_engine(connection_url)
    start = time.perf_counter()
    rows = []
    columns = []
    total_affected = 0

    with engine.begin() as conn:
        for index, statement in enumerate(statements):
            result = conn.execute(text(statement))
            if result.returns_rows:
                columns = list(result.keys())
                rows = [dict(row._mapping) for row in result.fetchall()]
                total_affected += len(rows)
            else:
                if result.rowcount and result.rowcount > 0:
                    total_affected += result.rowcount
                elif statement.strip().upper().startswith(("CREATE", "ALTER", "DROP")):
                    total_affected += 1

    elapsed = (time.perf_counter() - start) * 1000
    return rows, columns, total_affected, elapsed, len(statements)


@router.post("/generate", response_model=QueryResponse)
async def generate_query(
    req: QueryRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    conn = _get_connection(req.connection_id, current_user.id, db)

    schema = conn.schema_cache
    if not schema:
        try:
            url = _get_connection_url(conn)
            schema = get_schema(url, conn.db_type)
            conn.schema_cache = schema
            conn.schema_cached_at = datetime.utcnow()
            db.commit()
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Schema not loaded and auto-refresh failed: {str(e)}")

    schema_context = get_relevant_schema_context(
        req.natural_language,
        schema,
    )

    history = []
    if req.session_id:
        recent = (
            db.query(QueryHistory)
            .filter(
                QueryHistory.user_id == current_user.id,
                QueryHistory.session_id == req.session_id,
                QueryHistory.generated_sql != None,
            )
            .order_by(QueryHistory.created_at.desc())
            .limit(5)
            .all()
        )

        history = [
            {
                "user": q.natural_language,
                "sql": q.generated_sql,
            }
            for q in reversed(recent)
        ]

    ai_result = await generate_sql(
        req.natural_language,
        schema_context,
        history,
        req.mode,
        req.language,
    )

    sql = ai_result.get("sql", "").strip()

    print("===== AI RESULT =====")
    print(ai_result)

    if ai_result.get("query_type") == "BLOCKED":
        write_audit_log(
            db,
            "QUERY_BLOCKED",
            current_user.id,
            "query",
            None,
            {
                "reason": "AI security layer blocked request",
                "nl": req.natural_language[:200],
            },
            request.client.host if request.client else None,
        )
        raise HTTPException(
            status_code=400,
            detail=ai_result.get("explanation", "Query blocked."),
        )

    if not sql:
        raise HTTPException(
            status_code=400,
            detail=f"AI failed to generate SQL. Warnings: {ai_result.get('warnings', [])}",
        )

    query_type = _detect_query_type(sql, ai_result.get("query_type", "SELECT"))
    ai_result["query_type"] = query_type

    is_safe, reason, warnings = validate_sql(sql, conn.is_readonly)
    if not is_safe:
        write_audit_log(
            db,
            "QUERY_BLOCKED",
            current_user.id,
            "query",
            None,
            {
                "reason": reason,
                "sql": sql[:200],
            },
            request.client.host if request.client else None,
        )
        raise HTTPException(status_code=400, detail=f"Query blocked: {reason}")

    risk_level, risk_score, risk_reasons = estimate_risk(sql)

    is_schema_change = query_type in SCHEMA_CHANGE_TYPES
    if is_schema_change:
        ai_result.setdefault("warnings", [])
        ai_result["warnings"].append("This is a DDL query. After execution, the database schema will be refreshed automatically.")

    ai_result["risk_level"] = risk_level
    ai_result["risk_score"] = risk_score
    ai_result["risk_reasons"] = risk_reasons + ai_result.get("risk_reasons", [])
    ai_result["warnings"] = warnings + ai_result.get("warnings", [])

    share_token = secrets.token_urlsafe(12)

    history_entry = QueryHistory(
        user_id=current_user.id,
        connection_id=conn.id,
        natural_language=req.natural_language,
        generated_sql=sql,
        explanation=ai_result.get("explanation", ""),
        confidence_score=ai_result.get("confidence_score", 0),
        risk_level=risk_level,
        risk_score=risk_score,
        query_type=query_type,
        status="generated",
        alternatives=ai_result.get("alternatives", []),
        optimization_score=ai_result.get("optimization_score", 0),
        share_token=share_token,
        session_id=req.session_id,
    )

    db.add(history_entry)
    db.commit()
    db.refresh(history_entry)

    write_audit_log(
        db,
        "QUERY_GENERATED",
        current_user.id,
        "query",
        str(history_entry.id),
        {
            "nl": req.natural_language[:100],
            "type": query_type,
            "is_schema_change": is_schema_change,
        },
        request.client.host if request.client else None,
    )

    return QueryResponse(
        id=history_entry.id,
        natural_language=req.natural_language,
        generated_sql=sql,
        explanation=ai_result.get("explanation", ""),
        confidence_score=ai_result.get("confidence_score", 0.0),
        optimization_score=ai_result.get("optimization_score", 0.0),
        risk_level=risk_level,
        risk_score=risk_score,
        risk_reasons=ai_result.get("risk_reasons", []),
        query_type=query_type,
        estimated_rows=ai_result.get("estimated_rows"),
        estimated_time_ms=ai_result.get("estimated_time_ms"),
        alternatives=[
            {
                "sql": a.get("sql", ""),
                "explanation": a.get("explanation", ""),
                "rank": a.get("rank", 1),
                "reason": a.get("reason", ""),
            }
            for a in ai_result.get("alternatives", [])
        ],
        optimization_tips=ai_result.get("optimization_tips", []),
        learning_tips=ai_result.get("learning_tips", []),
        clauses_explained=ai_result.get("clauses_explained", {}),
        warnings=ai_result.get("warnings", []),
        share_token=share_token,
        is_schema_change=is_schema_change,
        refresh_schema_required=is_schema_change,
        database_builder=ai_result.get("database_builder"),
    )


@router.post("/execute", response_model=ExecuteResponse)
async def execute_query_endpoint(
    req: ExecuteRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    history_entry = (
        db.query(QueryHistory)
        .filter(
            QueryHistory.id == req.query_id,
            QueryHistory.user_id == current_user.id,
        )
        .first()
    )

    if not history_entry:
        raise HTTPException(status_code=404, detail="Query not found")

    if history_entry.risk_level in ("high", "critical") and not req.confirm:
        raise HTTPException(
            status_code=428,
            detail=f"Query has {history_entry.risk_level} risk. Set confirm=true to proceed.",
        )

    conn = _get_connection(history_entry.connection_id, current_user.id, db)

    is_safe, reason, _ = validate_sql(history_entry.generated_sql, conn.is_readonly)
    if not is_safe:
        raise HTTPException(status_code=400, detail=f"Execution blocked: {reason}")

    try:
        connection_url = _get_connection_url(conn)
        query_type = _detect_query_type(history_entry.generated_sql, history_entry.query_type or "SELECT")

        rows, columns, rows_affected, elapsed, statement_count = _execute_sql_statements(
            connection_url,
            history_entry.generated_sql,
        )

        schema_refreshed = False
        if query_type in SCHEMA_CHANGE_TYPES:
            try:
                schema = get_schema(connection_url, conn.db_type)
                conn.schema_cache = schema
                conn.schema_cached_at = datetime.utcnow()
                schema_refreshed = True
            except Exception as schema_error:
                history_entry.error_message = f"Query executed, but schema refresh failed: {schema_error}"

        history_entry.status = "executed"
        history_entry.rows_affected = rows_affected
        history_entry.rows_returned = len(rows)
        history_entry.execution_time_ms = elapsed
        history_entry.executed_at = datetime.utcnow()
        history_entry.query_type = query_type
        conn.last_used = datetime.utcnow()

        db.commit()

        write_audit_log(
            db,
            "QUERY_EXECUTED",
            current_user.id,
            "query",
            str(history_entry.id),
            {
                "rows": len(rows),
                "time_ms": round(elapsed, 2),
                "type": query_type,
                "schema_refreshed": schema_refreshed,
                "statement_count": statement_count,
            },
            request.client.host if request.client else None,
        )

        safe_rows = []
        for row in rows:
            safe_row = {}
            for key, value in row.items():
                try:
                    json.dumps(value)
                    safe_row[key] = value
                except (TypeError, ValueError):
                    safe_row[key] = str(value)

            safe_rows.append(safe_row)

        message = "Query executed successfully."
        if query_type in SCHEMA_CHANGE_TYPES:
            message = "DDL executed successfully. Schema refreshed." if schema_refreshed else "DDL executed successfully. Refresh schema manually if needed."

        return ExecuteResponse(
            success=True,
            rows=safe_rows,
            columns=columns,
            rows_affected=rows_affected,
            execution_time_ms=elapsed,
            message=message,
            query_type=query_type,
            schema_refreshed=schema_refreshed,
        )

    except Exception as e:
        history_entry.status = "failed"
        history_entry.error_message = str(e)
        db.commit()

        return ExecuteResponse(
            success=False,
            rows=[],
            columns=[],
            rows_affected=0,
            execution_time_ms=0,
            error=str(e),
            query_type=history_entry.query_type,
        )


@router.get("/share/{share_token}")
async def get_shared_query(
    share_token: str,
    db: Session = Depends(get_db),
):
    entry = (
        db.query(QueryHistory)
        .filter(QueryHistory.share_token == share_token)
        .first()
    )

    if not entry:
        raise HTTPException(status_code=404, detail="Shared query not found")

    return {
        "natural_language": entry.natural_language,
        "generated_sql": entry.generated_sql,
        "explanation": entry.explanation,
        "confidence_score": entry.confidence_score,
        "query_type": entry.query_type,
        "created_at": entry.created_at,
    }

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from datetime import datetime
import secrets
import json

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.query import QueryHistory, DatabaseConnection
from app.schemas.schemas import QueryRequest, QueryResponse, ExecuteRequest, ExecuteResponse
from app.services.ai_service import generate_sql, get_relevant_schema_context
from app.services.sql_firewall import validate_sql, estimate_risk
from app.services.db_connector import execute_query, decrypt_password, build_connection_url
from app.services.audit_service import write_audit_log

router = APIRouter()


def _get_connection(connection_id: int, user_id: int, db: Session) -> DatabaseConnection:
    conn = db.query(DatabaseConnection).filter(
        DatabaseConnection.id == connection_id,
        DatabaseConnection.user_id == user_id,
        DatabaseConnection.is_active == True,
    ).first()
    if not conn:
        raise HTTPException(status_code=404, detail="Database connection not found")
    return conn


def _get_connection_url(conn: DatabaseConnection) -> str:
    if conn.connection_string:
        return conn.connection_string
    password = decrypt_password(conn.encrypted_password) if conn.encrypted_password else ""
    return build_connection_url(conn.db_type, conn.host, conn.port, conn.database, conn.username, password)


def _safe_alternative(a) -> dict:
    """Safely convert an alternative — handles dict, string, or anything else."""
    if isinstance(a, dict):
        return {
            "sql": str(a.get("sql", "")),
            "explanation": str(a.get("explanation", "")),
            "rank": int(a.get("rank") or 1),
            "reason": str(a.get("reason", "")),
        }
    return {"sql": str(a) if a else "", "explanation": "", "rank": 1, "reason": "Alternative query"}


def _safe_list(value) -> list:
    if not value:
        return []
    if isinstance(value, list):
        return [str(i) for i in value if i is not None]
    if isinstance(value, str):
        return [value] if value else []
    return []


def _safe_dict(value) -> dict:
    if isinstance(value, dict):
        return {str(k): str(v) for k, v in value.items()}
    return {}


# ─── Generate ──────────────────────────────────────────────────────────────────

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
        from app.services.db_connector import get_schema
        try:
            url = _get_connection_url(conn)
            schema = get_schema(url, conn.db_type)
            conn.schema_cache = schema
            conn.schema_cached_at = datetime.utcnow()
            db.commit()
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Schema not loaded: {str(e)}")

    schema_context = get_relevant_schema_context(req.natural_language, schema)

    history = []
    if req.session_id:
        recent = db.query(QueryHistory).filter(
            QueryHistory.user_id == current_user.id,
            QueryHistory.session_id == req.session_id,
            QueryHistory.generated_sql != None,
        ).order_by(QueryHistory.created_at.desc()).limit(5).all()
        history = [{"user": q.natural_language, "sql": q.generated_sql} for q in reversed(recent)]

    ai_result = await generate_sql(req.natural_language, schema_context, history, req.mode, req.language)

    sql = str(ai_result.get("sql") or "").strip()
    print(f"[QUERY GEN] sql_len={len(sql)} model={ai_result.get('_model_used','?')}")

    if ai_result.get("query_type") == "BLOCKED":
        raise HTTPException(status_code=400, detail=ai_result.get("explanation", "Query blocked."))

    if not sql:
        raise HTTPException(status_code=400, detail="Query blocked: Empty SQL query")

    # DDL — admin only
    first_word = sql.upper().split()[0] if sql.split() else ""
    is_ddl = first_word in {"CREATE", "DROP", "ALTER", "TRUNCATE", "RENAME"}
    if is_ddl and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="DDL commands require admin role.")

    warnings = []
    if not is_ddl:
        is_safe, reason, warnings = validate_sql(sql, conn.is_readonly)
        if not is_safe:
            write_audit_log(db, "QUERY_BLOCKED", current_user.id, "query", None,
                {"reason": reason, "sql": sql[:200]}, request.client.host if request.client else None)
            raise HTTPException(status_code=400, detail=f"Query blocked: {reason}")

    risk_level, risk_score, risk_reasons = estimate_risk(sql)

    # ── Safe field extraction (THE CRASH FIX) ──────────────────────────────
    safe_alternatives = [_safe_alternative(a) for a in (ai_result.get("alternatives") or []) if a]
    safe_opt_tips     = _safe_list(ai_result.get("optimization_tips"))
    safe_learn_tips   = _safe_list(ai_result.get("learning_tips"))
    safe_clauses      = _safe_dict(ai_result.get("clauses_explained"))
    safe_warnings     = _safe_list(warnings) + _safe_list(ai_result.get("warnings"))
    safe_risk_reasons = risk_reasons + _safe_list(ai_result.get("risk_reasons"))

    share_token = secrets.token_urlsafe(12)

    history_entry = QueryHistory(
        user_id=current_user.id,
        connection_id=conn.id,
        natural_language=req.natural_language,
        generated_sql=sql,
        explanation=str(ai_result.get("explanation") or ""),
        confidence_score=float(ai_result.get("confidence_score") or 0),
        risk_level=risk_level,
        risk_score=risk_score,
        query_type=str(ai_result.get("query_type") or "SELECT"),
        status="generated",
        alternatives=safe_alternatives,
        optimization_score=float(ai_result.get("optimization_score") or 0),
        share_token=share_token,
        session_id=req.session_id,
    )
    db.add(history_entry)
    db.commit()
    db.refresh(history_entry)

    write_audit_log(db, "QUERY_GENERATED", current_user.id, "query", str(history_entry.id),
        {"nl": req.natural_language[:100], "type": ai_result.get("query_type")},
        request.client.host if request.client else None)

    return QueryResponse(
        id=history_entry.id,
        natural_language=req.natural_language,
        generated_sql=sql,
        explanation=str(ai_result.get("explanation") or ""),
        confidence_score=float(ai_result.get("confidence_score") or 0.0),
        optimization_score=float(ai_result.get("optimization_score") or 0.0),
        risk_level=risk_level,
        risk_score=risk_score,
        risk_reasons=safe_risk_reasons,
        query_type=str(ai_result.get("query_type") or "SELECT"),
        estimated_rows=ai_result.get("estimated_rows"),
        estimated_time_ms=ai_result.get("estimated_time_ms"),
        alternatives=safe_alternatives,
        optimization_tips=safe_opt_tips,
        learning_tips=safe_learn_tips,
        clauses_explained=safe_clauses,
        warnings=safe_warnings,
        share_token=share_token,
    )


# ─── Execute ───────────────────────────────────────────────────────────────────

@router.post("/execute", response_model=ExecuteResponse)
async def execute_query_endpoint(
    req: ExecuteRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    history_entry = db.query(QueryHistory).filter(
        QueryHistory.id == req.query_id,
        QueryHistory.user_id == current_user.id,
    ).first()
    if not history_entry:
        raise HTTPException(status_code=404, detail="Query not found")

    if history_entry.risk_level in ("high", "critical") and not req.confirm:
        raise HTTPException(status_code=428,
            detail=f"Query has {history_entry.risk_level} risk. Set confirm=true to proceed.")

    conn = _get_connection(history_entry.connection_id, current_user.id, db)
    sql = history_entry.generated_sql

    first_word = sql.upper().split()[0] if sql.split() else ""
    is_ddl = first_word in {"CREATE", "DROP", "ALTER", "TRUNCATE", "RENAME"}

    if is_ddl and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="DDL execution requires admin role.")

    if not is_ddl:
        is_safe, reason, _ = validate_sql(sql, conn.is_readonly)
        if not is_safe:
            raise HTTPException(status_code=400, detail=f"Execution blocked: {reason}")

    try:
        connection_url = _get_connection_url(conn)
        rows, columns, rows_affected, elapsed = execute_query(connection_url, sql)

        history_entry.status = "executed"
        history_entry.rows_affected = rows_affected
        history_entry.rows_returned = len(rows)
        history_entry.execution_time_ms = elapsed
        history_entry.executed_at = datetime.utcnow()
        conn.last_used = datetime.utcnow()
        db.commit()

        # Auto-refresh schema after DDL
        if is_ddl:
            try:
                from app.services.db_connector import get_schema
                conn.schema_cache = get_schema(connection_url, conn.db_type)
                conn.schema_cached_at = datetime.utcnow()
                db.commit()
                print(f"[DDL] Schema auto-refreshed for connection {conn.id}")
            except Exception as e:
                print(f"[DDL] Schema refresh failed: {e}")

        write_audit_log(db, "QUERY_EXECUTED", current_user.id, "query", str(history_entry.id),
            {"rows": len(rows), "time_ms": round(elapsed, 2)},
            request.client.host if request.client else None)

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

        return ExecuteResponse(success=True, rows=safe_rows, columns=columns,
            rows_affected=rows_affected, execution_time_ms=elapsed)

    except Exception as e:
        history_entry.status = "failed"
        history_entry.error_message = str(e)
        db.commit()
        return ExecuteResponse(success=False, rows=[], columns=[], rows_affected=0,
            execution_time_ms=0, error=str(e))


# ─── Share ─────────────────────────────────────────────────────────────────────

@router.get("/share/{share_token}")
async def get_shared_query(share_token: str, db: Session = Depends(get_db)):
    entry = db.query(QueryHistory).filter(QueryHistory.share_token == share_token).first()
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


# ─── DDL endpoints ─────────────────────────────────────────────────────────────

@router.post("/ddl/generate")
async def generate_ddl_query(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Generate DDL SQL from natural language using AI."""
    body = await request.json()
    natural_language = body.get("natural_language", "").strip()
    connection_id = body.get("connection_id")

    if not natural_language or not connection_id:
        raise HTTPException(status_code=400, detail="natural_language and connection_id required")

    conn = _get_connection(connection_id, current_user.id, db)
    schema = conn.schema_cache or {}
    schema_context = get_relevant_schema_context(natural_language, schema)

    ddl_prompt = f"Generate DDL SQL only (CREATE TABLE, ALTER TABLE, DROP TABLE, etc.) for: {natural_language}. Return only the DDL statement in the sql field."
    ai_result = await generate_sql(ddl_prompt, schema_context, [], "developer", "en")

    return {
        "sql": str(ai_result.get("sql") or ""),
        "explanation": str(ai_result.get("explanation") or ""),
        "confidence_score": float(ai_result.get("confidence_score") or 0),
        "warnings": _safe_list(ai_result.get("warnings")),
    }


@router.post("/ddl/execute")
async def execute_ddl_direct(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Execute a raw DDL statement directly. Admin only. Connection must not be read-only."""
    body = await request.json()
    sql = body.get("sql", "").strip()
    connection_id = body.get("connection_id")

    if not sql or not connection_id:
        raise HTTPException(status_code=400, detail="sql and connection_id required")

    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="DDL execution requires admin role.")

    conn = _get_connection(connection_id, current_user.id, db)
    if conn.is_readonly:
        raise HTTPException(status_code=400, detail="Connection is read-only. Disable read-only mode to run DDL.")

    first_word = sql.upper().split()[0] if sql.split() else ""
    allowed_ddl = {"CREATE", "DROP", "ALTER", "TRUNCATE", "RENAME"}
    if first_word not in allowed_ddl:
        raise HTTPException(status_code=400, detail=f"Only DDL statements allowed here. Got: {first_word}")

    try:
        connection_url = _get_connection_url(conn)
        _, _, rows_affected, elapsed = execute_query(connection_url, sql)

        # Auto-refresh schema
        try:
            from app.services.db_connector import get_schema
            conn.schema_cache = get_schema(connection_url, conn.db_type)
            conn.schema_cached_at = datetime.utcnow()
            db.commit()
        except Exception:
            pass

        write_audit_log(db, "DDL_EXECUTED", current_user.id, "ddl", str(connection_id),
            {"sql": sql[:300]}, request.client.host if request.client else None)

        return {
            "success": True,
            "message": f"DDL executed in {elapsed:.1f}ms",
            "rows_affected": rows_affected,
            "execution_time_ms": elapsed,
            "schema_refreshed": True,
        }
    except Exception as e:
        return {
            "success": False,
            "message": str(e),
            "rows_affected": 0,
            "execution_time_ms": 0,
            "schema_refreshed": False,
        }
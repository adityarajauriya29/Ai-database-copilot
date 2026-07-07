from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, File, Form
from sqlalchemy.orm import Session
from datetime import datetime
import shutil
from pathlib import Path
import re

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.query import DatabaseConnection
from app.schemas.schemas import ConnectionCreate, ConnectionResponse, SQLiteDatabaseCreate
from app.services.db_connector import (
    get_schema,
    test_connection,
    encrypt_password,
    decrypt_password,
    build_connection_url,
    get_demo_connection_url,
    preview_table_data,
)
from app.services.audit_service import write_audit_log

router = APIRouter()


def _get_connection(conn_id: int, user_id: int, db: Session) -> DatabaseConnection:
    conn = (
        db.query(DatabaseConnection)
        .filter(
            DatabaseConnection.id == conn_id,
            DatabaseConnection.user_id == user_id,
            DatabaseConnection.is_active == True,
        )
        .first()
    )

    if not conn:
        raise HTTPException(status_code=404, detail="Connection not found")

    return conn


def _get_connection_url(conn: DatabaseConnection) -> str:
    if conn.connection_string:
        return conn.connection_string

    password = decrypt_password(conn.encrypted_password) if conn.encrypted_password else ""

    return build_connection_url(
        conn.db_type,
        conn.host,
        conn.port,
        conn.database,
        conn.username,
        password,
    )


def _safe_sqlite_name(name: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_-]+", "_", name.strip()).strip("_")
    return cleaned[:60] or "database"


@router.get("/connections", response_model=list[ConnectionResponse])
async def list_connections(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return (
        db.query(DatabaseConnection)
        .filter(
            DatabaseConnection.user_id == current_user.id,
            DatabaseConnection.is_active == True,
        )
        .all()
    )


@router.post("/connections", response_model=ConnectionResponse, status_code=201)
async def create_connection(
    data: ConnectionCreate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    password = data.password or ""

    if data.connection_string:
        url = data.connection_string
    else:
        url = build_connection_url(
            data.db_type,
            data.host,
            data.port,
            data.database,
            data.username,
            password,
        )

    ok, msg = test_connection(url)
    if not ok:
        raise HTTPException(status_code=400, detail=f"Connection failed: {msg}")

    encrypted_pw = encrypt_password(password) if password else None

    conn = DatabaseConnection(
        user_id=current_user.id,
        name=data.name,
        db_type=data.db_type,
        host=data.host,
        port=data.port,
        database=data.database,
        username=data.username,
        encrypted_password=encrypted_pw,
        connection_string=data.connection_string,
        is_readonly=data.is_readonly,
    )

    db.add(conn)
    db.commit()
    db.refresh(conn)

    try:
        schema = get_schema(url, data.db_type)
        conn.schema_cache = schema
        conn.schema_cached_at = datetime.utcnow()
        db.commit()
    except Exception:
        pass

    write_audit_log(
        db,
        "CONNECTION_CREATED",
        current_user.id,
        "connection",
        str(conn.id),
        {"name": conn.name, "db_type": conn.db_type, "is_readonly": conn.is_readonly},
        request.client.host if request.client else None,
    )

    return conn


@router.post("/connections/create-sqlite-database")
async def create_sqlite_database_connection(
    data: SQLiteDatabaseCreate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Creates a blank SQLite database file and connects it to the project.
    Keep is_readonly=False so users can run safe DDL like CREATE TABLE.
    """
    upload_dir = Path("uploaded_databases")
    upload_dir.mkdir(exist_ok=True)

    safe_name = _safe_sqlite_name(data.name)
    file_path = upload_dir / f"user_{current_user.id}_{int(datetime.utcnow().timestamp())}_{safe_name}.sqlite"
    file_path.touch(exist_ok=False)

    url = f"sqlite:///{file_path.as_posix()}"
    ok, msg = test_connection(url)
    if not ok:
        file_path.unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail=f"SQLite creation failed: {msg}")

    conn = DatabaseConnection(
        user_id=current_user.id,
        name=data.name,
        db_type="sqlite",
        database=str(file_path),
        connection_string=url,
        is_readonly=data.is_readonly,
    )

    db.add(conn)
    db.commit()
    db.refresh(conn)

    schema = get_schema(url, "sqlite")
    conn.schema_cache = schema
    conn.schema_cached_at = datetime.utcnow()
    db.commit()
    db.refresh(conn)

    write_audit_log(
        db,
        "SQLITE_DATABASE_CREATED",
        current_user.id,
        "connection",
        str(conn.id),
        {"name": conn.name, "path": str(file_path), "is_readonly": conn.is_readonly},
        request.client.host if request.client else None,
    )

    return {
        "id": conn.id,
        "connection_id": conn.id,
        "name": conn.name,
        "db_type": conn.db_type,
        "database": conn.database,
        "is_readonly": conn.is_readonly,
        "tables": len(schema.get("tables", [])),
        "message": "Blank SQLite database created and connected. You can now run CREATE TABLE commands.",
    }


@router.post("/connections/{conn_id}/readonly")
async def update_readonly_mode(
    conn_id: int,
    is_readonly: bool,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    conn = _get_connection(conn_id, current_user.id, db)
    conn.is_readonly = is_readonly
    db.commit()
    db.refresh(conn)

    write_audit_log(
        db,
        "CONNECTION_READONLY_UPDATED",
        current_user.id,
        "connection",
        str(conn.id),
        {"is_readonly": conn.is_readonly},
        request.client.host if request.client else None,
    )

    return {"connection_id": conn.id, "is_readonly": conn.is_readonly}


@router.post("/connections/{conn_id}/refresh-schema")
async def refresh_schema(
    conn_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    conn = _get_connection(conn_id, current_user.id, db)
    url = _get_connection_url(conn)

    schema = get_schema(url, conn.db_type)
    conn.schema_cache = schema
    conn.schema_cached_at = datetime.utcnow()

    db.commit()

    return {
        "tables": len(schema.get("tables", [])),
        "refreshed_at": conn.schema_cached_at,
    }


@router.get("/connections/{conn_id}/schema")
async def get_connection_schema(
    conn_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    conn = _get_connection(conn_id, current_user.id, db)
    return conn.schema_cache or {}


@router.get("/connections/{conn_id}/tables/{table_name}/preview")
async def preview_table(
    conn_id: int,
    table_name: str,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    conn = _get_connection(conn_id, current_user.id, db)
    url = _get_connection_url(conn)

    try:
        rows, columns, rows_affected, elapsed = preview_table_data(
            url,
            table_name,
            limit,
        )

        return {
            "table": table_name,
            "columns": columns,
            "rows": rows,
            "row_count": len(rows),
            "execution_time_ms": elapsed,
        }

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/connections/upload-sqlite")
async def upload_sqlite_connection(
    name: str = Form(...),
    is_readonly: bool = Form(True),
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    allowed_ext = [".db", ".sqlite", ".sqlite3"]
    suffix = Path(file.filename).suffix.lower()

    if suffix not in allowed_ext:
        raise HTTPException(
            status_code=400,
            detail="Only .db, .sqlite, and .sqlite3 files are allowed",
        )

    upload_dir = Path("uploaded_databases")
    upload_dir.mkdir(exist_ok=True)

    safe_filename = f"user_{current_user.id}_{int(datetime.utcnow().timestamp())}_{file.filename}"
    file_path = upload_dir / safe_filename

    with file_path.open("wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    url = f"sqlite:///{file_path.as_posix()}"

    ok, msg = test_connection(url)
    if not ok:
        file_path.unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail=f"SQLite connection failed: {msg}")

    conn = DatabaseConnection(
        user_id=current_user.id,
        name=name,
        db_type="sqlite",
        database=str(file_path),
        connection_string=url,
        is_readonly=is_readonly,
    )

    db.add(conn)
    db.commit()
    db.refresh(conn)

    schema = get_schema(url, "sqlite")
    conn.schema_cache = schema
    conn.schema_cached_at = datetime.utcnow()
    db.commit()
    db.refresh(conn)

    return {
        "id": conn.id,
        "name": conn.name,
        "db_type": conn.db_type,
        "is_readonly": conn.is_readonly,
        "tables": len(schema.get("tables", [])),
        "message": "SQLite database uploaded and connected successfully",
    }


@router.delete("/connections/{conn_id}")
async def delete_connection(
    conn_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    conn = _get_connection(conn_id, current_user.id, db)

    conn.is_active = False
    db.commit()

    return {"message": "Connection removed"}


@router.post("/demo/{demo_name}/connect")
async def connect_demo(
    demo_name: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    valid_demos = ["ecommerce", "university", "hr"]

    if demo_name not in valid_demos:
        raise HTTPException(status_code=400, detail=f"Valid demos: {valid_demos}")

    url = get_demo_connection_url(demo_name)
    ok, msg = test_connection(url)

    if not ok:
        raise HTTPException(status_code=400, detail=f"Demo connection failed: {msg}")

    existing = (
        db.query(DatabaseConnection)
        .filter(
            DatabaseConnection.user_id == current_user.id,
            DatabaseConnection.name == f"Demo: {demo_name.title()}",
            DatabaseConnection.is_active == True,
        )
        .first()
    )

    if existing:
        if not existing.schema_cache:
            schema = get_schema(url, "sqlite")
            existing.schema_cache = schema
            existing.schema_cached_at = datetime.utcnow()
            db.commit()

        return {
            "connection_id": existing.id,
            "message": "Already connected",
            "tables": len(existing.schema_cache.get("tables", []) if existing.schema_cache else []),
        }

    conn = DatabaseConnection(
        user_id=current_user.id,
        name=f"Demo: {demo_name.title()}",
        db_type="sqlite",
        database=url,
        connection_string=url,
        is_readonly=True,
    )

    db.add(conn)
    db.commit()
    db.refresh(conn)

    schema = get_schema(url, "sqlite")
    conn.schema_cache = schema
    conn.schema_cached_at = datetime.utcnow()

    db.commit()

    return {
        "connection_id": conn.id,
        "tables": len(conn.schema_cache.get("tables", []) if conn.schema_cache else []),
    }

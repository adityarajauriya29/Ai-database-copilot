from __future__ import annotations

import os
import threading
from typing import Dict

from sqlalchemy import create_engine, inspect
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import settings


def _connect_args(database_url: str) -> dict:
    """Return safe SQLAlchemy connect args for local and Render databases."""
    url = (database_url or "").lower()

    if url.startswith("sqlite"):
        return {"check_same_thread": False}

    if url.startswith("postgresql") or url.startswith("postgres"):
        # Prevent Render startup from hanging forever if the DB is slow/asleep.
        return {"connect_timeout": int(os.getenv("DB_CONNECT_TIMEOUT", "8"))}

    return {}


def _engine_kwargs(database_url: str) -> dict:
    kwargs = {
        "pool_pre_ping": True,
        "pool_recycle": 300,
    }

    if (database_url or "").lower().startswith("sqlite"):
        kwargs["connect_args"] = _connect_args(database_url)
        # StaticPool keeps SQLite file DBs simple and avoids thread errors.
        kwargs["poolclass"] = StaticPool
    else:
        kwargs["connect_args"] = _connect_args(database_url)

    return kwargs


engine = create_engine(settings.DATABASE_URL, **_engine_kwargs(settings.DATABASE_URL))
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Startup migration state exposed for /api/health.
_migration_state = {
    "started": False,
    "finished": False,
    "ok": None,
    "error": None,
}
_migration_lock = threading.Lock()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _table_names(conn) -> set[str]:
    try:
        return set(inspect(conn).get_table_names())
    except Exception:
        return set()


def _column_names(conn, table_name: str) -> set[str]:
    try:
        return {col["name"] for col in inspect(conn).get_columns(table_name)}
    except Exception:
        return set()


def _quote_ident(dialect: str, name: str) -> str:
    if dialect == "postgresql":
        return '"' + name.replace('"', '""') + '"'
    return name


def _add_column_if_missing(conn, dialect: str, table_name: str, column_name: str, type_sql: str) -> None:
    if column_name in _column_names(conn, table_name):
        return

    table = _quote_ident(dialect, table_name)
    column = _quote_ident(dialect, column_name)

    if dialect == "postgresql":
        conn.exec_driver_sql(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {column} {type_sql}")
    else:
        conn.exec_driver_sql(f"ALTER TABLE {table} ADD COLUMN {column} {type_sql}")


def ensure_schema_columns() -> None:
    """Idempotent lightweight migrations for existing production DBs.

    SQLAlchemy create_all() creates new tables but does not alter old tables.
    This function safely adds columns introduced by later versions of the app.
    """
    dialect = engine.dialect.name

    if dialect == "postgresql":
        migrations: Dict[str, Dict[str, str]] = {
            "users": {
                "is_verified": "BOOLEAN DEFAULT FALSE",
                "last_login": "TIMESTAMP NULL",
                "preferred_mode": "VARCHAR DEFAULT 'simple'",
            },
            "database_connections": {
                "allow_ddl": "BOOLEAN DEFAULT FALSE",
                "schema_cache": "JSON NULL",
                "schema_cached_at": "TIMESTAMP NULL",
                "last_used": "TIMESTAMP NULL",
            },
            "query_history": {
                "is_ddl": "BOOLEAN DEFAULT FALSE",
                "session_id": "VARCHAR NULL",
                "optimization_score": "DOUBLE PRECISION NULL",
                "alternatives": "JSON NULL",
                "share_token": "VARCHAR NULL",
                "executed_at": "TIMESTAMP NULL",
            },
            "audit_logs": {
                "prev_hash": "VARCHAR NULL",
                "entry_hash": "VARCHAR NULL",
            },
        }
    elif dialect == "sqlite":
        migrations = {
            "users": {
                "is_verified": "BOOLEAN DEFAULT 0",
                "last_login": "DATETIME",
                "preferred_mode": "VARCHAR DEFAULT 'simple'",
            },
            "database_connections": {
                "allow_ddl": "BOOLEAN DEFAULT 0",
                "schema_cache": "JSON",
                "schema_cached_at": "DATETIME",
                "last_used": "DATETIME",
            },
            "query_history": {
                "is_ddl": "BOOLEAN DEFAULT 0",
                "session_id": "VARCHAR",
                "optimization_score": "FLOAT",
                "alternatives": "JSON",
                "share_token": "VARCHAR",
                "executed_at": "DATETIME",
            },
            "audit_logs": {
                "prev_hash": "VARCHAR",
                "entry_hash": "VARCHAR",
            },
        }
    else:
        migrations = {
            "database_connections": {"allow_ddl": "BOOLEAN DEFAULT FALSE"},
            "query_history": {"is_ddl": "BOOLEAN DEFAULT FALSE"},
        }

    with engine.begin() as conn:
        existing_tables = _table_names(conn)
        for table_name, columns in migrations.items():
            if table_name not in existing_tables:
                continue
            for column_name, type_sql in columns.items():
                try:
                    _add_column_if_missing(conn, dialect, table_name, column_name, type_sql)
                except Exception as exc:
                    print(f"[migration] skipped {table_name}.{column_name}: {exc}", flush=True)

    print("[migration] database schema checked", flush=True)


def run_startup_migrations() -> None:
    """Create/upgrade DB schema. Safe to run repeatedly."""
    # Import models here so Base contains every table before create_all().
    import app.models.user  # noqa: F401
    import app.models.query  # noqa: F401

    print("[startup] running database migrations", flush=True)
    Base.metadata.create_all(bind=engine)
    ensure_schema_columns()
    print("[startup] database ready", flush=True)


def run_startup_migrations_in_background() -> None:
    """Run migrations in a daemon thread so Render can bind the HTTP port fast.

    The previous version ran create_all() at import time, which can block Uvicorn
    before Render detects a port. This fixes the Render 'No open ports detected'
    timeout while still applying migrations automatically.
    """
    with _migration_lock:
        if _migration_state["started"]:
            return
        _migration_state.update({"started": True, "finished": False, "ok": None, "error": None})

    def _target():
        try:
            run_startup_migrations()
            _migration_state.update({"finished": True, "ok": True, "error": None})
        except Exception as exc:
            _migration_state.update({"finished": True, "ok": False, "error": str(exc)})
            print(f"[startup] migration failed: {exc}", flush=True)

    thread = threading.Thread(target=_target, name="startup-migrations", daemon=True)
    thread.start()


def get_migration_state() -> dict:
    return dict(_migration_state)

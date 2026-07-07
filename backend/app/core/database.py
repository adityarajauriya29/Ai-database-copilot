from sqlalchemy import create_engine, inspect
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {},
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _column_exists(table_name: str, column_name: str) -> bool:
    try:
        inspector = inspect(engine)
        if table_name not in inspector.get_table_names():
            return False
        return column_name in {col["name"] for col in inspector.get_columns(table_name)}
    except Exception:
        return False


def _add_column_if_missing(conn, dialect: str, table_name: str, column_name: str, type_sql: str):
    """Add one column only when it is missing.

    SQLAlchemy create_all() creates missing tables, but it does not update old
    tables. This lightweight migration fixes Render/PostgreSQL and local SQLite
    databases that were created before new columns were added.
    """
    if _column_exists(table_name, column_name):
        return

    if dialect == "postgresql":
        conn.exec_driver_sql(
            f'ALTER TABLE "{table_name}" ADD COLUMN IF NOT EXISTS "{column_name}" {type_sql}'
        )
    elif dialect == "sqlite":
        conn.exec_driver_sql(
            f'ALTER TABLE {table_name} ADD COLUMN {column_name} {type_sql}'
        )
    else:
        # MySQL/MariaDB fallback for local custom deployments.
        conn.exec_driver_sql(
            f'ALTER TABLE {table_name} ADD COLUMN {column_name} {type_sql}'
        )


def ensure_schema_columns():
    """Run safe startup migrations for existing production databases.

    Keep this function idempotent. It is intentionally small and only adds
    nullable/defaulted columns so it is safe to run on every Render deploy.
    """
    dialect = engine.dialect.name

    if dialect == "postgresql":
        migrations = {
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

    try:
        with engine.begin() as conn:
            for table_name, columns in migrations.items():
                if table_name not in inspect(engine).get_table_names():
                    continue
                for column_name, type_sql in columns.items():
                    try:
                        _add_column_if_missing(conn, dialect, table_name, column_name, type_sql)
                    except Exception as exc:
                        print(f"[migration] skipped {table_name}.{column_name}: {exc}")
        print("[migration] database schema checked")
    except Exception as exc:
        # Do not prevent the app from booting; the original database error will
        # still be visible in the endpoint logs if a required column is missing.
        print(f"[migration] schema check failed: {exc}")

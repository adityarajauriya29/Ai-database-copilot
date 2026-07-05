from sqlalchemy import create_engine
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


def ensure_schema_columns():
    """Lightweight SQLite migration for older local/deployed app databases.
    SQLAlchemy create_all() creates missing tables but does not add new columns,
    so older ai_copilot.db files need these ALTER statements.
    """
    if "sqlite" not in settings.DATABASE_URL:
        return

    required_columns = {
        "database_connections": {
            "allow_ddl": "BOOLEAN DEFAULT 0",
        },
        "query_history": {
            "is_ddl": "BOOLEAN DEFAULT 0",
        },
    }

    with engine.begin() as conn:
        for table, columns in required_columns.items():
            existing = {row[1] for row in conn.exec_driver_sql(f"PRAGMA table_info({table})").fetchall()}
            for column_name, column_type in columns.items():
                if column_name not in existing:
                    conn.exec_driver_sql(f"ALTER TABLE {table} ADD COLUMN {column_name} {column_type}")

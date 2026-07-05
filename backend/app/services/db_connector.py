from sqlalchemy import create_engine, text, inspect
from sqlalchemy.pool import StaticPool
from typing import Dict, Any, List, Tuple
import time
from cryptography.fernet import Fernet
import os
import re
import warnings
from pathlib import Path


# ─── Fernet key ────────────────────────────────────────────────────────────────
# IMPORTANT: If FERNET_KEY is not provided via env, we generate one at process
# start. That means encrypted passwords stored in the DB become unreadable
# after every restart. For production you MUST set FERNET_KEY in your env.
_FERNET_KEY = os.getenv("FERNET_KEY")
if not _FERNET_KEY:
    warnings.warn(
        "FERNET_KEY not set — generating an ephemeral key. Any encrypted "
        "connection passwords in the DB will become unreadable after restart. "
        "Set FERNET_KEY in your environment to fix this.",
        RuntimeWarning,
    )
    _FERNET_KEY = Fernet.generate_key()

if isinstance(_FERNET_KEY, str):
    _FERNET_KEY = _FERNET_KEY.encode()

fernet = Fernet(_FERNET_KEY)


def encrypt_password(password: str) -> str:
    return fernet.encrypt(password.encode()).decode()


def decrypt_password(encrypted: str) -> str:
    return fernet.decrypt(encrypted.encode()).decode()


def build_connection_url(
    db_type: str,
    host: str,
    port: int,
    database: str,
    username: str,
    password: str,
) -> str:
    if db_type == "postgresql":
        return f"postgresql://{username}:{password}@{host}:{port}/{database}"

    if db_type == "mysql":
        return f"mysql+pymysql://{username}:{password}@{host}:{port}/{database}"

    if db_type == "sqlite":
        return f"sqlite:///{database}"

    raise ValueError(f"Unsupported database type: {db_type}")


def _engine_kwargs(connection_url: str) -> Dict[str, Any]:
    kwargs = {}

    if "sqlite" in connection_url:
        kwargs["connect_args"] = {"check_same_thread": False}
        kwargs["poolclass"] = StaticPool

    return kwargs


def get_schema(connection_url: str, db_type: str) -> Dict[str, Any]:
    kwargs = _engine_kwargs(connection_url)

    engine = create_engine(connection_url, **kwargs)
    insp = inspect(engine)
    tables = []

    for table_name in insp.get_table_names():
        columns = []

        try:
            pk_cols = set(
                insp.get_pk_constraint(table_name).get("constrained_columns", [])
            )

            fk_map = {}
            for fk in insp.get_foreign_keys(table_name):
                referred_table = fk.get("referred_table")
                referred_columns = fk.get("referred_columns") or []

                for col in fk.get("constrained_columns", []):
                    if referred_table and referred_columns:
                        fk_map[col] = f"{referred_table}.{referred_columns[0]}"

            for col in insp.get_columns(table_name):
                columns.append(
                    {
                        "name": col["name"],
                        "type": str(col["type"]),
                        "nullable": col.get("nullable", True),
                        "primary_key": col["name"] in pk_cols,
                        "foreign_key": fk_map.get(col["name"]),
                        "default": str(col.get("default", ""))
                        if col.get("default")
                        else None,
                    }
                )

            indexes = []
            for idx in insp.get_indexes(table_name):
                indexes.append(
                    {
                        "name": idx["name"],
                        "columns": idx["column_names"],
                        "unique": idx.get("unique", False),
                    }
                )

            tables.append(
                {
                    "name": table_name,
                    "columns": columns,
                    "indexes": indexes,
                }
            )

        except Exception as e:
            tables.append(
                {
                    "name": table_name,
                    "columns": [],
                    "error": str(e),
                }
            )

    engine.dispose()

    return {
        "tables": tables,
        "db_type": db_type,
    }


def execute_query(
    connection_url: str,
    sql: str,
    timeout: int = 30,
) -> Tuple[List[Dict], List[str], int, float]:
    kwargs = _engine_kwargs(connection_url)

    engine = create_engine(connection_url, **kwargs)
    start = time.time()

    try:
        with engine.connect() as conn:
            if "sqlite" in connection_url:
                conn.execute(text(f"PRAGMA busy_timeout = {timeout * 1000}"))

            result = conn.execute(text(sql))
            elapsed = (time.time() - start) * 1000

            if result.returns_rows:
                cols = list(result.keys())
                rows = [
                    dict(zip(cols, row))
                    for row in result.fetchmany(1000)
                ]
                return rows, cols, len(rows), elapsed

            conn.commit()
            return [], [], result.rowcount, elapsed

    finally:
        engine.dispose()


def test_connection(connection_url: str) -> Tuple[bool, str]:
    try:
        kwargs = _engine_kwargs(connection_url)

        engine = create_engine(connection_url, **kwargs)

        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))

        engine.dispose()

        return True, "Connection successful"

    except Exception as e:
        return False, str(e)


# ─── Demo seed databases ──────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parents[2]
DEMO_SQLITE_PATH = BASE_DIR / "demo_databases"
USER_DB_PATH = BASE_DIR / "user_databases"


def _ensure_demo_databases():
    """Seed demo databases on demand if they are missing. This is the fix
    for `Demo connection failed` on fresh deployments where the seed script
    was not part of the build."""
    if all(
        (DEMO_SQLITE_PATH / f"{name}.db").exists()
        for name in ("ecommerce", "university", "hr")
    ):
        return
    try:
        # seed_demo_dbs.py lives at backend/seed_demo_dbs.py — import lazily
        import sys
        sys.path.insert(0, str(BASE_DIR))
        DEMO_SQLITE_PATH.mkdir(exist_ok=True)
        # The script writes to relative "demo_databases/" — run it with cwd
        # set to the backend folder so paths line up.
        old_cwd = os.getcwd()
        try:
            os.chdir(str(BASE_DIR))
            import seed_demo_dbs  # noqa: F401  (side-effect: seeds files)
        finally:
            os.chdir(old_cwd)
    except Exception as e:
        warnings.warn(f"Demo DB auto-seed failed: {e}")


def get_demo_connection_url(demo_name: str) -> str:
    _ensure_demo_databases()

    demos = {
        "ecommerce": DEMO_SQLITE_PATH / "ecommerce.db",
        "university": DEMO_SQLITE_PATH / "university.db",
        "hr": DEMO_SQLITE_PATH / "hr.db",
    }

    db_path = demos.get(demo_name)
    if db_path is None:
        raise ValueError(f"Unknown demo database: {demo_name}")

    if not db_path.exists():
        raise FileNotFoundError(
            f"Demo database file missing at {db_path}. "
            "Run `python seed_demo_dbs.py` from the backend folder."
        )

    return f"sqlite:///{db_path.as_posix()}"


def create_blank_sqlite(user_id: int, name: str) -> Tuple[str, Path]:
    """Create a brand-new empty SQLite database owned by the user.
    Returns (connection_url, file_path)."""
    USER_DB_PATH.mkdir(exist_ok=True)
    safe = re.sub(r"[^A-Za-z0-9_-]+", "_", name).strip("_") or "database"
    filename = f"user_{user_id}_{int(time.time())}_{safe}.db"
    file_path = USER_DB_PATH / filename
    # Just create the file — SQLite creates the schema container on first use.
    file_path.touch()
    return f"sqlite:///{file_path.as_posix()}", file_path


def preview_table_data(
    connection_url: str,
    table_name: str,
    limit: int = 10,
) -> Tuple[List[Dict], List[str], int, float]:
    if not re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", table_name):
        raise ValueError("Invalid table name")

    if limit == -1:
        sql = f"SELECT * FROM {table_name}"
    else:
        safe_limit = min(max(limit, 1), 5000)
        sql = f"SELECT * FROM {table_name} LIMIT {safe_limit}"

    return execute_query(connection_url, sql)

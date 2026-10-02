import os
import subprocess
import sys
from pathlib import Path

import psycopg
import pytest

# Point at a disposable test database on the same local Postgres instance,
# BEFORE any app module (which reads these at import time) is imported.
_ADMIN_URL = "postgresql://matrisathi_migrator:matrisathi_migrator_dev_pw@localhost:5433/matrisathi"
_TEST_DB = "matrisathi_test"
os.environ["DATABASE_URL_MIGRATOR"] = (
    f"postgresql+psycopg://matrisathi_migrator:matrisathi_migrator_dev_pw@localhost:5433/{_TEST_DB}"
)
os.environ["DATABASE_URL_APP"] = (
    f"postgresql+psycopg://matrisathi_app:matrisathi_app_dev_pw@localhost:5433/{_TEST_DB}"
)
# Pinned explicitly so a developer's real .env (e.g. a Supabase
# MATRISATHI_APP_DB_PASSWORD) can never leak into the test run via
# alembic/env.py's load_dotenv() and change this *cluster-wide* role's
# password out from under the dev database sharing the same local Postgres
# server. python-dotenv's load_dotenv() defaults to override=False, so
# anything already set here wins over whatever .env contains.
os.environ["MATRISATHI_APP_DB_PASSWORD"] = "matrisathi_app_dev_pw"
os.environ["JWT_SECRET"] = "test-only-secret"
os.environ["COOKIE_SECURE"] = "false"
os.environ["LOGIN_THROTTLE_MAX_ATTEMPTS"] = "3"
os.environ["LOGIN_THROTTLE_WINDOW_MINUTES"] = "15"

API_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="session", autouse=True)
def _test_database() -> None:
    with psycopg.connect(_ADMIN_URL, autocommit=True) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
                "WHERE datname = %s AND pid <> pg_backend_pid()",
                (_TEST_DB,),
            )
            cur.execute(f"DROP DATABASE IF EXISTS {_TEST_DB}")
            cur.execute(f"CREATE DATABASE {_TEST_DB}")

    subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=API_ROOT,
        env=os.environ.copy(),
        check=True,
    )


@pytest.fixture(autouse=True)
def _clean_tables(_test_database: None) -> None:
    """Truncates all app tables before every test for a clean slate, using
    the migrator role (the restricted app role cannot TRUNCATE — by design,
    see alembic/versions/0002_app_role_grants.py)."""
    admin_url = os.environ["DATABASE_URL_MIGRATOR"].replace("postgresql+psycopg://", "postgresql://")
    with psycopg.connect(admin_url, autocommit=True) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT tablename FROM pg_tables
                WHERE schemaname = 'public' AND tablename NOT IN ('alembic_version')
                """
            )
            tables = [row[0] for row in cur.fetchall()]
            if tables:
                cur.execute(f"TRUNCATE TABLE {', '.join(tables)} CASCADE")
    yield


@pytest.fixture
def client():
    from fastapi.testclient import TestClient

    from app.main import app

    with TestClient(app) as c:
        yield c


@pytest.fixture
def db_session():
    from app.core.db import SessionLocal

    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


CSRF_HEADERS = {"X-MatriSathi-Client": "web"}


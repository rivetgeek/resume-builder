"""API tests: set env before importing FastAPI app."""

import os
import tempfile
from pathlib import Path

from argon2 import PasswordHasher

_tmp = Path(tempfile.mkdtemp())
os.environ["RESUME_BUILDER_DB_PATH"] = str(_tmp / "submissions.db")
os.environ["RESUME_BUILDER_SKIP_ORIGIN_CHECK"] = "1"
os.environ["RESUME_BUILDER_COOKIE_SECURE"] = "0"
os.environ["RESUME_BUILDER_PASSWORD_HASH"] = PasswordHasher().hash("secret")
os.environ["RESUME_BUILDER_SESSION_SECRET"] = "x" * 40 + "yyyyyyyy"  # 48 chars
# Do not inherit dev bypass from the developer shell — security tests require real auth.
os.environ.pop("RESUME_BUILDER_DEV_NO_AUTH", None)
os.environ.pop("NEXT_PUBLIC_RESUME_BUILDER_DEV_NO_AUTH", None)

import pytest
from fastapi.testclient import TestClient

from api import db
from api.main import app


@pytest.fixture
def client() -> TestClient:
    db.init_db()
    with TestClient(app) as c:
        yield c


@pytest.fixture(autouse=True)
def _clear_submissions() -> None:
    yield
    try:
        with db.get_conn() as conn:
            conn.execute("DELETE FROM submissions")
    except Exception:
        pass
    from api import auth as auth_mod

    auth_mod._login_attempts.clear()
    auth_mod._generate_attempts.clear()


def auth_headers() -> dict[str, str]:
    return {
        "X-Requested-With": "XMLHttpRequest",
        "Origin": "http://testserver",
    }

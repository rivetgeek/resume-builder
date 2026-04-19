"""Security headers and cookie attributes (PRD §8.2)."""

from tests.api.conftest import auth_headers


def test_health_has_security_headers(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.headers.get("X-Content-Type-Options") == "nosniff"
    assert r.headers.get("X-Frame-Options") == "DENY"


def test_session_cookie_flags(client):
    r = client.post(
        "/api/auth/login",
        json={"password": "secret"},
        headers=auth_headers(),
    )
    assert r.status_code == 200
    sc = r.headers.get("set-cookie", "")
    assert "HttpOnly" in sc or "httponly" in sc.lower()
    assert "SameSite=strict" in sc or "samesite=strict" in sc.lower()

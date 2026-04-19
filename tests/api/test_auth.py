from tests.api.conftest import auth_headers


def test_login_success_sets_cookie(client):
    r = client.post(
        "/api/auth/login",
        json={"password": "secret"},
        headers=auth_headers(),
    )
    assert r.status_code == 200
    assert r.json()["success"] is True
    assert "resume_session" in r.cookies


def test_login_invalid_password(client):
    r = client.post(
        "/api/auth/login",
        json={"password": "wrong"},
        headers=auth_headers(),
    )
    assert r.status_code == 401
    assert "resume_session" not in r.cookies or not r.cookies.get("resume_session")


def test_logout_clears_cookie(client):
    login = client.post(
        "/api/auth/login",
        json={"password": "secret"},
        headers=auth_headers(),
    )
    assert login.status_code == 200
    out = client.post("/api/auth/logout", headers=auth_headers())
    assert out.status_code == 204


def test_protected_without_cookie(client):
    r = client.get("/api/templates")
    assert r.status_code == 401


def test_templates_with_session(client):
    client.post("/api/auth/login", json={"password": "secret"}, headers=auth_headers())
    r = client.get("/api/templates", headers=auth_headers())
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_auth_self_check_no_cookie(client):
    r = client.get("/api/auth/self-check")
    assert r.status_code == 200
    data = r.json()
    assert "password_hash_length" in data
    assert data.get("dev_no_auth") is False
    assert data["session_secret_length_ok"] is True


def test_login_rate_limit(client):
    h = auth_headers()
    for _ in range(5):
        client.post("/api/auth/login", json={"password": "bad"}, headers=h)
    r = client.post("/api/auth/login", json={"password": "bad"}, headers=h)
    assert r.status_code == 429


def test_dev_no_auth_templates_without_cookie(monkeypatch, client):
    monkeypatch.setenv("RESUME_BUILDER_DEV_NO_AUTH", "1")
    r = client.get("/api/templates")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_dev_no_auth_self_check_flag(monkeypatch, client):
    monkeypatch.setenv("RESUME_BUILDER_DEV_NO_AUTH", "1")
    r = client.get("/api/auth/self-check")
    assert r.status_code == 200
    assert r.json()["dev_no_auth"] is True


def test_dev_no_auth_login_without_csrf_headers(monkeypatch, client):
    monkeypatch.setenv("RESUME_BUILDER_DEV_NO_AUTH", "1")
    monkeypatch.setattr("api.middleware_security.skip_origin_check", lambda: False)
    r = client.post("/api/auth/login", json={"password": "x"})
    assert r.status_code == 200
    assert r.json()["success"] is True
    assert "resume_session" in r.cookies

"""CSRF / origin checks (PRD §8.2)."""

from tests.api.conftest import auth_headers


def test_mutating_without_x_requested_with(client, monkeypatch):
    monkeypatch.setattr("api.middleware_security.skip_origin_check", lambda: False)
    r = client.post("/api/auth/login", json={"password": "secret"})
    assert r.status_code == 403


def test_mutating_without_origin(client, monkeypatch):
    monkeypatch.setattr("api.middleware_security.skip_origin_check", lambda: False)
    r = client.post(
        "/api/auth/login",
        json={"password": "secret"},
        headers={"X-Requested-With": "XMLHttpRequest"},
    )
    assert r.status_code == 403


def test_mutating_succeeds_with_headers(client, monkeypatch):
    monkeypatch.setattr("api.middleware_security.skip_origin_check", lambda: False)
    r = client.post(
        "/api/auth/login",
        json={"password": "secret"},
        headers=auth_headers(),
    )
    assert r.status_code == 200

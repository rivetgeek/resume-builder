from tests.api.conftest import auth_headers


def _login(client):
    r = client.post("/api/auth/login", json={"password": "secret"}, headers=auth_headers())
    assert r.status_code == 200


def test_generate_pdf_preview(client):
    _login(client)
    body = {
        "template_id": "modern-minimal.html.j2",
        "data_file_id": "resume-example.yml",
        "formats": ["pdf"],
        "pdf_variant": "pdf/a-2b",
        "run_ats_check": False,
        "preview_only": True,
    }
    r = client.post("/api/generate", json=body, headers=auth_headers())
    assert r.status_code == 200, r.text
    data = r.json()
    assert "submission_id" in data
    sid = data["submission_id"]
    prev = client.get(f"/api/preview/{sid}", headers=auth_headers())
    assert prev.status_code == 200
    assert prev.headers["content-type"].startswith("application/pdf")
    assert prev.headers.get("X-Frame-Options") == "SAMEORIGIN"
    csp = prev.headers.get("content-security-policy", "")
    assert "frame-ancestors 'self'" in csp


def test_generate_invalid_template(client):
    _login(client)
    body = {
        "template_id": "../../etc/passwd",
        "data_file_id": "resume-example.yml",
        "formats": ["pdf"],
        "pdf_variant": "pdf/a-2b",
        "run_ats_check": False,
        "preview_only": True,
    }
    r = client.post("/api/generate", json=body, headers=auth_headers())
    assert r.status_code == 400


def test_generate_docx_bytes(client):
    _login(client)
    body = {
        "template_id": "modern-minimal.html.j2",
        "data_file_id": "resume-example.yml",
        "formats": ["pdf", "docx"],
        "pdf_variant": "pdf/a-2b",
        "run_ats_check": False,
        "preview_only": True,
    }
    r = client.post("/api/generate", json=body, headers=auth_headers())
    assert r.status_code == 200
    sid = r.json()["submission_id"]
    d = client.get(f"/api/download/{sid}/docx", headers=auth_headers())
    assert d.status_code == 200
    assert d.content[:2] == b"PK"


def test_generate_with_role_id(client):
    _login(client)
    body = {
        "template_id": "modern-minimal.html.j2",
        "data_file_id": "resume-example.yml",
        "formats": ["pdf"],
        "pdf_variant": "pdf/a-2b",
        "run_ats_check": False,
        "preview_only": True,
        "role_id": "role-123",
    }
    r = client.post("/api/generate", json=body, headers=auth_headers())
    assert r.status_code == 200

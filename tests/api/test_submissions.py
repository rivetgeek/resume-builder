from tests.api.conftest import auth_headers


def _login(client):
    client.post("/api/auth/login", json={"password": "secret"}, headers=auth_headers())


def test_submissions_list_after_generate(client):
    _login(client)
    client.post(
        "/api/generate",
        json={
            "template_id": "modern-minimal.html.j2",
            "data_file_id": "resume-example.yml",
            "formats": ["pdf"],
            "pdf_variant": "pdf/a-2b",
            "run_ats_check": False,
            "preview_only": True,
        },
        headers=auth_headers(),
    )
    r = client.get("/api/submissions?limit=25", headers=auth_headers())
    assert r.status_code == 200
    data = r.json()
    assert data["total"] >= 1
    assert len(data["items"]) >= 1


def test_submissions_notes(client):
    _login(client)
    client.post(
        "/api/generate",
        json={
            "template_id": "modern-minimal.html.j2",
            "data_file_id": "resume-example.yml",
            "formats": ["pdf"],
            "pdf_variant": "pdf/a-2b",
            "run_ats_check": False,
            "preview_only": True,
        },
        headers=auth_headers(),
    )
    lst = client.get("/api/submissions?limit=1", headers=auth_headers()).json()
    row_id = lst["items"][0]["id"]
    n = client.post(
        f"/api/submissions/{row_id}/notes",
        json={"notes": "hello"},
        headers=auth_headers(),
    )
    assert n.status_code == 200
    again = client.get("/api/submissions?limit=1", headers=auth_headers()).json()
    assert again["items"][0]["notes"] == "hello"


def test_submissions_delete(client):
    _login(client)
    client.post(
        "/api/generate",
        json={
            "template_id": "modern-minimal.html.j2",
            "data_file_id": "resume-example.yml",
            "formats": ["pdf"],
            "pdf_variant": "pdf/a-2b",
            "run_ats_check": False,
            "preview_only": True,
        },
        headers=auth_headers(),
    )
    lst = client.get("/api/submissions?limit=1", headers=auth_headers()).json()
    row_id = lst["items"][0]["id"]
    d = client.delete(f"/api/submissions/{row_id}", headers=auth_headers())
    assert d.status_code == 204

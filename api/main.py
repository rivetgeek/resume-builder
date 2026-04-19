import logging
import os
from contextlib import asynccontextmanager
from typing import Literal, Optional

from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.responses import JSONResponse

from api import db
from api.auth import (
    check_generate_rate_limit,
    check_login_rate_limit,
    clear_session_cookie,
    create_session_token,
    get_token_from_request,
    record_generate,
    record_login_failure,
    record_login_success,
    require_auth,
    set_session_cookie,
    verify_password,
)
from api.config import db_path, require_secrets, repo_root
from api.generate_service import execute_generate
from api.middleware_security import SecurityHeadersMiddleware
from api.models import GenerateBody, LoginBody, NotesBody
from api.paths_helper import disk_artifact_path, resume_stem_from_yaml
from api.preview_store import preview_store
from discovery import (
    data_display_name,
    data_origin,
    discover_data_files,
    discover_templates,
    template_display_name,
    template_origin,
)

logging.basicConfig(level=os.environ.get("RESUME_BUILDER_LOG_LEVEL", "INFO"))
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    require_secrets()
    db.init_db()
    os.makedirs(os.path.join(repo_root(), "outputs"), exist_ok=True)
    os.makedirs(os.path.dirname(db_path()), exist_ok=True)
    yield


app = FastAPI(title="Resume Builder API", version="2.0", lifespan=lifespan)
app.add_middleware(SecurityHeadersMiddleware)


def require_user(request: Request) -> None:
    require_auth(request)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/auth/self-check")
def auth_self_check(request: Request) -> dict[str, bool | str | int]:
    """Safe diagnostics for local setup (no secrets exposed)."""
    from api.config import _clean_secret_value, dev_no_auth, skip_origin_check
    from api.middleware_security import origin_would_allow

    ph = _clean_secret_value(os.environ.get("RESUME_BUILDER_PASSWORD_HASH", ""))
    sec = _clean_secret_value(os.environ.get("RESUME_BUILDER_SESSION_SECRET", ""))
    cookie_secure = os.environ.get("RESUME_BUILDER_COOKIE_SECURE", "1").lower() not in (
        "0",
        "false",
        "no",
    )
    return {
        "dev_no_auth": dev_no_auth(),
        "skip_origin_check": skip_origin_check(),
        "cookie_secure": cookie_secure,
        "password_hash_length": len(ph),
        "password_hash_starts_with_argon2": ph.startswith("$argon2"),
        "session_secret_length": len(sec),
        "session_secret_length_ok": len(sec) >= 32,
        "host_header": request.headers.get("host") or "",
        "x_forwarded_host": request.headers.get("x-forwarded-host") or "",
        "origin_header": request.headers.get("origin") or "",
        "origin_check_would_pass_for_this_request": origin_would_allow(request),
    }


@app.post("/api/auth/login")
def login(request: Request, response: Response, body: LoginBody) -> dict[str, bool]:
    from api.config import dev_no_auth

    if dev_no_auth():
        require_secrets()
        token = create_session_token()
        set_session_cookie(response, token)
        logger.warning(
            "login_bypass_dev_no_auth ip=%s — RESUME_BUILDER_DEV_NO_AUTH is set; do not use in production",
            request.client.host if request.client else "-",
        )
        return {"success": True}

    check_login_rate_limit(request)
    ph, _ = require_secrets()
    ip = request.client.host if request.client else "-"
    pwd_len = len(body.password)
    h_len = len(ph)
    h_ok = ph.startswith("$argon2")
    logger.info(
        "login_attempt ip=%s supplied_password_length=%s configured_hash_length=%s hash_starts_with_argon2=%s",
        ip,
        pwd_len,
        h_len,
        h_ok,
    )
    if not h_ok:
        logger.error(
            "login_misconfigured: RESUME_BUILDER_PASSWORD_HASH does not look like Argon2 "
            "(expected to start with $argon2). Check repo-root .env and restart uvicorn."
        )
    if verify_password(body.password, ph):
        record_login_success(request)
        token = create_session_token()
        set_session_cookie(response, token)
        logger.info("login_success ip=%s", ip)
        return {"success": True}
    record_login_failure(request)
    logger.warning(
        "login_verify_failed ip=%s (password wrong for this hash, or hash/env mismatch — "
        "regenerate hash with: python -c \"from argon2 import PasswordHasher; print(PasswordHasher().hash('YOUR_PASSWORD'))\")",
        ip,
    )
    raise HTTPException(status_code=401, detail="invalid_credentials")


@app.post("/api/auth/logout")
def logout(response: Response) -> Response:
    clear_session_cookie(response)
    return Response(status_code=204)


@app.get("/api/auth/status")
def auth_status(request: Request) -> dict[str, bool]:
    from api.config import dev_no_auth

    if dev_no_auth():
        return {"authenticated": True}
    token = get_token_from_request(request)
    if not token:
        return {"authenticated": False}
    try:
        require_auth(request)
        return {"authenticated": True}
    except HTTPException:
        return {"authenticated": False}


@app.get("/api/templates", dependencies=[Depends(require_user)])
def list_templates() -> list[dict[str, str]]:
    root = repo_root()
    ids, paths = discover_templates(root)
    return [
        {
            "id": tid,
            "name": template_display_name(tid),
            "origin": template_origin(paths[tid]),
        }
        for tid in ids
    ]


@app.get("/api/data-files", dependencies=[Depends(require_user)])
def list_data_files() -> list[dict[str, str]]:
    root = repo_root()
    ids, paths = discover_data_files(root)
    return [
        {
            "id": fid,
            "name": data_display_name(fid),
            "origin": data_origin(paths[fid]),
        }
        for fid in ids
    ]


@app.post("/api/generate", dependencies=[Depends(require_user)])
def generate(request: Request, body: GenerateBody) -> JSONResponse:
    check_generate_rate_limit(request)
    record_generate(request)
    try:
        result = execute_generate(
            template_id=body.template_id,
            data_file_id=body.data_file_id,
            formats=list(body.formats),
            pdf_variant=body.pdf_variant,
            run_ats_check=body.run_ats_check,
            preview_only=body.preview_only,
            role_id=body.role_id,
        )
    except ValueError as e:
        msg = str(e)
        if msg in ("invalid_id", "unknown_id"):
            raise HTTPException(status_code=400, detail={"error": "validation", "details": msg})
        if msg.startswith("generation_failed"):
            raise HTTPException(
                status_code=422,
                detail={"error": "generation_failed", "details": msg},
            )
        raise HTTPException(status_code=400, detail={"error": "validation", "details": msg})
    logger.info(
        "generate_ok submission=%s template=%s data=%s preview=%s",
        result["submission_id"],
        body.template_id,
        body.data_file_id,
        body.preview_only,
    )
    return JSONResponse(result)


def _stem_for_download(data_file: str) -> str:
    _, dp = discover_data_files(repo_root())
    path = dp[data_file]
    _, _, stem = resume_stem_from_yaml(path)
    return stem


@app.get("/api/preview/{submission_id}", dependencies=[Depends(require_user)])
def preview(submission_id: str) -> Response:
    row = db.get_by_uuid(submission_id)
    if not row:
        raise HTTPException(status_code=404, detail="not_found")
    stem = _stem_for_download(row["data_file"])
    art = preview_store.get(submission_id)
    if art and art.pdf_bytes:
        return Response(
            content=art.pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f'inline; filename="{stem}.pdf"'},
        )
    path = disk_artifact_path(row["data_file"], "pdf")
    if not path:
        raise HTTPException(status_code=404, detail="expired_or_missing")
    with open(path, "rb") as f:
        data = f.read()
    return Response(
        content=data,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{stem}.pdf"'},
    )


@app.get("/api/download/{submission_id}/{fmt}", dependencies=[Depends(require_user)])
def download(
    submission_id: str,
    fmt: Literal["pdf", "docx", "html"],
) -> Response:
    row = db.get_by_uuid(submission_id)
    if not row:
        raise HTTPException(status_code=404, detail="not_found")
    stem = _stem_for_download(row["data_file"])
    art = preview_store.get(submission_id)

    if fmt == "pdf":
        content: Optional[bytes] = None
        if art and art.pdf_bytes:
            content = art.pdf_bytes
        else:
            p = disk_artifact_path(row["data_file"], "pdf")
            if p:
                with open(p, "rb") as f:
                    content = f.read()
        if not content:
            raise HTTPException(status_code=404, detail="not_found")
        return Response(
            content=content,
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{stem}.pdf"'},
        )

    if fmt == "html":
        if art and art.html_str:
            return Response(
                content=art.html_str.encode("utf-8"),
                media_type="text/html; charset=utf-8",
                headers={"Content-Disposition": f'attachment; filename="{stem}.html"'},
            )
        p = disk_artifact_path(row["data_file"], "html")
        if not p:
            raise HTTPException(status_code=404, detail="not_found")
        with open(p, "rb") as f:
            content = f.read()
        return Response(
            content=content,
            media_type="text/html; charset=utf-8",
            headers={"Content-Disposition": f'attachment; filename="{stem}.html"'},
        )

    if fmt == "docx":
        if art and art.docx_bytes:
            return Response(
                content=art.docx_bytes,
                media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                headers={"Content-Disposition": f'attachment; filename="{stem}.docx"'},
            )
        p = disk_artifact_path(row["data_file"], "docx")
        if not p:
            raise HTTPException(status_code=404, detail="not_found")
        with open(p, "rb") as f:
            content = f.read()
        return Response(
            content=content,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers={"Content-Disposition": f'attachment; filename="{stem}.docx"'},
        )

    raise HTTPException(status_code=400, detail="bad_format")


@app.get("/api/submissions", dependencies=[Depends(require_user)])
def submissions(
    limit: int = 25,
    offset: int = 0,
    template_id: Optional[str] = None,
    data_file_id: Optional[str] = None,
) -> dict:
    items, total = db.list_submissions(
        limit=min(limit, 100),
        offset=max(offset, 0),
        template_id=template_id,
        data_file_id=data_file_id,
    )
    return {"items": items, "total": total}


@app.post("/api/submissions/{row_id}/notes", dependencies=[Depends(require_user)])
def post_notes(row_id: int, body: NotesBody) -> dict[str, bool]:
    db.update_notes(row_id, body.notes)
    return {"success": True}


@app.delete("/api/submissions/{row_id}", dependencies=[Depends(require_user)])
def delete_row(row_id: int) -> Response:
    db.delete_submission(row_id)
    return Response(status_code=204)

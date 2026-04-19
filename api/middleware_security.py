import logging
import re
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from api.config import dev_no_auth, skip_origin_check

logger = logging.getLogger(__name__)

SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Permissions-Policy": "geolocation=(), camera=(), microphone=()",
    "X-Frame-Options": "DENY",
    "Content-Security-Policy": (
        "default-src 'self'; object-src 'self'; frame-ancestors 'none'; "
        "base-uri 'self'; form-action 'self';"
    ),
}

# PDF preview is loaded in an <iframe> on the same origin (Next proxies /api/preview/*).
_PREVIEW_CSP = (
    "default-src 'self'; object-src 'self'; frame-ancestors 'self'; "
    "base-uri 'self'; form-action 'self';"
)


def _apply_security_headers(response: Response, path: str) -> None:
    preview_iframe = path.startswith("/api/preview/")
    for k, v in SECURITY_HEADERS.items():
        if preview_iframe and k == "X-Frame-Options":
            response.headers[k] = "SAMEORIGIN"
        elif preview_iframe and k == "Content-Security-Policy":
            response.headers[k] = _PREVIEW_CSP
        else:
            response.headers[k] = v


def _is_mutating(path: str, method: str) -> bool:
    if method not in ("POST", "PUT", "PATCH", "DELETE"):
        return False
    if path.startswith("/api/auth/login") or path.startswith("/api/auth/logout"):
        return True
    if path.startswith("/api/generate"):
        return True
    if re.match(r"^/api/submissions/\d+/notes$", path) and method == "POST":
        return True
    if re.match(r"^/api/submissions/\d+$", path) and method == "DELETE":
        return True
    return False


def _origin_ok(request: Request) -> bool:
    """Origin must match the public Host (or X-Forwarded-Host when behind Next.js / a reverse proxy)."""
    if skip_origin_check():
        return True
    origin = request.headers.get("origin")
    if not origin:
        return False
    try:
        from urllib.parse import urlparse

        o = urlparse(origin)
        if not o.scheme or not o.netloc:
            return False
        origin_netloc = o.netloc
        origin_host = origin_netloc.split(":", 1)[0]

        candidates: list[str] = []
        host = request.headers.get("host", "").strip()
        if host:
            candidates.append(host)
        xf = request.headers.get("x-forwarded-host", "")
        for part in xf.split(","):
            p = part.strip()
            if p:
                candidates.append(p)

        for c in candidates:
            if origin_netloc == c:
                return True
            ch = c.split(":", 1)[0]
            if ch == origin_host:
                return True
        return False
    except Exception:
        return False


def origin_would_allow(request: Request) -> bool:
    """Expose origin check for diagnostics (e.g. GET /api/auth/self-check)."""
    return _origin_ok(request)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        if dev_no_auth():
            response: Response = await call_next(request)
            _apply_security_headers(response, request.url.path)
            return response
        if _is_mutating(request.url.path, request.method):
            if request.headers.get("X-Requested-With") != "XMLHttpRequest":
                return Response(status_code=403, content=b"missing_x_requested_with")
            if not _origin_ok(request):
                return Response(status_code=403, content=b"origin_mismatch")

        response: Response = await call_next(request)
        _apply_security_headers(response, request.url.path)
        return response

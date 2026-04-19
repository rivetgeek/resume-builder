import logging
import time
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Optional

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError
from fastapi import HTTPException, Request, Response

from api.config import dev_no_auth, require_secrets, session_max_age_days

logger = logging.getLogger(__name__)

COOKIE_NAME = "resume_session"
JWT_ALG = "HS256"

# OWASP 2024-ish memory cost ~19 MiB: m_cost in KiB (2**15 = 32768 KiB = 32 MiB; use 19456 ≈ 19 MiB)
_hasher = PasswordHasher(time_cost=2, memory_cost=19456, parallelism=1, hash_len=32, salt_len=16)

_login_attempts: dict[str, list[float]] = defaultdict(list)
_generate_attempts: dict[str, list[float]] = defaultdict(list)


def verify_password(plain: str, password_hash: str) -> bool:
    try:
        _hasher.verify(password_hash, plain)
        if _hasher.check_needs_rehash(password_hash):
            logger.warning("Password hash should be rehashed with current parameters")
        return True
    except VerifyMismatchError:
        return False
    except InvalidHashError as e:
        logger.error(
            "argon2_invalid_hash (check .env: full hash on one line, no stray quotes): %s",
            e.__class__.__name__,
        )
        return False
    except Exception as e:
        logger.exception("argon2_verify_unexpected_error: %s", e)
        return False


def create_session_token() -> str:
    _, secret = require_secrets()
    now = datetime.now(timezone.utc)
    exp = now + timedelta(days=session_max_age_days())
    payload = {
        "sub": "user",
        "iat": int(now.timestamp()),
        "exp": int(exp.timestamp()),
        "jti": f"{int(now.timestamp() * 1000)}",
    }
    return jwt.encode(payload, secret, algorithm=JWT_ALG)


def decode_session_token(token: str) -> dict:
    _, secret = require_secrets()
    return jwt.decode(token, secret, algorithms=[JWT_ALG])


def _cookie_secure() -> bool:
    import os

    return os.environ.get("RESUME_BUILDER_COOKIE_SECURE", "1").lower() not in ("0", "false", "no")


def set_session_cookie(response: Response, token: str) -> None:
    max_age = session_max_age_days() * 86400
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        max_age=max_age,
        httponly=True,
        secure=_cookie_secure(),
        samesite="strict",
        path="/",
    )


def clear_session_cookie(response: Response) -> None:
    response.delete_cookie(COOKIE_NAME, path="/")


def get_token_from_request(request: Request) -> Optional[str]:
    return request.cookies.get(COOKIE_NAME)


def require_auth(request: Request) -> None:
    if dev_no_auth():
        return
    token = get_token_from_request(request)
    if not token:
        raise HTTPException(status_code=401, detail="not_authenticated")
    try:
        decode_session_token(token)
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="session_expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="invalid_session")


def _client_ip(request: Request) -> str:
    if request.client:
        return request.client.host or "unknown"
    return "unknown"


def check_login_rate_limit(request: Request) -> None:
    if dev_no_auth():
        return
    ip = _client_ip(request)
    now = time.time()
    window = 15 * 60
    cutoff = now - window
    attempts = [t for t in _login_attempts[ip] if t > cutoff]
    _login_attempts[ip] = attempts
    if len(attempts) >= 5:
        retry = max(0, int(window - (now - attempts[0])))
        raise HTTPException(
            status_code=429,
            detail="rate_limited",
            headers={"Retry-After": str(retry)},
        )


def record_login_failure(request: Request) -> None:
    if dev_no_auth():
        return
    _login_attempts[_client_ip(request)].append(time.time())


def record_login_success(request: Request) -> None:
    ip = _client_ip(request)
    _login_attempts[ip] = []


def check_generate_rate_limit(request: Request) -> None:
    if dev_no_auth():
        return
    token = get_token_from_request(request)
    key = token or _client_ip(request)
    now = time.time()
    window = 60
    cutoff = now - window
    attempts = [t for t in _generate_attempts[key] if t > cutoff]
    _generate_attempts[key] = attempts
    if len(attempts) >= 30:
        raise HTTPException(status_code=429, detail="generate_rate_limited")


def record_generate(request: Request) -> None:
    if dev_no_auth():
        return
    token = get_token_from_request(request)
    key = token or _client_ip(request)
    _generate_attempts[key].append(time.time())

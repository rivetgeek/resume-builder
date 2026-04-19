import os
from functools import lru_cache
from pathlib import Path


def _load_dotenv() -> None:
    """Load repo-root `.env` into the process (so vars exist before `require_secrets()`)."""
    try:
        from dotenv import load_dotenv
    except ImportError:
        return
    root = Path(__file__).resolve().parent.parent
    env_file = root / ".env"
    if env_file.is_file():
        # Argon2 PHC strings contain many `$` — interpolation would mangle them unless quoted.
        load_dotenv(env_file, interpolate=False)


_load_dotenv()


def repo_root() -> str:
    return os.path.abspath(
        os.environ.get("RESUME_BUILDER_REPO_ROOT", os.path.join(os.path.dirname(__file__), ".."))
    )


def db_path() -> str:
    default = os.path.join(repo_root(), "db", "submissions.db")
    return os.environ.get("RESUME_BUILDER_DB_PATH", default)


def session_max_age_days() -> int:
    return int(os.environ.get("RESUME_BUILDER_SESSION_MAX_AGE_DAYS", "30"))


def _clean_secret_value(raw: str) -> str:
    """Strip whitespace and one pair of surrounding quotes (common in .env files)."""
    s = raw.strip()
    if len(s) >= 2 and s[0] == s[-1] and s[0] in ("'", '"'):
        s = s[1:-1].strip()
    return s


@lru_cache
def require_secrets() -> tuple[str, str]:
    ph = _clean_secret_value(os.environ.get("RESUME_BUILDER_PASSWORD_HASH", ""))
    sec = _clean_secret_value(os.environ.get("RESUME_BUILDER_SESSION_SECRET", ""))
    if not ph or not sec:
        raise RuntimeError(
            "RESUME_BUILDER_PASSWORD_HASH and RESUME_BUILDER_SESSION_SECRET must be set."
        )
    if len(sec) < 32:
        raise RuntimeError("RESUME_BUILDER_SESSION_SECRET must be at least 32 characters.")
    return ph, sec


def skip_origin_check() -> bool:
    return os.environ.get("RESUME_BUILDER_SKIP_ORIGIN_CHECK", "").lower() in ("1", "true", "yes")


def dev_no_auth() -> bool:
    """Local development only: skip session checks on protected API routes (never enable in production)."""
    return os.environ.get("RESUME_BUILDER_DEV_NO_AUTH", "").lower() in ("1", "true", "yes")

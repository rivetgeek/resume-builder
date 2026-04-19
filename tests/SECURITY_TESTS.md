# Security test matrix (Resume Builder v2 web surface)

This document maps automated tests to PRD §8.2 controls. It is the auditable artifact for the web API and related client expectations.

| Test | Module | Threat / control | Expected |
|------|--------|------------------|----------|
| `test_path_traversal_prevention` | `test_security.py` | §8.2 path traversal — filename allowlist | Invalid suffix patterns rejected |
| `test_xss_protection_in_name` | `test_security.py` | §8.2 XSS — Jinja2 autoescape | Payload escaped in HTML |
| `test_xss_protection_in_summary` | `test_security.py` | §8.2 XSS | Script escaped |
| `test_login_success_sets_cookie` | `test_auth.py` | §8.2 auth session | 200 + session cookie |
| `test_login_invalid_password` | `test_auth.py` | §8.2 credential privacy | 401, no session |
| `test_logout_clears_cookie` | `test_auth.py` | §8.2 logout | 204 |
| `test_protected_without_cookie` | `test_auth.py` | §8.2 protected routes | 401 |
| `test_templates_with_session` | `test_auth.py` | §8.2 session required | 200 with cookie |
| `test_login_rate_limit` | `test_auth.py` | §8.2 brute-force — login rate limit | 6th failure → 429 |
| `test_mutating_without_x_requested_with` | `test_csrf.py` | §8.2 CSRF depth — `X-Requested-With` | 403 |
| `test_mutating_without_origin` | `test_csrf.py` | §8.2 same-origin | 403 without `Origin` |
| `test_mutating_succeeds_with_headers` | `test_csrf.py` | Positive control | 200 with headers |
| `test_health_has_security_headers` | `test_security_headers.py` | §8.2 security headers | `nosniff`, `DENY` |
| `test_session_cookie_flags` | `test_security_headers.py` | §8.2 cookie flags | `HttpOnly`, `SameSite=Strict` |
| `test_generate_invalid_template` | `test_generate.py` | §8.2 path traversal / allowlist | 400 for bad id |
| `test_generate_pdf_preview` | `test_generate.py` | Happy path PDF | 200 + PDF bytes |
| `test_generate_docx_bytes` | `test_generate.py` | DOCX pipeline | Valid ZIP (`PK`) |

## Per-test notes

### `test_login_rate_limit`

- **Threat:** brute-force password guessing.
- **Control:** §8.2 — rate limiting on `/api/auth/login`.
- **Strategy:** Five failed attempts, then a sixth within the window.
- **Expected:** HTTP 429 with `Retry-After`.
- **Coverage gaps:** In-memory limiter resets on process restart; not distributed across replicas.
- **Related:** `test_login_invalid_password`.

### `test_mutating_without_origin`

- **Threat:** CSRF from unrelated sites.
- **Control:** §8.2 — `Origin` check + `SameSite=Strict` cookies.
- **Strategy:** With enforcement on (`skip_origin_check` false), POST without `Origin` must fail even with `X-Requested-With`.
- **Expected:** 403.
- **Coverage gaps:** Does not test browser preflight `OPTIONS` behavior.
- **Related:** `test_mutating_succeeds_with_headers`.

### `test_session_cookie_flags`

- **Threat:** token theft via XSS reading cookies.
- **Control:** §8.2 — `HttpOnly` session cookie.
- **Strategy:** Inspect `Set-Cookie` after successful login (dev mode may omit `Secure` when `RESUME_BUILDER_COOKIE_SECURE=0`).
- **Expected:** `HttpOnly` and `SameSite=Strict` present; `Secure` in production with default env.
- **Coverage gaps:** Does not validate JWT signature strength beyond secret length check at startup.

### `test_generate_invalid_template`

- **Threat:** arbitrary file read via crafted `template_id`.
- **Control:** §8.2 — allowlist from directory scan + filename regex.
- **Expected:** HTTP 400.
- **Coverage gaps:** Does not fuzz every Unicode normalization edge case.

---

End of security test documentation for v2.0.

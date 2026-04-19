# PRD: Resume Builder — Web Interface (v2.0)

**Owner:** Remington Winters
**Target repo:** `rivetgeek/resume-builder` (additive, non-breaking)
**Deployment target:** Docker on Synology, accessed over Tailscale
**Document type:** Implementation spec — consumed by Cursor
**Status:** Draft v1.0

---

## 1. Summary

Add a web interface to the existing Python resume-builder CLI. The web interface is additive: the CLI continues to function unchanged. The web interface is a Next.js app that talks to a FastAPI wrapper around the existing Python generation pipeline. Deployed as a two-container Docker Compose stack on Synology, accessed over Tailscale.

The interface exposes the existing workflow as a dropdown-driven GUI: pick a template, pick a YAML data file, preview the rendered PDF live, download as PDF or DOCX. All existing CLI feature flags are represented in the UI. A lightweight submission tracker logs each generation event to SQLite for audit and future Vulture integration.

Single-user, password-protected. Runs on the Tailnet only — no public exposure.

## 2. Goals & Non-Goals

### In scope

- Next.js frontend with dark/light theming, mobile-responsive
- FastAPI wrapper around existing `resume_builder.py` and `ats_checker.py` — no changes to the Python generation logic itself
- Live PDF preview (debounced re-render on template/data change)
- Download in PDF (existing) and DOCX (new) formats
- All existing CLI flags exposed as UI controls
- Single-user password authentication (argon2id hash, env-configured)
- Session-based auth with signed HTTP-only cookies
- SQLite-backed submission/generation log
- Security test suite extended to cover the new web surface
- Docker Compose deployment to Synology

### Out of scope (explicitly)

- CLI changes or removal — CLI continues to work exactly as today
- Multi-user support
- Password recovery flows — password reset is via env var + container restart (see §10 for future revisit)
- Public internet exposure — Tailnet only
- Vulture integration — API contract designed to anticipate it, but no Vulture-specific code
- In-app YAML editing — file selection only for v2.0 (see §14 future work)
- In-app template editing — file selection only for v2.0

### Future work (named, not built)

- Vulture integration via `POST /api/submissions` with optional `role_id` field
- In-browser YAML editing with schema validation
- Template authoring UI
- Multi-user support + SSO (if open-sourced or sold)

## 3. Users

Single user: Remington. Accessing from desktop or mobile over Tailscale, primarily during active job search activity. Typical session: pick data file + template, preview, download PDF for application, occasionally download DOCX for recruiter submissions.

## 4. Architecture

### 4.1 Component overview

```
┌──────────────────────────────────────────────────────────┐
│                     Tailnet (only)                        │
└──────────────────────────────────────────────────────────┘
                            │
                            ▼
              ┌─────────────────────────────┐
              │   Next.js Frontend (web)    │
              │   - App Router              │
              │   - React Server Components │
              │   - Tailwind CSS            │
              │   Port: 3000                │
              └──────────────┬──────────────┘
                             │ HTTP (internal network only)
                             ▼
              ┌─────────────────────────────┐
              │   FastAPI Backend (api)     │
              │   - Auth (argon2id + JWT)   │
              │   - Wraps resume_builder.py │
              │   - SQLite submissions DB   │
              │   - DOCX generation         │
              │   Port: 8000 (internal)     │
              └──────────────┬──────────────┘
                             │
                ┌────────────┴────────────┐
                ▼                         ▼
         ┌──────────────┐         ┌──────────────┐
         │ Existing     │         │ SQLite       │
         │ Python       │         │ submissions  │
         │ pipeline     │         │ .db          │
         │ (unchanged)  │         │              │
         └──────────────┘         └──────────────┘
                │
                ▼
         Read-only volume mounts:
         - templates/html
         - data/  (read+write for uploaded YAMLs — future)
         - fonts/
         - outputs/  (generated files, gitignored)
```

### 4.2 Technology choices

| Layer | Choice | Rationale |
|---|---|---|
| Frontend framework | Next.js 14+ (App Router) | SSR, API routes, image optimization, strong TS support |
| UI library | React 18+ with Tailwind CSS | Matches style requirements; no heavy UI kit |
| Backend | FastAPI (Python 3.11+) | Wraps existing Python cleanly; async; auto OpenAPI |
| Template engine | Jinja2 (existing, unchanged) | No rewrite |
| PDF engine | WeasyPrint (existing, unchanged) | Preserves PDF/A variant support |
| DOCX engine | `python-docx` | Mature, pure Python, no system deps |
| Auth password hash | argon2id via `argon2-cffi` | Current best practice |
| Session | Signed JWT in HTTP-only cookie | Stateless, simple for single-user |
| Database | SQLite (WAL mode) | Zero-config, matches Vulture stack, sufficient for single-user |
| Deploy | Docker Compose | Native on Synology, two services |
| Reverse proxy | None required | Tailscale provides TLS via MagicDNS; optional Caddy sidecar for HSTS |

### 4.3 Why two services, not one

The Python pipeline is mature, tested, and stable. Reimplementing in Node would lose PDF/A compliance (Puppeteer cannot produce PDF/A), require rewriting three Jinja2 templates into Nunjucks, and duplicate the ATS checker logic. Keeping them separate preserves the existing test surface and the existing CLI. The cost is one extra container — acceptable on Synology.

### 4.4 No changes to existing Python code

**Critical constraint:** `resume_builder.py`, `ats_checker.py`, and the Jinja2 templates MUST NOT be modified. The FastAPI wrapper imports `render_resume` and `ATSComplianceChecker` and calls them as-is.

If any refactor is required to expose the pipeline cleanly to FastAPI, it should be done by extracting `if __name__ == "__main__":` logic from `resume_builder.py` into a thin `cli.py` wrapper — leaving `render_resume()` itself untouched and fully backward-compatible.

## 5. Feature requirements

### 5.1 Core workflow

The primary UI is a single page with:

1. **Template dropdown** — populated from `templates/html/*.html.j2` and `templates/html/personal/*.html.j2` (same discovery logic as the CLI at `resume_builder.py` lines 92–114)
2. **Data file dropdown** — populated from `data/*.yml` and `data/personal/*.yml` (same logic as CLI lines 129–148)
3. **Options panel** — exposes all CLI flags (see §5.2)
4. **Generate button** — triggers rendering
5. **Live preview pane** — shows the rendered PDF inline
6. **Download controls** — PDF (default), PDF variant selector, DOCX

Changing template or data file triggers a debounced (500ms) re-render to update the preview.

### 5.2 Feature flag coverage

Every CLI flag must have a UI equivalent:

| CLI flag | UI control | Default |
|---|---|---|
| `--pdf` | Toggle: "Generate PDF" | On |
| `--no-ats-check` | Toggle: "Run ATS compliance check" (inverted) | Off (matches CLI default behavior) |
| `--pdf-variant` | Dropdown: PDF/A-1b, PDF/A-2b, PDF/A-3b, PDF/A-4b | PDF/A-2b |

New UI-only controls:
- Format selector: PDF / DOCX / HTML (download only — preview is always PDF)
- "View ATS report" — opens report panel if ATS check was run

### 5.3 Live preview

- Rendered PDF displayed inline via `<iframe src="/api/preview/:submission_id">` or PDF.js rendering
- Re-renders on debounced change (500ms) to template or data file selection
- Loading spinner while WeasyPrint runs (typically 1–2 seconds)
- Error state with readable message if generation fails (e.g., missing contact fields, WeasyPrint dependency issue)
- Preview PDF is stored ephemerally; not written to `outputs/`

### 5.4 Downloads

Three download actions:

- **PDF** — uses existing WeasyPrint pipeline with selected PDF/A variant
- **DOCX** — new: renders the Jinja2 template to HTML, then converts HTML → DOCX via `python-docx`. Preserve section structure (name, title, contact, summary, experience, skills). ATS-friendly: no tables for layout, use paragraph styles for headings
- **HTML** — returns the rendered HTML directly (useful for debugging, kept behind a "developer" toggle)

Filename convention matches existing CLI: `{First}_{Last}_Resume.{ext}`.

DOCX conversion notes:
- Input: rendered HTML string
- Output: `.docx` file
- Must preserve: headings, bold/italic, bullet lists, paragraph breaks
- Must NOT include: CSS styling (drop it), images, tables-as-layout
- Use `python-docx` with a minimal style map. Do not attempt pixel-perfect fidelity — ATS-friendly plain DOCX is the goal.

### 5.5 Submission tracking

Every generation event is logged to SQLite:

```sql
CREATE TABLE submissions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT NOT NULL,              -- ISO 8601 UTC
    template_name TEXT NOT NULL,           -- e.g., "modern-minimal.html.j2"
    data_file TEXT NOT NULL,               -- e.g., "resume-Director-SaaS.yml"
    pdf_variant TEXT,                      -- nullable
    ats_check_run INTEGER NOT NULL,        -- boolean 0/1
    ats_errors_count INTEGER,              -- nullable, only if ATS ran
    ats_warnings_count INTEGER,
    ats_suggestions_count INTEGER,
    output_formats TEXT NOT NULL,          -- JSON array: ["pdf","docx"]
    output_hash TEXT,                      -- SHA-256 of canonical PDF bytes (for dedup/integrity)
    role_id TEXT,                          -- RESERVED for Vulture; nullable
    notes TEXT                             -- user-added label, nullable
);

CREATE INDEX idx_submissions_created ON submissions(created_at DESC);
CREATE INDEX idx_submissions_role ON submissions(role_id) WHERE role_id IS NOT NULL;
```

A simple history view lists recent submissions with filter by template/data file. This is explicitly NOT a full Vulture clone — it is a local log. The `role_id` column is reserved for future integration and should not be populated in v2.0.

### 5.6 Authentication

- Single password, hashed with argon2id (`argon2-cffi`, defaults tuned for current hardware)
- Hash stored in environment variable `RESUME_BUILDER_PASSWORD_HASH` (read at container start)
- Login endpoint validates plaintext input against the hash
- On success, sets signed HTTP-only cookie containing a JWT
- Session secret stored in env var `RESUME_BUILDER_SESSION_SECRET` (must be ≥32 random bytes)
- Session cookie: `HttpOnly`, `Secure`, `SameSite=Strict`, 30-day sliding expiration
- Logout clears the cookie server-side and client-side
- No registration, no password recovery in v2.0

Password rotation is operational: edit `.env`, restart the `api` container. This is acceptable for a single-user, self-hosted tool. If this project is ever open-sourced or sold, password recovery and multi-user support become required (see §14).

## 6. UI & styling

### 6.1 Visual design

Minimal, professional. No illustrations, no gradients, no shadows beyond subtle elevation on interactive elements. Typography-first.

**Light mode:**
- Background: cream (`#F5F1E8`)
- Foreground: charcoal (`#2A2A2A`)
- Muted text: `#6B6B6B`
- Borders/dividers: `#D4CEBF`
- Accent (focus rings, primary buttons): `#2A2A2A` with cream text

**Dark mode:**
- Background: charcoal (`#1E1E1E`)
- Foreground: light heather gray (`#D0D0D0`)
- Muted text: `#8A8A8A`
- Borders/dividers: `#333333`
- Accent: `#D0D0D0` with charcoal text

Theme values defined as CSS custom properties in a single `theme.css` file and consumed via Tailwind's `@apply` or theme extension. Do not hardcode hex values in components.

### 6.2 Theme toggle

- Toggle control in header, persists to `localStorage`
- Default: `prefers-color-scheme` from the browser
- SSR-safe: initial render should not flash wrong theme (use a blocking script in `<head>` or `next-themes`)

### 6.3 Layout & responsiveness

Desktop (≥1024px):
- Two-column layout: controls on left (~40%), preview on right (~60%)
- Downloads fixed at bottom-right of preview pane

Tablet (640–1023px):
- Stacked: controls on top, preview below
- Preview collapsible

Mobile (<640px):
- Stacked, controls collapsed by default behind an accordion
- Preview pane full-width, scrollable
- Downloads in a sticky footer

All interactive elements must have ≥44×44px tap targets. Form controls must pass WCAG AA contrast in both themes.

### 6.4 Typography

- Body: system font stack (`system-ui, -apple-system, ...`) — no web font downloads
- Monospace (for file names, hashes): `ui-monospace, 'SF Mono', Menlo, monospace`
- Base size: 16px; scale 1.25 (major third)

### 6.5 Component inventory (minimum)

- `Header` (logo, theme toggle, logout)
- `LoginForm`
- `TemplateSelect`, `DataFileSelect` — native `<select>` with custom styling
- `OptionsPanel` — toggles and radio group for PDF variant
- `GenerateButton` — primary action, shows loading state
- `PreviewPane` — PDF iframe with error boundary
- `DownloadBar` — PDF/DOCX/HTML buttons, variant selector
- `SubmissionHistory` — paginated table, ≤25 rows per page
- `ATSReportModal` — shows ATS errors/warnings/suggestions
- `Toast` — error/success notifications (no library — build it)

No UI kit. Use Tailwind directly. Use `clsx` or `cva` for variant composition if needed.

## 7. API specification

All endpoints prefixed `/api`. JSON bodies unless noted. All mutating endpoints require a valid session cookie.

### 7.1 Auth

```
POST /api/auth/login
  body: { "password": "string" }
  200: { "success": true } + sets cookie
  401: { "error": "invalid_credentials" }
  429: { "error": "rate_limited", "retry_after_seconds": N }

POST /api/auth/logout
  204: (clears cookie)

GET /api/auth/status
  200: { "authenticated": true | false }
```

Login endpoint is rate-limited: 5 attempts per IP per 15 minutes. Exceeding triggers a 15-minute lockout. Implementation: in-memory counter is acceptable for v2.0 (single container, single user).

### 7.2 Resources

```
GET /api/templates
  200: [ { "id": "modern-minimal.html.j2", "name": "Modern Minimal", "origin": "public|personal" } ]

GET /api/data-files
  200: [ { "id": "resume-Director-SaaS.yml", "name": "Director-SaaS", "origin": "public|personal" } ]
```

### 7.3 Generation

```
POST /api/generate
  body: {
    "template_id": "string",
    "data_file_id": "string",
    "formats": ["pdf"|"docx"|"html"],
    "pdf_variant": "pdf/a-1b"|"pdf/a-2b"|"pdf/a-3b"|"pdf/a-4b",
    "run_ats_check": boolean,
    "preview_only": boolean
  }
  200: {
    "submission_id": "uuid",
    "artifacts": {
      "pdf": "/api/download/{submission_id}/pdf",
      "docx": "/api/download/{submission_id}/docx",
      "html": "/api/download/{submission_id}/html"
    },
    "ats_report": { "errors": [...], "warnings": [...], "suggestions": [...] } | null
  }
  400: { "error": "validation", "details": {...} }
  422: { "error": "generation_failed", "details": "..." }

GET /api/download/{submission_id}/{format}
  200: binary with appropriate Content-Type + Content-Disposition: attachment
  404: if submission not found or artifact not in requested format

GET /api/preview/{submission_id}
  200: PDF bytes, Content-Disposition: inline
  404: if preview expired or not found
```

Preview artifacts live for 1 hour then are garbage-collected. Non-preview (downloaded) artifacts live under `outputs/{suffix}/` matching existing CLI behavior.

### 7.4 Submissions

```
GET /api/submissions?limit=25&offset=0&template_id=&data_file_id=
  200: {
    "items": [ {...submission row...} ],
    "total": N
  }

POST /api/submissions/{id}/notes
  body: { "notes": "string" }
  200: { "success": true }

DELETE /api/submissions/{id}
  204: (deletes DB row; artifacts on disk are NOT deleted — they remain under outputs/)
```

### 7.5 Vulture forward-compatibility note

The `/api/generate` endpoint accepts an optional `role_id` field in the body. In v2.0 it is passed through to the submissions table and nothing else. In the future, Vulture will POST a role ID here when requesting a targeted resume. No additional API surface is built for this now.

## 8. Security requirements

### 8.1 Threat model (abbreviated)

**Primary adversary:** accidental exposure to the public internet (e.g., Tailscale misconfiguration, neighbor on LAN if VLAN boundary fails).

**Secondary:** malicious YAML or template files placed into mounted volumes (supply chain).

**Out of scope:** nation-state, targeted phishing, physical access (these are handled at other layers — see Remington's broader home infra).

**Primary assets:**
- Resume data (work history, contact info — sensitive but not regulated)
- Session secret
- Password hash

### 8.2 Controls

- **Transport:** Tailscale provides TLS. The app MUST bind to `0.0.0.0` only inside the Docker network; the `api` service MUST NOT be exposed on the host network directly. The `web` service is exposed on the Tailnet interface only, not the LAN.
- **Auth:** argon2id, parameters meeting OWASP 2024 minimums (time_cost≥2, memory_cost≥19 MiB, parallelism≥1). Constant-time password comparison.
- **Session:** JWT signed with HS256 using `RESUME_BUILDER_SESSION_SECRET` (≥32 random bytes, generated with `secrets.token_urlsafe(32)`). Cookie flags: `HttpOnly`, `Secure`, `SameSite=Strict`, explicit expiry.
- **CSRF:** `SameSite=Strict` cookies + same-origin check on state-changing requests. No `Origin` header or mismatched origin → reject with 403. For defense in depth, require `X-Requested-With: XMLHttpRequest` on mutating requests from the Next.js client.
- **Rate limiting:** `/api/auth/login` (5/15min per IP). `/api/generate` (30/min per session).
- **Input validation:** All incoming fields validated via Pydantic models. File IDs validated against the existing allow-listed filename pattern (`^[a-zA-Z0-9_.-]+$` for full filenames; suffix-only fields use the existing `^[a-zA-Z0-9_-]+$`).
- **Path traversal:** File ID parameters are NEVER concatenated with path separators. They are looked up against an in-memory allowlist built at request time by scanning `templates/html/` and `data/` (same discovery as CLI). If the requested ID isn't in the allowlist, reject with 404.
- **XSS:** Jinja2 autoescape already enabled (see `resume_builder.py:43-46`). Preserve this. The Next.js frontend must never `dangerouslySetInnerHTML` on user-controlled fields — including the YAML content, which should not be displayed as HTML. For the preview pane, render the PDF, not the raw HTML.
- **Content Security Policy:** `default-src 'self'; object-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self';`. Preview iframes use `sandbox="allow-same-origin"` only.
- **Security headers:** `X-Content-Type-Options: nosniff`, `Referrer-Policy: strict-origin-when-cross-origin`, `Permissions-Policy: geolocation=(), camera=(), microphone=()`, `X-Frame-Options: DENY`.
- **Logging:** Log auth events (login success/fail, logout) with timestamp and source IP. Do NOT log passwords, session tokens, or full YAML content. Log to stdout for Docker log capture.
- **Dependencies:** Pin all dependencies. Run `pip-audit` and `npm audit` in CI. No unreviewed transitive upgrades.

### 8.3 Docker hardening

- Both services run as non-root (`USER app` with UID 1000)
- Read-only root filesystem where possible; writable tmpfs for `/tmp`
- Only the `outputs/` and database paths are writable volumes
- No `--privileged`, no host networking, no host PID/IPC namespaces
- Drop all Linux capabilities; add back only what's needed (likely none)
- `seccomp=default`, `no-new-privileges:true`
- Healthcheck on both services

### 8.4 Secret management

- `.env` file on Synology, mode 0600, owner = Docker user
- Never commit `.env`, `.env.local`, or any file containing real secrets
- `.env.example` committed with placeholder values and generation instructions
- At container start, the app MUST verify `RESUME_BUILDER_PASSWORD_HASH` and `RESUME_BUILDER_SESSION_SECRET` are set; refuse to start otherwise

## 9. Testing

### 9.1 Existing tests

The existing test suite under `tests/` continues to run unchanged and must continue to pass. Do not modify these tests unless a refactor to `resume_builder.py` makes them require adjustment (which it should not — see §4.4).

### 9.2 New test suites

#### 9.2.1 Backend (Python / FastAPI)

Add under `tests/api/`:

- `test_auth.py`
  - Login with correct password returns 200 and sets cookie
  - Login with wrong password returns 401, no cookie set
  - Login rate limiting triggers after 5 failed attempts
  - Logout clears cookie
  - Protected endpoints return 401 without cookie
  - Expired session cookie rejected
  - Tampered JWT rejected
  - Missing env vars at startup cause clean exit, not crash

- `test_generate.py`
  - Happy path: generate PDF with valid template + data file
  - Invalid template_id returns 400
  - Invalid data_file_id returns 400
  - Path traversal attempt in template_id returns 400 (e.g., `../../etc/passwd`, `templates/../`)
  - Path traversal attempt in data_file_id returns 400
  - DOCX generation produces valid .docx file
  - ATS check runs when requested, results included in response
  - PDF variant parameter honored

- `test_submissions.py`
  - Submission row created on every generation
  - `role_id` accepted but not auto-populated
  - History endpoint paginates correctly
  - Notes can be added and retrieved

- `test_security.py` (EXPAND existing)
  - All existing tests continue to pass
  - Add: CSRF — state-changing requests without proper origin header are rejected
  - Add: XSS — YAML content with script tags rendered in PDF is escaped in the Jinja2 template (already covered by existing tests; re-verify through the API)
  - Add: Session cookie has `HttpOnly`, `Secure`, `SameSite=Strict`
  - Add: Security headers present on all responses
  - Add: Content-Type validation on upload endpoints (if any)
  - Add: Argon2id parameters meet OWASP minimums
  - Add: Constant-time password comparison (verify no timing leak via test helper)
  - Add: Rate limit enforcement on `/api/auth/login`
  - Add: Rate limit enforcement on `/api/generate`
  - Add: Arbitrary file read via crafted template_id / data_file_id is rejected
  - Add: Arbitrary file write via crafted filename is rejected

#### 9.2.2 Frontend (Next.js)

Add under `web/__tests__/`:

- Component tests with React Testing Library
  - Theme toggle persists and applies correctly
  - Login form shows error on 401
  - Generate button disables during request
  - Preview pane shows error state on 422
  - Download buttons produce correct Content-Disposition behavior (smoke via MSW)

- E2E smoke test with Playwright
  - Login → select template → select data → generate → preview renders → download PDF
  - Login → logout → protected route redirects to login
  - Theme toggle persists across reload

### 9.3 Security test documentation

**Requirement:** Every security test must be documented in `tests/SECURITY_TESTS.md` with:

- **Test name** (mirrors test function name)
- **Threat / control** — what this test protects against, referencing the control in §8.2
- **Test strategy** — what the test actually does (positive case, negative case, edge case)
- **Expected behavior** — the assertion
- **Coverage gaps** — what this test does NOT cover (be honest)
- **Related tests** — cross-references

Format as a markdown table followed by per-test detail sections. This file is the auditable artifact — if someone (including future-Remington) asks "how do we know this is secure?", this file is the answer.

Example entry:

```markdown
### test_login_rate_limit

- **Threat:** brute-force password guessing
- **Control:** §8.2 — rate limiting on /api/auth/login
- **Strategy:** Submit 6 failed login attempts within 1 minute; assert 6th returns 429
- **Expected:** HTTP 429 with `Retry-After` header >= 0
- **Coverage gaps:** Does not test distributed brute force across multiple IPs;
  does not test rate limit persistence across container restart (acceptable for v2.0
  since rate limit is in-memory by design)
- **Related:** test_login_invalid_password, test_auth_protected_routes
```

### 9.4 CI

GitHub Actions workflow:
- Python: `pytest`, `pip-audit`, `ruff check`
- Node: `npm test`, `npm audit --audit-level=high`, `tsc --noEmit`, `eslint`
- Docker: `docker build` for both services (smoke only)
- Playwright E2E against the built compose stack (ephemeral)

All must pass before merge to `main`.

## 10. Deployment

### 10.1 Compose stack

`docker-compose.yml` at repo root:

```yaml
services:
  api:
    build:
      context: .
      dockerfile: docker/api.Dockerfile
    env_file: .env
    volumes:
      - ./templates:/app/templates:ro
      - ./data:/app/data:ro
      - ./fonts:/app/fonts:ro
      - outputs:/app/outputs
      - db:/app/db
    expose:
      - "8000"
    restart: unless-stopped
    read_only: true
    tmpfs:
      - /tmp
    security_opt:
      - no-new-privileges:true
    cap_drop:
      - ALL
    healthcheck:
      test: ["CMD", "curl", "-fsS", "http://localhost:8000/api/health"]
      interval: 30s
      timeout: 5s
      retries: 3

  web:
    build:
      context: ./web
      dockerfile: ../docker/web.Dockerfile
    env_file: .env
    depends_on:
      api:
        condition: service_healthy
    ports:
      - "127.0.0.1:3000:3000"   # bind localhost only; Tailscale proxies externally
    restart: unless-stopped
    read_only: true
    tmpfs:
      - /tmp
    security_opt:
      - no-new-privileges:true
    cap_drop:
      - ALL
    healthcheck:
      test: ["CMD", "wget", "-qO-", "http://localhost:3000/api/health"]
      interval: 30s
      timeout: 5s
      retries: 3

volumes:
  outputs:
  db:
```

### 10.2 Tailscale integration

The `web` service binds to `127.0.0.1:3000` on the Synology host. Tailscale's `serve` or `funnel` feature (`tailscale funnel` is disabled — we want Tailnet-only) exposes it on the Tailnet. Command:

```bash
tailscale serve --bg --https=443 http://127.0.0.1:3000
```

Document this in `docs/DEPLOY.md`.

### 10.3 Environment variables

`.env.example`:

```
# Generate with: python -c "import argon2; print(argon2.PasswordHasher().hash('your-password'))"
RESUME_BUILDER_PASSWORD_HASH=

# Generate with: python -c "import secrets; print(secrets.token_urlsafe(32))"
RESUME_BUILDER_SESSION_SECRET=

# Optional: override defaults
# RESUME_BUILDER_SESSION_MAX_AGE_DAYS=30
# RESUME_BUILDER_LOG_LEVEL=INFO
```

### 10.4 Initial setup

Documented in `docs/DEPLOY.md`:

1. `git clone` onto Synology
2. `cp .env.example .env` and populate
3. `docker compose up -d`
4. `tailscale serve --bg --https=443 http://127.0.0.1:3000`
5. Access via `https://{hostname}.{tailnet}.ts.net`

### 10.5 Backup

SQLite DB is in a named volume. Document a cron-driven `sqlite3 .backup` routine in `docs/BACKUP.md`. Artifacts under `outputs/` are reproducible from DB + source files and do not require backup.

## 11. Logging & observability

- All logs to stdout (Docker captures)
- Structured JSON logs in production (`python-json-logger`), pretty logs in dev
- Log levels: ERROR, WARNING, INFO. No DEBUG in production.
- Log every auth event, every generation request (without body content), every rate-limit trigger
- No PII or secret material in logs

No metrics backend in v2.0 — overkill for single-user local tool. Add `/api/health` for container healthcheck only.

## 12. Performance targets

- Cold generation (WeasyPrint): ≤3 seconds p95 on Synology hardware
- Warm preview re-render (debounced): ≤1.5 seconds p95
- Login: ≤500ms p95 (argon2 dominates)
- History page load: ≤200ms p95 for 100 rows

If cold generation exceeds 5 seconds, investigate WeasyPrint font cache warming.

## 13. Acceptance criteria

The feature is complete when:

1. ✅ CLI continues to work exactly as before (no changes to `resume_builder.py` semantics or test suite)
2. ✅ Web UI loads on desktop Firefox/Chrome/Safari and iOS Safari at a Tailnet URL
3. ✅ All three light/dark styling requirements met; toggle works and persists
4. ✅ Login with correct password works; wrong password fails; rate limit triggers at 6th attempt
5. ✅ Template and data file dropdowns populate from filesystem matching CLI's discovery
6. ✅ Generate produces a valid PDF preview within 3 seconds for the example data
7. ✅ All CLI flags are represented in UI controls
8. ✅ PDF download works; DOCX download works and opens in Word/LibreOffice without errors
9. ✅ Every generation creates a submissions row
10. ✅ Security test suite passes; `SECURITY_TESTS.md` is complete
11. ✅ `docker compose up -d` works from a clean checkout with a populated `.env`
12. ✅ No secrets in git; `.env.example` documents all required vars
13. ✅ Logout clears session; protected routes redirect to login
14. ✅ `/api/generate` accepts (and ignores) `role_id` without error

## 14. Future work (named, explicit)

- **Vulture integration:** consume `role_id` in submissions, add `/api/submissions?role_id=` filter, render a "Generated for role: {role_title}" label in history. Requires Vulture to expose a role lookup endpoint.
- **Password recovery & multi-user:** required if this project is open-sourced or sold. Design SMTP-free flows (e.g., recovery key file, admin CLI reset) before SMTP-based ones. Consider passkeys over passwords.
- **In-browser YAML editor:** Monaco or CodeMirror with YAML schema validation from a JSON Schema derived from `resume-example.yml`.
- **Template authoring UI:** defer until there's a real second author.
- **Role-tailored generation:** "Generate for this job description" — paste JD, LLM-rewrite summary + reorder bullets. Out of scope for v2.0; naturally belongs in Vulture.
- **PDF variant diff tool:** compare two generations side-by-side for proofing.

## 15. Open questions

None remaining for v2.0 scope. File any new questions as GitHub issues on the repo before implementation.

---

## Appendix A: Repository layout (target state)

```
resume-builder/
├── resume_builder.py          # UNCHANGED
├── ats_checker.py             # UNCHANGED
├── requirements.txt           # extended for FastAPI deps
├── cli.py                     # NEW — extracted __main__ from resume_builder.py
├── api/                       # NEW — FastAPI service
│   ├── __init__.py
│   ├── main.py
│   ├── auth.py
│   ├── generate.py
│   ├── submissions.py
│   ├── security.py
│   ├── db.py
│   ├── docx_converter.py
│   └── models.py              # Pydantic schemas
├── web/                       # NEW — Next.js app
│   ├── app/
│   ├── components/
│   ├── lib/
│   ├── styles/
│   │   └── theme.css
│   ├── __tests__/
│   ├── package.json
│   └── next.config.js
├── docker/
│   ├── api.Dockerfile
│   └── web.Dockerfile
├── docker-compose.yml
├── .env.example
├── docs/
│   ├── DEPLOY.md
│   └── BACKUP.md
├── templates/                 # UNCHANGED
├── data/                      # UNCHANGED
├── fonts/                     # UNCHANGED
├── outputs/                   # UNCHANGED
└── tests/
    ├── test_resume_builder.py # UNCHANGED
    ├── test_ats_checker.py    # UNCHANGED
    ├── test_security.py       # EXPANDED
    ├── SECURITY_TESTS.md      # NEW
    └── api/                   # NEW
        ├── test_auth.py
        ├── test_generate.py
        └── test_submissions.py
```

## Appendix B: Data flow for a single generation

1. User clicks Generate (or changes template/data file, triggering debounced generation)
2. Next.js client calls `POST /api/generate` with selected IDs and options
3. FastAPI handler validates inputs against allowlist
4. Handler creates a `submission_id` (UUID) and reserves an entry in the DB
5. Handler calls `render_resume(template_path, data_path, html_output_path, pdf_output_path, ...)` — the existing Python function, unchanged
6. WeasyPrint writes the PDF under `outputs/{suffix}/{first}_{last}_Resume.pdf`
7. If DOCX requested: handler runs HTML → DOCX conversion, writes `.docx` to same folder
8. Handler computes SHA-256 of PDF bytes, updates submission row
9. If ATS check requested: handler runs `ATSComplianceChecker`, includes report in response
10. Handler responds with `submission_id` and download URLs
11. Client updates preview pane (`<iframe src="/api/preview/{submission_id}">`)
12. User clicks Download → browser hits `/api/download/{submission_id}/{format}` → file served with `Content-Disposition: attachment`

## Appendix C: Implementation ordering (suggested)

A pragmatic order for Cursor to work through. Each phase is independently testable and mergeable.

1. **Phase 1 — Foundation (~1 day)**
   - Extract `cli.py` from `resume_builder.py` `__main__` block
   - Add FastAPI scaffolding, `/api/health`, `/api/templates`, `/api/data-files`
   - SQLite schema + migrations runner
   - Docker scaffold for api service only
   - CI for Python side

2. **Phase 2 — Auth (~1 day)**
   - Argon2id password hashing
   - JWT session cookies
   - Login/logout/status endpoints
   - Rate limiting
   - Security tests for all of the above

3. **Phase 3 — Generation (~2 days)**
   - `/api/generate` wrapping existing Python
   - `/api/preview/{id}` and `/api/download/{id}/{format}`
   - DOCX converter
   - Submission row creation
   - Security tests (path traversal, etc.)

4. **Phase 4 — Frontend foundation (~2 days)**
   - Next.js scaffold, theme system, layout, login page
   - API client with cookie handling
   - Docker scaffold for web service

5. **Phase 5 — Core workflow UI (~2 days)**
   - Template + data file dropdowns
   - Options panel
   - Generate + preview
   - Download bar
   - Theme toggle

6. **Phase 6 — History & polish (~1 day)**
   - Submissions history view
   - ATS report modal
   - Notes on submissions
   - Mobile responsive QA

7. **Phase 7 — Hardening (~1 day)**
   - Full security test suite
   - `SECURITY_TESTS.md` written
   - CSP / security headers verified
   - Docker hardening applied
   - `docs/DEPLOY.md` written
   - Playwright E2E

Total estimate: ~10 focused working days. Adjust as discovery occurs.

---

**End of PRD.**

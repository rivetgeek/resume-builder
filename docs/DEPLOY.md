# Deploying Resume Builder (web + API)

Target: Docker on Synology (or any host) with access restricted to your Tailnet.

## Prerequisites

- Docker with Compose v2
- Tailscale on the host
- This repository cloned on the machine

## 1. Configure secrets

```bash
cp .env.example .env
chmod 600 .env
```

Populate:

- `RESUME_BUILDER_PASSWORD_HASH` — `python -c "from argon2 import PasswordHasher; print(PasswordHasher().hash('your-password'))"`
- `RESUME_BUILDER_SESSION_SECRET` — `python -c "import secrets; print(secrets.token_urlsafe(32))"`

## 2. Start the stack

From the repository root:

```bash
docker compose up -d --build
```

- **API** listens on port `8000` inside the Compose network only (not published to the host by default).
- **Web** listens on `127.0.0.1:3000` on the host (localhost only).

Named volumes `outputs` and `db` store generated files and the SQLite submissions log.

## 3. Expose via Tailscale

Bind is localhost-only so LAN clients do not hit the app. Expose to your tailnet:

```bash
tailscale serve --bg --https=443 http://127.0.0.1:3000
```

Browse to `https://{hostname}.{tailnet}.ts.net` from a device on the same tailnet.

## 4. Operational notes

- Rotate the password by updating `RESUME_BUILDER_PASSWORD_HASH` in `.env` and restarting the `api` container (and `web` if you change shared env).
- For direct API debugging on the host, set `RESUME_BUILDER_SKIP_ORIGIN_CHECK=1` and `RESUME_BUILDER_COOKIE_SECURE=0` **only** in non-production environments.
- Logs go to stdout for both services (`docker compose logs -f api web`).

## 5. Local development (without Docker)

Put secrets in a **repo-root `.env`** file (same directory as `requirements.txt`). The API loads that file on startup via `python-dotenv` with **`interpolate=False`**, so Argon2 hashes full of `$` are not mangled as variable references. Values already set in the shell are **not** overridden by `.env`, so **a stale `export RESUME_BUILDER_PASSWORD_HASH=...` in your shell wins over `.env`** — run `unset RESUME_BUILDER_PASSWORD_HASH RESUME_BUILDER_SESSION_SECRET` (or start Uvicorn from a clean terminal) if you changed only the file.

After editing `.env`, **restart the API** so the new hash and session secret are read.

**`.env` pitfalls:** (1) Argon2 hash must be **one line**; an opening `"` without a closing `"` breaks parsing. (2) For **http://localhost**, set **`RESUME_BUILDER_COOKIE_SECURE=0`** (and usually **`RESUME_BUILDER_SKIP_ORIGIN_CHECK=1`**) — if those are commented out, the session cookie is `Secure` and the browser will not send it over HTTP, so login always fails.

**Login still failing?** Open **`http://localhost:3000/api/auth/self-check`** (same tab is fine). The JSON shows whether the hash looks loaded, secret length, cookie/flags, and `Host` / `X-Forwarded-Host`. The UI now shows **403 vs 401** instead of always saying “Invalid password.” The Next app proxies `/api/*` through **`app/api/[[...path]]/route.ts`** so **`Set-Cookie` from the API is forwarded** (plain `rewrites()` to another port often dropped the session cookie).

**Logs:** Watch the terminal where **`uvicorn`** is running (not the `npm` terminal). On each sign-in attempt you should see **`login_attempt`** with `supplied_password_length`, `configured_hash_length`, and `hash_starts_with_argon2`. A wrong password shows **`login_verify_failed`**. A broken hash string shows **`argon2_invalid_hash`** or **`login_misconfigured`** (hash does not start with `$argon2`).

Terminal 1 — API:

```bash
export RESUME_BUILDER_PASSWORD_HASH="$(python -c 'from argon2 import PasswordHasher; print(PasswordHasher().hash("dev"))')"
export RESUME_BUILDER_SESSION_SECRET="$(python -c 'import secrets; print(secrets.token_urlsafe(40))')"
export RESUME_BUILDER_SKIP_ORIGIN_CHECK=1
export RESUME_BUILDER_COOKIE_SECURE=0
uvicorn api.main:app --reload --port 8000
```

Terminal 2 — web (proxies `/api/*` to the API):

```bash
cd web && INTERNAL_API_URL=http://127.0.0.1:8000 npm run dev
```

Open `http://localhost:3000`, sign in with the dev password you hashed.

**Bypass auth in local dev (optional):** add **`RESUME_BUILDER_DEV_NO_AUTH=1`** to the **repo-root** `.env`, restart **Uvicorn** and **`npm run dev`** (Next reads that flag from the parent `.env` via `next.config.mjs`). The home page no longer redirects to `/login`, and the API accepts protected routes without a session cookie. **Do not set this in production** — it disables session enforcement and CSRF-style checks on mutating requests.

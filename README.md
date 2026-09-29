# MatriSathi

An independent maternal & child health companion. See `CLAUDE.md` for
product scope and boundaries, and `docs/specifications/` for the approved
specification and its proposed amendments.

This is the first implementation slice only: staff login, registering a
synthetic mother, creating a pregnancy episode, and viewing the persisted
record. See `docs/status.md` for what's built and what's next.

## Prerequisites (pinned versions)

- Docker (for local Postgres) — any recent version with Compose v2
- Python **3.12.14**, managed via [`uv`](https://docs.astral.sh/uv/) (the
  backend pins this exactly in `apps/api/.python-version`; `uv` will fetch
  it automatically if not already installed)
- Node **26.8.1** (pinned in `apps/web/.nvmrc`)

## 1. Start Postgres

```
cd infra
docker compose up -d db
```

Waits for a healthy container on `localhost:5433` (not 5432, to avoid
clashing with any other local Postgres).

## 2. Backend (one terminal)

```
cd apps/api
cp .env.example .env          # synthetic dev secrets only — never real credentials
uv sync                       # installs pinned deps from uv.lock into apps/api/.venv
uv run alembic upgrade head   # creates schema AND the restricted app DB role
uv run python -m app.scripts.seed_dev   # creates one synthetic org/facility/coordinator
uv run uvicorn app.main:app --port 8000 --reload
```

The seed script prints a synthetic login (`coordinator1` / a generated
password) to the terminal — that's what you log in with in step 3.

## 3. Frontend (a second, separate terminal)

```
cd apps/web
npm install
npm run dev
```

Open `http://localhost:5173`.

## Verification commands

Run from `apps/api` (with `uv sync` already done):

```
uv run pytest -q          # 26 tests: auth, access isolation, org-admin,
                           # person/pregnancy authorization, shared-phone
                           # privacy, and audit durability/DB-role enforcement
uv run ruff check .
uv run mypy app
```

Run from `apps/web`:

```
npm run typecheck          # tsc --noEmit
npm run build              # typecheck + production bundle
```

CI configuration exists at `.github/workflows/ci.yml` but does not run
anywhere yet — this repository has no git remote configured.

## What this slice deliberately does not include

No WhatsApp, no Child/Caregiver/CareTask/content/messaging tables (modeled
in the design doc, not migrated — kept provisional), no admin UI for
creating organizations/facilities (done via the seed script or directly in
tests for now). See `docs/status.md`.

## Session, tokens, and CSRF

- **Storage**: both the access token (JWT, 15 min) and refresh token
  (opaque, hashed at rest, 14 days, rotated on every use) ride as
  `httpOnly` cookies — never `localStorage`, never a JS-readable cookie.
  Page JavaScript cannot read either token, which is the main defense
  against token theft via XSS.
- **`SameSite=Lax`**, plus `Secure` in any real deployment
  (`COOKIE_SECURE=true`, currently `false` for local HTTP-only dev).
- **CSRF**: because auth is cookie-based, a browser attaches those cookies
  to same-origin *and* certain cross-site requests automatically. Every
  mutating request (`POST`) must carry an `X-MatriSathi-Client: web`
  header (`app/core/deps.py::require_csrf_header`). A classic cross-site
  form submission can't set a custom header; a cross-origin script
  attempting to via `fetch()` is blocked by CORS before the request is
  even sent, since the API only allows the configured frontend origin
  with credentials (`app/main.py`).
- **Revocation**: disabling a `StaffUser` takes effect on the very next
  request, not at token expiry — `get_current_staff` re-checks `active`
  against the database every time, it isn't decided purely from the JWT.
  Refresh-token reuse (replaying an already-rotated-out token) revokes
  every live session for that user, not just the one token.

## Known, low-severity dev-only advisory

`npm audit` flags an esbuild dev-server advisory
([GHSA-67mh-4wv8-2f99](https://github.com/advisories/GHSA-67mh-4wv8-2f99))
that Vite 5.x cannot avoid without a breaking major-version jump to Vite 6+.
It only affects the local Vite **dev server** (a malicious site could probe
it while you're running `npm run dev`), not the production build. Left as
Vite 5.4.21 for this slice; revisit alongside a deliberate Vite 6 upgrade
later rather than as an incidental bump here.

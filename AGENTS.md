# AGENTS.md – Einsatzbereit

Authoritative guide for coding agents working in this repository. Read it fully before changing code.

## What this app is

Einsatzbereit tracks which members of a volunteer fire brigade hold which certifications and when
they expire. Members never log in. Users (role `user`) record completions and maintain members;
admins additionally manage certifications, positions and users.

Scale: roughly 50 members and 10 certifications. Do not optimise for more.

## Domain vocabulary

| UI (German) | Code (English) | Notes |
|---|---|---|
| Kamerad | `Member` | `number` (Nr), `last_name`, `first_name`, `is_active`, positions |
| Funktion | `Position` | n:m to members and to certifications |
| Nachweis | `Certification` | seminar, exercise, test, training |
| Abschluss | `Completion` | full history is kept; the latest `completed_on` wins |
| Benutzer | `User` | people who log in |

Required certifications of a member = union of certifications of all their positions.

Validity modes (`ValidityMode`): `unlimited`, `fixed_duration` (expires the day before
completion + N months), `end_of_year` (Dec 31 of the year reached after N months),
`manual` (expiry entered per completion). Each certification has its own `warn_days`.

Cell statuses: `missing`, `expired`, `expiring`, `valid`, `not_required`. Non-required
certifications never produce open TODOs. All of this lives in
`backend/src/einsatzbereit/services/status.py`. Expiry is computed on read, never stored.

## Layout

```
backend/   FastAPI, SQLAlchemy 2 (sync), Alembic, pytest, uv
  src/einsatzbereit/
    routers/    HTTP only – no business rules here
    services/   status.py (rules), export.py (CSV/XLSX/PDF)
frontend/  Vue 3 + TypeScript + Vite, vue-router, no state library
deploy/    Kustomize: base (app + Postgres + InfisicalSecret), overlays/public (Ingress)
```

The built SPA is served by FastAPI from `EB_STATIC_DIR`; everything under `/api` is JSON.

## Commands

```bash
# backend
cd backend
uv sync
uv run ruff check . && uv run ruff format --check .
uv run mypy src tests
uv run pytest -q
EB_TEST_DATABASE_URL=postgresql+psycopg://…/eb_test uv run pytest -q   # same suite on Postgres
uv run alembic revision --autogenerate -m "..."   # needs EB_DATABASE_URL
uv run python -m einsatzbereit.seed               # demo data (50 members)

# frontend
cd frontend
npm ci
npm run dev        # proxies /api to :8000
npm run build      # includes vue-tsc type check
```

All four backend checks and the frontend build must pass before a change is done.

## Conventions

- Code, comments, docstrings, commit messages, README: **English**.
- All user-facing text (UI, export files, mails): **German**. Use „du“, sentence case,
  active verbs („Abschluss eintragen“, not „Absenden“).
- API error `detail` strings are English; the frontend maps them to German in `api.ts:errorText`.
  When adding a new error, add its translation there.
- mypy strict and ruff must stay clean. No `# type: ignore` without a reason in the same line.
- Every schema change needs an Alembic migration. Enums are stored as strings
  (`native_enum=False`), keep it that way.
- Business rules go into `services/`, with unit tests in `tests/test_status.py` style.
- Migrations are hand-checked: after `--autogenerate`, replace `sa.text('(CURRENT_TIMESTAMP)')`
  with `sa.func.now()` and make sure `downgrade()` works. CI runs upgrade, `alembic check`
  and downgrade on PostgreSQL.
- Completion input validation lives in `routers/members.py:_checked_certification` and is
  shared by the single and the bulk endpoint. Bulk entry skips members that already have a
  completion for the same certification and date.
- Filter parameters are shared by `/api/overview` and `/api/exports/{fmt}`
  (`routers/overview.py:matrix_filter`). A new filter must work for both.

## Security model – do not weaken

- Access token: JWT (HS256, 15 min), kept **in memory only** in the SPA. Never put tokens in
  `localStorage`/`sessionStorage`.
- Refresh token: opaque, stored hashed, httpOnly + SameSite=Strict cookie on `/api/auth`,
  rotated on every use; reuse revokes the whole token family.
- `User.token_version` invalidates access tokens on password change, reset, deactivation,
  role change and 2FA reset (`revoke_all_sessions`).
- TOTP 2FA is optional per user. Login with 2FA returns a short-lived `mfa` token, which is
  not accepted as an access token.
- Password reset: always answer 202, tokens hashed, single-use, 60 min, at most one mail
  per user every 5 min, a new link invalidates older ones.
- Account lockout after 5 failed attempts for 15 min.
- The last active admin cannot be demoted or deactivated.
- Strict CSP is set in `main.py`. Do not load fonts, scripts or styles from CDNs
  (fonts are bundled via `@fontsource`; GDPR).

## Out of scope – do not add unless asked

- SSE, WebSockets, polling or any live update mechanism
- Offline mode / caching service worker (the SW only makes the app installable)
- Member self-service login
- Multi-tenancy (multiple brigades)
- Additional member fields (birth date, address, …) – data minimisation
- A second frontend state library (Pinia etc.) or a CSS framework

## Design

Peg board („Stecktafel“) metaphor: quiet dispatch-blue chrome, colour reserved for status.
Tokens are in `frontend/src/styles.css`. Status colours: green valid, amber expiring,
solid red expired, **dashed** red missing. Keep mobile first: the bottom tab bar is the
primary navigation below 760 px (Offen, Übersicht, Erfassen, Kameraden, Konto), the matrix table is replaced by peg strips there.

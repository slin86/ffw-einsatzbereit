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
    services/   status.py (rules), export.py (CSV/XLSX/PDF), audit.py (change log)
frontend/  Vue 3 + TypeScript + Vite, vue-router, Vitest, no state library
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
uv run pytest -q --cov        # fails below 95 % branch coverage
EB_TEST_DATABASE_URL=postgresql+psycopg://…/eb_test uv run pytest -q   # same suite on Postgres
uv run alembic revision --autogenerate -m "..."   # needs EB_DATABASE_URL

# frontend
cd frontend
npm ci
npm run dev        # proxies /api to :8000
npm test           # Vitest unit tests (TZ=Europe/Berlin)
npm run coverage   # fails below 95 % lines/functions, 90 % branches
npm run lint       # Prettier check + vue-tsc
npm run format     # Prettier write
npm run build      # vue-tsc + Vite build
```

All backend checks (including coverage), the frontend lint, coverage and build must pass
before a change is done.

## Conventions

- Code, docstrings, commit messages, README: **English**.
- **No code comments.** The only allowed comments are `TODO` markers and tool directives
  (`# noqa: …`). Do not add explanatory `#`, `//`, `/* */` or `<!-- -->` comments.
- **Documentation only on complicated functions.** Add a docstring (Python) or JSDoc (TS/Vue)
  when a function has non-obvious logic, side effects or security relevance. Trivial
  functions, modules and classes get no docstring.
- **Plain text docs.** Docstrings and JSDoc contain only letters, digits, spaces, periods and
  commas: no hyphens, dashes, arrows, backticks, brackets, colons, slashes or quotes. Write
  full English sentences. `tests/test_code_style.py` enforces this and the comment rule.
- Frontend code is formatted with Prettier (print width 120). Python with ruff format.
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
- **Initial seed:** `seed.py:run_initial_seed` runs on every start and seeds only while
  `app_state.initialized` is false. It must stay idempotent and set the flag in the same
  transaction. Tests create the admin and an initialized `app_state` row themselves
  (`conftest.py`), so the startup seed never interferes with other tests.
- **Change log:** every write endpoint for members, completions, certifications, positions
  and users calls `services/audit.py:record` *before* the commit, in the same transaction.
  Use the `*_snapshot` helpers for before/after state; no-op updates are skipped automatically.
  Snapshots must never contain secrets (password hashes, TOTP secrets, tokens). A new write
  endpoint without an audit call is a bug. `member_id` is set for member and completion
  entries so the member page can show them.
- **Frontend logic** that is not pure presentation lives in plain TS modules
  (`api.ts`, `session.ts`, `guard.ts`, `filter.ts`, `labels.ts`, `todo.ts`, `auditText.ts`)
  with a `*.test.ts` next to it. Coverage is measured for these modules; Vue components
  are not unit-tested.
- Every backend error `detail` needs a German text in `api.ts:ERROR_TEXT`;
  `tests/test_translations.py` enforces this in both directions.
- Update endpoints load related rows (positions, certifications) **before** mutating the
  entity. Otherwise SQLAlchemy autoflush writes the half-changed row early and a unique
  violation surfaces as HTTP 500 instead of 409.
  Views stay thin. New field names in audit snapshots need a German label in
  `auditText.ts:FIELD_LABEL`.
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

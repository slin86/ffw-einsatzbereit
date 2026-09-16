# Einsatzbereit

Web app for volunteer fire brigades: which member holds which certification (Nachweis), and
what is missing or about to expire. Mobile first, works well on a laptop too.

- **Offen** – members with open items, most urgent first, colour-coded
- **Übersicht** – full matrix with filters (search, position, certification, status,
  only open, include inactive) and CSV / Excel / PDF export of exactly that selection
- **Erfassen** – record one completion for many members at once (e.g. after an exercise);
  re-submitting the same date is idempotent
- **Kameraden** – member management with positions and full completion history
- **Offen** can be narrowed to one position (Funktion); the choice is kept in the URL
- **Änderungen / Protokoll** – change log: who changed which member, completion,
  certification, position or user, and when. Per member for all users, complete log for admins
- **Admin** – certifications (with validity rules and warning period), positions, users
- Login with JWT + rotating refresh cookie, optional TOTP 2FA, password reset by e-mail

Stack: FastAPI · SQLAlchemy 2 · Alembic · PostgreSQL · Vue 3 · TypeScript · Vite.
See [AGENTS.md](AGENTS.md) for architecture, domain rules and conventions.

## Local development

```bash
docker compose up -d                       # PostgreSQL on :5432
cd backend
cp .env.example .env
uv sync
uv run alembic upgrade head
uv run uvicorn einsatzbereit.main:app --reload

cd ../frontend
npm ci
npm run dev                                # http://localhost:5173
```

On the first start the app seeds the empty database, see [Initial seed](#initial-seed).
With the example `.env` you log in as `admin@example.org` / `admin-password` and get
50 demo members.
Without SMTP settings, password reset links are written to the backend log.

Tests and coverage:

```bash
cd backend && uv run pytest -q --cov      # minimum 95 % branch coverage
cd frontend && npm run coverage           # minimum 95 % lines, 90 % branches (logic modules)
```

Run the backend test suite against PostgreSQL instead of SQLite:

```bash
EB_TEST_DATABASE_URL=postgresql+psycopg://einsatzbereit:einsatzbereit@localhost:5432/eb_test \
  uv run pytest -q
```

CI runs the tests on both databases and checks that `alembic upgrade head`, `alembic check`
(no drift between models and migrations) and `alembic downgrade base` succeed on PostgreSQL.

## Deployment (k3s via ArgoCD)

1. Push to `main` – GitHub Actions runs the checks and pushes
   `ghcr.io/slin86/einsatzbereit:{latest,<sha>}`.
2. Create the secrets in Infisical under `/einsatzbereit`. They are synced into the Secret
   `einsatzbereit-secrets` (plain Opaque, therefore without `secretType`):

   | Key | Value |
   |---|---|
   | `EB_JWT_SECRET` | `openssl rand -base64 48`; the app refuses to start with the dev default |
   | `POSTGRES_PASSWORD` | random |
   | `EB_DATABASE_URL` | `postgresql+psycopg://einsatzbereit:<POSTGRES_PASSWORD>@postgres:5432/einsatzbereit` |
   | `EB_INITIAL_ADMIN_EMAIL`, `EB_INITIAL_ADMIN_PASSWORD` | first admin, used only by the initial seed |
   | `EB_SMTP_HOST`, `EB_SMTP_PORT`, `EB_SMTP_USERNAME`, `EB_SMTP_PASSWORD`, `EB_SMTP_FROM` | mail relay for password resets; empty host logs the link instead |

3. Replace all `CHANGE-ME` values in `deploy/base/infisical-secret.yaml`.
4. Copy `deploy/` into `slin86/argocd` (or point an ArgoCD Application at
   `deploy/overlays/public`) and pin `newTag` to a commit SHA.
5. The app refuses to start if `EB_JWT_SECRET` is still the development default. It runs
   migrations on start and then the initial seed. Remove the admin password from Infisical
   afterwards and change it in the app.

Public URL: `https://einsatzbereit.slin.io`, exposed through Traefik with the existing
`*.slin.io` wildcard certificate.

Design decisions in `deploy/`:

- PostgreSQL uses `local-path` storage on the NUC: Postgres on NFS is fragile and the NAS
  disks use deep sleep. Backups go to the NAS once per night via `backup-cronjob.yaml`.
- The app runs as a single replica with `Recreate` strategy, because migrations run on
  container start.

## Initial seed

The table `app_state` holds a single row with an `initialized` flag. On every start the app
locks this row and checks the flag:

- **Not initialized:** it creates the admin from `EB_INITIAL_ADMIN_EMAIL` and
  `EB_INITIAL_ADMIN_PASSWORD`, the standard certifications and positions, and with
  `EB_SEED_DEMO_DATA=true` also 50 demo members with completions. The flag is set in the same
  transaction.
- **Initialized:** nothing happens, even if the admin or the catalog were deleted later.
- **No admin credentials on first start:** nothing is seeded and the flag stays unset, so the
  seed runs as soon as the credentials are provided.

Migration `0004` marks existing installations as initialized if they already contain users.
To seed again on purpose, set the flag back:
`UPDATE app_state SET initialized = false, initialized_at = NULL;`
Downgrading below `0004` drops the flag; the next upgrade derives it from existing users again.

Never enable `EB_SEED_DEMO_DATA` in production.

## Notes

- The change log starts with migration `0003`; earlier changes and data created by the
  initial seed have no log entries.
- Log entries are kept indefinitely. At ~50 members this stays small; add a retention
  job if that ever matters.

## Open points

- SMTP provider for password reset mails (`EB_SMTP_*`)
- Enable `deploy/base/backup-cronjob.yaml` once the NFS target is set
- Check the Ingress annotations against the existing Traefik setup

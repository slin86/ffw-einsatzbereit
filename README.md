# Einsatzbereit

Web app for volunteer fire brigades: which member holds which certification (Nachweis), and
what is missing or about to expire. Mobile first, works well on a laptop too.

- **Offen** – members with open items, most urgent first, colour-coded
- **Übersicht** – full matrix with filters (search, position, certification, status,
  only open, include inactive) and CSV / Excel / PDF export of exactly that selection
- **Erfassen** – record one completion for many members at once (e.g. after an exercise);
  re-submitting the same date is idempotent
- **Kameraden** – member management with positions and full completion history
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
uv run python -m einsatzbereit.seed        # optional demo data
uv run uvicorn einsatzbereit.main:app --reload

cd ../frontend
npm ci
npm run dev                                # http://localhost:5173
```

Demo login after seeding: `admin@example.org` / `admin-password`.
Without SMTP settings, password reset links are written to the backend log.

Run the test suite against PostgreSQL instead of SQLite:

```bash
EB_TEST_DATABASE_URL=postgresql+psycopg://einsatzbereit:einsatzbereit@localhost:5432/eb_test \
  uv run pytest -q
```

CI runs the tests on both databases and checks that `alembic upgrade head`, `alembic check`
(no drift between models and migrations) and `alembic downgrade base` succeed on PostgreSQL.

## Deployment (k3s via ArgoCD)

1. Push to `main` – GitHub Actions runs the checks and pushes
   `ghcr.io/slin86/einsatzbereit:{latest,<sha>}`.
2. Create the secrets in Infisical under `/einsatzbereit` (keys listed in
   `deploy/base/infisical-secret.yaml`). Generate the JWT secret with
   `openssl rand -base64 48`.
3. Replace all `CHANGE-ME` values in `deploy/base/infisical-secret.yaml`.
4. Copy `deploy/` into `slin86/argocd` (or point an ArgoCD Application at
   `deploy/overlays/public`) and pin `newTag` to a commit SHA.
5. The app runs migrations on start and creates the first admin from
   `EB_INITIAL_ADMIN_*` if the user table is empty. Remove the password from Infisical
   afterwards and change it in the app.

Public URL: `https://einsatzbereit.slin.io`.

## Open points

- SMTP provider for password reset mails (`EB_SMTP_*`)
- Enable `deploy/base/backup-cronjob.yaml` once the NFS target is set
- Check the Ingress annotations against the existing Traefik setup

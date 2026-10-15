# Run the civic application locally

Start with [the complete developer guide](../../DEVELOPMENT.md). From the
repository root, `.\run.ps1` starts Docker data/email services and all host apps
and workers; `.\start.ps1` runs everything in Docker. The individual steps below
are useful when running services in separate terminals.

## Option A: data in Docker, apps in your terminals

From the repository root, start only the data/email services:

```powershell
docker compose -f infra/docker-compose.local.yml up -d --wait db mongodb redis mailpit
```

Existing named volumes are retained. PostgreSQL uses port 5432, MongoDB 27017,
Redis 6379. Only loopback ports are published. Mailpit captures local development
emails at http://localhost:8025 (SMTP port 1025); it does not deliver Internet mail.

If needed, copy `.env.example` to `.env` without replacing your existing settings.
Set these **server-only** keys in the root `.env` to provision the mayor:

```dotenv
ADMIN_EMAIL=your-email@example.com
ADMIN_PASSWORD=your-own-unique-password-of-at-least-8-characters
ADMIN_NAME=Mayor
```

Never put these credentials in `NEXT_PUBLIC_` variables. The `.env` file is ignored
by Git. The bootstrap stores an Argon2 hash in PostgreSQL; subsequent starts do not
overwrite the admin password or promote an existing citizen with the same email.
The `.env` values are setup inputs: adding them does not create an account by
itself. The launcher runs setup, but starting Uvicorn directly skips it. After
setting the credentials, run this once from `apps/api` before trying to log in:

```powershell
uv run python -m app.workers.bootstrap
```

The command must report `Administrator provisioned.` or `Administrator already
provisioned; password unchanged.` Login reads the saved PostgreSQL account, not
the plaintext `.env` password. Admin setup, citizen and worker signup, and password
resets all accept passwords of 8–128 characters. Repeated login
attempts can temporarily return HTTP 429; allow the cooldown to finish before
retrying after correcting the setup.

Start all host apps and both background workers:

```powershell
./scripts/run-all.ps1
```

The launcher migrates the database and bootstraps categories/admin before starting
the servers. Stop manually running copies first so ports 3000, 8000 and 8001 are free.

For separate terminals, use:

```powershell
# Terminal 1
cd apps/api
./run.ps1

# Terminal 2
cd apps/ml-service
./run.ps1

# Terminal 3
cd apps/web
./run.ps1

# Terminal 4: reliable PostgreSQL -> MongoDB delivery
cd apps/api
./run-worker.ps1 -Worker project_events

# Terminal 5: current ML classifier -> durable category suggestions
cd apps/api
./run-worker.ps1 -Worker classify_reports
```

If using Uvicorn directly, migrate manually first:

```powershell
cd apps/api
uv sync --locked
uv run python -m alembic upgrade head
uv run python -m app.workers.bootstrap
uv run uvicorn app.main:app --reload --port 8000
```

Use lowercase `--port 8001` for the ML service. The API can accept reports while
ML is unavailable; pending classification jobs back off and retry. The Mongo
projector can also recover after a Mongo outage without losing committed reports.

## Option B: everything in Docker

Configure the root `.env`, stop competing host servers, then:

```powershell
./start.ps1
```

This includes the API, web, ML service, event projector and classifier worker.
The API runs migrations/bootstrap automatically. Uploaded public report photos
persist in the `civic_media` volume. Use `./start.ps1 -Stop` to stop without deleting
data. No `down -v` is needed for upgrades.

## Try the workflows

1. Open http://localhost:3000/map without signing in. New databases have no fake
   reports or assumed-good roads. The mayor can add areas/roads in the Roads tab.
2. Open `/register` and choose **Citizen** or **Worker**. Both share the profile
   fields; worker signup also requires a NID number or private NID image link and
   submits a pending application with the account. Open the verification link
   from Mailpit, then sign in with email or phone + password. Pending applicants
   land on their application-status page; worker tools require mayor approval.
3. Open **Report an issue**. Enter a precise Dhaka location or choose a catalogued
   road. Upload an optional JPEG/PNG/WebP (max 5 MB) or supply HTTPS image links.
4. View **My contributions** for reports and the points ledger.
5. Existing citizens can still apply under **Become a worker**. Worker signups have
   already submitted their application. The mayor reviews applications at `/admin`.
   Approved accounts gain access to `/worker` on the next account refresh/sign-in.
6. The mayor opens a report to assign an approved worker, manually or automatically.
   Workers opt into automatic assignment by sharing a current location.
7. The assigned worker submits a completion comment and optional photo. Citizens
   verify the work on the complaint detail page; 5 confirmations award 5 points.
8. Evidence-backed disputes and qualifying false reports appear under Moderation.
   The mayor can block/unblock accounts under Users/Workers and review aggregate
   analytics, category/status charts, area totals and points leaders.

Public pages: `/`, `/map`, `/complaints`, `/complaints/{id}`.
Authenticated pages: `/community`, `/complaints/new`, `/workers/apply`.
Role workspaces: `/worker`, `/admin`. Backend permissions apply independently of UI.

Swagger is at http://127.0.0.1:8000/docs. Mutations use the existing session-bound
CSRF flow: GET `/api/v1/auth/csrf`, then send the returned `X-CSRF-Token` with an
allowed `Origin` and the session cookies. Tokens rotate on sign-in/out/reset.

## Checks

```powershell
cd apps/api
uv run ruff check app tests
uv run pytest -q
$env:RUN_POSTGRES_TESTS='1'
uv run pytest -q

cd ../web
npx.cmd --yes pnpm@10.34.5 typecheck
npx.cmd --yes pnpm@10.34.5 test
npx.cmd --yes pnpm@10.34.5 lint
npx.cmd --yes pnpm@10.34.5 build
```

See [`db/README.md`](../../db/README.md) for normalization, indexes, clustering,
the PostgreSQL/MongoDB boundary, first-release policies and verification limits.

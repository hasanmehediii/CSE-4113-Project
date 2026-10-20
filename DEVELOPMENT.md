# Running DubsiBhai locally

For Linux, run `bash scripts/start.sh` to start the whole stack in Docker. See
[the Linux script guide](scripts/README.md) for requirements, flags and helpers.
The instructions below describe the Windows launchers.

Run commands below in PowerShell from the repository root. Choose one mode;
both use ports 3000, 8000 and 8001, so they cannot run together.

| Mode | Start command | Where services run |
| --- | --- | --- |
| Host development | `.\run.ps1` | PostgreSQL, MongoDB, Redis and Mailpit in Docker; frontend, API, ML and both workers on the host |
| Everything in Docker | `.\start.ps1` | All services above plus Nginx in Docker |

Use host development when working on application code. Use the Docker mode when
you want the whole stack without installing Node.js or Python on your machine.

## Prerequisites

Both modes require Git, Windows PowerShell 5.1 or PowerShell 7, and Docker Desktop
running **Linux containers** (WSL 2 backend). Open Docker Desktop and wait until
the engine is running. First startup requires internet access and may take several
minutes to download images and dependencies.

Host development also requires:

- Node.js **20.9+**; Node.js 22 matches the Docker image. `npx.cmd` comes with Node.
- [uv](https://docs.astral.sh/uv/getting-started/installation/) for Python dependencies.
- Python **3.11+**, either installed locally or managed by uv. For a fresh machine,
  `uv python install 3.11` installs a compatible interpreter.

You do not need global pnpm, Uvicorn, PostgreSQL, MongoDB or Redis installations.
The launchers use the pinned pnpm version and each Python app's own `.venv`.
Reopen PowerShell after installing tools so PATH updates take effect.

## First setup

Clone the repository, enter its root and create configuration files if missing:

```powershell
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
if (-not (Test-Path apps/web/.env.local)) {
    Copy-Item apps/web/.env.example apps/web/.env.local
}
```

The root launchers also create these files automatically. Existing files are
never replaced. Keep the example's localhost service URLs for host development;
the Docker stack supplies its own internal service addresses.

To create a mayor account, set these server-only values in the root `.env`
**before startup**:

```dotenv
ADMIN_EMAIL=your-email@example.com
ADMIN_PASSWORD=choose-your-own-password
ADMIN_NAME=Mayor
```

Passwords must contain **8–128 characters**, including admin passwords. Leave
both admin credentials empty if you do not need an admin account yet. Bootstrap
creates the category catalog and, when configured, the admin account. It does
not reset an existing admin password or promote a citizen account with the same
email. Login checks the saved database account. Never put admin credentials or
other secrets in `NEXT_PUBLIC_` variables or commit environment files.

`apps/web/.env.local` should contain `NEXT_PUBLIC_API_URL=http://localhost:8000`.
Google sign-in is optional: for host development, set `GOOGLE_CLIENT_ID` in root
`.env` and the same `NEXT_PUBLIC_GOOGLE_CLIENT_ID` in the web file. See the
[web guide](apps/web/README.md) for Google OAuth setup.

## Start the complete host development environment

```powershell
.\run.ps1 -Check   # Check tools, Node version, Docker engine/Compose and free app ports
.\run.ps1          # Start everything
```

The preflight command starts nothing and does not install dependencies. The
normal startup performs these steps:

1. Checks prerequisites and refuses to use occupied application ports.
2. Creates missing environment files and starts PostgreSQL, MongoDB, Redis and
   Mailpit using `infra/docker-compose.local.yml`. Waits for the data services.
3. Installs locked API and ML dependencies with uv and frontend dependencies with
   pnpm. Shared API dependencies are installed once before its workers start.
4. Starts the API, which applies Alembic migrations and runs catalog/admin
   bootstrap. Starts ML, which trains the bundled synthetic dataset only if its
   configured model file is missing.
5. Waits for the API and ML readiness endpoints, starts both background workers
   and the frontend, then waits for the login page to respond.
6. Supervises the five host processes until you press **Ctrl+C**. If one exits,
   shows its recent logs and stops the other processes it launched.

API, ML and frontend servers reload application source changes. Background
workers do not auto-reload: restart the launcher after changing worker code.
Existing model files are retained; an incompatible model causes startup to fail
with instructions to retrain it explicitly.

Keep this terminal open. Logs are saved separately for each service under the
unique `.cache/run-all/<run-id>/` directory printed at startup. For example:

```powershell
Get-Content .cache/run-all/<run-id>/api.err.log -Tail 50 -Wait
Get-Content .cache/run-all/<run-id>/classify-reports.err.log -Tail 50 -Wait
```

Replace `<run-id>` with the printed directory name. Each service has `.out.log`
and `.err.log` files; Uvicorn normally writes startup messages to stderr.

### Stop or restart host development

Press **Ctrl+C** in the launcher terminal. It stops only the host processes it
started, including their child servers. Docker data services remain running:

```powershell
.\start.ps1 -DataOnly -Status   # Inspect data containers
.\start.ps1 -DataOnly -Logs     # Follow data-container logs; Ctrl+C exits logs
.\start.ps1 -DataOnly -Stop     # Stop the four data/email containers
.\run.ps1                     # Start the host environment again
```

Stopping containers preserves database volumes. Host-uploaded files are under
`apps/api/media/`; host model weights are under `apps/ml-service/weights/` unless
`ML_MODEL_PATH` overrides the path.

## Start everything in Docker

Only Docker Desktop and PowerShell are needed for this mode:

```powershell
.\start.ps1            # Build images, start all services and wait for health checks
.\start.ps1 -Status    # Show running/stopped containers
.\start.ps1 -Logs      # Follow logs; Ctrl+C exits logs, services keep running
.\start.ps1 -NoBuild   # Reuse existing app images
.\start.ps1 -Stop      # Stop/remove this stack's containers; retain volumes
```

This includes the `project-events` and `classify-reports` workers. Migrations,
bootstrap and missing-model training also run automatically in Docker.
Source directories are mounted for reload. Rebuild with `.\start.ps1` after
changing dependencies, Dockerfiles, frontend configuration or other files outside
the mounted directories. See [Docker development](docs/guideline/DOCKER_DEVELOPMENT.md).

Both root launchers accept `-StartupTimeoutSeconds 900` (default 600) for
readiness waits on a slower machine. Host dependency downloads are separate from
these waits. Inspect logs for failures before increasing a timeout.

To switch from Docker apps to host apps, run `.\start.ps1 -Stop` and then
`.\run.ps1`. To switch back, press Ctrl+C in the host launcher before running
`.\start.ps1`. The same data-service volumes are reused. The older
`infra/docker-compose.dev.yml` is a partial stack; use the complete local Compose
file through these launchers and stop the older stack before switching.

## Services and addresses

Use **http://localhost:3000** consistently in the browser for auth and cookies.

| Service | Address | Purpose |
| --- | --- | --- |
| Frontend | http://localhost:3000 | Next.js UI |
| API | http://localhost:8000/ | HTML overview, live process health and links to `/docs` |
| ML | http://localhost:8001/ | HTML model overview and Bengali classification playground |
| Mailpit | http://localhost:8025 | Development verification/reset email inbox |
| PostgreSQL | `localhost:5432` | Accounts, reports, assignments, points and transactional source of truth |
| MongoDB | `localhost:27017` | Flexible complaint/event projections |
| Redis | `localhost:6379` | Shared rate limiting and short-lived auth state |
| SMTP | `localhost:1025` | Mailpit mail capture |
| project-events worker | No HTTP port | Delivers PostgreSQL outbox events to MongoDB |
| classify-reports worker | No HTTP port | Calls ML and saves complaint category suggestions/retry state |
| Nginx (Docker mode only) | http://localhost:8080/ | HTML service hub; API reverse proxy under `/api/` |

Local PostgreSQL database/user are `dubsibhai`, with the development password
`local-dev-only`; MongoDB uses database `dubsibhai`; Redis uses database 0.
Published Docker ports bind to loopback. Persistent PostgreSQL, MongoDB, Redis,
Docker ML weights and Docker-uploaded files use named volumes. Mailpit messages
are temporary and may disappear when its container is recreated. Host and Docker
ML artifacts and uploaded-file directories are separate.

Mailpit **captures mail locally**; it does not send messages to your real email
inbox. Open http://localhost:8025 to follow signup verification and password-reset
links. Real delivery requires configuring a real SMTP provider separately.

Check the running apps from another terminal:

```powershell
Invoke-RestMethod http://localhost:8000/health
Invoke-RestMethod http://localhost:8001/ready
(Invoke-WebRequest -UseBasicParsing http://localhost:3000/login).StatusCode
```

The API also exposes `/api/v1/health`. API `/health` is a process liveness check,
not a database probe. ML `/ready` checks that its classifier is loaded; ML
`/health` alone does not establish that classification can work.

## Run individual services

For separate terminals, start dependencies first from the repository root:

```powershell
.\start.ps1 -DataOnly
```

Then run each command in its own terminal, from the repository root:

```powershell
.\apps\api\run.ps1
.\apps\ml-service\run.ps1
.\apps\web\run.ps1
.\apps\api\run-worker.ps1 -Worker project_events
.\apps\api\run-worker.ps1 -Worker classify_reports
```

Start the workers after API migrations/bootstrap and ML startup finish. These
individual launchers install their dependencies by default. `-SkipInstall` is
used by the supervisor after it installs everything; use it manually only when
your dependencies already match the lockfiles. Do not run individual copies
alongside `.\run.ps1`.

If you invoke Uvicorn directly, you must prepare dependencies, migrations,
bootstrap and ML weights yourself. The API uses `--port 8000`; ML uses
`--port 8001`. The option is lowercase `--port`, not `--PORT`.

## Database migrations and ML training

Normal startup runs migrations automatically. When adding a schema change, add
an Alembic revision in `apps/api/alembic/versions/`; do not rewrite released
migrations. To apply migrations explicitly:

```powershell
Push-Location apps/api
uv run python -m alembic upgrade head
Pop-Location
```

`db/schema.sql` is a schema snapshot/alternative empty-database installation;
do not import it into an already migrated database. See [database design](db/README.md).
Routine startup does not run physical `CLUSTER` maintenance.

To retrain the host classifier after changing the dataset, stop the host launcher,
run training, then restart:

```powershell
.\apps\ml-service\train.ps1                    # Bundled synthetic dataset
# For a real labeled dataset instead:
# .\apps\ml-service\train.ps1 -Dataset path/to/real.csv -DataSource real
.\run.ps1
```

Synthetic model metrics do not measure performance on real complaints. Docker
training commands are in the [Docker guide](docs/guideline/DOCKER_DEVELOPMENT.md#ml-retraining).

## Checks before a pull request

Run frontend checks from `apps/web`:

```powershell
npx.cmd --yes pnpm@10.34.5 test
npx.cmd --yes pnpm@10.34.5 lint
npx.cmd --yes pnpm@10.34.5 typecheck
npx.cmd --yes pnpm@10.34.5 build
```

Run `uv run pytest` separately from `apps/api` and `apps/ml-service`. Optional
PostgreSQL integration checks require a dedicated test database; follow the
[civic guide](docs/guideline/CIVIC_DEVELOPMENT.md) before enabling them.

## Troubleshooting

- **Scripts blocked:** use a policy override for this invocation, for example
  `powershell -NoProfile -ExecutionPolicy Bypass -File .\run.ps1` (or `start.ps1`).
- **Docker unavailable:** open Docker Desktop, select Linux containers and wait
  for the engine; confirm `docker info` and `docker compose version` succeed.
- **Port already in use:** stop the existing app in its original terminal or stop
  the existing Docker stack. The launchers do not kill unrelated processes.
  Required data ports are 5432, 27017, 6379, 1025 and 8025; Docker apps also use 8080.
- **Dependency install fails:** inspect the package-manager output, check network
  access and the installed Node/Python versions, then rerun. Existing environment
  files and database volumes are retained.
- **API startup fails:** inspect `api.err.log` and `api.out.log` for migration or
  bootstrap errors. Root `.env` must point at the local PostgreSQL container in
  host mode. Old volumes retain the credentials used at their first initialization.
- **ML `/ready` returns 503:** inspect ML logs for training/model-load errors.
  Retrain explicitly if an existing model is incompatible; it is not overwritten
  by startup. Restart ML after changing its artifact.
- **Email did not arrive:** check Mailpit at port 8025. Local capture is not delivery
  to Gmail or another external mailbox.
- **Admin login fails:** bootstrap must create the account successfully. Changing
  `ADMIN_PASSWORD` does not reset an existing account; use password recovery.
  A 429 response means the shared Redis login limiter needs time to cool down.
- **Environment changes not applied:** restart the host launcher; for Docker,
  rerun `start.ps1` to recreate affected containers. A plain container restart does
  not load changed environment variables.
- **Worker edits have no effect:** restart the host launcher; in Docker, restart
  the affected worker after editing its mounted source.

The launchers never request volume deletion. Avoid `docker compose down --volumes`
unless you intend to delete the stored data. These commands configure local
development; production deployment is a separate setup.

## Launcher reference

| File | Responsibility |
| --- | --- |
| [`run.ps1`](run.ps1) | Root entry point: preflight, Docker data services, host apps/workers |
| [`start.ps1`](start.ps1) | Complete Docker stack; also data-only start/status/logs/stop |
| [`scripts/run-all.ps1`](scripts/run-all.ps1) | Host dependency setup, readiness checks, logs and process supervision |
| `apps/*/run.ps1` | Individual app dependency setup/startup |
| [`apps/api/run-worker.ps1`](apps/api/run-worker.ps1) | Start either API-owned worker |
| [`infra/docker-compose.local.yml`](infra/docker-compose.local.yml) | Complete local Docker service definitions |

See also [civic workflows](docs/guideline/CIVIC_DEVELOPMENT.md),
[API setup](apps/api/README.md), [web setup](apps/web/README.md) and
[ML training/inference](apps/ml-service/README.md).

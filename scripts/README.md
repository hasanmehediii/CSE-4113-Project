# Project scripts

`import-road-geometry.py` rebuilds the Dhaka main-road shapes from the checked-in,
attributed OpenStreetMap snapshot. It is an offline maintenance helper; normal
startup does not need to run it. See [map geometry](../docs/guideline/LIVE_MAP.md#road-catalog-and-geometry)
for the command, source license and update procedure.

## Linux: run everything in Docker

Requirements: Bash, Docker Engine or Docker Desktop, and a recent Docker Compose
v2 plugin supporting `up --wait --wait-timeout`. `docker info` must work for the
user running the command. Host Node.js, Python, uv and databases are unnecessary.
First startup needs internet access for images and locked dependencies.

From the repository root:

```bash
bash scripts/start.sh
```

Open http://localhost:3000. API: http://localhost:8000; ML: http://localhost:8001;
service hub: http://localhost:8080; development email: http://localhost:8025.
Ports bind to the local machine.

Missing `.env` and `apps/web/.env.local` files are copied from their examples;
existing files are preserved. Configure server-only `ADMIN_EMAIL`, `ADMIN_PASSWORD`
and `ADMIN_NAME` in `.env` before the first mayor bootstrap if needed. The launcher
passes environment files to Compose and never evaluates them as Bash code.
Optional Google sign-in client IDs must match when both are configured.

Docker builds the apps, starts dependencies in order, applies migrations, seeds
catalogs, trains missing complaint/road-risk models and waits for service health.
Existing weights are preserved. See [road-model training](../docs/guideline/ROAD_DATASET_TRAINING.md)
for intentional retraining after changing the dataset.

| Command | Purpose |
| --- | --- |
| `bash scripts/start.sh` | Build changed images and start the full stack in the background |
| `bash scripts/start.sh --no-build` | Start existing images without building |
| `bash scripts/start.sh --status` | Show all project containers |
| `bash scripts/start.sh --logs` | Follow logs; Ctrl+C closes only the viewer |
| `bash scripts/start.sh --stop` | Stop/remove containers while preserving named volumes |
| `bash scripts/start.sh --timeout 1200` | Set startup timeout (30–1800 seconds; default 600) |
| `bash scripts/start.sh --data-only` | Start only PostgreSQL, MongoDB, Redis and Mailpit |
| `bash scripts/start.sh --data-only --stop` | Stop only those four data/email services |
| `bash scripts/start.sh --help` | Show options without needing Docker |

`--data-only` also works with `--logs` and `--status`. Choose one of `--stop`,
`--logs` or `--status` per invocation. Stopping preserves database, upload and ML
model volumes. These scripts do not terminate competing host processes; stop the
other server before retrying a port conflict.

The scripts find the repository from their own location, so absolute script
paths work from other directories. The commands use `bash`, so executable file
permissions are not required. `.gitattributes` keeps shell files on LF endings.

## Other Linux helpers

These maintenance helpers run through the same Docker configuration:

| Script | Purpose |
| --- | --- |
| `migrate.sh` | Build the API image, start data services and apply Alembic migrations |
| `seed.sh` | Apply migrations and run the existing idempotent catalog/mayor bootstrap |
| `lint-all.sh` | Run API/ML Ruff, frontend ESLint and TypeScript checks in disposable containers |
| `docker-common.sh` | Shared internal functions, sourced by the other scripts |

```bash
bash scripts/migrate.sh
bash scripts/seed.sh
bash scripts/lint-all.sh
```

Normal startup already migrates and bootstraps. Migration/seed helpers leave data
services running. Seed preserves existing accounts/passwords and does not invent
sample complaints. Lint does not start databases; its containers install locked
development tools and may need network access. Each helper supports `--help`.

## How the PowerShell launchers relate

| Windows file | Role |
| --- | --- |
| Root `start.ps1` | Complete stack in Docker; Linux equivalent is `scripts/start.sh` |
| Root `run.ps1` | Docker data services, with apps/workers running on Windows |
| `scripts/run-all.ps1` | Internal helper called by root `run.ps1` to install and supervise host processes |

Use root `run.ps1` for Windows host development so prerequisite checks and
data-service setup run first. The Linux scripts implement the Docker workflow.
Run one mode at a time because application ports are shared.

## Launcher checks

Tests run under Linux Bash with mocked Docker; they never start containers or
change application data:

```bash
python3 -m unittest discover -s scripts/tests -v
```

Python is needed for tests only. CI runs them on Ubuntu. Checks cover shell
syntax/LF endings, paths containing spaces, configuration preservation, argument
validation, Docker errors and volume-preserving stop commands.

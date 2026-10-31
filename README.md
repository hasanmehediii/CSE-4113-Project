# DubsiBhai - Drainage Waterlogging Management for Dhaka

<p align="center">
  <img src="docs/icon.png" alt="Logo" width="180" height="180"/>
  <br>
  <strong>Collaborative Community Platform</strong>
</p>

Urban waterlogging and drainage management for Dhaka. This repository contains the frontend, backend, and machine learning service for the DubsiBhai project. The frontend is built with Next.js, while the backend and ML service are built with FastAPI.

The repository root is `CSE-4113-Project/`.

- [Project structure](docs/architecture/MONOREPO_ARCHITECTURE.md)
- [System design](docs/architecture/SYSTEM_DESIGN.md)
- [Developer setup: run the complete project](DEVELOPMENT.md)
- [Civic app setup and workflows](docs/guideline/CIVIC_DEVELOPMENT.md)
- [Live map, Google Maps switch and road-risk model](docs/guideline/LIVE_MAP.md)
- [Automatic release versions after dev-to-main merges](docs/guideline/RELEASES.md)
- [Database schema, normalization and indexes](db/README.md)
- [Incident grouping: matching, preserved evidence and shared work](docs/guideline/INCIDENTS.md)
- [Pre-release checks and verified browser flows](docs/guideline/PRE_RELEASE_CHECKS.md)

## Project status

Status reviewed on **31 October 2026** against the checked-in implementation.
"Implemented" means a working application path exists; it is not a claim that
every browser/device has been tested or that the application is production-ready.

### Implemented

| Area | Working features |
| --- | --- |
| Accounts | Citizen/worker registration, email or phone identifier + password login, Google sign-in, email verification/resend, password reset/recovery, password history |
| Sessions and access | Session listing/revocation, logout/all-device logout, backend role checks, CSRF protection, Redis rate limits and administrator bootstrap |
| Reporting | Complaints and road observations, category/address, map pin/GPS/manual Dhaka coordinates, image uploads/HTTPS links, public search/filter/detail pages |
| Incident grouping | Nearby reports about the same active problem share one incident; all submissions, authors, timestamps, locations and photos are retained. Ambiguous matches require a choice; a separate-incident override is available |
| Community | Incident-level voting with reporter-aware controls, false-report evidence and mayor moderation, completion verification/disputes, paginated personal contributions and an auditable points ledger |
| Workers | Identity application/review, availability/location sharing, manual/automatic assignment, explicit reassignment with history, completion submission and paginated active assignments |
| Mayor workspace | User blocking/unblocking, application review, assignments/reassignments, moderation, area/road creation, status/category/area summaries and point leaders |
| Maps and weather | Leaflet/OpenStreetMap, optional configured Google Maps, road/report overlays, search/filter/selection, periodic refresh and a Dhaka weather widget |
| ML integration | Bengali complaint category suggestions with durable retry/fallback, plus a separate synthetic-data waterlogging/traffic scenario model |
| Interface | English/Bangla switching, worker/workspace translations, light/dark themes, stale-response protection and request/upload failure handling |
| Local development | Windows host/Docker launchers, Linux Docker launchers, migrations/bootstrap, persistent local media/model volumes and API/ML service dashboards |
| Checks and releases | API, Web, ML, release-automation and Linux-launcher CI. A dev-to-main PR publishes the next V-number release after all five checks pass on its merge commit |

### Partially implemented / remaining work

| Area | What remains |
| --- | --- |
| Prediction quality | Obtain and validate real Dhaka observations. Current results use simulated data and uncalibrated probabilities; the saved report shows weak precision, particularly for waterlogging |
| Prediction inputs | Feed verified live/forecast weather and traffic into inference. The weather widget is separate; prediction rainfall is still a user-entered scenario |
| Geographic coverage | Validate the dataset-to-road mapping and expand overlays. The 14 map corridors currently cover 82 of 210 dataset segments; the other 128 have no overlay |
| Hotspots | The API has a deterministic grid baseline; geographic ML clustering is not implemented |
| Incident matching | Matching is a documented location/category/time rule, not semantic understanding. Human selection is needed for ambiguous nearby problems; administrative merge/split correction tools are not implemented |
| Email | Verification/reset delivery works with configured SMTP; local Mailpit captures messages instead of delivering to real inboxes. Delivery is not backed by a durable email queue |
| Identity and media | NID review is manual, not government verification. Managed private document storage, deep image inspection and retention/cleanup remain deployment work |
| Production operations | Local Docker/Nginx exists; public HTTPS deployment, monitored hosting, tested backup/restore and operational alerting remain to be configured |

### Known open bugs and verification gaps

- **Browser coverage:** API/database regression tests and simulated UI interaction
  tests exist. Chromium smoke checks have also verified the main workflow at desktop
  and mobile sizes; a complete, checked-in automated real-browser end-to-end suite
  is not in the repo. See the linked pre-release verification record.
- **Release publication:** numbering/retry/gating tests use a fake GitHub client;
  actual first publication must also be checked after installing the workflow on main.
- **Matching limits:** very close, same-category problems can be genuinely different.
  Use the separate-incident option. Old reports are deliberately not retroactively
  merged, and grouped reports cannot yet be moved/split through an admin screen.

Recently fixed defects include stuck assignments after worker unavailability,
completed history hiding unfinished work, stale report responses after navigation,
uploads blocking later saves, unreadable responses appearing successful, and
independent work orders being created for corroborating reports of one incident.
Citizen report/points history now has independent pagination and account-scoped
totals. Incident voting controls recognize every reporter without hiding completion
verification. Fresh-checkout/browser testing also fixed direct Docker authentication
requests being rejected without a proxy header, and a tall sticky location panel
covering the complaint submit button.
False-case dismissal now restores the appropriate completion state. Superseded
completions and stale moderation reviews cannot resolve or dispute replacement
work; their evidence and votes remain read-only history. Migration `20261031_06`
also repairs active work blocked by the older lifecycle bug; see the incident guide
for its legacy-history reconciliation policy.
There is no claim that all undiscovered defects have been eliminated.

### Not started in this repository

- IoT sensor ingestion and sensor-based water-level/drainage monitoring.
- SMS/phone OTP ownership verification.
- In-app/push notifications for assignment and status changes.
- ML-based geographic clustering and semantic duplicate matching.
- A managed private NID-document upload/review storage service.
- A durable authentication-email delivery queue and retry worker.
- A comprehensive real-browser end-to-end test suite and a public production
  deployment/backup-monitoring workflow.

### How repeated road complaints are handled

Ten citizens reporting the same blockage should mean **one incident, ten preserved
reports and ten distinct reporters**, rather than ten independent worker jobs.
New complaints can join an active same-category incident within **80 metres** of
its original report when it has activity in the last **24 hours**. Two known,
different road IDs do not match. Matching does not chain reports along an entire
road. Multiple eligible incidents require an explicit choice, and users can mark
a genuinely different blockage as separate.

Assignment, completion, verification and incident status are shared. Each person's
evidence stays individually accessible; personal contributions retain every
submission. Each person receives at most one complaint-contribution point per
incident, so repeated submissions do not multiply their points or reporter count.
These limits count accounts, not independently verified human identities.
Voting and false-incident moderation also apply to the shared blockage; one person
cannot vote repeatedly by opening different report URLs. The existing false-report
points-forfeiture policy applies to the original incident reporter, not an automatic
penalty on every corroborating citizen.
Road observations remain independent. A resolved or false incident is not reused
for a new blockage. Public map/queue/hotspot/analytics work counts count an incident
once, while report totals retain the full number of submissions.

## High-level architecture

The target architecture combines a FastAPI modular monolith with a separate ML
service. The core API owns business data, authorization, and workflow decisions;
an API-owned background worker calls ML over HTTP and saves versioned results.

![DubsiBhai high-level architecture](<docs/Client-Driven Next.js-2026-10-09-203929.svg>)

The civic implementation includes authenticated reports and road updates, public
map overlays, worker approval/assignment/completion, community verification,
points, moderation and mayor analytics. Background workers project transactional
events into **MongoDB** and obtain category suggestions from the existing ML service.
PostgreSQL remains the source of truth; Redis provides shared rate limits and
short-lived auth state. Rule-based incident grouping preserves corroborating reports
under one work item. Improved road-risk prediction, semantic matching, ML geographic
clustering, IoT ingestion and production HTTPS remain future work.
The diagram predates these additions; the linked database/workflow guides describe
the implementation. External integrations provide Google sign-in, map tiles and email.

## Run on Linux with Docker

Install Bash, Docker Engine (or Docker Desktop) and the Docker Compose v2 plugin.
Make sure `docker info` succeeds, then run from the repository root:

```bash
bash scripts/start.sh
```

This is the Linux equivalent of root `start.ps1`: it builds and starts the whole
stack, creates missing environment files, applies migrations and trains missing
models. Node.js, Python and uv run inside Docker. Open http://localhost:3000.

```bash
bash scripts/start.sh --status          # Inspect containers
bash scripts/start.sh --logs            # Follow logs; Ctrl+C exits logs only
bash scripts/start.sh --stop            # Stop the stack; keep database/model volumes
bash scripts/start.sh --no-build        # Start using existing images
bash scripts/start.sh --timeout 1200    # Allow more time for first startup
bash scripts/start.sh --data-only      # Start only databases, Redis and Mailpit
```

Run only one launch mode at a time; they share ports 3000, 8000 and 8001. Bash
commands work without changing executable permissions. See [scripts/README.md](scripts/README.md)
for Linux migration, seed and lint helpers, and how the PowerShell scripts relate.

## Run on Windows

See [DEVELOPMENT.md](DEVELOPMENT.md) for first-time configuration, all services,
logs, shutdown, migrations, training and troubleshooting. Choose one startup mode.

### Which launcher should I use?

**Use `.\start.ps1` for the standard setup and for teammates.** It runs the whole
project in Docker. Use `.\run.ps1` when you want to debug the application processes
directly on your computer.

Both launch the same project, but run its services in different places:

| | `start.ps1` | `run.ps1` |
| --- | --- | --- |
| Frontend, API, ML service and background workers | Docker containers | Directly on your computer |
| PostgreSQL, MongoDB, Redis and Mailpit | Docker containers | Docker containers |
| Requirements | Docker Desktop and PowerShell | Docker Desktop, PowerShell, Node.js, Python and uv |
| Stop application services | `.\start.ps1 -Stop` | Ctrl+C in the launcher terminal |
| Data services after stopping | Stopped; volumes preserved | Keep running; stop with `.\start.ps1 -DataOnly -Stop` |
| Model weights | Persistent Docker volume | `apps/ml-service/weights/` by default |

**Run only one mode at a time:** both use ports **3000, 8000 and 8001**. Before
switching from Docker to host mode, run `.\start.ps1 -Stop`. Before switching back,
press Ctrl+C in the `.\run.ps1` terminal and stop any independently launched app servers.
The model files are stored separately in the two modes; each trains missing weights
from the repository's datasets automatically.

`scripts/run-all.ps1` is an internal helper called by root `run.ps1`: it installs
dependencies and supervises the host apps/workers after Docker data services start.
Start through root `run.ps1` so its prerequisite checks and data setup run first.
It is separate from the all-Docker launcher `start.ps1`.

### Run everything with Docker

Install and start Docker Desktop with Linux containers, stop any manually running
app servers, and run this from the repository root:

```powershell
.\start.ps1
```

This starts the frontend, API, ML service, PostgreSQL, Redis, MongoDB, Mailpit,
and Nginx. Images and dependencies download automatically; migrations and initial
synthetic ML training run automatically. Existing environment files are retained,
and database/model data persists in Docker volumes.

Open http://localhost:3000. Use `.\start.ps1 -Logs` to follow logs and
`.\start.ps1 -Stop` to stop without deleting data. Teammates only need Docker
Desktop and PowerShell for this path; host Node.js and Python are unnecessary.
See [Docker development](docs/guideline/DOCKER_DEVELOPMENT.md) for ports, Google sign-in,
retraining, and troubleshooting. Set server-only `ADMIN_EMAIL`, `ADMIN_PASSWORD`
and `ADMIN_NAME` in the root `.env` before the first mayor bootstrap.

### Run apps directly on the host

Install Node.js 20.9+ (22 recommended), Python 3.11+, and [uv](https://docs.astral.sh/uv/), then open PowerShell.
A global pnpm installation is not needed. First launch requires internet access to install dependencies.

Start Docker Desktop, then run this from the repository root:

```powershell
.\run.ps1 -Check
.\run.ps1
```

The root launcher starts PostgreSQL, MongoDB, Redis and Mailpit in Docker,
installs locked dependencies, migrates the database, bootstraps the configured
mayor, prepares a missing ML model, and starts the three apps and both background
workers. It waits for readiness, then supervises them until you press Ctrl+C.
Logs are written to the unique `.cache/run-all/` directory printed in the terminal.
If an app exits, the launcher stops the others. Occupied ports are reported before startup.
Docker data services remain running after Ctrl+C; stop them with
`.\start.ps1 -DataOnly -Stop`. Existing environment files and data are retained.

To run just one app, enter its folder and use `./run.ps1` (the extension is `.ps1`):

```powershell
cd apps/web
./run.ps1
```

The same command works inside `apps/api` and `apps/ml-service`.
Each launcher synchronizes locked dependencies, starts its development server with reload,
and restores your working directory when it exits. Press Ctrl+C to stop an individual server.

| App | URL | API documentation |
| --- | --- | --- |
| Next.js frontend | http://localhost:3000 | - |
| Core FastAPI service | http://localhost:8000/ | http://localhost:8000/docs |
| FastAPI ML service | http://localhost:8001/ | http://localhost:8001/docs |
| Local service hub (Docker) | http://localhost:8080/ | - |

The API root shows live process health and documentation links. The ML root
shows model readiness and includes a Bengali complaint classification form.
The Docker service hub links to all three apps. Health and data endpoints
continue to return JSON for app clients and automated checks.

JavaScript tooling and dependencies live entirely inside `apps/web`.
Each Python service has its own `.venv`, `pyproject.toml`, and `uv.lock`.
The API also exposes `/api/v1/health`. API `/health` checks process liveness;
ML `/ready` checks that its classifier is loaded.

## Configuration and checks

The root launchers create missing environment files from their examples. To customize settings,
edit `.env` at the root and `apps/web/.env.local`. The Python services read the root
`.env`; Next.js reads its app-local environment file. Restart the affected app after editing settings.

From `apps/web`:

```powershell
npx --yes pnpm@10.34.5 lint
npx --yes pnpm@10.34.5 typecheck
npx --yes pnpm@10.34.5 build
```

From either Python app directory:

```powershell
uv run pytest
```

The ML service now supports Bengali complaint classification using the synthetic dataset.
The launchers train a missing model automatically; existing artifacts are preserved.
After replacing the CSV with real data, run `./train.ps1 -DataSource real` and restart the service.
See the [ML service guide](apps/ml-service/README.md) for inference and evaluation details.

The API now includes email/password and Google authentication, revocable sessions,
email verification and reset, database migrations, and Redis leaky-bucket limits.
See [the API guide](apps/api/README.md) for API configuration. The bilingual web app
includes public road/complaint maps, citizen reporting, worker applications and
workflows, community verification, mayor administration, login/signup, email
verification, password recovery, and account/session management. See the
[web setup guide](apps/web/README.md) for Google sign-in. Local verification and
reset messages are captured at http://localhost:8025; they are not delivered to
real inboxes. Phone verification, improved prediction/clustering, IoT readings,
semantic matching and production deployment remain future work.

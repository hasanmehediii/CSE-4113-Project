# DubsiBhai — Monorepo Architecture

This extends `SYSTEM_DESIGN.md` with the actual repo layout, tooling, and conventions for keeping web, api, and ml-service in one repository.

---

## 1. Top-Level Layout

The project is named **DubsiBhai**. The existing repository folder, `CSE-4113-Project/`, is the root shown below; create all planned folders directly inside it. Use `dubsibhai` for lowercase package and infrastructure identifiers.

```
CSE-4113-Project/
├── apps/
│   ├── web/                      # Next.js frontend
│   ├── api/                      # FastAPI monolith (core app)
│   └── ml-service/               # FastAPI ML microservice
│
├── packages/
│   ├── shared-types/             # Shared TS types (API contracts) for web
│   ├── shared-schemas/           # Shared Pydantic/OpenAPI schemas for api <-> ml-service
│   └── ui/                       # (optional) shared React components if web grows
│
├── infra/
│   ├── docker/
│   │   ├── api.Dockerfile
│   │   ├── ml-service.Dockerfile
│   │   └── web.Dockerfile
│   ├── docker-compose.yml
│   ├── docker-compose.dev.yml
│   ├── docker-compose.prod.yml
│   └── nginx/
│       └── nginx.conf            # reverse proxy config for prod
│
├── db/
│   ├── migrations/                # Alembic migrations (owned by api, lives at root for visibility)
│   ├── init/
│   │   └── 001_extensions.sql     # CREATE EXTENSION postgis, vector
│   └── seed/
│       └── seed_dev_data.py
│
├── scripts/
│   ├── run-all.ps1                # start all three apps on Windows
│   ├── setup.sh                   # planned dev bootstrap
│   ├── migrate.sh
│   ├── seed.sh
│   └── lint-all.sh
│
├── docs/
│   ├── SYSTEM_DESIGN.md
│   ├── MONOREPO_ARCHITECTURE.md   # this file
│   ├── API_CONTRACTS.md
│   └── adr/                       # Architecture Decision Records
│       ├── 0001-monolith-plus-ml-service.md
│       └── 0002-postgres-postgis-pgvector.md
│
├── .github/
│   └── workflows/
│       ├── ci-api.yml
│       ├── ci-ml-service.yml
│       ├── ci-web.yml
│       └── deploy.yml
│
├── .env.example
├── .gitignore
├── Makefile
└── README.md
```

---

## 2. `apps/api/` — Core Monolith (detailed)

```
apps/api/
├── app/
│   ├── main.py
│   ├── core/
│   │   ├── config.py               # pydantic-settings, reads .env
│   │   ├── security.py             # JWT, password hashing
│   │   ├── dependencies.py         # RBAC guards, get_db, get_current_user
│   │   └── logging.py
│   ├── models/                     # SQLAlchemy ORM models
│   │   ├── __init__.py
│   │   ├── user.py
│   │   ├── complaint.py
│   │   ├── assignment.py
│   │   ├── status_update.py
│   │   └── cluster.py
│   ├── schemas/                    # Pydantic I/O schemas
│   │   ├── user.py
│   │   ├── complaint.py
│   │   └── assignment.py
│   ├── api/
│   │   └── v1/
│   │       ├── router.py           # aggregates all v1 routers
│   │       ├── auth.py
│   │       ├── complaints.py
│   │       ├── assignments.py
│   │       ├── map.py
│   │       ├── analytics.py
│   │       ├── admin.py
│   │       └── internal.py         # ml-callback endpoint, service-to-service only
│   ├── services/
│   │   ├── complaint_service.py
│   │   ├── assignment_service.py
│   │   ├── notification_service.py
│   │   ├── storage_service.py      # MinIO client wrapper
│   │   └── ml_client.py            # typed HTTP client -> ml-service
│   ├── workers/
│   │   └── classify_consumer.py    # Redis/RQ consumer, runs as separate process
│   └── db/
│       └── session.py
├── alembic/
│   ├── env.py
│   └── versions/
├── tests/
│   ├── conftest.py
│   ├── test_complaints.py
│   ├── test_auth.py
│   └── test_assignments.py
├── run.ps1                        # Windows development launcher
├── pyproject.toml                  # or requirements.txt + requirements-dev.txt
├── Dockerfile -> ../../infra/docker/api.Dockerfile  # (symlink or just referenced by path)
└── README.md
```

---

## 3. `apps/ml-service/` — ML Microservice (detailed)

```
apps/ml-service/
├── app/
│   ├── main.py
│   ├── core/
│   │   ├── config.py
│   │   └── logging.py
│   ├── models/
│   │   ├── classifier.py           # Bengali text classification
│   │   ├── embedder.py             # sentence-transformer wrapper
│   │   └── clustering.py           # DBSCAN pipeline
│   ├── api/
│   │   ├── classify.py
│   │   ├── dedup.py
│   │   ├── cluster.py
│   │   └── health.py
│   ├── consumers/
│   │   └── queue_consumer.py       # picks up jobs api enqueued
│   └── db/
│       └── session.py              # separate lightweight session for reading complaints/writing ml_result
├── weights/                        # gitignored — downloaded at build/first-run
│   └── .gitkeep
├── notebooks/                      # exploration only, never imported by app/
│   └── classifier_experiments.ipynb
├── tests/
│   ├── test_classifier.py
│   └── test_dedup.py
├── run.ps1                        # Windows development launcher
├── pyproject.toml
└── README.md
```

**Important boundary rule**: `ml-service` never talks to `MinIO`/photo storage and never owns user-facing auth — it only receives `{complaint_id, text, geo}` and writes ML results. This keeps it a genuinely swappable/independently-deployable unit, not a disguised second half of the monolith.

---

## 4. `apps/web/` — Next.js Frontend (detailed)

```
apps/web/
├── src/
│   ├── app/                        # Next.js App Router
│   │   ├── (public)/
│   │   │   ├── map/page.tsx
│   │   │   └── complaints/[id]/page.tsx
│   │   ├── (auth)/
│   │   │   ├── login/page.tsx
│   │   │   └── register/page.tsx
│   │   ├── (dashboard)/
│   │   │   ├── worker/page.tsx
│   │   │   └── admin/page.tsx
│   │   └── layout.tsx
│   ├── components/
│   │   ├── map/
│   │   │   ├── ComplaintMap.tsx    # Leaflet wrapper
│   │   │   └── HotspotLayer.tsx
│   │   ├── complaints/
│   │   └── ui/                     # or import from packages/ui
│   ├── lib/
│   │   ├── api-client.ts           # typed fetch wrapper using packages/shared-types
│   │   └── auth.ts
│   └── hooks/
├── public/
├── run.ps1                        # Windows development launcher
├── pnpm-lock.yaml
├── pnpm-workspace.yaml             # local dependency build policy
├── next.config.js
├── package.json
└── tsconfig.json
```

---

## 5. `packages/` — Shared Code

| Package | Purpose | Used by |
| --- | --- | --- |
| `shared-types` | TypeScript interfaces generated/hand-kept in sync with API's Pydantic schemas (e.g. via `openapi-typescript` from api's `/openapi.json`) | `web` |
| `shared-schemas` | If you want Python-side sharing between `api` and `ml-service` (e.g. the exact shape of the queue job payload) | `api`, `ml-service` |
| `ui` | Optional — shared button/form/card components if the dashboard grows complex | `web` |

Keeping `shared-types` generated (not hand-written) avoids the classic monorepo drift problem where the frontend's idea of a `Complaint` silently diverges from the backend's.

---

## 6. Why This Layout (Monorepo Rationale)

| Decision | Reasoning |
| --- | --- |
| `apps/` for deployables, `packages/` for shared libs | Standard convention (Turborepo/Nx-style) — a grader or new contributor immediately knows what's runnable vs. what's a library |
| `infra/` centralizes all Docker/deploy config | Avoids scattering Dockerfiles across app folders; one place to see the whole deployment topology |
| `db/migrations/` visible at root, not buried in `apps/api/` | Migrations affect the whole system (both api and ml-service read/write the same Postgres) — root-level visibility signals "shared resource" |
| `docs/adr/` (Architecture Decision Records) | For a lab report, ADRs are gold — a one-page "why monolith + ml-service" doc you can literally hand to your evaluator |
| `scripts/run-all.ps1` + per-app `run.ps1` | One-command Windows development startup; Docker support is planned |

---

## 7. Local Windows Launchers

JavaScript tooling belongs to `apps/web/`, including `package.json`, `pnpm-lock.yaml`,
and the local `pnpm-workspace.yaml` dependency build policy. There is no root JavaScript workspace.
Each Python app owns its `pyproject.toml`, `uv.lock`, and virtual environment.

From the repository root, run `./scripts/run-all.ps1`, or enter `scripts/` and run `./run-all.ps1`.
To run a single app, enter `apps/web/`, `apps/api/`, or `apps/ml-service/` and run `./run.ps1`.
The scripts install locked dependencies before starting development servers on ports 3000, 8000,
and 8001 respectively. The combined launcher writes logs to `.cache/run-all/` and stops all
three apps on Ctrl+C or when one exits. Docker launch options will be implemented later;
the Docker configurations below remain design sketches.

### `.env.example` (root — one file, services read the vars they need)

```
# Postgres
POSTGRES_USER=dubsibhai
POSTGRES_PASSWORD=changeme
POSTGRES_DB=dubsibhai
DATABASE_URL=postgresql://dubsibhai:changeme@postgres:5432/dubsibhai

# Redis
REDIS_URL=redis://redis:6379/0

# MinIO
MINIO_ROOT_USER=minioadmin
MINIO_ROOT_PASSWORD=minioadmin
MINIO_BUCKET=dubsibhai-photos

# Auth
JWT_SECRET=changeme
JWT_EXPIRE_MINUTES=1440

# ML Service
ML_SERVICE_URL=http://ml-service:8001

# Web
NEXT_PUBLIC_API_URL=http://localhost:8000
```

---

## 8. `infra/docker-compose.dev.yml` (sketch)

```yaml
services:
  postgres:
    image: postgis/postgis:16-3.4
    env_file: ../.env
    volumes:
      - pgdata:/var/lib/postgresql/data
      - ../db/init:/docker-entrypoint-initdb.d
    ports: ["5432:5432"]

  redis:
    image: redis:7-alpine
    ports: ["6379:6379"]

  minio:
    image: minio/minio
    command: server /data --console-address ":9001"
    env_file: ../.env
    ports: ["9000:9000", "9001:9001"]
    volumes: ["miniodata:/data"]

  api:
    build:
      context: ../apps/api
      dockerfile: ../../infra/docker/api.Dockerfile
    env_file: ../.env
    volumes: ["../apps/api:/app"]
    ports: ["8000:8000"]
    depends_on: [postgres, redis, minio]

  ml-service:
    build:
      context: ../apps/ml-service
      dockerfile: ../../infra/docker/ml-service.Dockerfile
    env_file: ../.env
    volumes: ["../apps/ml-service:/app"]
    ports: ["8001:8001"]
    depends_on: [postgres, redis]

  web:
    build:
      context: ../apps/web
      dockerfile: ../../infra/docker/web.Dockerfile
    env_file: ../.env
    volumes: ["../apps/web:/app"]
    ports: ["3000:3000"]
    depends_on: [api]

volumes:
  pgdata:
  miniodata:
```

---

## 9. CI Structure (`.github/workflows/`)

Splitting CI per-app means a change to `apps/web/` doesn't trigger a slow ML-dependency install, and vice versa:

- **`ci-api.yml`** — triggers on `apps/api/**` changes, `packages/shared-schemas/**` — runs pytest, ruff/black
- **`ci-ml-service.yml`** — triggers on `apps/ml-service/**` — runs pytest (mock the model to keep CI fast; don't download real weights in CI)
- **`ci-web.yml`** — triggers on `apps/web/**`, `packages/shared-types/**` — runs lint, typecheck, build
- **`deploy.yml`** — manual/tag-triggered, builds and pushes all three images

Path-based triggers (`paths:` filter in GitHub Actions) are the key monorepo CI trick — without it, every commit rebuilds everything, which gets slow fast once the ML service has heavy dependencies.

---

## 10. Ownership Boundaries Cheat Sheet

| Resource | Owned by | Others access via |
| --- | --- | --- |
| `users`, `complaints`, `assignments` tables | `api` (writes) | `ml-service` reads complaint text/geo only, never writes these directly |
| `complaint_ml_result`, `complaint_cluster` tables | `ml-service` (writes) | `api` reads these for display |
| Photo storage (MinIO) | `api` only | `ml-service` never touches this |
| Redis queue | `api` produces, `ml-service` consumes | one-directional |
| JWT/auth | `api` only | `ml-service` has no user-facing auth; secure it with a shared internal API key or network-level isolation (not exposed publicly) instead |

This table is the actual architectural contract — worth pasting into your report almost verbatim, since it's the concrete answer to "how do you keep this from turning back into a tangled monolith with extra steps."

---

## 11. Suggested First Commit Structure

```
git init
mkdir -p apps/{web,api,ml-service} packages infra/docker db/{migrations,init,seed} docs/adr scripts .github/workflows
touch README.md .env.example .gitignore Makefile
git add . && git commit -m "chore: scaffold monorepo structure"
```

Then build out `apps/api` first (per the build order in `SYSTEM_DESIGN.md`), stub `apps/ml-service` with just a `/health` endpoint early so the Docker Compose network is provably wired end-to-end before you write any real ML code.
# DubsiBhai

Urban waterlogging and drainage management for Dhaka.

The repository root is `CSE-4113-Project/`.

- [Project structure](docs/MONOREPO_ARCHITECTURE.md)
- [System design](docs/SYSTEM_DESIGN.md)

## Run on Windows

Install Node.js 20.9+ (22 recommended), Python 3.11+, and [uv](https://docs.astral.sh/uv/), then open PowerShell.
A global pnpm installation is not needed. First launch requires internet access to install dependencies.

To start all three apps from the repository root:

```powershell
./scripts/run-all.ps1
```

Or, from the `scripts` folder:

```powershell
./run-all.ps1
```

The launcher starts the apps together in the background and stays attached until you press Ctrl+C.
Logs are written to the unique `.cache/run-all/` directory printed in the terminal.
If an app exits, the launcher stops the others. Occupied ports are reported before startup.

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
| Core FastAPI service | http://localhost:8000/health | http://localhost:8000/docs |
| FastAPI ML service | http://localhost:8001/health | http://localhost:8001/docs |

JavaScript tooling and dependencies live entirely inside `apps/web`.
Each Python service has its own `.venv`, `pyproject.toml`, and `uv.lock`.
The API also exposes `/api/v1/health`. Health endpoints check process liveness only.

## Configuration and checks

The starter runs without environment files. To customize settings, copy `.env.example` to `.env`
at the root and `apps/web/.env.example` to `apps/web/.env.local`. The Python services read the root
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

Authentication, complaints, maps, model inference, databases, queues, Docker, and CI are still planned.
Docker launch options will be added later. The planned web routes currently display coming-soon pages.

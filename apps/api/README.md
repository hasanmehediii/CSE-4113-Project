# DubsiBhai API

Core FastAPI application. From this directory:

```powershell
./run.ps1
```

The launcher installs locked dependencies before starting FastAPI with reload. Press Ctrl+C to stop.
Run `uv run pytest` in this directory for tests.

Swagger UI: http://localhost:8000/docs. Liveness: `/health` and `/api/v1/health`.
Configuration is in `app/core/config.py` and reads the root `.env`.
CORS permits the local Next.js app on port 3000 by default.
Business routes, persistence, and authentication are not implemented yet.

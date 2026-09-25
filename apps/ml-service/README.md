# DubsiBhai ML Service

Independent FastAPI service for future Bengali NLP inference. From this directory:

```powershell
./run.ps1
```

The launcher installs locked dependencies before starting FastAPI with reload. Press Ctrl+C to stop.
Run `uv run pytest` in this directory for tests.

Swagger UI: http://localhost:8001/docs. Liveness: `/health`.
Configuration is in `app/core/config.py` and reads the root `.env` using the `ML_` prefix.
No ML models are downloaded or loaded yet. Classifier, deduplication, and clustering remain placeholders.

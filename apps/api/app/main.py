from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.v1.router import router
from app.core.config import get_settings
from app.core.rate_limit import get_limiter

settings = get_settings()
app = FastAPI(
    title="DubsiBhai API",
    description="Core application for urban waterlogging and drainage management in Dhaka.",
    version="0.1.0",
)
app.state.limiter = get_limiter()
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.api_cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "X-CSRF-Token"],
)
app.include_router(router)
app.mount("/media", StaticFiles(directory=settings.media_directory, check_dir=False), name="media")


@app.middleware("http")
async def auth_response_headers(request, call_next):
    response = await call_next(request)
    if request.url.path.startswith(("/api/v1/auth", "/api/v1/admin", "/api/v1/me", "/api/v1/workers")):
        response.headers["Cache-Control"] = "no-store"
        response.headers["Pragma"] = "no-cache"
    response.headers["X-Content-Type-Options"] = "nosniff"
    return response


@app.get("/health", tags=["Health"])
def health() -> dict[str, str]:
    """Process liveness only; database and queue checks will be added with those services."""
    return {"status": "ok", "service": "dubsibhai-api"}


@app.get("/", include_in_schema=False)
def root() -> FileResponse:
    """Browser-friendly service overview; health and API routes still return JSON."""
    return FileResponse(Path(__file__).parent / "static" / "index.html", media_type="text/html")

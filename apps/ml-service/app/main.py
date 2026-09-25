from fastapi import FastAPI

from app.api.health import router
from app.core.config import get_settings

app = FastAPI(
    title=get_settings().app_name,
    description="Internal Bengali NLP service for DubsiBhai. Model endpoints are planned.",
    version="0.1.0",
)
app.include_router(router)

@app.get("/", tags=["Root"])
def root() -> dict[str, str]:
    """Root endpoint for the DubsiBhai ML service."""
    return {"message": "Welcome to the DubsiBhai ML service",
            "status": "ok", "service": "dubsibhai-ml-service"}
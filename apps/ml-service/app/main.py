import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.classify import router as classify_router
from app.api.health import router
from app.core.config import get_settings
from app.models.classifier import ComplaintClassifier


@asynccontextmanager
async def lifespan(application: FastAPI):
    application.state.classifier = None
    try:
        application.state.classifier = ComplaintClassifier.load(get_settings().model_path)
    except Exception:
        logging.getLogger(__name__).exception(
            "Classifier unavailable. Run python -m app.train and restart the service."
        )
    yield
    application.state.classifier = None


app = FastAPI(
    title=get_settings().app_name,
    description="Internal Bengali complaint classification service for DubsiBhai.",
    version="0.1.0",
    lifespan=lifespan,
)
app.include_router(router)
app.include_router(classify_router)


@app.get("/", tags=["Root"])
def root() -> dict[str, str]:
    """Root endpoint for the DubsiBhai ML service."""
    return {
        "message": "Welcome to the DubsiBhai ML service",
        "status": "ok",
        "service": "dubsibhai-ml-service",
    }

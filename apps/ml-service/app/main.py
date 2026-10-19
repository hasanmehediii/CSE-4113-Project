import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse

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


@app.get("/", include_in_schema=False)
def root() -> FileResponse:
    """Browser-friendly model overview and classification playground."""
    return FileResponse(Path(__file__).parent / "static" / "index.html", media_type="text/html")

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse

from app.api.classify import router as classify_router
from app.api.health import router
from app.api.road_risk import router as road_risk_router
from app.core.config import get_settings
from app.core.diagnostics import describe_load_failure
from app.models.classifier import ComplaintClassifier
from app.models.road_risk import RoadRiskModel


def load_model(application: FastAPI, kind: str, loader, path: Path) -> None:
    """Load one artifact; keep the other model and liveness independent of failures."""
    setattr(application.state, kind, None)
    setattr(application.state, f"{kind}_error", None)
    try:
        setattr(application.state, kind, loader(path))
    except Exception as error:
        detail = describe_load_failure(kind, path, error)
        setattr(application.state, f"{kind}_error", detail)
        logging.getLogger(__name__).exception(detail)


@asynccontextmanager
async def lifespan(application: FastAPI):
    settings = get_settings()
    load_model(application, "road_risk", RoadRiskModel.load, settings.road_risk_model_path)
    load_model(application, "classifier", ComplaintClassifier.load, settings.model_path)
    yield
    application.state.classifier = None
    application.state.road_risk = None


app = FastAPI(
    title=get_settings().app_name,
    description="Internal complaint classification and synthetic Dhaka road-risk inference.",
    version="0.1.0",
    lifespan=lifespan,
)
app.include_router(router)
app.include_router(classify_router)
app.include_router(road_risk_router)


@app.get("/", include_in_schema=False)
def root() -> FileResponse:
    """Browser-friendly model overview and classification playground."""
    return FileResponse(Path(__file__).parent / "static" / "index.html", media_type="text/html")

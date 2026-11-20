from fastapi import APIRouter, Request

from app.core.diagnostics import require_model

router = APIRouter(tags=["Health"])


@router.get("/health")
def health() -> dict[str, str]:
    """Process liveness; /ready checks the trained classifier."""
    return {"status": "ok", "service": "dubsibhai-ml-service"}


@router.get("/ready")
def ready(request: Request) -> dict[str, str]:
    """Ready means the classifier is loaded; road-risk status is reported, not required."""
    model = require_model(request, "classifier")
    road_risk = getattr(request.app.state, "road_risk", None)
    return {
        "status": "ready",
        "model_version": model.metadata["model_version"],
        "road_risk_model": "loaded" if road_risk is not None else (
            getattr(request.app.state, "road_risk_error", None) or "unavailable"),
    }

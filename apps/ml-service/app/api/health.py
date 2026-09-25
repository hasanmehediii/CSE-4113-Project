from fastapi import APIRouter, HTTPException, Request

router = APIRouter(tags=["Health"])


@router.get("/health")
def health() -> dict[str, str]:
    """Process liveness; /ready checks the trained classifier."""
    return {"status": "ok", "service": "dubsibhai-ml-service"}


@router.get("/ready")
def ready(request: Request) -> dict[str, str]:
    model = getattr(request.app.state, "classifier", None)
    if model is None:
        raise HTTPException(503, "Classifier unavailable. Train a model and restart the service.")
    return {"status": "ready", "model_version": model.metadata["model_version"]}

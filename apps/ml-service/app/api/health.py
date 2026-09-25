from fastapi import APIRouter

router = APIRouter(tags=["Health"])


@router.get("/health")
def health() -> dict[str, str]:
    """Process liveness only; model inference is not implemented yet."""
    return {"status": "ok", "service": "dubsibhai-ml-service"}

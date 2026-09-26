from fastapi import APIRouter

from app.api.v1.auth import router as auth_router

router = APIRouter(prefix="/api/v1")
router.include_router(auth_router)


@router.get("/health", tags=["Health"])
def health() -> dict[str, str]:
    return {"status": "ok", "service": "dubsibhai-api"}

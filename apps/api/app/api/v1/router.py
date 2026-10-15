from fastapi import APIRouter

from app.api.v1.admin import router as admin_router
from app.api.v1.auth import router as auth_router
from app.api.v1.community import router as community_router
from app.api.v1.complaints import router as complaints_router
from app.api.v1.map import router as map_router
from app.api.v1.media import router as media_router

router = APIRouter(prefix="/api/v1")
router.include_router(auth_router)
router.include_router(complaints_router)
router.include_router(community_router)
router.include_router(map_router)
router.include_router(admin_router)
router.include_router(media_router)


@router.get("/health", tags=["Health"])
def health() -> dict[str, str]:
    return {"status": "ok", "service": "dubsibhai-api"}

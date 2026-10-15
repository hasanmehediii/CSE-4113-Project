import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile

from app.core.config import get_settings
from app.core.dependencies import require_csrf, require_roles
from app.core.rate_limit import enforce

router = APIRouter(prefix="/media", tags=["Images"], dependencies=[Depends(require_csrf)])
Member = Annotated[object, Depends(require_roles("citizen", "worker", "admin"))]


@router.post("", status_code=201)
def upload(file: UploadFile, user: Member, request: Request):
    enforce(request, "image-upload", user.id, 20, 3600)
    content = file.file.read(5 * 1024 * 1024 + 1)
    if len(content) > 5 * 1024 * 1024:
        raise HTTPException(413, "Images must be at most 5 MB")
    if content.startswith(b"\xff\xd8\xff"):
        extension = "jpg"
    elif content.startswith(b"\x89PNG\r\n\x1a\n"):
        extension = "png"
    elif content[:4] == b"RIFF" and content[8:12] == b"WEBP":
        extension = "webp"
    else:
        raise HTTPException(422, "Use a JPEG, PNG or WebP image")
    directory = get_settings().media_directory
    directory.mkdir(parents=True, exist_ok=True)
    name = f"{uuid.uuid4().hex}.{extension}"
    (directory / name).write_bytes(content)
    return {"url": f"/media/{name}"}

from fastapi import APIRouter, Depends

from app.api.dependencies import get_gallery_service
from app.core.response import success
from app.service.gallery_service import GalleryService

router = APIRouter(prefix="/gallery", tags=["gallery"])


@router.get("/photos")
async def list_photos(service: GalleryService = Depends(get_gallery_service)):
    data = await service.list_photos()
    return success(data)

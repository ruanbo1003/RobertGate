from fastapi import APIRouter, Depends

from app.application.services.gallery_service import GalleryService
from app.interfaces.api.deps import get_gallery_service
from app.interfaces.api.response import success

router = APIRouter(prefix="/gallery", tags=["gallery"])


@router.get("/photos")
async def list_photos(service: GalleryService = Depends(get_gallery_service)):
    data = await service.list_photos()
    return success(data)

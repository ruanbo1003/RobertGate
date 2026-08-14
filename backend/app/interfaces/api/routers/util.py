from fastapi import APIRouter

from app.interfaces.api.response import success

router = APIRouter(tags=["util"])


@router.get("/health")
async def health():
    return success({"status": "ok"})

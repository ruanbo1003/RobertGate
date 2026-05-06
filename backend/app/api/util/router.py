from fastapi import APIRouter

from app.core.response import success

router = APIRouter(tags=["util"])


@router.get("/health")
async def health():
    return success({"status": "ok"})

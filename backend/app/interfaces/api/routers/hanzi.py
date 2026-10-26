from fastapi import APIRouter, Depends

from app.application.services.hanzi_service import HanziService
from app.interfaces.api.deps import (
    get_current_user_id,
    get_hanzi_service,
)
from app.interfaces.api.response import success
from app.interfaces.api.schemas.hanzi import PracticeTextRequest, UpdateProgressRequest

router = APIRouter(prefix="/hanzi", tags=["hanzi"])


@router.get("/levels")
async def list_levels(
    user_id: str = Depends(get_current_user_id),
    service: HanziService = Depends(get_hanzi_service),
):
    data = await service.list_levels_with_progress(user_id)
    return success(data)


@router.get("/levels/{level_id}/characters")
async def list_characters(
    level_id: str,
    user_id: str = Depends(get_current_user_id),
    service: HanziService = Depends(get_hanzi_service),
):
    data = await service.list_characters_for_user(user_id, level_id)
    return success(data)


@router.put("/progress/{character_id}")
async def update_progress(
    character_id: str,
    body: UpdateProgressRequest,
    user_id: str = Depends(get_current_user_id),
    service: HanziService = Depends(get_hanzi_service),
):
    data = await service.update_progress(user_id, character_id, body.learned)
    return success(data)


@router.post("/practice-text")
async def generate_practice_text(
    body: PracticeTextRequest,
    user_id: str = Depends(get_current_user_id),
    service: HanziService = Depends(get_hanzi_service),
):
    data = await service.generate_practice_text(user_id, body.level_id)
    return success(data)

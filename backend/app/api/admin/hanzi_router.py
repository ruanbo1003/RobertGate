from fastapi import APIRouter, Depends

from app.api.dependencies import get_admin_hanzi_service, require_admin
from app.core.response import success
from app.schemas.hanzi import (
    BatchImportRequest,
    CharacterCreateRequest,
    CharacterUpdateRequest,
    LevelCreateRequest,
    LevelUpdateRequest,
)
from app.service.admin_hanzi_service import AdminHanziService

router = APIRouter(prefix="/admin/hanzi", tags=["admin-hanzi"])


# ---------- Levels ----------


@router.get("/levels")
async def list_levels(
    _: str = Depends(require_admin),
    service: AdminHanziService = Depends(get_admin_hanzi_service),
):
    data = await service.list_levels()
    return success(data)


@router.post("/levels")
async def create_level(
    body: LevelCreateRequest,
    _: str = Depends(require_admin),
    service: AdminHanziService = Depends(get_admin_hanzi_service),
):
    data = await service.create_level(body.name, body.description, body.order_index)
    return success(data)


@router.put("/levels/{level_id}")
async def update_level(
    level_id: str,
    body: LevelUpdateRequest,
    _: str = Depends(require_admin),
    service: AdminHanziService = Depends(get_admin_hanzi_service),
):
    description_set = "description" in body.model_fields_set
    data = await service.update_level(
        level_id,
        name=body.name,
        description=body.description,
        description_set=description_set,
        order_index=body.order_index,
    )
    return success(data)


@router.delete("/levels/{level_id}")
async def delete_level(
    level_id: str,
    _: str = Depends(require_admin),
    service: AdminHanziService = Depends(get_admin_hanzi_service),
):
    await service.delete_level(level_id)
    return success(None)


# ---------- Characters ----------


@router.get("/levels/{level_id}/characters")
async def list_characters(
    level_id: str,
    _: str = Depends(require_admin),
    service: AdminHanziService = Depends(get_admin_hanzi_service),
):
    data = await service.list_characters(level_id)
    return success(data)


@router.post("/levels/{level_id}/characters")
async def create_character(
    level_id: str,
    body: CharacterCreateRequest,
    _: str = Depends(require_admin),
    service: AdminHanziService = Depends(get_admin_hanzi_service),
):
    data = await service.create_character(
        level_id, body.char, body.pinyin, body.meaning, body.order_index
    )
    return success(data)


@router.post("/levels/{level_id}/characters/batch")
async def batch_import_characters(
    level_id: str,
    body: BatchImportRequest,
    _: str = Depends(require_admin),
    service: AdminHanziService = Depends(get_admin_hanzi_service),
):
    data = await service.batch_import(
        level_id, [item.model_dump() for item in body.items]
    )
    return success(data)


@router.put("/characters/{character_id}")
async def update_character(
    character_id: str,
    body: CharacterUpdateRequest,
    _: str = Depends(require_admin),
    service: AdminHanziService = Depends(get_admin_hanzi_service),
):
    meaning_set = "meaning" in body.model_fields_set
    data = await service.update_character(
        character_id,
        char=body.char,
        pinyin=body.pinyin,
        meaning=body.meaning,
        meaning_set=meaning_set,
        order_index=body.order_index,
    )
    return success(data)


@router.delete("/characters/{character_id}")
async def delete_character(
    character_id: str,
    _: str = Depends(require_admin),
    service: AdminHanziService = Depends(get_admin_hanzi_service),
):
    await service.delete_character(character_id)
    return success(None)

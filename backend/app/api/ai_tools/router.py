from fastapi import APIRouter, Depends

from app.api.dependencies import (
    get_english_service,
    get_t2i_service,
    get_translate_service,
)
from app.core.response import success
from app.schemas.ai_tools import (
    QuizRequest,
    Text2ImageRequest,
    TranslateRequest,
)
from app.service.english_service import EnglishService
from app.service.t2i_service import T2IService
from app.service.translate_service import TranslateService

router = APIRouter(tags=["ai-tools"])


# ---------- 翻译 ----------


@router.post("/ai/translate")
async def translate(
    body: TranslateRequest,
    service: TranslateService = Depends(get_translate_service),
):
    data = await service.process(body.text, body.action)
    return success(data)


# ---------- 英文启蒙（匿名） ----------


@router.get("/english/themes")
async def english_themes(service: EnglishService = Depends(get_english_service)):
    data = service.list_themes()
    return success(data)


@router.post("/english/quiz")
async def english_quiz(
    body: QuizRequest,
    service: EnglishService = Depends(get_english_service),
):
    data = service.generate_quiz(body.theme_id, body.count)
    return success(data)


# ---------- 文生图（匿名） ----------


@router.post("/ai/text-to-image")
async def text_to_image(
    body: Text2ImageRequest,
    service: T2IService = Depends(get_t2i_service),
):
    data = await service.generate(body.prompt)
    return success(data)

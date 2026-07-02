from urllib.parse import unquote

from fastapi import APIRouter, Depends

from app.api.dependencies import (
    get_current_user_id,
    get_english_service,
    get_hanzi_service,
    get_t2i_service,
    get_translate_service,
)
from app.core.response import success
from app.schemas.ai_tools import (
    AddHanziRequest,
    CharacterInfoRequest,
    QuizRequest,
    SentenceRequest,
    Text2ImageRequest,
    TranslateRequest,
    UpdateHanziRequest,
)
from app.service.english_service import EnglishService
from app.service.hanzi_service import HanziService
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


# ---------- 汉字字库（需登录） ----------


@router.get("/hanzi/library")
async def list_hanzi(
    user_id: str = Depends(get_current_user_id),
    service: HanziService = Depends(get_hanzi_service),
):
    data = await service.list_library(user_id)
    return success(data)


@router.post("/hanzi/library")
async def add_hanzi(
    body: AddHanziRequest,
    user_id: str = Depends(get_current_user_id),
    service: HanziService = Depends(get_hanzi_service),
):
    data = await service.add_from_text(user_id, body.text)
    return success(data)


@router.patch("/hanzi/library/{char}")
async def update_hanzi(
    char: str,
    body: UpdateHanziRequest,
    user_id: str = Depends(get_current_user_id),
    service: HanziService = Depends(get_hanzi_service),
):
    data = await service.update_learned(user_id, unquote(char), body.learned)
    return success(data)


@router.delete("/hanzi/library/{char}")
async def delete_hanzi(
    char: str,
    user_id: str = Depends(get_current_user_id),
    service: HanziService = Depends(get_hanzi_service),
):
    data = await service.delete(user_id, unquote(char))
    return success(data)


# ---------- 汉字 AI 内容（匿名） ----------


@router.post("/ai/character-info")
async def character_info(
    body: CharacterInfoRequest,
    service: HanziService = Depends(get_hanzi_service),
):
    data = await service.character_info(body.char)
    return success(data)


@router.post("/ai/sentence")
async def sentence(
    body: SentenceRequest,
    service: HanziService = Depends(get_hanzi_service),
):
    data = await service.compose_sentence(body.known_chars)
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

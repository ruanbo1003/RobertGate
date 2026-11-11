"""ai-videos 路由。对应 docs/api/ai-videos.md。

鉴权：业务接口全部需登录；`files` 与 `download` 匿名可用——产物要被
<img>/<video> 标签直接引用，带不上 Authorization 头（与 t2i 图片接口同一先例）。
路径安全由 FsAvStorage.absolute() 的根目录约束保证。
"""

from __future__ import annotations

import mimetypes

from fastapi import APIRouter, Depends, Query
from fastapi.responses import FileResponse, Response

from app.application.services.av_service import AvCharacterService, AvProjectService
from app.domain.models.ai_video import AssetKind
from app.infrastructure.data.av_models import AV_MODELS
from app.interfaces.api.deps import (
    get_av_character_service,
    get_av_project_service,
    get_av_storage,
    get_current_user_id,
)
from app.interfaces.api.response import success
from app.interfaces.api.schemas.ai_videos import (
    ComposeRequest,
    CreateCharacterRequest,
    CreateProjectRequest,
    CreateShotRequest,
    GenerateAllRequest,
    GenerateAssetRequest,
    GenerateCharacterImageRequest,
    GenerateScriptRequest,
    ReorderShotsRequest,
    SplitShotsRequest,
    UpdateCharacterRequest,
    UpdateProjectRequest,
    UpdateShotRequest,
)

router = APIRouter(prefix="/ai-videos", tags=["ai-videos"])


# ---- 模型 ----


@router.get("/models")
async def list_models(
    type: str | None = Query(default=None, pattern="^(llm|t2i|i2v|tts|dialogue_video)$"),
    _user_id: str = Depends(get_current_user_id),
):
    models = {type: AV_MODELS[type]} if type else AV_MODELS
    return success({"models": models})


# ---- 角色 ----


@router.get("/characters")
async def list_characters(
    service: AvCharacterService = Depends(get_av_character_service),
    _user_id: str = Depends(get_current_user_id),
):
    return success(await service.list_characters())


@router.post("/characters")
async def create_character(
    body: CreateCharacterRequest,
    service: AvCharacterService = Depends(get_av_character_service),
    _user_id: str = Depends(get_current_user_id),
):
    return success(
        await service.create_character(
            body.name, body.appearance_prompt, body.personality, body.voice_desc
        )
    )


@router.put("/characters/{character_id}")
async def update_character(
    character_id: int,
    body: UpdateCharacterRequest,
    service: AvCharacterService = Depends(get_av_character_service),
    _user_id: str = Depends(get_current_user_id),
):
    return success(
        await service.update_character(
            character_id,
            name=body.name,
            appearance_prompt=body.appearance_prompt,
            personality=body.personality,
            cover_image_id=body.cover_image_id,
            voice_desc=body.voice_desc,
        )
    )


@router.delete("/characters/{character_id}")
async def delete_character(
    character_id: int,
    service: AvCharacterService = Depends(get_av_character_service),
    _user_id: str = Depends(get_current_user_id),
):
    await service.delete_character(character_id)
    return success(None)


@router.post("/characters/{character_id}/generate-image")
async def generate_character_image(
    character_id: int,
    body: GenerateCharacterImageRequest,
    service: AvCharacterService = Depends(get_av_character_service),
    _user_id: str = Depends(get_current_user_id),
):
    image = await service.generate_image(character_id, model=body.model, prompt=body.prompt)
    return success({"image": image})


# ---- 项目 ----


@router.get("/projects")
async def list_projects(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=50),
    service: AvProjectService = Depends(get_av_project_service),
    _user_id: str = Depends(get_current_user_id),
):
    return success(await service.list_projects(page, page_size))


@router.post("/projects")
async def create_project(
    body: CreateProjectRequest,
    service: AvProjectService = Depends(get_av_project_service),
    _user_id: str = Depends(get_current_user_id),
):
    return success(
        await service.create_project(
            title=body.title,
            synopsis=body.synopsis,
            character_ids=body.character_ids,
            target_duration=body.target_duration,
            default_models=body.default_models,
            tts_voice=body.tts_voice,
        )
    )


@router.get("/projects/{project_id}")
async def get_project(
    project_id: int,
    service: AvProjectService = Depends(get_av_project_service),
    _user_id: str = Depends(get_current_user_id),
):
    return success(await service.get_project(project_id))


@router.put("/projects/{project_id}")
async def update_project(
    project_id: int,
    body: UpdateProjectRequest,
    service: AvProjectService = Depends(get_av_project_service),
    _user_id: str = Depends(get_current_user_id),
):
    return success(
        await service.update_project(
            project_id,
            title=body.title,
            synopsis=body.synopsis,
            default_models=body.default_models,
            tts_voice=body.tts_voice,
        )
    )


@router.delete("/projects/{project_id}")
async def delete_project(
    project_id: int,
    service: AvProjectService = Depends(get_av_project_service),
    _user_id: str = Depends(get_current_user_id),
):
    await service.delete_project(project_id)
    return success(None)


# ---- 剧本 / 分镜 ----


@router.post("/projects/{project_id}/script/generate")
async def generate_script(
    project_id: int,
    body: GenerateScriptRequest,
    service: AvProjectService = Depends(get_av_project_service),
    _user_id: str = Depends(get_current_user_id),
):
    return success({"script": await service.generate_script(project_id, body.model)})


@router.put("/projects/{project_id}/script")
async def update_script(
    project_id: int,
    body: dict,
    service: AvProjectService = Depends(get_av_project_service),
    _user_id: str = Depends(get_current_user_id),
):
    return success(await service.update_script(project_id, body))


@router.post("/projects/{project_id}/shots/split")
async def split_shots(
    project_id: int,
    body: SplitShotsRequest,
    service: AvProjectService = Depends(get_av_project_service),
    _user_id: str = Depends(get_current_user_id),
):
    shots = await service.split_shots(project_id, body.model, body.confirm_replace)
    return success({"shots": shots})


@router.post("/projects/{project_id}/shots")
async def create_shot(
    project_id: int,
    body: CreateShotRequest,
    service: AvProjectService = Depends(get_av_project_service),
    _user_id: str = Depends(get_current_user_id),
):
    return success(await service.create_shot(project_id, body.after_shot_id))


@router.put("/projects/{project_id}/shots/order")
async def reorder_shots(
    project_id: int,
    body: ReorderShotsRequest,
    service: AvProjectService = Depends(get_av_project_service),
    _user_id: str = Depends(get_current_user_id),
):
    await service.reorder_shots(project_id, body.shot_ids)
    return success(None)


@router.put("/projects/{project_id}/shots/{shot_id}")
async def update_shot(
    project_id: int,
    shot_id: int,
    body: UpdateShotRequest,
    service: AvProjectService = Depends(get_av_project_service),
    _user_id: str = Depends(get_current_user_id),
):
    patch = body.model_dump(exclude_unset=True)
    return success(await service.update_shot(project_id, shot_id, patch))


@router.delete("/projects/{project_id}/shots/{shot_id}")
async def delete_shot(
    project_id: int,
    shot_id: int,
    service: AvProjectService = Depends(get_av_project_service),
    _user_id: str = Depends(get_current_user_id),
):
    await service.delete_shot(project_id, shot_id)
    return success(None)


# ---- 生成 / 合成 ----


@router.post("/projects/{project_id}/shots/{shot_id}/{kind}")
async def generate_asset(
    project_id: int,
    shot_id: int,
    kind: AssetKind,
    body: GenerateAssetRequest,
    service: AvProjectService = Depends(get_av_project_service),
    _user_id: str = Depends(get_current_user_id),
):
    await service.generate_asset(project_id, shot_id, kind, model=body.model, voice=body.voice)
    return success(None)


@router.post("/projects/{project_id}/generate-all")
async def generate_all(
    project_id: int,
    body: GenerateAllRequest,
    service: AvProjectService = Depends(get_av_project_service),
    _user_id: str = Depends(get_current_user_id),
):
    enqueued = await service.generate_all(project_id, body.types, body.scope)
    return success({"enqueued": enqueued})


@router.post("/projects/{project_id}/queue/cancel")
async def cancel_queue(
    project_id: int,
    service: AvProjectService = Depends(get_av_project_service),
    _user_id: str = Depends(get_current_user_id),
):
    return success({"cancelled": service.cancel_queue(project_id)})


@router.post("/projects/{project_id}/compose")
async def compose(
    project_id: int,
    body: ComposeRequest,
    service: AvProjectService = Depends(get_av_project_service),
    _user_id: str = Depends(get_current_user_id),
):
    await service.compose(project_id, body.ignore_stale)
    return success(None)


@router.get("/projects/{project_id}/status")
async def get_status(
    project_id: int,
    service: AvProjectService = Depends(get_av_project_service),
    _user_id: str = Depends(get_current_user_id),
):
    return success(await service.get_status(project_id))


@router.get("/projects/{project_id}/download")
async def download(
    project_id: int,
    service: AvProjectService = Depends(get_av_project_service),
):
    path, filename = await service.download_path(project_id)
    return FileResponse(path, media_type="video/mp4", filename=filename)


# ---- 产物文件 ----


@router.get("/files/{path:path}")
async def get_file(path: str):
    storage = get_av_storage()
    try:
        abs_path = storage.absolute(path)
    except ValueError:
        return Response(status_code=404)
    if not abs_path.is_file():
        return Response(status_code=404)
    media_type = mimetypes.guess_type(abs_path.name)[0] or "application/octet-stream"
    return FileResponse(abs_path, media_type=media_type)

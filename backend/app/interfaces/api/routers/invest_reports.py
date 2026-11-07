"""invest-reports 路由：只做参数校验与 service 调用（docs/api/invest-reports.md）。"""

from __future__ import annotations

import mimetypes

from fastapi import APIRouter, Depends, File, Form, Query, Response, UploadFile
from fastapi.responses import FileResponse

from app.interfaces.api.deps import (
    get_current_user_id,
    get_ir_library_service,
    get_ir_project_service,
)
from app.interfaces.api.response import success
from app.interfaces.api.schemas.invest_reports import (
    AddUrlSourceRequest,
    ChatRequest,
    CreateProjectRequest,
    LearnTemplateRequest,
    ResearchRequest,
    ResolveTbdRequest,
    RewriteParagraphRequest,
    UpdateParagraphRequest,
    UpdateTemplateRequest,
)

router = APIRouter(prefix="/invest-reports", tags=["invest-reports"])


async def _read_uploads(files: list[UploadFile]) -> list[tuple[str, bytes]]:
    return [(f.filename or "unnamed", await f.read()) for f in files]


# ---------------- 范本库与模板 ----------------


@router.get("/library")
async def get_library(
    _user_id: str = Depends(get_current_user_id),
    service=Depends(get_ir_library_service),
):
    out = await service.get_library()
    return success(out.model_dump())


@router.post("/samples")
async def upload_samples(
    type: str = Form(...),
    files: list[UploadFile] = File(...),
    _user_id: str = Depends(get_current_user_id),
    service=Depends(get_ir_library_service),
):
    samples = await service.upload_samples(type, await _read_uploads(files))
    return success({"samples": [s.model_dump() for s in samples]})


@router.delete("/samples/{sample_id}")
async def delete_sample(
    sample_id: int,
    _user_id: str = Depends(get_current_user_id),
    service=Depends(get_ir_library_service),
):
    await service.delete_sample(sample_id)
    return success(None)


@router.post("/templates/{type}/learn")
async def learn_template(
    type: str,
    body: LearnTemplateRequest,
    _user_id: str = Depends(get_current_user_id),
    service=Depends(get_ir_library_service),
):
    await service.learn(type, body.sample_ids)
    return success(None)


@router.put("/templates/{type}")
async def update_template(
    type: str,
    body: UpdateTemplateRequest,
    _user_id: str = Depends(get_current_user_id),
    service=Depends(get_ir_library_service),
):
    template = await service.update_template(
        type, [c.model_dump() for c in body.chapters], body.style_notes
    )
    return success({"template": template.model_dump()})


# ---------------- 项目 ----------------


@router.get("/projects")
async def list_projects(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=12, ge=1, le=50),
    _user_id: str = Depends(get_current_user_id),
    service=Depends(get_ir_project_service),
):
    out = await service.list_projects(page, page_size)
    return success(
        {"items": [i.model_dump() for i in out["items"]], "total": out["total"]}
    )


@router.post("/projects")
async def create_project(
    body: CreateProjectRequest,
    _user_id: str = Depends(get_current_user_id),
    service=Depends(get_ir_project_service),
):
    out = await service.create_project(body.title, body.type)
    return success({"project": out["project"].model_dump()})


@router.get("/projects/{project_id}")
async def get_project(
    project_id: int,
    _user_id: str = Depends(get_current_user_id),
    service=Depends(get_ir_project_service),
):
    out = await service.get_project(project_id)
    return success({"project": out["project"].model_dump()})


@router.delete("/projects/{project_id}")
async def delete_project(
    project_id: int,
    _user_id: str = Depends(get_current_user_id),
    service=Depends(get_ir_project_service),
):
    await service.delete_project(project_id)
    return success(None)


# ---------------- 资料 ----------------


@router.get("/projects/{project_id}/sources")
async def list_sources(
    project_id: int,
    _user_id: str = Depends(get_current_user_id),
    service=Depends(get_ir_project_service),
):
    return success(await service.list_sources(project_id))


@router.post("/projects/{project_id}/sources")
async def upload_sources(
    project_id: int,
    files: list[UploadFile] = File(...),
    _user_id: str = Depends(get_current_user_id),
    service=Depends(get_ir_project_service),
):
    sources = await service.upload_sources(project_id, await _read_uploads(files))
    return success({"sources": [s.model_dump() for s in sources]})


@router.post("/projects/{project_id}/sources/url")
async def add_url_source(
    project_id: int,
    body: AddUrlSourceRequest,
    _user_id: str = Depends(get_current_user_id),
    service=Depends(get_ir_project_service),
):
    source = await service.add_url_source(project_id, body.url)
    return success({"source": source.model_dump()})


@router.delete("/projects/{project_id}/sources/{source_id}")
async def delete_source(
    project_id: int,
    source_id: int,
    _user_id: str = Depends(get_current_user_id),
    service=Depends(get_ir_project_service),
):
    await service.delete_source(project_id, source_id)
    return success(None)


@router.get("/projects/{project_id}/sources/{source_id}/file")
async def source_file(
    project_id: int,
    source_id: int,
    _user_id: str = Depends(get_current_user_id),
    service=Depends(get_ir_project_service),
):
    path = await service.source_file_path(project_id, source_id)
    if not path.is_file():
        return Response(status_code=404)
    media_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    return FileResponse(path, media_type=media_type)


@router.post("/projects/{project_id}/sources/{source_id}/impact")
async def analyze_impact(
    project_id: int,
    source_id: int,
    _user_id: str = Depends(get_current_user_id),
    service=Depends(get_ir_project_service),
):
    affected = await service.analyze_impact(project_id, source_id)
    return success({"affected": affected})


# ---------------- 研究与状态 ----------------


@router.post("/projects/{project_id}/research")
async def start_research(
    project_id: int,
    body: ResearchRequest,
    _user_id: str = Depends(get_current_user_id),
    service=Depends(get_ir_project_service),
):
    return success(await service.start_research(project_id, body.chapter_ids, body.confirm))


@router.post("/projects/{project_id}/queue/cancel")
async def cancel_queue(
    project_id: int,
    _user_id: str = Depends(get_current_user_id),
    service=Depends(get_ir_project_service),
):
    return success(service.cancel_queue(project_id))


@router.get("/projects/{project_id}/status")
async def get_status(
    project_id: int,
    feed_after: int = Query(default=0, ge=0),
    _user_id: str = Depends(get_current_user_id),
    service=Depends(get_ir_project_service),
):
    return success(await service.get_status(project_id, feed_after))


# ---------------- 章节与编辑 ----------------


@router.get("/projects/{project_id}/chapters/{chapter_id}")
async def get_chapter(
    project_id: int,
    chapter_id: int,
    _user_id: str = Depends(get_current_user_id),
    service=Depends(get_ir_project_service),
):
    out = await service.get_chapter(project_id, chapter_id)
    return success({"chapter": out["chapter"].model_dump()})


@router.put("/projects/{project_id}/chapters/{chapter_id}/paragraphs/{paragraph_id}")
async def update_paragraph(
    project_id: int,
    chapter_id: int,
    paragraph_id: str,
    body: UpdateParagraphRequest,
    _user_id: str = Depends(get_current_user_id),
    service=Depends(get_ir_project_service),
):
    out = await service.update_paragraph(project_id, chapter_id, paragraph_id, body.text)
    return success({"chapter": out["chapter"].model_dump()})


@router.post("/projects/{project_id}/chapters/{chapter_id}/paragraphs/{paragraph_id}/rewrite")
async def rewrite_paragraph(
    project_id: int,
    chapter_id: int,
    paragraph_id: str,
    body: RewriteParagraphRequest,
    _user_id: str = Depends(get_current_user_id),
    service=Depends(get_ir_project_service),
):
    out = await service.rewrite_paragraph(project_id, chapter_id, paragraph_id, body.instruction)
    return success({"chapter": out["chapter"].model_dump()})


@router.post("/projects/{project_id}/tbds/{tbd_id}/resolve")
async def resolve_tbd(
    project_id: int,
    tbd_id: int,
    body: ResolveTbdRequest,
    _user_id: str = Depends(get_current_user_id),
    service=Depends(get_ir_project_service),
):
    out = await service.resolve_tbd(project_id, tbd_id, body.value)
    return success({"chapter": out["chapter"].model_dump()})


# ---------------- 对话 ----------------


@router.get("/projects/{project_id}/chat")
async def list_chat(
    project_id: int,
    limit: int = Query(default=50, ge=1, le=200),
    _user_id: str = Depends(get_current_user_id),
    service=Depends(get_ir_project_service),
):
    return success(await service.list_chat(project_id, limit))


@router.post("/projects/{project_id}/chat")
async def send_chat(
    project_id: int,
    body: ChatRequest,
    _user_id: str = Depends(get_current_user_id),
    service=Depends(get_ir_project_service),
):
    return success(await service.send_chat(project_id, body.message, body.chapter_id))


# ---------------- 导出 ----------------


@router.post("/projects/{project_id}/export")
async def export_report(
    project_id: int,
    _user_id: str = Depends(get_current_user_id),
    service=Depends(get_ir_project_service),
):
    return success(await service.export(project_id))


@router.get("/projects/{project_id}/download")
async def download_report(
    project_id: int,
    _user_id: str = Depends(get_current_user_id),
    service=Depends(get_ir_project_service),
):
    path = await service.download_path(project_id)
    return FileResponse(
        path,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        filename=f"invest-report-{project_id}.docx",
    )

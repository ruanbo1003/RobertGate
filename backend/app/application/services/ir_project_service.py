"""invest-reports 项目用例（第一批：项目/资料；研究/编辑/对话在第二批追加）。"""

from __future__ import annotations

import logging
import uuid
from pathlib import Path

from app.application.dto.invest_report import (
    ChapterMetaOut,
    ProjectDetailOut,
    ProjectSummaryOut,
    SourceOut,
)
from app.application.ports import IrAgent, TaskRunner
from app.application.services.av_queue import AvStorage
from app.domain.errors import ParamException, codes, ensure_found
from app.domain.models.invest_report import (
    SOURCE_EXTS,
    UPLOAD_MAX_BYTES,
    ChapterState,
    IrChapter,
    IrChatMessage,
    IrProject,
    IrSource,
    ParseState,
    TemplateStatus,
    derive_project_status,
    unresolved_tbds,
    validate_report_type,
)
from app.domain.repositories.uow import UnitOfWork
from app.infrastructure.ir_parsers import parse_document, parse_url

logger = logging.getLogger(__name__)

CHECKLIST = [
    "商业计划书 BP",
    "财务明细（Excel）",
    "天眼查导出：工商信息 / 股权结构 / 涉诉记录",
]


class IrProjectService:
    def __init__(
        self,
        uow: UnitOfWork,
        agent: IrAgent,
        queue,
        storage: AvStorage,
        runner: TaskRunner,
        uow_factory,
    ) -> None:
        self._uow = uow
        self._agent = agent
        self._queue = queue
        self._storage = storage
        self._runner = runner
        self._uow_factory = uow_factory

    # ---------------- 内部 ----------------

    async def _get_project(self, project_id: int) -> IrProject:
        return ensure_found(
            await self._uow.ir_projects.find_by_id(project_id), codes.IR_NOT_FOUND, "项目不存在"
        )

    def _queue_active(self, project_id: int) -> bool:
        pending, running = self._queue.counts(project_id)
        return pending + running > 0

    async def _summary(self, project: IrProject, chapters: list[IrChapter]) -> ProjectSummaryOut:
        done = sum(1 for c in chapters if c.state in (ChapterState.DONE, ChapterState.STALE))
        return ProjectSummaryOut(
            id=project.id,
            title=project.title,
            type=project.type,
            status=derive_project_status(chapters, self._queue_active(project.id)),
            chapters_done=done,
            chapters_total=len(chapters),
            tbd_count=sum(len(unresolved_tbds(c.content)) for c in chapters),
            updated_at=project.updated_at.isoformat(),
        )

    async def _detail(self, project: IrProject) -> ProjectDetailOut:
        chapters = await self._uow.ir_chapters.list_by_project(project.id)
        sources = await self._uow.ir_sources.list_by_project(project.id)
        summary = await self._summary(project, chapters)
        return ProjectDetailOut(
            **summary.model_dump(),
            chapters=[ChapterMetaOut.build(c) for c in chapters],
            sources=[SourceOut.build(s) for s in sources],
            checklist=CHECKLIST,
        )

    # ---------------- 项目 ----------------

    async def list_projects(self, page: int, page_size: int) -> dict:
        rows, total = await self._uow.ir_projects.list_page(page, page_size)
        items = []
        for p in rows:
            chapters = await self._uow.ir_chapters.list_by_project(p.id)
            items.append(await self._summary(p, chapters))
        return {"items": items, "total": total}

    async def create_project(self, title: str, type_: str) -> dict:
        validate_report_type(type_)
        template = await self._uow.ir_templates.find_by_type(type_)
        if template is None or template.status != TemplateStatus.READY:
            raise ParamException(
                codes.IR_TEMPLATE_NOT_READY, "该类型模板未学习，请先到范本库完成学习"
            )
        project = IrProject.create(title, type_)
        self._uow.ir_projects.add(project)
        await self._uow.flush()
        for i, ch in enumerate(template.chapters, start=1):
            self._uow.ir_chapters.add(
                IrChapter.create(project.id, ch.get("key", f"ch{i}"), ch.get("title", f"第{i}章"), i)
            )
        await self._uow.flush()
        await self._uow.commit()
        return {"project": await self._detail(project)}

    async def get_project(self, project_id: int) -> dict:
        project = await self._get_project(project_id)
        return {"project": await self._detail(project)}

    async def delete_project(self, project_id: int) -> None:
        project = await self._get_project(project_id)
        self._queue.cancel_project(project_id)
        self._storage.delete_tree(f"projects/{project_id}")
        await self._uow.ir_projects.delete(project)
        await self._uow.commit()

    # ---------------- 资料 ----------------

    async def list_sources(self, project_id: int) -> dict:
        await self._get_project(project_id)
        sources = await self._uow.ir_sources.list_by_project(project_id)
        return {"sources": [SourceOut.build(s) for s in sources]}

    async def upload_sources(
        self, project_id: int, files: list[tuple[str, bytes]]
    ) -> list[SourceOut]:
        project = await self._get_project(project_id)
        for filename, data in files:
            if not filename.lower().endswith(SOURCE_EXTS):
                raise ParamException(codes.IR_PARAM_INVALID, f"不支持的资料类型：{filename}")
            if len(data) > UPLOAD_MAX_BYTES:
                raise ParamException(codes.IR_PARAM_INVALID, f"文件超过 50MB：{filename}")
        created: list[IrSource] = []
        for filename, data in files:
            ext = Path(filename).suffix.lower()
            rel = self._storage.save(
                f"projects/{project_id}/sources/{uuid.uuid4().hex[:12]}{ext}", data
            )
            source = IrSource.create_file(project_id, filename, rel)
            self._uow.ir_sources.add(source)
            created.append(source)
        project.touch()
        await self._uow.flush()
        await self._uow.commit()
        for source in created:
            self._runner.spawn(self._parse_source(source.id))
        return [SourceOut.build(s) for s in created]

    async def _parse_source(self, source_id: int) -> None:
        async with self._uow_factory() as uow:
            source = await uow.ir_sources.find_by_id(source_id)
            if source is None:
                return
            kind, file_path, url = source.kind, source.file_path, source.url
        try:
            if kind == "url":
                text, quality = await parse_url(url or ""), "ok"
            else:
                text, quality = await parse_document(
                    self._storage.absolute(file_path or ""), self._agent
                )
        except Exception as e:  # noqa: BLE001
            logger.warning("资料解析失败 source=%s: %s", source_id, e)
            async with self._uow_factory() as uow:
                source = await uow.ir_sources.find_by_id(source_id)
                if source is not None:
                    source.parse_state = ParseState.FAILED
                    await uow.commit()
            return
        async with self._uow_factory() as uow:
            source = await uow.ir_sources.find_by_id(source_id)
            if source is not None:
                source.parsed_text = text
                source.quality = quality
                source.parse_state = ParseState.READY
                await uow.commit()

    async def add_url_source(self, project_id: int, url: str) -> SourceOut:
        project = await self._get_project(project_id)
        if not url.startswith(("http://", "https://")):
            raise ParamException(codes.IR_PARAM_INVALID, "URL 必须以 http(s):// 开头")
        source = IrSource.create_url(project_id, url)
        self._uow.ir_sources.add(source)
        project.touch()
        await self._uow.flush()
        await self._uow.commit()
        self._runner.spawn(self._parse_source(source.id))
        return SourceOut.build(source)

    async def delete_source(self, project_id: int, source_id: int) -> None:
        await self._get_project(project_id)
        source = ensure_found(
            await self._uow.ir_sources.find_by_id(source_id), codes.IR_NOT_FOUND, "资料不存在"
        )
        if source.project_id != project_id:
            raise ParamException(codes.IR_NOT_FOUND, "资料不存在")
        if source.file_path:
            self._storage.delete(source.file_path)
        await self._uow.ir_sources.delete(source)
        await self._uow.commit()

    async def source_file_path(self, project_id: int, source_id: int) -> Path:
        await self._get_project(project_id)
        source = ensure_found(
            await self._uow.ir_sources.find_by_id(source_id), codes.IR_NOT_FOUND, "资料不存在"
        )
        if source.project_id != project_id or not source.file_path:
            raise ParamException(codes.IR_NOT_FOUND, "资料不存在")
        return self._storage.absolute(source.file_path)

    async def analyze_impact(self, project_id: int, source_id: int) -> list[dict]:
        await self._get_project(project_id)
        source = ensure_found(
            await self._uow.ir_sources.find_by_id(source_id), codes.IR_NOT_FOUND, "资料不存在"
        )
        if source.parse_state != ParseState.READY:
            raise ParamException(codes.IR_PARAM_INVALID, "资料尚未解析完成")
        chapters = await self._uow.ir_chapters.list_by_project(project_id)
        done = [
            c for c in chapters if c.state in (ChapterState.DONE, ChapterState.STALE)
        ]
        if not done:
            return []
        draft = await self._agent.analyze_impact(
            source.parsed_text[:10_000], [{"key": c.key, "title": c.title} for c in done]
        )
        by_key = {c.key: c for c in done}
        out = []
        for item in draft.items:
            chapter = by_key.get(item.chapter_key)
            if chapter is not None:
                out.append(
                    {"chapter_id": chapter.id, "title": chapter.title, "reason": item.reason}
                )
        return out

    # ---------------- 对话落库（供第二批复用） ----------------

    def _add_chat(
        self, project_id: int, role: str, content: str,
        chapter_id: int | None, updated: list[int] | None = None,
    ) -> IrChatMessage:
        msg = IrChatMessage.create(project_id, role, content, chapter_id, updated)
        self._uow.ir_chats.add(msg)
        return msg

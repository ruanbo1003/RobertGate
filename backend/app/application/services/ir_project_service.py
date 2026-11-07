"""invest-reports 项目用例（第一批：项目/资料；研究/编辑/对话在第二批追加）。"""

from __future__ import annotations

import copy
import logging
import re
import uuid
from pathlib import Path

from app.application.dto.invest_report import (
    ChapterDetailOut,
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
    resolve_tbd_in_content,
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

    # ---------------- 研究与状态 ----------------

    async def start_research(
        self, project_id: int, chapter_ids: list[int] | None, confirm: bool = False
    ) -> dict:
        del confirm  # 2046 预留：未保存编辑由前端本地确认，后端暂不校验
        await self._get_project(project_id)
        chapters = await self._uow.ir_chapters.list_by_project(project_id)
        if chapter_ids:
            targets = [c.id for c in chapters if c.id in chapter_ids]
        else:
            targets = [c.id for c in chapters if c.state != ChapterState.DONE]
        enqueued = await self._queue.enqueue(project_id, targets)
        return {"enqueued": enqueued}

    def cancel_queue(self, project_id: int) -> dict:
        return {"cancelled": self._queue.cancel_project(project_id)}

    async def get_status(self, project_id: int, feed_after: int) -> dict:
        await self._get_project(project_id)
        chapters = await self._uow.ir_chapters.list_by_project(project_id)
        pending, running = self._queue.counts(project_id)
        return {
            "status": derive_project_status(chapters, pending + running > 0),
            "queue": {
                "pending": pending,
                "running": running,
                "paused": self._queue.paused,
                "paused_reason": self._queue.paused_reason,
            },
            "chapters": [
                {
                    "id": c.id,
                    "state": c.state,
                    "tbd_count": len(unresolved_tbds(c.content)),
                    "version": c.version,
                    "error": c.error,
                }
                for c in chapters
            ],
            "tbd_count": sum(len(unresolved_tbds(c.content)) for c in chapters),
            "feed": self._queue.feed(project_id, feed_after),
        }

    # ---------------- 章节与编辑 ----------------

    async def _get_chapter(self, project_id: int, chapter_id: int):
        chapter = ensure_found(
            await self._uow.ir_chapters.find_by_id(chapter_id), codes.IR_NOT_FOUND, "章节不存在"
        )
        if chapter.project_id != project_id:
            raise ParamException(codes.IR_NOT_FOUND, "章节不存在")
        return chapter

    async def get_chapter(self, project_id: int, chapter_id: int) -> dict:
        await self._get_project(project_id)
        chapter = await self._get_chapter(project_id, chapter_id)
        return {"chapter": ChapterDetailOut.build(chapter)}

    @staticmethod
    def _prune_content(content: dict) -> dict:
        """重算引用/tbd 子集：仅保留正文仍引用的（人工删标记 = 解除关联）。"""
        text_all = "".join(p["text"] for p in content.get("paragraphs", []))
        used_c = {int(m) for m in re.findall(r"⟦c:(\d+)⟧", text_all)}
        used_t = {int(m) for m in re.findall(r"⟦tbd:(\d+)⟧", text_all)}
        content["citations"] = [c for c in content.get("citations", []) if c["id"] in used_c]
        for i, c in enumerate(content["citations"], start=1):
            c["n"] = i
        content["tbds"] = [
            t for t in content.get("tbds", []) if t["id"] in used_t or t.get("resolved")
        ]
        return content

    async def update_paragraph(
        self, project_id: int, chapter_id: int, paragraph_id: str, text: str
    ) -> dict:
        project = await self._get_project(project_id)
        chapter = await self._get_chapter(project_id, chapter_id)
        chapter.ensure_not_busy()
        content = copy.deepcopy(chapter.content)
        para = next((p for p in content["paragraphs"] if p["id"] == paragraph_id), None)
        if para is None:
            raise ParamException(codes.IR_NOT_FOUND, "段落不存在")
        para["text"] = text
        chapter.bump_version(self._prune_content(content))
        project.touch()
        await self._uow.commit()
        return {"chapter": ChapterDetailOut.build(chapter)}

    async def rewrite_paragraph(
        self, project_id: int, chapter_id: int, paragraph_id: str, instruction: str
    ) -> dict:
        project = await self._get_project(project_id)
        chapter = await self._get_chapter(project_id, chapter_id)
        chapter.ensure_not_busy()
        content = copy.deepcopy(chapter.content)
        para = next((p for p in content["paragraphs"] if p["id"] == paragraph_id), None)
        if para is None:
            raise ParamException(codes.IR_NOT_FOUND, "段落不存在")
        new_text = await self._agent.rewrite_paragraph(
            para["text"], instruction, list(content.get("citations", []))
        )
        known = {c["id"] for c in content.get("citations", [])} | {
            t["id"] for t in content.get("tbds", [])
        }
        para["text"] = re.sub(
            r"⟦(c|tbd):(\d+)⟧",
            lambda m: m.group(0) if int(m.group(2)) in known else "",
            new_text,
        )
        chapter.bump_version(self._prune_content(content))
        project.touch()
        await self._uow.commit()
        return {"chapter": ChapterDetailOut.build(chapter)}

    async def resolve_tbd(self, project_id: int, tbd_id: int, value: str) -> dict:
        project = await self._get_project(project_id)
        chapters = await self._uow.ir_chapters.list_by_project(project_id)
        for chapter in chapters:
            if any(t.get("id") == tbd_id for t in chapter.content.get("tbds", [])):
                chapter.ensure_not_busy()
                chapter.bump_version(resolve_tbd_in_content(chapter.content, tbd_id, value))
                project.touch()
                await self._uow.commit()
                return {"chapter": ChapterDetailOut.build(chapter)}
        raise ParamException(codes.IR_NOT_FOUND, "待补充项不存在")

    # ---------------- 对话 ----------------

    async def list_chat(self, project_id: int, limit: int = 50) -> dict:
        await self._get_project(project_id)
        messages = await self._uow.ir_chats.list_by_project(project_id, limit)
        return {
            "messages": [
                {
                    "id": m.id,
                    "role": m.role,
                    "content": m.content,
                    "chapter_id": m.chapter_id,
                    "updated_chapter_ids": list(m.updated_chapter_ids),
                    "ts": m.created_at.isoformat(),
                }
                for m in messages
            ]
        }

    async def send_chat(
        self, project_id: int, message: str, chapter_id: int | None
    ) -> dict:
        project = await self._get_project(project_id)
        chapter = None
        if chapter_id is not None:
            chapter = await self._get_chapter(project_id, chapter_id)
            chapter.ensure_not_busy()
        self._add_chat(project_id, "user", message, chapter_id)
        chapter_dict = (
            {
                "title": chapter.title,
                "paragraphs": chapter.content.get("paragraphs", []),
                "citations": chapter.content.get("citations", []),
            }
            if chapter is not None
            else None
        )
        outcome = await self._agent.chat(
            f"{project.title}（{project.type}）", chapter_dict, message
        )
        updated: list[int] = []
        if outcome.updated and outcome.paragraphs and chapter is not None:
            content = copy.deepcopy(chapter.content)
            content["paragraphs"] = [
                {"id": f"p{i + 1}", "text": text} for i, text in enumerate(outcome.paragraphs)
            ]
            chapter.bump_version(self._prune_content(content))
            updated = [chapter.id]
        self._add_chat(project_id, "assistant", outcome.reply, chapter_id, updated)
        project.touch()
        await self._uow.commit()
        return {"reply": outcome.reply, "updated_chapter_ids": updated}

    # ---------------- 对话落库（供第二批复用） ----------------

    def _add_chat(
        self, project_id: int, role: str, content: str,
        chapter_id: int | None, updated: list[int] | None = None,
    ) -> IrChatMessage:
        msg = IrChatMessage.create(project_id, role, content, chapter_id, updated)
        self._uow.ir_chats.add(msg)
        return msg

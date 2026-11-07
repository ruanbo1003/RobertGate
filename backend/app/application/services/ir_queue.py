"""invest-reports 章节研究队列。

规则（docs/api/invest-reports.md §5/§9）：
- 串行 FIFO（研究一个章节可长达分钟级，默认并发 1）
- 入队即把章节置 researching/updating 并 commit；重复入队跳过
- IR_UPSTREAM_QUOTA → 队列全局暂停、当前与排队章节回退 pending；新入队自动恢复
- 失败单章 failed，不连坐；取消只回退排队中的
- feed：每项目内存环形缓冲（近 _FEED_KEEP 条，进程内单调 id；重启丢失可接受）

队列脱离请求生命周期，经 uow_factory 自开工作单元读写；Agent 调用（含联网检索）
严格发生在数据库事务之外。
"""

from __future__ import annotations

import asyncio
import itertools
import logging
from datetime import datetime, timezone

from app.application.dto.invest_report import ResearchContext, SourceDoc
from app.application.ports import IrAgent, TaskRunner
from app.application.services.ir_content import remap_draft
from app.domain.errors import ServerException, codes
from app.domain.models.invest_report import ChapterState, ParseState

logger = logging.getLogger(__name__)

_FEED_KEEP = 500
_SOURCE_TEXT_LIMIT = 15_000  # 每份资料进入研究上下文的最大字符数


class IrResearchQueue:
    def __init__(
        self,
        uow_factory,
        agent: IrAgent,
        runner: TaskRunner,
        poll_interval: float = 1.0,
    ) -> None:
        self._uow_factory = uow_factory
        self._agent = agent
        self._runner = runner
        self._poll = poll_interval
        self._sem = asyncio.Semaphore(1)
        self._items: dict[int, str] = {}  # chapter_id -> queued | running
        self._cancelled: set[int] = set()
        self._paused = False
        self._paused_reason: str | None = None
        self._feeds: dict[int, list[dict]] = {}
        self._feed_seq = itertools.count(1)

    # ---------------- 对外状态 ----------------

    @property
    def paused(self) -> bool:
        return self._paused

    @property
    def paused_reason(self) -> str | None:
        return self._paused_reason

    @property
    def active_count(self) -> int:
        return len(self._items)

    def counts(self, project_id: int) -> tuple[int, int]:
        del project_id  # 单用户规模：队列不分项目统计
        pending = sum(1 for s in self._items.values() if s == "queued")
        running = sum(1 for s in self._items.values() if s == "running")
        return pending, running

    def feed(self, project_id: int, after: int = 0) -> list[dict]:
        return [e for e in self._feeds.get(project_id, []) if e["id"] > after][:100]

    def _push_feed(
        self, project_id: int, chapter_id: int, kind: str, text: str, url: str | None
    ) -> None:
        buf = self._feeds.setdefault(project_id, [])
        buf.append(
            {
                "id": next(self._feed_seq),
                "chapter_id": chapter_id,
                "kind": kind,
                "text": text,
                "ref": {"url": url, "source_id": None, "page": None} if url else None,
                "ts": datetime.now(timezone.utc).isoformat(),
            }
        )
        if len(buf) > _FEED_KEEP:
            del buf[: len(buf) - _FEED_KEEP]

    # ---------------- 入队 / 取消 ----------------

    async def enqueue(self, project_id: int, chapter_ids: list[int]) -> list[int]:
        # 用户重新发起研究 = 已处理全局错误（充值/换 Key），自动恢复
        self._paused = False
        self._paused_reason = None
        enqueued: list[int] = []
        async with self._uow_factory() as uow:
            for cid in chapter_ids:
                if cid in self._items:
                    continue
                chapter = await uow.ir_chapters.find_by_id(cid)
                if chapter is None or chapter.project_id != project_id:
                    continue
                if chapter.state in (ChapterState.RESEARCHING, ChapterState.UPDATING):
                    continue
                chapter.mark_researching()
                enqueued.append(cid)
            if enqueued:
                await uow.commit()
        for cid in enqueued:
            self._items[cid] = "queued"
            self._cancelled.discard(cid)
            self._runner.spawn(self._run(project_id, cid))
        return enqueued

    def cancel_project(self, project_id: int) -> int:
        del project_id
        cancelled = 0
        for cid, state in list(self._items.items()):
            if state == "queued":
                self._cancelled.add(cid)
                cancelled += 1
        return cancelled

    # ---------------- 执行 ----------------

    async def _run(self, project_id: int, chapter_id: int) -> None:
        try:
            while self._paused and chapter_id not in self._cancelled:
                await asyncio.sleep(self._poll)
            async with self._sem:
                if chapter_id in self._cancelled or self._paused:
                    await self._revert_pending(chapter_id)
                    return
                self._items[chapter_id] = "running"
                await self._research(project_id, chapter_id)
        finally:
            self._items.pop(chapter_id, None)
            self._cancelled.discard(chapter_id)

    async def _research(self, project_id: int, chapter_id: int) -> None:
        async with self._uow_factory() as uow:
            project = await uow.ir_projects.find_by_id(project_id)
            chapter = await uow.ir_chapters.find_by_id(chapter_id)
            if project is None or chapter is None:
                return
            template = await uow.ir_templates.find_by_type(project.type)
            chapters = await uow.ir_chapters.list_by_project(project_id)
            sources = await uow.ir_sources.list_by_project(project_id)
            brief = ""
            if template is not None:
                brief = next(
                    (c.get("brief", "") for c in template.chapters if c.get("key") == chapter.key),
                    "",
                )
            ctx = ResearchContext(
                project_title=project.title,
                report_type=project.type,
                chapter_key=chapter.key,
                chapter_title=chapter.title,
                chapter_brief=brief,
                style_notes=template.style_notes if template else "",
                prior_chapter_titles=[
                    c.title for c in chapters if c.state == ChapterState.DONE
                ],
                sources=[
                    SourceDoc(id=s.id, name=s.display_name(), text=s.parsed_text[:_SOURCE_TEXT_LIMIT])
                    for s in sources
                    if s.parse_state == ParseState.READY and s.parsed_text
                ],
            )

        def on_event(kind: str, text: str, url: str | None = None) -> None:
            self._push_feed(project_id, chapter_id, kind, text, url)

        try:
            draft = await self._agent.research_chapter(ctx, on_event)
        except ServerException as e:
            if e.code == codes.IR_UPSTREAM_QUOTA:
                self._paused = True
                self._paused_reason = e.message
                await self._revert_pending(chapter_id)
                await self._revert_all_queued()
            else:
                await self._fail(project_id, chapter_id, e.message)
            return
        except Exception as e:  # noqa: BLE001
            logger.exception("章节研究异常 chapter=%s", chapter_id)
            await self._fail(project_id, chapter_id, str(e)[:300])
            return

        content = remap_draft(draft, itertools.count(start=chapter_id * 100_000 + 1).__next__)
        async with self._uow_factory() as uow:
            chapter = await uow.ir_chapters.find_by_id(chapter_id)
            project = await uow.ir_projects.find_by_id(project_id)
            if chapter is not None:
                chapter.mark_done(content)
                if project is not None:
                    project.touch()
                await uow.commit()
        self._push_feed(project_id, chapter_id, "done", f"{ctx.chapter_title} 初稿完成", None)

    async def _fail(self, project_id: int, chapter_id: int, error: str) -> None:
        async with self._uow_factory() as uow:
            chapter = await uow.ir_chapters.find_by_id(chapter_id)
            if chapter is not None:
                chapter.mark_failed(error)
                await uow.commit()
        self._push_feed(project_id, chapter_id, "error", f"研究失败：{error}", None)

    async def _revert_pending(self, chapter_id: int) -> None:
        async with self._uow_factory() as uow:
            chapter = await uow.ir_chapters.find_by_id(chapter_id)
            if chapter is not None and chapter.state in (
                ChapterState.RESEARCHING,
                ChapterState.UPDATING,
            ):
                chapter.mark_pending()
                await uow.commit()

    async def _revert_all_queued(self) -> None:
        for cid, state in list(self._items.items()):
            if state == "queued":
                self._cancelled.add(cid)
                await self._revert_pending(cid)

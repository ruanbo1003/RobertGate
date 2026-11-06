"""invest-reports 范本库用例：范本上传/删除、模板学习/微调。

异步环节（范本解析、模板学习）经 runner.spawn + uow_factory 自开工作单元，
与请求事务解耦（同 ai-videos 模式）。
"""

from __future__ import annotations

import logging
import uuid

from app.application.dto.invest_report import LibraryOut, SampleOut, TemplateOut
from app.application.ports import IrAgent, TaskRunner
from app.application.services.av_queue import AvStorage
from app.domain.errors import ParamException, codes, ensure_found
from app.domain.models.invest_report import (
    SAMPLE_EXTS,
    UPLOAD_MAX_BYTES,
    IrSample,
    IrTemplate,
    ParseState,
    TemplateStatus,
    validate_report_type,
)
from app.domain.repositories.uow import UnitOfWork
from app.infrastructure.ir_parsers import parse_document

logger = logging.getLogger(__name__)

_LEARN_TEXT_LIMIT = 20_000  # 每份范本喂给 LLM 的最大字符数


class IrLibraryService:
    def __init__(
        self, uow: UnitOfWork, agent: IrAgent, storage: AvStorage, runner: TaskRunner, uow_factory
    ) -> None:
        self._uow = uow
        self._agent = agent
        self._storage = storage
        self._runner = runner
        self._uow_factory = uow_factory

    async def get_library(self) -> LibraryOut:
        out: dict = {}
        for type_ in ("advice", "dd"):
            template = await self._uow.ir_templates.find_by_type(type_)
            samples = await self._uow.ir_samples.list_by_type(type_)
            out[type_] = {
                "template": TemplateOut.build(template) if template else None,
                "samples": [SampleOut.build(s) for s in samples],
            }
        return LibraryOut(advice=out["advice"], dd=out["dd"])

    # ---------------- 范本 ----------------

    async def upload_samples(
        self, type_: str, files: list[tuple[str, bytes]]
    ) -> list[SampleOut]:
        validate_report_type(type_)
        for filename, data in files:
            if not filename.lower().endswith(SAMPLE_EXTS):
                raise ParamException(codes.IR_PARAM_INVALID, f"范本仅支持 .docx：{filename}")
            if len(data) > UPLOAD_MAX_BYTES:
                raise ParamException(codes.IR_PARAM_INVALID, f"文件超过 50MB：{filename}")
        created: list[IrSample] = []
        for filename, data in files:
            rel = self._storage.save(f"samples/{uuid.uuid4().hex[:12]}.docx", data)
            sample = IrSample.create(type_, filename, rel)
            self._uow.ir_samples.add(sample)
            created.append(sample)
        await self._uow.flush()
        await self._uow.commit()
        for sample in created:
            self._runner.spawn(self._parse_sample(sample.id))
        return [SampleOut.build(s) for s in created]

    async def _parse_sample(self, sample_id: int) -> None:
        async with self._uow_factory() as uow:
            sample = await uow.ir_samples.find_by_id(sample_id)
            if sample is None:
                return
            path = self._storage.absolute(sample.file_path)
        try:
            text, _quality = await parse_document(path, self._agent)
        except Exception as e:  # noqa: BLE001
            logger.warning("范本解析失败 sample=%s: %s", sample_id, e)
            async with self._uow_factory() as uow:
                sample = await uow.ir_samples.find_by_id(sample_id)
                if sample is not None:
                    sample.parse_state = ParseState.FAILED
                    await uow.commit()
            return
        async with self._uow_factory() as uow:
            sample = await uow.ir_samples.find_by_id(sample_id)
            if sample is not None:
                sample.parsed_text = text
                sample.parse_state = ParseState.READY
                await uow.commit()

    async def delete_sample(self, sample_id: int) -> None:
        sample = ensure_found(
            await self._uow.ir_samples.find_by_id(sample_id), codes.IR_NOT_FOUND, "范本不存在"
        )
        self._storage.delete(sample.file_path)
        await self._uow.ir_samples.delete(sample)
        await self._uow.commit()

    # ---------------- 模板 ----------------

    async def learn(self, type_: str, sample_ids: list[int] | None) -> None:
        validate_report_type(type_)
        samples = await self._uow.ir_samples.list_by_type(type_)
        ready = [s for s in samples if s.parse_state == ParseState.READY]
        if sample_ids:
            ready = [s for s in ready if s.id in sample_ids]
        if not ready:
            raise ParamException(codes.IR_PARAM_INVALID, "该类型暂无已解析的范本，请先上传并等待解析")
        template = await self._uow.ir_templates.find_by_type(type_)
        if template is None:
            template = IrTemplate.create(type_)
            self._uow.ir_templates.add(template)
        template.start_learning([s.id for s in ready])
        await self._uow.flush()
        await self._uow.commit()
        texts = [s.parsed_text[:_LEARN_TEXT_LIMIT] for s in ready]
        self._runner.spawn(self._learn_bg(type_, texts))

    async def _learn_bg(self, type_: str, texts: list[str]) -> None:
        try:
            draft = await self._agent.learn_template(texts, type_)
        except Exception as e:  # noqa: BLE001
            logger.warning("模板学习失败 type=%s: %s", type_, e)
            async with self._uow_factory() as uow:
                template = await uow.ir_templates.find_by_type(type_)
                if template is not None:
                    template.fail_learning(str(e))
                    await uow.commit()
            return
        chapters = [c.model_dump() for c in draft.chapters]
        async with self._uow_factory() as uow:
            template = await uow.ir_templates.find_by_type(type_)
            if template is not None:
                template.finish_learning(chapters, draft.style_notes)
                await uow.commit()

    async def update_template(
        self, type_: str, chapters: list[dict], style_notes: str | None
    ) -> TemplateOut:
        template = await self._uow.ir_templates.find_by_type(validate_report_type(type_))
        if template is None or template.status != TemplateStatus.READY:
            raise ParamException(codes.IR_NOT_FOUND, "模板不存在或未就绪")
        if not chapters:
            raise ParamException(codes.IR_PARAM_INVALID, "模板至少保留一个章节")
        template.chapters = chapters
        if style_notes is not None:
            template.style_notes = style_notes
        template.finish_learning(chapters, template.style_notes)
        await self._uow.commit()
        return TemplateOut.build(template)

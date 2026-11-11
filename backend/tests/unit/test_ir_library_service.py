"""IrLibraryService 单测：上传校验、异步解析、学习门槛与状态流转。"""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock

import pytest

from app.application.services.ir_library_service import IrLibraryService
from app.domain.errors import ParamException, codes
from app.domain.models.invest_report import IrSample, IrTemplate, ParseState, TemplateStatus
from app.infrastructure.ai.ir_agent_mock import MockIrAgent


class FakeStorage:
    def __init__(self):
        self.saved: dict[str, bytes] = {}

    def save(self, rel_path: str, data: bytes) -> str:
        self.saved[rel_path] = data
        return rel_path

    def read(self, rel_path: str) -> bytes:
        return self.saved[rel_path]

    def absolute(self, rel_path: str):
        from pathlib import Path

        return Path("/fake") / rel_path

    def delete(self, rel_path: str) -> None:
        self.saved.pop(rel_path, None)


class InlineRunner:
    """同步执行 spawn 的 runner：后台任务立刻跑完，便于断言。"""

    def spawn(self, coro) -> None:
        asyncio.get_event_loop().create_task(coro)


@pytest.fixture
def storage():
    return FakeStorage()


def _stamp_ids(uow) -> None:
    """FakeUow 无 DB：add 时给实体回填自增 id，模拟 flush 行为。"""
    counter = {"n": 100}

    def stamp(repo_name):
        def _side(entity):
            counter["n"] += 1
            if getattr(entity, "id", None) is None:
                entity.id = counter["n"]
            uow.calls.append(f"{repo_name}.add")
        return _side

    from unittest.mock import MagicMock
    for name in ("ir_samples", "ir_templates", "ir_projects", "ir_chapters", "ir_sources", "ir_chats"):
        getattr(uow, name).add = MagicMock(side_effect=stamp(name))


class FakeParser:
    def __init__(self):
        self.result = ("全文", "ok")
        self.calls: list[str] = []

    async def parse_document(self, path, agent):
        self.calls.append(str(path))
        return self.result

    async def parse_url(self, url):
        return "网页正文"


@pytest.fixture
def parser():
    return FakeParser()


@pytest.fixture
def service(uow, storage, parser):
    _stamp_ids(uow)
    @asynccontextmanager
    async def uow_factory():
        yield uow

    svc = IrLibraryService(
        uow=uow, agent=MockIrAgent(), storage=storage,
        runner=InlineRunner(), uow_factory=uow_factory, parser=parser,
    )
    return svc


async def test_upload_rejects_non_docx(service):
    with pytest.raises(ParamException) as e:
        await service.upload_samples("advice", [("a.pdf", b"x")])
    assert e.value.code == codes.IR_PARAM_INVALID


async def test_upload_rejects_oversize(service):
    with pytest.raises(ParamException) as e:
        await service.upload_samples("advice", [("a.docx", b"x" * (50 * 1024 * 1024 + 1))])
    assert e.value.code == codes.IR_PARAM_INVALID


async def test_upload_saves_and_spawns_parse(service, uow, storage, parser):
    sample = IrSample.create("advice", "a.docx", "samples/x.docx")
    sample.id = 7
    uow.ir_samples.find_by_id = AsyncMock(return_value=sample)

    out = await service.upload_samples("advice", [("a.docx", b"content")])
    assert len(out) == 1
    assert list(storage.saved.values()) == [b"content"]
    await asyncio.sleep(0.05)  # 等后台解析
    assert parser.calls and sample.parse_state == ParseState.READY and sample.parsed_text == "全文"


async def test_learn_requires_ready_samples(service, uow):
    uow.ir_samples.list_by_type = AsyncMock(return_value=[])
    uow.ir_templates.find_by_type = AsyncMock(return_value=None)
    with pytest.raises(ParamException) as e:
        await service.learn("advice", None)
    assert e.value.code == codes.IR_PARAM_INVALID


async def test_learn_transitions_to_ready(service, uow):
    s = IrSample.create("advice", "a.docx", "p")
    s.id = 1
    s.parse_state = ParseState.READY
    s.parsed_text = "样本全文"
    uow.ir_samples.list_by_type = AsyncMock(return_value=[s])
    tpl = IrTemplate.create("advice")
    uow.ir_templates.find_by_type = AsyncMock(return_value=tpl)

    await service.learn("advice", None)
    assert tpl.status == TemplateStatus.LEARNING
    await asyncio.sleep(0.1)
    assert tpl.status == TemplateStatus.READY
    assert len(tpl.chapters) >= 3 and tpl.learned_from == [1]


async def test_update_template_requires_ready(service, uow):
    tpl = IrTemplate.create("advice")
    uow.ir_templates.find_by_type = AsyncMock(return_value=tpl)
    with pytest.raises(ParamException) as e:
        await service.update_template("advice", [{"key": "a", "title": "一", "brief": ""}], None)
    assert e.value.code == codes.IR_NOT_FOUND

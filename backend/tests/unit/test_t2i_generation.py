"""T2IGenerator 后台生成逻辑测试：成功路径 + 两种失败路径。

用 InlineRunner 代替真实 AsyncioTaskRunner——spawn() 只捕获 coroutine，
测试自己 await 它，从而在同一个事件循环里同步驱动、断言结果。
生成器现在注入 uow_factory，因此这里直接喂一个返回假 UoW 的工厂，
不再 monkeypatch 模块里的 Repo 符号。
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest

from app.application.services.t2i_generation import T2IGenerator
from app.domain.models.t2i import T2IImage, T2ITask

from .conftest import make_uow


class InlineRunner:
    def __init__(self):
        self.captured = None

    def spawn(self, coro):
        self.captured = coro


class _FakeUowCM:
    def __init__(self, uow):
        self._uow = uow

    async def __aenter__(self):
        return self._uow

    async def __aexit__(self, *exc_info):
        return False


def _image(status: str = "generating") -> T2IImage:
    return T2IImage(
        id="img-1",
        task_id="task-1",
        status=status,
        available=False,
        mime=None,
        created_at=datetime.now(timezone.utc),
    )


def _task(status: str = "generating") -> T2ITask:
    now = datetime.now(timezone.utc)
    return T2ITask(
        id="task-1",
        template_code="english-primer",
        keywords={"item": "apple"},
        keywords_hash="hash",
        status=status,
        last_failed=False,
        created_at=now,
        updated_at=now,
    )


@pytest.fixture
def bg_uow():
    """后台任务自开的工作单元（与请求 session 无关）。"""
    return make_uow()


@pytest.fixture
def runner():
    return InlineRunner()


@pytest.fixture
def ai():
    mock = AsyncMock()
    mock.generate_image.return_value = "https://example.com/generated.png"
    return mock


@pytest.fixture
def fetch_image():
    async def _fetch(url):
        return b"payload", "image/png"

    return AsyncMock(side_effect=_fetch)


@pytest.fixture
def generator(runner, ai, fetch_image, bg_uow):
    return T2IGenerator(
        uow_factory=lambda: _FakeUowCM(bg_uow),
        ai=ai,
        fetch_image=fetch_image,
        runner=runner,
    )


@pytest.mark.asyncio
async def test_spawn_delegates_to_runner(generator, runner):
    generator.spawn("task-1", "img-1", "a cute cat")

    assert runner.captured is not None
    runner.captured.close()  # 未 await 的 coroutine 需要 close，避免 RuntimeWarning


@pytest.mark.asyncio
async def test_run_success_marks_image_and_task_succeeded(
    generator, runner, ai, fetch_image, bg_uow
):
    img = _image()
    task = _task()
    bg_uow.t2i_images.find_by_id.return_value = img
    bg_uow.t2i_tasks.find_by_id.return_value = task

    generator.spawn("task-1", "img-1", "a cute cat")
    await runner.captured

    ai.generate_image.assert_awaited_once_with("a cute cat")
    fetch_image.assert_awaited_once_with("https://example.com/generated.png")

    assert img.status == "succeeded"
    assert img.mime == "image/png"
    bg_uow.t2i_blobs.add.assert_called_once()

    assert task.status == "succeeded"
    assert task.last_failed is False
    # 原实现三次 commit（blob / image / task），现在合并为一次
    assert bg_uow.commit.await_count == 1


@pytest.mark.asyncio
async def test_run_generate_image_failure_marks_failed(generator, runner, ai, bg_uow):
    img = _image()
    task = _task()
    ai.generate_image.side_effect = RuntimeError("boom")
    bg_uow.t2i_images.find_by_id.return_value = img
    bg_uow.t2i_tasks.find_by_id.return_value = task

    generator.spawn("task-1", "img-1", "a cute cat")
    await runner.captured

    bg_uow.t2i_blobs.add.assert_not_called()
    assert img.status == "failed"
    assert task.status == "failed"
    assert task.last_failed is True
    assert bg_uow.commit.await_count == 1


@pytest.mark.asyncio
async def test_run_fetch_image_failure_marks_failed(
    generator, runner, fetch_image, bg_uow
):
    img = _image()
    task = _task()
    fetch_image.side_effect = RuntimeError("network down")
    bg_uow.t2i_images.find_by_id.return_value = img
    bg_uow.t2i_tasks.find_by_id.return_value = task

    generator.spawn("task-1", "img-1", "a cute cat")
    await runner.captured

    bg_uow.t2i_blobs.add.assert_not_called()
    assert img.status == "failed"
    assert task.status == "failed"


@pytest.mark.asyncio
async def test_run_image_missing_is_noop(generator, runner, bg_uow):
    bg_uow.t2i_images.find_by_id.return_value = None

    generator.spawn("task-1", "img-1", "a cute cat")
    await runner.captured

    bg_uow.t2i_blobs.add.assert_not_called()
    bg_uow.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_mark_failed_task_missing_is_noop(generator, runner, ai, bg_uow):
    img = _image()
    ai.generate_image.side_effect = RuntimeError("boom")
    bg_uow.t2i_images.find_by_id.return_value = img
    bg_uow.t2i_tasks.find_by_id.return_value = None

    generator.spawn("task-1", "img-1", "a cute cat")
    await runner.captured

    # 任务记录已不在，图片状态仍要落库
    assert img.status == "failed"
    assert bg_uow.commit.await_count == 1

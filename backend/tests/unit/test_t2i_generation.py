"""T2IGenerator 后台生成逻辑测试：成功路径 + 两种失败路径。

用 InlineRunner 代替真实 AsyncioTaskRunner——spawn() 只捕获 coroutine，
测试自己 await 它，从而在同一个事件循环里同步驱动、断言结果。
repo 类在 t2i_generation 模块内按 session 现造，因此这里 monkeypatch 模块
里的 Repo 类为返回固定 AsyncMock 实例的工厂，绕开真实 DB。
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest

from app.application.services import t2i_generation as gen
from app.application.services.t2i_generation import T2IGenerator
from app.domain.models.t2i import T2IImage, T2ITask


class InlineRunner:
    def __init__(self):
        self.captured = None

    def spawn(self, coro):
        self.captured = coro


class _FakeSessionCM:
    def __init__(self, session):
        self._session = session

    async def __aenter__(self):
        return self._session

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
def fake_repos(monkeypatch):
    image_repo = AsyncMock()
    task_repo = AsyncMock()
    blob_repo = AsyncMock()

    monkeypatch.setattr(gen, "T2IImageRepo", lambda session: image_repo)
    monkeypatch.setattr(gen, "T2ITaskRepo", lambda session: task_repo)
    monkeypatch.setattr(gen, "T2IImageBlobRepo", lambda session: blob_repo)

    return image_repo, task_repo, blob_repo


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
def generator(runner, ai, fetch_image):
    session = object()
    return T2IGenerator(
        session_factory=lambda: _FakeSessionCM(session),
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
    generator, runner, ai, fetch_image, fake_repos
):
    image_repo, task_repo, blob_repo = fake_repos
    image_repo.find_by_id.return_value = _image()
    task_repo.find_by_id.return_value = _task()

    generator.spawn("task-1", "img-1", "a cute cat")
    await runner.captured

    ai.generate_image.assert_awaited_once_with("a cute cat")
    fetch_image.assert_awaited_once_with("https://example.com/generated.png")

    img_arg = image_repo.update.call_args.args[0]
    assert img_arg.status == "succeeded"
    assert img_arg.mime == "image/png"
    blob_repo.save.assert_awaited_once()

    task_arg = task_repo.update.call_args.args[0]
    assert task_arg.status == "succeeded"
    assert task_arg.last_failed is False


@pytest.mark.asyncio
async def test_run_generate_image_failure_marks_failed(
    generator, runner, ai, fake_repos
):
    image_repo, task_repo, blob_repo = fake_repos
    ai.generate_image.side_effect = RuntimeError("boom")
    image_repo.find_by_id.return_value = _image()
    task_repo.find_by_id.return_value = _task()

    generator.spawn("task-1", "img-1", "a cute cat")
    await runner.captured

    blob_repo.save.assert_not_called()
    img_arg = image_repo.update.call_args.args[0]
    assert img_arg.status == "failed"
    task_arg = task_repo.update.call_args.args[0]
    assert task_arg.status == "failed"
    assert task_arg.last_failed is True


@pytest.mark.asyncio
async def test_run_fetch_image_failure_marks_failed(
    generator, runner, fetch_image, fake_repos
):
    image_repo, task_repo, blob_repo = fake_repos
    fetch_image.side_effect = RuntimeError("network down")
    image_repo.find_by_id.return_value = _image()
    task_repo.find_by_id.return_value = _task()

    generator.spawn("task-1", "img-1", "a cute cat")
    await runner.captured

    blob_repo.save.assert_not_called()
    img_arg = image_repo.update.call_args.args[0]
    assert img_arg.status == "failed"
    task_arg = task_repo.update.call_args.args[0]
    assert task_arg.status == "failed"


@pytest.mark.asyncio
async def test_run_image_missing_is_noop(generator, runner, fake_repos):
    image_repo, task_repo, blob_repo = fake_repos
    image_repo.find_by_id.return_value = None

    generator.spawn("task-1", "img-1", "a cute cat")
    await runner.captured

    image_repo.update.assert_not_called()
    blob_repo.save.assert_not_called()


@pytest.mark.asyncio
async def test_mark_failed_task_missing_is_noop(generator, runner, ai, fake_repos):
    image_repo, task_repo, _ = fake_repos
    ai.generate_image.side_effect = RuntimeError("boom")
    image_repo.find_by_id.return_value = _image()
    task_repo.find_by_id.return_value = None

    generator.spawn("task-1", "img-1", "a cute cat")
    await runner.captured

    image_repo.update.assert_awaited_once()
    task_repo.update.assert_not_called()

"""AsyncioTaskRunner 测试：任务被排入事件循环、异常任务被记录且从集合移除。"""

import asyncio
import logging

import pytest

from app.infrastructure.tasks import AsyncioTaskRunner


@pytest.mark.asyncio
async def test_spawn_runs_coroutine_and_discards_task_on_success():
    runner = AsyncioTaskRunner()
    result = []

    async def _coro():
        result.append(1)

    runner.spawn(_coro())
    pending = set(runner._tasks)
    assert len(pending) == 1

    await asyncio.gather(*pending)

    assert result == [1]
    assert len(runner._tasks) == 0


@pytest.mark.asyncio
async def test_spawn_logs_exception_and_discards_task(caplog):
    runner = AsyncioTaskRunner()

    async def _boom():
        raise RuntimeError("kaboom")

    with caplog.at_level(logging.ERROR, logger="app.core.tasks"):
        runner.spawn(_boom())
        pending = set(runner._tasks)
        await asyncio.gather(*pending, return_exceptions=True)

    assert len(runner._tasks) == 0
    assert any("后台任务异常" in record.message for record in caplog.records)


@pytest.mark.asyncio
async def test_spawn_cancelled_task_not_logged_as_error(caplog):
    runner = AsyncioTaskRunner()

    async def _sleep_forever():
        await asyncio.sleep(10)

    with caplog.at_level(logging.ERROR, logger="app.core.tasks"):
        runner.spawn(_sleep_forever())
        pending = set(runner._tasks)
        for t in pending:
            t.cancel()
        await asyncio.gather(*pending, return_exceptions=True)

    assert len(runner._tasks) == 0
    assert not any("后台任务异常" in record.message for record in caplog.records)

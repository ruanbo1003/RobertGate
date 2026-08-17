"""后台任务运行器：包一层 asyncio.create_task，防 GC + 记录异常。"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Coroutine
from typing import Any

from app.application.ports import TaskRunner

logger = logging.getLogger(__name__)

__all__ = ["TaskRunner", "AsyncioTaskRunner"]


class AsyncioTaskRunner:
    def __init__(self) -> None:
        self._tasks: set[asyncio.Task] = set()

    def spawn(self, coro: Coroutine[Any, Any, Any]) -> None:
        t = asyncio.create_task(coro)
        self._tasks.add(t)
        t.add_done_callback(self._on_done)

    def _on_done(self, t: asyncio.Task) -> None:
        self._tasks.discard(t)
        if not t.cancelled() and t.exception():
            logger.error("后台任务异常", exc_info=t.exception())

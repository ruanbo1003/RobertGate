"""文生图后台生成：从任务创建/重试触发，跑生图 + 落库。

由 T2ITaskService 的 create_task / retry_task 调用 spawn() 排队后立即返回，
生成结果异步写回 DB（成功/失败两条路径）。

后台任务脱离请求生命周期，不能复用请求的 session，因此注入 uow_factory
（异步上下文管理器）自开一个工作单元，用完即提交。
"""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from datetime import datetime, timezone

import httpx

from app.application.ports import AIClient
from app.domain.models.t2i import T2IImageBlob
from app.infrastructure.tasks import TaskRunner

logger = logging.getLogger(__name__)

FetchImage = Callable[[str], Awaitable[tuple[bytes, str]]]


async def fetch_image_bytes(url: str) -> tuple[bytes, str]:
    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        return resp.content, resp.headers.get("content-type", "image/png")


class T2IGenerator:
    def __init__(
        self,
        uow_factory,
        ai: AIClient,
        fetch_image: FetchImage,
        runner: TaskRunner,
    ) -> None:
        self._uow_factory = uow_factory
        self._ai = ai
        self._fetch_image = fetch_image
        self._runner = runner

    def spawn(self, task_id: str, image_id: str, prompt: str) -> None:
        self._runner.spawn(self._run(task_id, image_id, prompt))

    async def _run(self, task_id: str, image_id: str, prompt: str) -> None:
        try:
            url = await self._ai.generate_image(prompt)
        except Exception as e:  # noqa: BLE001
            logger.exception(
                "generate_image failed for task=%s img=%s: %s", task_id, image_id, e
            )
            await self._mark_failed(task_id, image_id)
            return

        try:
            payload, mime = await self._fetch_image(url)
        except Exception as e:  # noqa: BLE001
            logger.exception("download image bytes failed for task=%s: %s", task_id, e)
            await self._mark_failed(task_id, image_id)
            return

        async with self._uow_factory() as uow:
            img = await uow.t2i_images.find_by_id(image_id)
            if img is None:
                return
            img.status = "succeeded"
            img.mime = mime
            uow.t2i_blobs.add(T2IImageBlob(image_id=image_id, bytes_=payload))

            task = await uow.t2i_tasks.find_by_id(task_id)
            if task is not None:
                task.status = "succeeded"
                task.last_failed = False
                task.updated_at = datetime.now(timezone.utc)

            await uow.commit()

    async def _mark_failed(self, task_id: str, image_id: str) -> None:
        async with self._uow_factory() as uow:
            img = await uow.t2i_images.find_by_id(image_id)
            if img is None:
                return
            img.status = "failed"

            task = await uow.t2i_tasks.find_by_id(task_id)
            if task is not None:
                task.status = "failed"
                task.last_failed = True
                task.updated_at = datetime.now(timezone.utc)

            await uow.commit()

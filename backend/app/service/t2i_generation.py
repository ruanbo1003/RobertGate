"""文生图后台生成：从任务创建/重试触发，跑生图 + 落库。

由 T2ITaskService 的 create_task / retry_task 调用 spawn() 排队后立即返回，
生成结果异步写回 DB（成功/失败两条路径）。
"""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from datetime import datetime, timezone

import httpx

from app.core.tasks import TaskRunner
from app.models.t2i import T2IImageBlob
from app.repository.t2i_repo import T2IImageBlobRepo, T2IImageRepo, T2ITaskRepo
from app.service.ai_client import AIClient

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
        session_factory,
        ai: AIClient,
        fetch_image: FetchImage,
        runner: TaskRunner,
    ) -> None:
        self._session_factory = session_factory
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

        async with self._session_factory() as session:
            image_repo = T2IImageRepo(session)
            blob_repo = T2IImageBlobRepo(session)
            task_repo = T2ITaskRepo(session)

            img = await image_repo.find_by_id(image_id)
            if img is None:
                return
            img.status = "succeeded"
            img.mime = mime
            blob = T2IImageBlob(image_id=image_id, bytes_=payload)
            await blob_repo.save(blob)
            await image_repo.update(img)

            task = await task_repo.find_by_id(task_id)
            if task is not None:
                task.status = "succeeded"
                task.last_failed = False
                task.updated_at = datetime.now(timezone.utc)
                await task_repo.update(task)

    async def _mark_failed(self, task_id: str, image_id: str) -> None:
        async with self._session_factory() as session:
            image_repo = T2IImageRepo(session)
            task_repo = T2ITaskRepo(session)
            img = await image_repo.find_by_id(image_id)
            if img is None:
                return
            img.status = "failed"
            await image_repo.update(img)
            task = await task_repo.find_by_id(task_id)
            if task is not None:
                task.status = "failed"
                task.last_failed = True
                task.updated_at = datetime.now(timezone.utc)
                await task_repo.update(task)

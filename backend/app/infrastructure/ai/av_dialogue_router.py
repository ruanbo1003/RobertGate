"""对白镜生成路由：kie.ai 主 + OpenRouter seedance 兜底。

primary 抛任意 ServerException（上游失败/配额耗尽/超时）即视为不可用，
降级走 fallback；fallback 自身失败则异常直接冒泡（无第三级兜底）。
"""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable

from app.application.services.av_dialogue import snap_dialogue_duration
from app.domain.errors import ServerException

logger = logging.getLogger(__name__)

FallbackVideo = Callable[[bytes, str, int], Awaitable[bytes]]


class DialogueVideoRouter:
    def __init__(
        self,
        primary: object | None,
        fallback_video: FallbackVideo,
        primary_tag: str,
        fallback_tag: str,
        fallback_ladder: tuple[int, ...],
    ) -> None:
        self._primary = primary
        self._fallback_video = fallback_video
        self._primary_tag = primary_tag
        self._fallback_tag = fallback_tag
        self._fallback_ladder = fallback_ladder

    async def generate_dialogue_video(
        self, image: bytes, prompt: str, duration_seconds: int
    ) -> tuple[bytes, str]:
        if self._primary is not None:
            try:
                video = await self._primary.generate_dialogue_video(
                    image, prompt, duration_seconds
                )
                return video, self._primary_tag
            except ServerException as e:
                logger.warning(
                    "dialogue primary failed, falling back to %s: %s",
                    self._fallback_tag,
                    e.message,
                )
        snapped = snap_dialogue_duration(float(duration_seconds), self._fallback_ladder)
        video = await self._fallback_video(image, prompt, snapped)
        return video, self._fallback_tag

"""kie.ai ai-videos 主客户端（t2i / i2v / llm-json；tts 已退役）。

复用 KieVideoClient 的 jobs 骨架（上传 / createTask / 轮询 / 下载 / 错误映射，
见 av_client_kie.py 头注释的 kie 接口形态与错误约定）：
- 文生图  nano-banana 系：input {prompt, image_urls?, aspect_ratio 9:16}，
          多参考图 = 先逐张上传拿 downloadUrl 再按序进 image_urls（顺序即
          prompt 里点名的 reference image N）；图像任务 ~10s 出图，轮询间隔
          用更短的 image_poll_interval。
- 图生视频 seedance 系：input {prompt, image_urls(首帧), duration(字符串、
          snap 到注册表档位), aspect_ratio, resolution, generate_audio?}。
- LLM     OpenAI 兼容同步端点 {chat_base}/chat/completions（与 jobs 不同源），
          response_format=json_object（Task 5 实现）。
- TTS     generate_speech 保留签名（AvGenClient Protocol 要求）但直接抛错：
          链路已退役（对白镜音视同出替代，生成端入口全被拦，见
          specs/2026-11-13-kie-migration-design.md"TTS 不在范围内"）。
"""

from __future__ import annotations

import httpx

from app.domain.errors import ServerException, codes
from app.infrastructure.ai.av_client_kie import KieVideoClient
from app.infrastructure.data.av_models import snap_duration

_IMAGE_POLL_INTERVAL = 2.5


class KieAvClient(KieVideoClient):
    def __init__(
        self,
        api_key: str,
        base: str = "https://api.kie.ai/api/v1",
        upload_base: str = "https://kieai.redpandaai.co/api",
        chat_base: str = "https://api.kie.ai/v1",
        poll_interval: float = 10.0,
        image_poll_interval: float = _IMAGE_POLL_INTERVAL,
        poll_timeout: float = 900.0,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        super().__init__(
            api_key=api_key,
            model="",  # 本类不走对白镜，模型逐调用传入
            base=base,
            upload_base=upload_base,
            poll_interval=poll_interval,
            poll_timeout=poll_timeout,
            transport=transport,
        )
        self._chat_base = chat_base.rstrip("/")
        self._image_poll_interval = image_poll_interval

    # ---------------- t2i ----------------

    async def generate_image(
        self, prompt: str, model: str, reference_images: list[bytes] | None = None
    ) -> bytes:
        task_input: dict = {"prompt": prompt, "aspect_ratio": "9:16"}
        if reference_images:
            # 上传失败让异常冒泡（_upload_image 内已映射 ServerException）：
            # 静默丢参考图 = 角色跨镜变脸，宁可整个失败
            task_input["image_urls"] = [
                await self._upload_image(img) for img in reference_images
            ]
        task_id = await self._create_task_for(model, task_input, "文生图")
        url = await self._poll_result(task_id, self._image_poll_interval, "文生图")
        return await self._download(url)

    # ---------------- i2v ----------------

    async def generate_video(
        self,
        image: bytes,
        prompt: str,
        model: str,
        duration_seconds: int = 5,
        generate_audio: bool = False,
    ) -> bytes:
        image_url = await self._upload_image(image)
        task_input: dict = {
            "prompt": prompt,
            "image_urls": [image_url],
            "duration": str(snap_duration(model, duration_seconds)),
            "aspect_ratio": "9:16",
            "resolution": "720p",
        }
        if generate_audio:
            task_input["generate_audio"] = True
        task_id = await self._create_task_for(model, task_input, "图生视频")
        url = await self._poll_result(task_id, self._poll_interval, "图生视频")
        return await self._download(url)

    # ---------------- tts（已退役）----------------

    async def generate_speech(self, text: str, model: str, voice: str) -> bytes:
        raise ServerException(
            codes.AV_UPSTREAM_FAILED,
            "TTS 链路已退役：说话镜走音视同出（对白镜），无独立配音",
        )

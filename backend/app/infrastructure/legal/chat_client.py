"""法律咨询流式对话客户端（SiliconFlow / OpenAI 兼容）+ 无 Key Mock。"""

from __future__ import annotations

from collections.abc import AsyncIterator


class SiliconFlowLegalChat:
    def __init__(self, api_key: str, base_url: str, model: str) -> None:
        self._model = model

        from openai import AsyncOpenAI

        self._client = AsyncOpenAI(api_key=api_key, base_url=base_url)

    async def stream_chat(self, messages: list[dict[str, str]]) -> AsyncIterator[str]:
        stream = await self._client.chat.completions.create(
            model=self._model,
            messages=messages,  # type: ignore[arg-type]
            stream=True,
            temperature=0.3,
        )
        async for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content


class MockLegalChat:
    """无 API Key 时的兜底：返回固定提示文本，保持链路可跑通。"""

    async def stream_chat(self, messages: list[dict[str, str]]) -> AsyncIterator[str]:
        text = (
            "（Mock 模式）当前后端未配置 LLM_API_KEY，无法调用真实模型。"
            "系统提示词中的检索条文与对话历史均已就位，配置 Key 后即可获得真实解读。"
        )
        for i in range(0, len(text), 4):
            yield text[i : i + 4]

"""AI 客户端全局单例装配。

配置了 LLM_API_KEY 时使用 LLMClient（LangChain 接入任意 OpenAI 兼容模型：
智谱 BigModel / OpenRouter / DeepSeek / OpenAI 等），
否则回退到 MockAIClient，保证本地无 key 环境仍可运行。
"""

from __future__ import annotations

from app.application.ports import AIClient
from app.infrastructure.ai.mock_client import MockAIClient

_default_client: AIClient | None = None


def get_ai_client() -> AIClient:
    """FastAPI 依赖：返回全局 AI 客户端。"""
    global _default_client
    if _default_client is not None:
        return _default_client

    from app.config import get_settings

    settings = get_settings()
    if settings.LLM_API_KEY:
        # 延迟导入，避免未安装 langchain 时也能启动 mock 模式
        from app.infrastructure.ai.llm_client import LLMClient

        _default_client = LLMClient(
            api_key=settings.LLM_API_KEY,
            model=settings.LLM_MODEL,
            base_url=settings.LLM_BASE_URL,
            image_model=settings.T2I_MODEL,
            image_size=settings.T2I_SIZE,
        )
    else:
        _default_client = MockAIClient()
    return _default_client


def set_ai_client(client: AIClient) -> None:
    """测试或联调时替换全局 AI 客户端。"""
    global _default_client
    _default_client = client

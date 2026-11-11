"""invest-reports Agent 装配：配置了 OPENROUTER_API_KEY 用 Pydantic AI 实现，否则 Mock。"""

from __future__ import annotations

from app.infrastructure.ai.ir_agent_mock import MockIrAgent

_ir_agent = None


def _load_settings():
    """间接层：测试可 monkeypatch。"""
    from app.config import get_settings

    return get_settings()


def get_ir_agent():
    global _ir_agent
    if _ir_agent is not None:
        return _ir_agent
    settings = _load_settings()
    if settings.OPENROUTER_API_KEY:
        # 延迟 import：真实实现依赖 pydantic-ai（Task 8 落地）
        from app.infrastructure.ai.ir_agent_pydantic import PydanticIrAgent

        _ir_agent = PydanticIrAgent(
            api_key=settings.OPENROUTER_API_KEY,
            base_url=settings.OPENROUTER_BASE_URL,
            model=settings.IR_LLM_MODEL,
            search_model=settings.IR_SEARCH_MODEL,
        )
    else:
        _ir_agent = MockIrAgent()
    return _ir_agent


def set_ir_agent(agent) -> None:
    """测试/联调替换；传 None 重置单例。"""
    global _ir_agent
    _ir_agent = agent

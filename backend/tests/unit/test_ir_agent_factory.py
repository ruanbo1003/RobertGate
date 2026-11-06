"""ir agent 工厂单测：无 Key 回落 Mock、单例可替换重置。"""

from __future__ import annotations

import app.infrastructure.ai.ir_agent_factory as factory_module
from app.infrastructure.ai.ir_agent_factory import get_ir_agent, set_ir_agent
from app.infrastructure.ai.ir_agent_mock import MockIrAgent


def _patch_settings(monkeypatch, key: str):
    class _S:
        OPENROUTER_API_KEY = key
        OPENROUTER_BASE_URL = "https://openrouter.test/api/v1"
        IR_LLM_MODEL = "google/gemini-3.8-flash"
        IR_SEARCH_MODEL = "google/gemini-3.8-flash:online"

    monkeypatch.setattr(factory_module, "_load_settings", lambda: _S())


def test_factory_returns_mock_without_key(monkeypatch):
    set_ir_agent(None)
    _patch_settings(monkeypatch, "")
    assert isinstance(get_ir_agent(), MockIrAgent)
    set_ir_agent(None)


def test_set_ir_agent_overrides_singleton():
    sentinel = object()
    set_ir_agent(sentinel)
    assert get_ir_agent() is sentinel
    set_ir_agent(None)

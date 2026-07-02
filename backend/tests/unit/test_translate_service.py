from unittest.mock import AsyncMock

import pytest

from app.core.exceptions import ServerException
from app.service.translate_service import TranslateService


@pytest.fixture
def ai():
    return AsyncMock()


@pytest.fixture
def service(ai):
    return TranslateService(ai=ai)


@pytest.mark.asyncio
async def test_translate_action(service, ai):
    ai.translate.return_value = ("zh", "en", "Hello")

    result = await service.process("你好", "translate")

    assert result["action"] == "translate"
    assert result["source_lang"] == "zh"
    assert result["target_lang"] == "en"
    assert result["result"] == "Hello"
    ai.translate.assert_awaited_once_with("你好")


@pytest.mark.asyncio
async def test_grammar_action(service, ai):
    ai.grammar_correct.return_value = "I am fine."

    result = await service.process("i am fine", "grammar")

    assert result["source_lang"] == "en"
    assert result["target_lang"] == "en"
    assert result["result"] == "I am fine."


@pytest.mark.asyncio
async def test_native_action(service, ai):
    ai.rewrite_native.return_value = "How's it going?"

    result = await service.process("How are you doing today", "native")

    assert result["result"] == "How's it going?"


@pytest.mark.asyncio
async def test_ai_failure_wraps_to_server_exception(service, ai):
    ai.translate.side_effect = RuntimeError("upstream down")

    with pytest.raises(ServerException) as exc_info:
        await service.process("hello", "translate")
    assert exc_info.value.code == 5001

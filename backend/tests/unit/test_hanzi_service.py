from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest

from app.core.exceptions import ParamException, ServerException
from app.models.hanzi_entry import HanziEntry
from app.service.hanzi_service import HanziService, _extract_chinese_chars


@pytest.fixture
def repo():
    return AsyncMock()


@pytest.fixture
def ai():
    return AsyncMock()


@pytest.fixture
def service(repo, ai):
    return HanziService(repo=repo, ai=ai)


def _make_entry(char: str, learned: bool = False) -> HanziEntry:
    return HanziEntry(
        id=f"id-{char}",
        user_id="u1",
        char=char,
        learned=learned,
        created_at=datetime.now(timezone.utc),
        learned_at=datetime.now(timezone.utc) if learned else None,
    )


# --------- 提取汉字 ---------


def test_extract_dedupes_and_preserves_order():
    result = _extract_chinese_chars("Hello 汉字 World 中华 汉字!")
    assert result == ["汉", "字", "中", "华"]


def test_extract_ignores_non_chinese():
    assert _extract_chinese_chars("abc123!@#") == []


# --------- 字库 ---------


@pytest.mark.asyncio
async def test_list_library(service, repo):
    repo.list_by_user.return_value = [
        _make_entry("汉", learned=True),
        _make_entry("字", learned=False),
    ]
    result = await service.list_library("u1")
    assert result["total"] == 2
    assert result["learned"] == 1
    assert len(result["items"]) == 2
    assert result["items"][0]["char"] == "汉"
    assert result["items"][0]["learned"] is True


@pytest.mark.asyncio
async def test_add_from_text_dedupes_and_records_duplicates(service, repo):
    repo.existing_chars.return_value = {"汉"}
    repo.list_by_user.return_value = [_make_entry("汉"), _make_entry("字")]

    result = await service.add_from_text("u1", "汉字 汉字")

    assert result["added"] == ["字"]
    assert result["duplicated"] == ["汉"]
    assert result["total"] == 2
    repo.add_many.assert_awaited_once()


@pytest.mark.asyncio
async def test_add_from_text_no_valid_chars(service):
    with pytest.raises(ParamException) as exc_info:
        await service.add_from_text("u1", "abc123")
    assert exc_info.value.code == 2004


@pytest.mark.asyncio
async def test_add_from_text_all_duplicated(service, repo):
    repo.existing_chars.return_value = {"汉", "字"}
    repo.list_by_user.return_value = [_make_entry("汉"), _make_entry("字")]

    result = await service.add_from_text("u1", "汉字")

    assert result["added"] == []
    assert result["duplicated"] == ["汉", "字"]
    repo.add_many.assert_not_awaited()


@pytest.mark.asyncio
async def test_update_learned_success(service, repo):
    entry = _make_entry("汉", learned=False)
    repo.find.return_value = entry

    result = await service.update_learned("u1", "汉", True)

    assert result["learned"] is True
    assert result["learned_at"] != ""
    assert entry.learned is True


@pytest.mark.asyncio
async def test_update_learned_not_in_library(service, repo):
    repo.find.return_value = None
    with pytest.raises(ParamException) as exc_info:
        await service.update_learned("u1", "汉", True)
    assert exc_info.value.code == 2005


@pytest.mark.asyncio
async def test_update_learned_unmark(service, repo):
    entry = _make_entry("汉", learned=True)
    repo.find.return_value = entry

    result = await service.update_learned("u1", "汉", False)

    assert result["learned"] is False
    assert result["learned_at"] == ""


@pytest.mark.asyncio
async def test_delete_success(service, repo):
    entry = _make_entry("汉")
    repo.find.return_value = entry
    repo.list_by_user.return_value = []

    result = await service.delete("u1", "汉")

    assert result["char"] == "汉"
    assert result["total"] == 0
    repo.delete.assert_awaited_once_with(entry)


@pytest.mark.asyncio
async def test_delete_not_in_library(service, repo):
    repo.find.return_value = None
    with pytest.raises(ParamException) as exc_info:
        await service.delete("u1", "汉")
    assert exc_info.value.code == 2005


# --------- AI 内容 ---------


@pytest.mark.asyncio
async def test_character_info_success(service, ai):
    ai.character_info.return_value = {
        "pinyin": "hàn",
        "words": ["汉字"],
        "sentence": "汉字很美。",
        "sentence_pinyin": "hàn zì hěn měi",
    }

    result = await service.character_info("汉")

    assert result["char"] == "汉"
    assert result["pinyin"] == "hàn"
    assert result["words"] == ["汉字"]


@pytest.mark.asyncio
async def test_character_info_ai_failure(service, ai):
    ai.character_info.side_effect = RuntimeError("model down")
    with pytest.raises(ServerException) as exc_info:
        await service.character_info("汉")
    assert exc_info.value.code == 5001


@pytest.mark.asyncio
async def test_compose_sentence_computes_out_of_vocab(service, ai):
    ai.compose_sentence.return_value = {
        "sentence": "汉字是中华瑰宝。",
        "pinyin": "hàn zì shì zhōng huá guī bǎo",
        "translation": "Chinese characters are treasures.",
    }

    result = await service.compose_sentence(["汉", "字", "是", "中", "华"])

    # 瑰、宝 不在已学，应作为库外字返回
    assert set(result["out_of_vocab"]) == {"瑰", "宝"}
    assert result["sentence"] == "汉字是中华瑰宝。"


@pytest.mark.asyncio
async def test_compose_sentence_ai_failure(service, ai):
    ai.compose_sentence.side_effect = RuntimeError("model down")
    with pytest.raises(ServerException) as exc_info:
        await service.compose_sentence(["汉", "字", "是", "中", "华"])
    assert exc_info.value.code == 5001

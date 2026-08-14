from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest

from app.application.services.admin_hanzi_service import AdminHanziService, _extract_chars
from app.domain.errors import ParamException
from app.domain.models.hanzi import HanziCharacter, HanziLevel


@pytest.fixture
def level_repo():
    return AsyncMock()


@pytest.fixture
def character_repo():
    return AsyncMock()


@pytest.fixture
def ai():
    return AsyncMock()


@pytest.fixture
def service(level_repo, character_repo, ai):
    return AdminHanziService(
        level_repo=level_repo, character_repo=character_repo, ai=ai
    )


def _level(id_: str = "l1", name: str = "L1") -> HanziLevel:
    now = datetime.now(timezone.utc)
    return HanziLevel(
        id=id_, name=name, description=None, order_index=0,
        created_at=now, updated_at=now,
    )


def _character(id_: str, char: str, level_id: str = "l1") -> HanziCharacter:
    now = datetime.now(timezone.utc)
    return HanziCharacter(
        id=id_, level_id=level_id, char=char, pinyin="p",
        example_words=[], order_index=0, created_at=now, updated_at=now,
    )


# ---------- Extract ----------


def test_extract_chars_dedup_ordered():
    assert _extract_chars("你好世界，Hello 好！") == ["你", "好", "世", "界"]


def test_extract_chars_empty():
    assert _extract_chars("no chinese here 123") == []


# ---------- Levels ----------


@pytest.mark.asyncio
async def test_create_level_success(service, level_repo):
    level_repo.find_by_name.return_value = None
    result = await service.create_level("New Level", "desc", 3)
    assert result["name"] == "New Level"
    assert result["total"] == 0
    level_repo.save.assert_awaited_once()


@pytest.mark.asyncio
async def test_create_level_duplicate_name(service, level_repo):
    level_repo.find_by_name.return_value = _level(name="dup")
    with pytest.raises(ParamException) as exc:
        await service.create_level("dup", None, 0)
    assert exc.value.code == 2011


@pytest.mark.asyncio
async def test_update_level_not_found(service, level_repo):
    level_repo.find_by_id.return_value = None
    with pytest.raises(ParamException) as exc:
        await service.update_level("nope", "n", None, False, None)
    assert exc.value.code == 2010


@pytest.mark.asyncio
async def test_update_level_name_conflict(service, level_repo):
    level_repo.find_by_id.return_value = _level("l1", "old")
    level_repo.find_by_name.return_value = _level("l2", "taken")
    with pytest.raises(ParamException) as exc:
        await service.update_level("l1", "taken", None, False, None)
    assert exc.value.code == 2011


@pytest.mark.asyncio
async def test_update_level_success_partial(service, level_repo, character_repo):
    level = _level("l1", "old")
    level_repo.find_by_id.return_value = level
    level_repo.find_by_name.return_value = None
    character_repo.count_by_level.return_value = 5

    result = await service.update_level(
        "l1", name="new", description=None, description_set=False, order_index=7
    )

    assert result["name"] == "new"
    assert result["order_index"] == 7
    assert result["total"] == 5


@pytest.mark.asyncio
async def test_delete_level_not_found(service, level_repo):
    level_repo.find_by_id.return_value = None
    with pytest.raises(ParamException) as exc:
        await service.delete_level("x")
    assert exc.value.code == 2010


@pytest.mark.asyncio
async def test_delete_level_non_empty(service, level_repo, character_repo):
    level_repo.find_by_id.return_value = _level()
    character_repo.count_by_level.return_value = 3
    with pytest.raises(ParamException) as exc:
        await service.delete_level("l1")
    assert exc.value.code == 2012


@pytest.mark.asyncio
async def test_delete_level_success(service, level_repo, character_repo):
    level = _level()
    level_repo.find_by_id.return_value = level
    character_repo.count_by_level.return_value = 0
    await service.delete_level("l1")
    level_repo.delete.assert_awaited_once_with(level)


# ---------- Characters ----------


@pytest.mark.asyncio
async def test_create_character_success(service, level_repo, character_repo):
    level_repo.find_by_id.return_value = _level()
    character_repo.find_by_char.return_value = None
    character_repo.max_order_index.return_value = 4

    result = await service.create_character("l1", "人", "rén", ["人口"], None)

    assert result["char"] == "人"
    assert result["order_index"] == 5
    assert result["example_words"] == ["人口"]
    character_repo.save.assert_awaited_once()


@pytest.mark.asyncio
async def test_create_character_level_not_found(service, level_repo):
    level_repo.find_by_id.return_value = None
    with pytest.raises(ParamException) as exc:
        await service.create_character("nope", "人", "rén", None, None)
    assert exc.value.code == 2010


@pytest.mark.asyncio
async def test_create_character_global_conflict(
    service, level_repo, character_repo
):
    level_repo.find_by_id.return_value = _level()
    character_repo.find_by_char.return_value = _character("c-other", "人", "l2")
    with pytest.raises(ParamException) as exc:
        await service.create_character("l1", "人", "rén", None, None)
    assert exc.value.code == 2011


# ---------- AI Add ----------


@pytest.mark.asyncio
async def test_ai_add_no_hanzi(service, level_repo):
    level_repo.find_by_id.return_value = _level()
    result = await service.ai_add("l1", "hello 123")
    assert result == {"ok": 0, "added": [], "skipped": [], "failed": []}


@pytest.mark.asyncio
async def test_ai_add_mixed(service, level_repo, character_repo, ai):
    level_repo.find_by_id.return_value = _level()
    character_repo.existing_chars.return_value = {"好"}
    character_repo.max_order_index.return_value = -1

    async def fake_info(char: str) -> dict:
        if char == "世":
            raise RuntimeError("upstream down")
        return {
            "pinyin": {"你": "nǐ", "界": "jiè"}[char],
            "words": [char + "a", char + "b", char + "c", char + "d"],
            "sentence": "",
            "sentence_pinyin": "",
        }

    ai.character_info.side_effect = fake_info

    result = await service.ai_add("l1", "你好世界")

    assert result["ok"] == 2
    added_chars = {a["char"] for a in result["added"]}
    assert added_chars == {"你", "界"}
    assert result["skipped"] == [{"char": "好", "reason": "已存在"}]
    assert len(result["failed"]) == 1
    assert result["failed"][0]["char"] == "世"
    # order index continues from max+1
    orders = sorted(a["order_index"] for a in result["added"])
    assert orders == [0, 1]
    character_repo.save_many.assert_awaited_once()


@pytest.mark.asyncio
async def test_ai_add_bad_ai_response(service, level_repo, character_repo, ai):
    level_repo.find_by_id.return_value = _level()
    character_repo.existing_chars.return_value = set()
    character_repo.max_order_index.return_value = -1
    ai.character_info.return_value = {"pinyin": "", "words": []}

    result = await service.ai_add("l1", "字")

    assert result["ok"] == 0
    assert result["failed"][0]["char"] == "字"
    assert "格式" in result["failed"][0]["reason"]


@pytest.mark.asyncio
async def test_update_character_char_conflict(service, character_repo):
    character_repo.find_by_id.return_value = _character("c1", "人")
    character_repo.find_by_char.return_value = _character("c2", "口")
    with pytest.raises(ParamException) as exc:
        await service.update_character(
            "c1", char="口", pinyin=None, example_words=None,
            example_words_set=False, order_index=None,
        )
    assert exc.value.code == 2011


@pytest.mark.asyncio
async def test_update_character_success(service, character_repo):
    original = _character("c1", "人")
    character_repo.find_by_id.return_value = original
    character_repo.find_by_char.return_value = None

    result = await service.update_character(
        "c1", char="口", pinyin="kǒu", example_words=["口水", "开口"],
        example_words_set=True, order_index=3,
    )

    assert result["pinyin"] == "kǒu"
    assert result["example_words"] == ["口水", "开口"]
    assert result["order_index"] == 3


@pytest.mark.asyncio
async def test_update_character_words_cleared_when_set(service, character_repo):
    original = _character("c1", "人")
    original.example_words = ["a", "b"]
    character_repo.find_by_id.return_value = original

    result = await service.update_character(
        "c1", char=None, pinyin=None, example_words=None,
        example_words_set=True, order_index=None,
    )
    assert result["example_words"] == []


@pytest.mark.asyncio
async def test_delete_character_success(service, character_repo):
    c = _character("c1", "人")
    character_repo.find_by_id.return_value = c
    await service.delete_character("c1")
    character_repo.delete.assert_awaited_once_with(c)


@pytest.mark.asyncio
async def test_delete_character_not_found(service, character_repo):
    character_repo.find_by_id.return_value = None
    with pytest.raises(ParamException) as exc:
        await service.delete_character("x")
    assert exc.value.code == 2010

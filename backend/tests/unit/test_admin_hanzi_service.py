from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest

from app.core.exceptions import ParamException
from app.models.hanzi_character import HanziCharacter
from app.models.hanzi_level import HanziLevel
from app.service.admin_hanzi_service import AdminHanziService


@pytest.fixture
def level_repo():
    return AsyncMock()


@pytest.fixture
def character_repo():
    return AsyncMock()


@pytest.fixture
def service(level_repo, character_repo):
    return AdminHanziService(level_repo=level_repo, character_repo=character_repo)


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
        meaning=None, order_index=0, created_at=now, updated_at=now,
    )


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

    result = await service.create_character("l1", "人", "rén", "人类", None)

    assert result["char"] == "人"
    assert result["order_index"] == 5
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


@pytest.mark.asyncio
async def test_batch_import_mixed_results(service, level_repo, character_repo):
    level_repo.find_by_id.return_value = _level()
    character_repo.existing_chars.return_value = {"口"}
    character_repo.max_order_index.return_value = -1

    result = await service.batch_import(
        "l1",
        items=[
            {"char": "人", "pinyin": "rén", "meaning": None},
            {"char": "口", "pinyin": "kǒu", "meaning": None},  # conflict
            {"char": "A", "pinyin": "a", "meaning": None},  # invalid
            {"char": "人", "pinyin": "rén", "meaning": None},  # dup in batch
            {"char": "山", "pinyin": "", "meaning": None},  # empty pinyin
        ],
    )

    assert result["ok"] == 1
    reasons = [f["reason"] for f in result["failed"]]
    assert any("单个汉字" in r for r in reasons)
    assert any("批次内重复" in r for r in reasons)
    assert any("已存在" in r for r in reasons)
    assert any("pinyin" in r for r in reasons)


@pytest.mark.asyncio
async def test_batch_import_all_valid_allocates_order(
    service, level_repo, character_repo
):
    level_repo.find_by_id.return_value = _level()
    character_repo.existing_chars.return_value = set()
    character_repo.max_order_index.return_value = 9

    result = await service.batch_import(
        "l1",
        items=[
            {"char": "山", "pinyin": "shān", "meaning": None},
            {"char": "水", "pinyin": "shuǐ", "meaning": None},
        ],
    )

    assert result["ok"] == 2
    # save_many should have been called once
    character_repo.save_many.assert_awaited_once()
    saved = character_repo.save_many.await_args.args[0]
    assert [c.order_index for c in saved] == [10, 11]


@pytest.mark.asyncio
async def test_update_character_char_conflict(service, character_repo):
    character_repo.find_by_id.return_value = _character("c1", "人")
    character_repo.find_by_char.return_value = _character("c2", "口")
    with pytest.raises(ParamException) as exc:
        await service.update_character(
            "c1", char="口", pinyin=None, meaning=None,
            meaning_set=False, order_index=None,
        )
    assert exc.value.code == 2011


@pytest.mark.asyncio
async def test_update_character_success(service, character_repo):
    original = _character("c1", "人")
    character_repo.find_by_id.return_value = original
    character_repo.find_by_char.return_value = None

    result = await service.update_character(
        "c1", char="人口", pinyin="rén kǒu", meaning="new",
        meaning_set=True, order_index=3,
    )

    # actually char must be single hanzi — schema handles that; here we bypass to
    # test service logic: it stores whatever the schema passes through.
    assert result["pinyin"] == "rén kǒu"
    assert result["meaning"] == "new"
    assert result["order_index"] == 3


@pytest.mark.asyncio
async def test_update_character_meaning_cleared_when_set(service, character_repo):
    original = _character("c1", "人")
    original.meaning = "old"
    character_repo.find_by_id.return_value = original

    result = await service.update_character(
        "c1", char=None, pinyin=None, meaning=None,
        meaning_set=True, order_index=None,
    )
    assert result["meaning"] is None


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

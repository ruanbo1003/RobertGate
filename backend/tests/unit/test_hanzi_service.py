from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest

from app.application.services.hanzi_service import HanziService
from app.domain.errors import ParamException
from app.domain.models.hanzi import HanziCharacter, HanziLevel, HanziUserProgress


@pytest.fixture
def level_repo(uow):
    return uow.hanzi_levels


@pytest.fixture
def character_repo(uow):
    return uow.hanzi_characters


@pytest.fixture
def progress_repo(uow):
    return uow.hanzi_progress


@pytest.fixture
def ai():
    return AsyncMock()


@pytest.fixture
def service(uow, ai):
    return HanziService(uow=uow, ai=ai)


def _level(id_: str, name: str, order: int = 0) -> HanziLevel:
    now = datetime.now(timezone.utc)
    return HanziLevel(
        id=id_,
        name=name,
        description=None,
        order_index=order,
        created_at=now,
        updated_at=now,
    )


def _character(id_: str, level_id: str, char: str, order: int = 0) -> HanziCharacter:
    now = datetime.now(timezone.utc)
    return HanziCharacter(
        id=id_,
        level_id=level_id,
        char=char,
        pinyin="p",
        example_words=[],
        order_index=order,
        created_at=now,
        updated_at=now,
    )


# ---------- list_levels_with_progress ----------


@pytest.mark.asyncio
async def test_list_levels_returns_totals_and_learned(
    service, level_repo, character_repo, progress_repo
):
    level_repo.list_all.return_value = [_level("l1", "L1", 1), _level("l2", "L2", 2)]
    character_repo.count_by_levels.return_value = {"l1": 20, "l2": 15}
    progress_repo.learned_count_by_levels.return_value = {"l1": 8}

    result = await service.list_levels_with_progress("u1")

    assert len(result["levels"]) == 2
    assert result["levels"][0].total == 20
    assert result["levels"][0].learned == 8
    assert result["levels"][1].total == 15
    assert result["levels"][1].learned == 0  # missing in map defaults to 0


@pytest.mark.asyncio
async def test_list_levels_empty(service, level_repo, character_repo, progress_repo):
    level_repo.list_all.return_value = []
    character_repo.count_by_levels.return_value = {}
    progress_repo.learned_count_by_levels.return_value = {}

    result = await service.list_levels_with_progress("u1")
    assert result["levels"] == []


# ---------- list_characters_for_user ----------


@pytest.mark.asyncio
async def test_list_characters_marks_learned_state(
    service, level_repo, character_repo, progress_repo
):
    now = datetime.now(timezone.utc)
    level_repo.find_by_id.return_value = _level("l1", "L1")
    character_repo.list_by_level.return_value = [
        _character("c1", "l1", "人", 0),
        _character("c2", "l1", "口", 1),
    ]
    progress_repo.progress_map_by_level.return_value = {
        "c1": HanziUserProgress(
            id="p1", user_id="u1", character_id="c1", learned_at=now
        )
    }

    result = await service.list_characters_for_user("u1", "l1")

    assert result["level"].id == "l1"
    assert len(result["characters"]) == 2
    assert result["characters"][0].learned is True
    assert result["characters"][0].learned_at is not None
    assert result["characters"][1].learned is False
    assert result["characters"][1].learned_at is None


@pytest.mark.asyncio
async def test_list_characters_level_not_found(service, level_repo):
    level_repo.find_by_id.return_value = None
    with pytest.raises(ParamException) as exc:
        await service.list_characters_for_user("u1", "nope")
    assert exc.value.code == 2010


# ---------- update_progress ----------


@pytest.mark.asyncio
async def test_update_progress_mark_learned_new(
    service, uow, character_repo, progress_repo
):
    character_repo.find_by_id.return_value = _character("c1", "l1", "人")
    progress_repo.find.return_value = None

    result = await service.update_progress("u1", "c1", True)

    assert result.learned is True
    assert result.learned_at is not None
    progress_repo.add.assert_called_once()
    assert uow.commit.await_count == 1


@pytest.mark.asyncio
async def test_update_progress_mark_learned_idempotent(
    service, uow, character_repo, progress_repo
):
    now = datetime.now(timezone.utc)
    character_repo.find_by_id.return_value = _character("c1", "l1", "人")
    progress_repo.find.return_value = HanziUserProgress(
        id="p1", user_id="u1", character_id="c1", learned_at=now
    )

    result = await service.update_progress("u1", "c1", True)

    assert result.learned is True
    progress_repo.add.assert_not_called()
    # 只读分支不开事务
    uow.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_update_progress_unmark_deletes(
    service, uow, character_repo, progress_repo
):
    now = datetime.now(timezone.utc)
    character_repo.find_by_id.return_value = _character("c1", "l1", "人")
    existing = HanziUserProgress(
        id="p1", user_id="u1", character_id="c1", learned_at=now
    )
    progress_repo.find.return_value = existing

    result = await service.update_progress("u1", "c1", False)

    assert result.learned is False
    assert result.learned_at is None
    progress_repo.delete.assert_awaited_once_with(existing)
    assert uow.commit.await_count == 1


@pytest.mark.asyncio
async def test_update_progress_unmark_idempotent(
    service, uow, character_repo, progress_repo
):
    character_repo.find_by_id.return_value = _character("c1", "l1", "人")
    progress_repo.find.return_value = None

    result = await service.update_progress("u1", "c1", False)

    assert result.learned is False
    progress_repo.delete.assert_not_awaited()
    uow.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_update_progress_character_not_found(service, character_repo):
    character_repo.find_by_id.return_value = None
    with pytest.raises(ParamException) as exc:
        await service.update_progress("u1", "nope", True)
    assert exc.value.code == 2010

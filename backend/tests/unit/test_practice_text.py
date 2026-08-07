from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest

from app.core.exceptions import ParamException
from app.models.hanzi_character import HanziCharacter
from app.models.hanzi_level import HanziLevel
from app.models.hanzi_progress import HanziUserProgress
from app.service.hanzi_service import HanziService


@pytest.fixture
def level_repo():
    return AsyncMock()


@pytest.fixture
def character_repo():
    return AsyncMock()


@pytest.fixture
def progress_repo():
    return AsyncMock()


@pytest.fixture
def ai():
    return AsyncMock()


@pytest.fixture
def service(level_repo, character_repo, progress_repo, ai):
    return HanziService(
        level_repo=level_repo,
        character_repo=character_repo,
        progress_repo=progress_repo,
        ai=ai,
    )


def _lvl(id_: str = "l1") -> HanziLevel:
    now = datetime.now(timezone.utc)
    return HanziLevel(
        id=id_, name="L1", description=None, order_index=0,
        created_at=now, updated_at=now,
    )


def _char(id_: str, ch: str, level_id: str = "l1") -> HanziCharacter:
    now = datetime.now(timezone.utc)
    return HanziCharacter(
        id=id_, level_id=level_id, char=ch, pinyin="p",
        example_words=[], order_index=0, created_at=now, updated_at=now,
    )


def _progress(char_id: str) -> HanziUserProgress:
    return HanziUserProgress(
        id=f"p-{char_id}", user_id="u1", character_id=char_id,
        learned_at=datetime.now(timezone.utc),
    )


@pytest.mark.asyncio
async def test_generate_practice_text_level_not_found(service, level_repo):
    level_repo.find_by_id.return_value = None
    with pytest.raises(ParamException) as exc:
        await service.generate_practice_text("u1", "nope")
    assert exc.value.code == 2010


@pytest.mark.asyncio
async def test_generate_practice_text_too_few_learned(
    service, level_repo, character_repo, progress_repo
):
    level_repo.find_by_id.return_value = _lvl()
    character_repo.list_by_level.return_value = [
        _char("c1", "人"), _char("c2", "口"), _char("c3", "山"),
    ]
    progress_repo.progress_map_by_level.return_value = {
        "c1": _progress("c1"), "c2": _progress("c2"),
    }
    with pytest.raises(ParamException) as exc:
        await service.generate_practice_text("u1", "l1")
    assert exc.value.code == 2013


@pytest.mark.asyncio
async def test_generate_practice_text_success(
    service, level_repo, character_repo, progress_repo, ai
):
    level_repo.find_by_id.return_value = _lvl()
    character_repo.list_by_level.return_value = [
        _char("c1", "人"), _char("c2", "口"), _char("c3", "山"), _char("c4", "水"),
    ]
    progress_repo.progress_map_by_level.return_value = {
        "c1": _progress("c1"), "c2": _progress("c2"), "c3": _progress("c3"),
    }
    ai.practice_text.return_value = {
        "text": "人在山口。",
        "annotations": [
            {"char": "人", "pinyin": "rén"},
            {"char": "在", "pinyin": "zài"},
            {"char": "山", "pinyin": "shān"},
            {"char": "口", "pinyin": "kǒu"},
        ],
        "new_chars": ["在"],
    }

    result = await service.generate_practice_text("u1", "l1")

    ai.practice_text.assert_awaited_once()
    call_args = ai.practice_text.call_args
    assert set(call_args.args[0]) == {"人", "口", "山"}
    assert result["text"] == "人在山口。"
    assert result["new_chars"] == ["在"]
    assert len(result["annotations"]) == 4


@pytest.mark.asyncio
async def test_generate_practice_text_ai_missing_annotations(
    service, level_repo, character_repo, progress_repo, ai
):
    level_repo.find_by_id.return_value = _lvl()
    character_repo.list_by_level.return_value = [
        _char("c1", "人"), _char("c2", "口"), _char("c3", "山"),
    ]
    progress_repo.progress_map_by_level.return_value = {
        "c1": _progress("c1"), "c2": _progress("c2"), "c3": _progress("c3"),
    }
    ai.practice_text.return_value = {"text": "人口山。"}

    result = await service.generate_practice_text("u1", "l1")

    assert result["text"] == "人口山。"
    assert result["annotations"] == []
    assert result["new_chars"] == []


@pytest.mark.asyncio
async def test_generate_practice_text_empty_text_fails(
    service, level_repo, character_repo, progress_repo, ai
):
    level_repo.find_by_id.return_value = _lvl()
    character_repo.list_by_level.return_value = [
        _char("c1", "人"), _char("c2", "口"), _char("c3", "山"),
    ]
    progress_repo.progress_map_by_level.return_value = {
        "c1": _progress("c1"), "c2": _progress("c2"), "c3": _progress("c3"),
    }
    ai.practice_text.return_value = {"text": "  ", "annotations": [], "new_chars": []}

    with pytest.raises(ParamException) as exc:
        await service.generate_practice_text("u1", "l1")
    assert exc.value.code == 5000


@pytest.mark.asyncio
async def test_generate_practice_text_ai_raises(
    service, level_repo, character_repo, progress_repo, ai
):
    level_repo.find_by_id.return_value = _lvl()
    character_repo.list_by_level.return_value = [
        _char("c1", "人"), _char("c2", "口"), _char("c3", "山"),
    ]
    progress_repo.progress_map_by_level.return_value = {
        "c1": _progress("c1"), "c2": _progress("c2"), "c3": _progress("c3"),
    }
    ai.practice_text.side_effect = RuntimeError("upstream")

    with pytest.raises(ParamException) as exc:
        await service.generate_practice_text("u1", "l1")
    assert exc.value.code == 5000

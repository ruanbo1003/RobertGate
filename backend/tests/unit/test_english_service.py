import pytest

from app.application.services.english_service import EnglishService
from app.domain.errors import ParamException
from app.infrastructure.data.english_data import ENGLISH_THEMES


@pytest.fixture
def service():
    return EnglishService(themes=ENGLISH_THEMES)


def test_list_themes_contains_all_seed_themes(service):
    result = service.list_themes()
    ids = {t["id"] for t in result["themes"]}
    assert {"colors", "animals", "shapes", "fruits"} <= ids


def test_generate_quiz_returns_expected_shape(service):
    result = service.generate_quiz("colors", count=10)
    assert result["theme_id"] == "colors"
    assert len(result["questions"]) == 10
    for q in result["questions"]:
        assert q["word"]
        assert q["translation"]
        assert len(q["options"]) == 4
        assert 0 <= q["correct_index"] < 4
        assert q["options"][q["correct_index"]]


def test_generate_quiz_correct_option_matches_target(service):
    result = service.generate_quiz("animals", count=5)
    for q in result["questions"]:
        # 正确选项 URL 一定与主题的 word 对应
        target_url = q["options"][q["correct_index"]]
        assert q["word"] in target_url


def test_generate_quiz_unknown_theme(service):
    with pytest.raises(ParamException) as exc_info:
        service.generate_quiz("nonexistent")
    assert exc_info.value.code == 2008


def test_generate_quiz_not_ready_theme(service):
    with pytest.raises(ParamException) as exc_info:
        service.generate_quiz("fruits")  # ready=False
    assert exc_info.value.code == 2009

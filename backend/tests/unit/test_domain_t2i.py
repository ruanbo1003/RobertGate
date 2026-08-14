"""文生图领域模型测试：状态机、工厂、校验错误码、prompt 渲染。"""

import json

import pytest

from app.domain.errors import ParamException
from app.domain.models.t2i import (
    ITEM_PLACEHOLDER,
    T2IImage,
    T2ITask,
    T2ITemplate,
    TaskStatus,
    business_status,
    normalize_keywords,
)


# ---------- normalize_keywords ----------


def test_normalize_keywords_trims():
    assert normalize_keywords({"item": "  Apple "}) == {"item": "Apple"}


def test_normalize_keywords_missing():
    with pytest.raises(ParamException) as exc:
        normalize_keywords({})
    assert exc.value.code == 2022
    assert exc.value.message == "item 不能为空"


def test_normalize_keywords_empty_string():
    with pytest.raises(ParamException) as exc:
        normalize_keywords({"item": "   "})
    assert exc.value.code == 2022


def test_normalize_keywords_non_string():
    with pytest.raises(ParamException) as exc:
        normalize_keywords({"item": 123})
    assert exc.value.code == 2022
    assert exc.value.message == "item 必须是字符串"


def test_normalize_keywords_too_long():
    with pytest.raises(ParamException) as exc:
        normalize_keywords({"item": "x" * 101})
    assert exc.value.code == 2022
    assert exc.value.message == "item 超长（最大 100 字符）"


# ---------- compute_hash ----------


def test_compute_hash_deterministic():
    assert T2ITask.compute_hash("english-primer", {"item": "apple"}) == (
        T2ITask.compute_hash("english-primer", {"item": "apple"})
    )


def test_compute_hash_template_scoped():
    a = T2ITask.compute_hash("english-primer", {"item": "apple"})
    b = T2ITask.compute_hash("general", {"item": "apple"})
    assert a != b


# ---------- render_prompt ----------


def _template(prompt: str = "cute {{item}} illustration", is_builtin: bool = False):
    return T2ITemplate.create(
        code="pets",
        name="宠物",
        description=None,
        prompt=prompt,
        order_index=None,
    )


def test_render_prompt_replaces_placeholder():
    assert _template().render_prompt({"item": "apple"}) == "cute apple illustration"


def test_render_prompt_no_placeholder_passthrough():
    tpl = _template()
    tpl.prompt = "static prompt with no vars"
    assert tpl.render_prompt({"item": "apple"}) == "static prompt with no vars"


# ---------- 模板校验 ----------


def test_template_create_invalid_code():
    with pytest.raises(ParamException) as exc:
        T2ITemplate.create("Bad Code!", "x", None, ITEM_PLACEHOLDER, None)
    assert exc.value.code == 2030


def test_template_create_normalizes_code():
    tpl = T2ITemplate.create("  PETS  ", "宠物", None, ITEM_PLACEHOLDER, None)
    assert tpl.code == "pets"
    assert tpl.order_index == 0
    assert tpl.is_builtin is False


def test_template_create_empty_name():
    with pytest.raises(ParamException) as exc:
        T2ITemplate.create("pets", "  ", None, ITEM_PLACEHOLDER, None)
    assert exc.value.code == 2031
    assert exc.value.message == "name 不能为空"


def test_template_create_name_too_long():
    with pytest.raises(ParamException) as exc:
        T2ITemplate.create("pets", "n" * 65, None, ITEM_PLACEHOLDER, None)
    assert exc.value.code == 2031
    assert exc.value.message == "name 超长（最大 64 字符）"


def test_template_create_empty_prompt():
    with pytest.raises(ParamException) as exc:
        T2ITemplate.create("pets", "宠物", None, "   ", None)
    assert exc.value.code == 2032
    assert exc.value.message == "prompt 不能为空"


def test_template_create_missing_placeholder():
    with pytest.raises(ParamException) as exc:
        T2ITemplate.create("pets", "宠物", None, "cute cat", None)
    assert exc.value.code == 2032
    assert exc.value.message == f"prompt 必须包含占位符 {ITEM_PLACEHOLDER}"


def test_template_apply_update_strips_description_to_none():
    tpl = _template()
    tpl.apply_update("改名", "   ", "new {{item}}", 5)
    assert tpl.name == "改名"
    assert tpl.description is None
    assert tpl.prompt == "new {{item}}"
    assert tpl.order_index == 5


def test_template_apply_update_keeps_order_when_none():
    tpl = _template()
    tpl.order_index = 7
    tpl.apply_update("改名", None, "new {{item}}", None)
    assert tpl.order_index == 7


def test_template_apply_update_missing_placeholder():
    tpl = _template()
    with pytest.raises(ParamException) as exc:
        tpl.apply_update("n", None, "no vars", None)
    assert exc.value.code == 2032


def test_template_builtin_guards():
    tpl = _template()
    tpl.is_builtin = True
    with pytest.raises(ParamException) as exc:
        tpl.ensure_editable()
    assert (exc.value.code, exc.value.message) == (2035, "内置模板不可修改")
    with pytest.raises(ParamException) as exc:
        tpl.ensure_deletable()
    assert (exc.value.code, exc.value.message) == (2035, "内置模板不可删除")


# ---------- 任务状态机 ----------


def test_task_create_initial_state():
    task = T2ITask.create("english-primer", {"item": "apple"})
    assert task.status == TaskStatus.GENERATING
    assert task.last_failed is False
    assert task.created_at == task.updated_at
    assert task.keywords_hash == T2ITask.compute_hash(
        "english-primer", {"item": "apple"}
    )


def test_task_status_serializes_as_plain_string():
    """状态枚举进 JSON 信封必须还是历史字符串，不能变成 'TaskStatus.X'。"""
    task = T2ITask.create("english-primer", {"item": "apple"})
    assert json.dumps({"status": task.status}) == '{"status": "generating"}'


def test_task_mark_succeeded():
    task = T2ITask.create("english-primer", {"item": "apple"})
    task.last_failed = True
    task.mark_succeeded()
    assert task.status == "succeeded"
    assert task.last_failed is False


def test_task_mark_failed():
    task = T2ITask.create("english-primer", {"item": "apple"})
    task.mark_failed()
    assert task.status == "failed"
    assert task.last_failed is True


def test_task_mark_generating_after_failure():
    task = T2ITask.create("english-primer", {"item": "apple"})
    task.mark_failed()
    before = task.updated_at
    task.mark_generating()
    assert task.status == "generating"
    assert task.updated_at >= before


def test_task_touch_only_moves_updated_at():
    task = T2ITask.create("english-primer", {"item": "apple"})
    created = task.created_at
    task.touch()
    assert task.created_at == created
    assert task.updated_at >= created


# ---------- 图片状态机 ----------


def test_image_create_initial_state():
    img = T2IImage.create("t1")
    assert img.task_id == "t1"
    assert img.status == TaskStatus.GENERATING
    assert img.available is False
    assert img.mime is None


def test_image_mark_succeeded_sets_mime():
    img = T2IImage.create("t1")
    img.mark_succeeded("image/webp")
    assert img.status == "succeeded"
    assert img.mime == "image/webp"


def test_image_set_available_requires_succeeded():
    img = T2IImage.create("t1")
    with pytest.raises(ParamException) as exc:
        img.set_available(True)
    assert (exc.value.code, exc.value.message) == (2026, "只有已生成的图片可以标记")


def test_image_set_available_after_success():
    img = T2IImage.create("t1")
    img.mark_succeeded("image/png")
    img.set_available(True)
    assert img.available is True


def test_image_ensure_deletable_blocks_available():
    img = T2IImage.create("t1")
    img.mark_succeeded("image/png")
    img.set_available(True)
    with pytest.raises(ParamException) as exc:
        img.ensure_deletable()
    assert (exc.value.code, exc.value.message) == (
        2027,
        "可用图片不可删除，请先取消可用",
    )


def test_image_ensure_deletable_allows_unavailable():
    img = T2IImage.create("t1")
    img.ensure_deletable()  # 不抛异常即通过


# ---------- business_status ----------


def test_business_status_done_when_any_available():
    a = T2IImage.create("t1")
    b = T2IImage.create("t1")
    b.mark_succeeded("image/png")
    b.set_available(True)
    assert business_status([a, b]) == "done"


def test_business_status_pending_when_none_available():
    assert business_status([T2IImage.create("t1")]) == "pending"
    assert business_status([]) == "pending"

from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest

from app.core.exceptions import ParamException
from app.domain.models.t2i import T2IImage, T2ITask, T2ITemplate
from app.service.t2i_task_service import (
    T2ITaskService,
    _build_prompt,
    _canonical_hash,
    _normalize_item,
)


class FakeGenerator:
    """记录 spawn 调用，不真正跑后台生成——隔离 T2IGenerator 的实现细节。"""

    def __init__(self):
        self.calls: list[tuple[str, str, str]] = []

    def spawn(self, task_id: str, image_id: str, prompt: str) -> None:
        self.calls.append((task_id, image_id, prompt))


@pytest.fixture
def template_repo():
    return AsyncMock()


@pytest.fixture
def task_repo():
    return AsyncMock()


@pytest.fixture
def image_repo():
    return AsyncMock()


@pytest.fixture
def blob_repo():
    return AsyncMock()


@pytest.fixture
def ai():
    return AsyncMock()


@pytest.fixture
def generator():
    return FakeGenerator()


@pytest.fixture
def service(template_repo, task_repo, image_repo, blob_repo, ai, generator):
    return T2ITaskService(
        template_repo=template_repo,
        task_repo=task_repo,
        image_repo=image_repo,
        blob_repo=blob_repo,
        ai=ai,
        generator=generator,
    )


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _template(
    code: str = "english-primer",
    name: str = "英文启蒙",
    prompt: str = "cute {{item}} illustration",
    is_builtin: bool = False,
) -> T2ITemplate:
    now = _now()
    return T2ITemplate(
        id="tpl-1",
        code=code,
        name=name,
        description=None,
        prompt=prompt,
        order_index=0,
        is_builtin=is_builtin,
        created_at=now,
        updated_at=now,
    )


def _task(
    id_: str = "t1",
    template_code: str = "english-primer",
    keywords: dict | None = None,
) -> T2ITask:
    now = _now()
    kw = keywords or {"item": "apple"}
    return T2ITask(
        id=id_,
        template_code=template_code,
        keywords=kw,
        keywords_hash=_canonical_hash(template_code, kw),
        status="generating",
        last_failed=False,
        created_at=now,
        updated_at=now,
    )


def _image(
    id_: str = "i1",
    task_id: str = "t1",
    status: str = "generating",
    available: bool = False,
) -> T2IImage:
    return T2IImage(
        id=id_,
        task_id=task_id,
        status=status,
        available=available,
        mime="image/png" if status == "succeeded" else None,
        created_at=_now(),
    )


# ---------- item normalization ----------


def test_normalize_item_trims():
    assert _normalize_item({"item": "  Apple "}) == {"item": "Apple"}


def test_normalize_item_missing():
    with pytest.raises(ParamException) as exc:
        _normalize_item({})
    assert exc.value.code == 2022


def test_normalize_item_empty_string():
    with pytest.raises(ParamException) as exc:
        _normalize_item({"item": "   "})
    assert exc.value.code == 2022


def test_normalize_item_non_string():
    with pytest.raises(ParamException) as exc:
        _normalize_item({"item": 123})
    assert exc.value.code == 2022


def test_normalize_item_too_long():
    with pytest.raises(ParamException) as exc:
        _normalize_item({"item": "x" * 101})
    assert exc.value.code == 2022


# ---------- canonical hash + prompt ----------


def test_canonical_hash_deterministic():
    assert _canonical_hash("english-primer", {"item": "apple"}) == _canonical_hash(
        "english-primer", {"item": "apple"}
    )


def test_canonical_hash_template_scoped():
    a = _canonical_hash("english-primer", {"item": "apple"})
    b = _canonical_hash("general", {"item": "apple"})
    assert a != b


def test_build_prompt_replaces_placeholder():
    out = _build_prompt("cute {{item}} illustration", {"item": "apple"})
    assert out == "cute apple illustration"


def test_build_prompt_no_placeholder_passthrough():
    out = _build_prompt("static prompt with no vars", {"item": "apple"})
    assert out == "static prompt with no vars"


# ---------- list_templates ----------


@pytest.mark.asyncio
async def test_list_templates(service, template_repo):
    template_repo.list_all.return_value = [
        _template("english-primer", "英文启蒙"),
        _template("general", "常规"),
    ]
    out = await service.list_templates()
    codes = [t["code"] for t in out["templates"]]
    assert codes == ["english-primer", "general"]
    assert "prompt" in out["templates"][0]


# ---------- create_template ----------


@pytest.mark.asyncio
async def test_create_template_success(service, template_repo):
    template_repo.find_by_code.return_value = None
    out = await service.create_template(
        code="pets",
        name="宠物",
        description="小动物",
        prompt="a cute {{item}} photo",
        order_index=2,
    )
    assert out["code"] == "pets"
    assert out["order_index"] == 2
    template_repo.save.assert_awaited_once()


@pytest.mark.asyncio
async def test_create_template_invalid_code(service):
    with pytest.raises(ParamException) as exc:
        await service.create_template(
            code="Bad Code!", name="x", description=None,
            prompt="{{item}}", order_index=None,
        )
    assert exc.value.code == 2030


@pytest.mark.asyncio
async def test_create_template_missing_placeholder(service):
    with pytest.raises(ParamException) as exc:
        await service.create_template(
            code="pets", name="宠物", description=None,
            prompt="cute cat", order_index=None,
        )
    assert exc.value.code == 2032


@pytest.mark.asyncio
async def test_create_template_duplicate_code(service, template_repo):
    template_repo.find_by_code.return_value = _template(code="pets")
    with pytest.raises(ParamException) as exc:
        await service.create_template(
            code="pets", name="宠物", description=None,
            prompt="{{item}}", order_index=None,
        )
    assert exc.value.code == 2033


# ---------- update_template ----------


@pytest.mark.asyncio
async def test_update_template_not_found(service, template_repo):
    template_repo.find_by_id.return_value = None
    with pytest.raises(ParamException) as exc:
        await service.update_template("nope", "n", None, "{{item}}", None)
    assert exc.value.code == 2034


@pytest.mark.asyncio
async def test_update_template_builtin_blocked(service, template_repo):
    template_repo.find_by_id.return_value = _template(is_builtin=True)
    with pytest.raises(ParamException) as exc:
        await service.update_template("tpl-1", "n", None, "{{item}}", None)
    assert exc.value.code == 2035


@pytest.mark.asyncio
async def test_update_template_success(service, template_repo):
    tpl = _template()
    template_repo.find_by_id.return_value = tpl
    out = await service.update_template(
        "tpl-1", name="改名", description="d",
        prompt="new {{item}}", order_index=5,
    )
    assert out["name"] == "改名"
    assert out["prompt"] == "new {{item}}"
    assert out["order_index"] == 5


@pytest.mark.asyncio
async def test_update_template_missing_placeholder(service, template_repo):
    template_repo.find_by_id.return_value = _template()
    with pytest.raises(ParamException) as exc:
        await service.update_template("tpl-1", "n", None, "no vars", None)
    assert exc.value.code == 2032


# ---------- delete_template ----------


@pytest.mark.asyncio
async def test_delete_template_not_found(service, template_repo):
    template_repo.find_by_id.return_value = None
    with pytest.raises(ParamException) as exc:
        await service.delete_template("nope")
    assert exc.value.code == 2034


@pytest.mark.asyncio
async def test_delete_template_builtin_blocked(service, template_repo):
    template_repo.find_by_id.return_value = _template(is_builtin=True)
    with pytest.raises(ParamException) as exc:
        await service.delete_template("tpl-1")
    assert exc.value.code == 2035


@pytest.mark.asyncio
async def test_delete_template_has_tasks_blocked(
    service, template_repo, task_repo
):
    template_repo.find_by_id.return_value = _template(code="pets")
    task_repo.count_by_template_code.return_value = 3
    with pytest.raises(ParamException) as exc:
        await service.delete_template("tpl-1")
    assert exc.value.code == 2036


@pytest.mark.asyncio
async def test_delete_template_success(
    service, template_repo, task_repo
):
    tpl = _template(code="pets")
    template_repo.find_by_id.return_value = tpl
    task_repo.count_by_template_code.return_value = 0
    await service.delete_template("tpl-1")
    template_repo.delete.assert_awaited_once_with(tpl)


# ---------- list_tasks ----------


@pytest.mark.asyncio
async def test_list_tasks_unknown_template(service, template_repo):
    template_repo.find_by_code.return_value = None
    with pytest.raises(ParamException) as exc:
        await service.list_tasks("nope", 1, 20)
    assert exc.value.code == 2020


@pytest.mark.asyncio
async def test_list_tasks_bad_pagination(service, template_repo):
    template_repo.find_by_code.return_value = _template()
    with pytest.raises(ParamException) as exc:
        await service.list_tasks("english-primer", 1, 999)
    assert exc.value.code == 2021


@pytest.mark.asyncio
async def test_list_tasks_success(service, template_repo, task_repo, image_repo):
    template_repo.find_by_code.return_value = _template()
    task = _task()
    img = _image(status="succeeded", available=True)
    task_repo.list_by_template.return_value = ([task], 1)
    image_repo.list_by_task.return_value = [img]

    out = await service.list_tasks("english-primer", 1, 20)

    assert out["total"] == 1
    assert out["template"]["code"] == "english-primer"
    item = out["items"][0]
    assert item["business_status"] == "done"
    assert item["summary"] == "apple"


# ---------- create_task ----------


@pytest.mark.asyncio
async def test_create_task_unknown_template(service, template_repo):
    template_repo.find_by_code.return_value = None
    with pytest.raises(ParamException) as exc:
        await service.create_task("nope", {"item": "apple"})
    assert exc.value.code == 2020


@pytest.mark.asyncio
async def test_create_task_idempotent(
    service, template_repo, task_repo, image_repo, generator
):
    template_repo.find_by_code.return_value = _template()
    existing = _task()
    task_repo.find_by_hash.return_value = existing
    image_repo.list_by_task.return_value = []

    out = await service.create_task("english-primer", {"item": "apple"})

    assert out["existing"] is True
    assert out["task"]["id"] == existing.id
    task_repo.save.assert_not_called()
    assert generator.calls == []  # 命中已有任务不重新排队生成


@pytest.mark.asyncio
async def test_create_task_new(
    service, template_repo, task_repo, image_repo, generator
):
    template_repo.find_by_code.return_value = _template()
    task_repo.find_by_hash.return_value = None

    out = await service.create_task("english-primer", {"item": "Apple"})

    assert out["existing"] is False
    assert out["task"]["keywords"] == {"item": "Apple"}
    assert out["task"]["status"] == "generating"
    task_repo.save.assert_awaited_once()
    image_repo.save.assert_awaited_once()

    # 排队即返回：create_task 落库返回时，generator.spawn 已被调用恰好一次。
    assert len(generator.calls) == 1
    spawned_task_id, spawned_image_id, spawned_prompt = generator.calls[0]
    assert spawned_task_id == out["task"]["id"]
    assert spawned_prompt == "cute Apple illustration"


# ---------- get_task ----------


@pytest.mark.asyncio
async def test_get_task_not_found(service, task_repo):
    task_repo.find_by_id.return_value = None
    with pytest.raises(ParamException) as exc:
        await service.get_task("nope")
    assert exc.value.code == 2023


@pytest.mark.asyncio
async def test_get_task_returns_images(service, task_repo, image_repo):
    task = _task()
    imgs = [
        _image("i1", status="succeeded", available=True),
        _image("i2", status="succeeded", available=False),
        _image("i3", status="failed"),
    ]
    task_repo.find_by_id.return_value = task
    image_repo.list_by_task.return_value = imgs

    out = await service.get_task(task.id)
    assert out["task"]["images_available"] == 1
    assert out["task"]["images_failed"] == 1
    assert [i["id"] for i in out["images"]] == ["i1", "i2", "i3"]


# ---------- retry_task ----------


@pytest.mark.asyncio
async def test_retry_task_not_found(service, task_repo):
    task_repo.find_by_id.return_value = None
    with pytest.raises(ParamException) as exc:
        await service.retry_task("nope")
    assert exc.value.code == 2023


@pytest.mark.asyncio
async def test_retry_task_generating_guard(service, task_repo, image_repo):
    task_repo.find_by_id.return_value = _task()
    image_repo.has_generating.return_value = True
    with pytest.raises(ParamException) as exc:
        await service.retry_task("t1")
    assert exc.value.code == 2024


@pytest.mark.asyncio
async def test_retry_task_template_deleted(
    service, task_repo, image_repo, template_repo
):
    task_repo.find_by_id.return_value = _task()
    image_repo.has_generating.return_value = False
    template_repo.find_by_code.return_value = None
    with pytest.raises(ParamException) as exc:
        await service.retry_task("t1")
    assert exc.value.code == 2020


@pytest.mark.asyncio
async def test_retry_task_success(
    service, task_repo, image_repo, template_repo, generator
):
    task_repo.find_by_id.return_value = _task()
    image_repo.has_generating.return_value = False
    template_repo.find_by_code.return_value = _template()

    out = await service.retry_task("t1")
    assert out["image"]["status"] == "generating"
    image_repo.save.assert_awaited_once()
    task_repo.update.assert_awaited_once()

    assert len(generator.calls) == 1
    spawned_task_id, spawned_image_id, _ = generator.calls[0]
    assert spawned_task_id == "t1"
    assert spawned_image_id == out["image"]["id"]


# ---------- patch_image ----------


@pytest.mark.asyncio
async def test_patch_image_not_found(service, image_repo):
    image_repo.find_by_id.return_value = None
    with pytest.raises(ParamException) as exc:
        await service.patch_image("nope", True)
    assert exc.value.code == 2025


@pytest.mark.asyncio
async def test_patch_image_not_succeeded(service, image_repo):
    image_repo.find_by_id.return_value = _image(status="generating")
    with pytest.raises(ParamException) as exc:
        await service.patch_image("i1", True)
    assert exc.value.code == 2026


@pytest.mark.asyncio
async def test_patch_image_flip(service, task_repo, image_repo):
    img = _image(status="succeeded", available=False)
    image_repo.find_by_id.return_value = img
    task_repo.find_by_id.return_value = _task()
    image_repo.list_by_task.return_value = [
        _image("i1", status="succeeded", available=True),
    ]

    out = await service.patch_image("i1", True)
    assert img.available is True
    assert out["task_business_status"] == "done"


# ---------- delete_image ----------


@pytest.mark.asyncio
async def test_delete_image_not_found(service, image_repo):
    image_repo.find_by_id.return_value = None
    with pytest.raises(ParamException) as exc:
        await service.delete_image("nope")
    assert exc.value.code == 2025


@pytest.mark.asyncio
async def test_delete_image_available_guard(service, image_repo):
    image_repo.find_by_id.return_value = _image(status="succeeded", available=True)
    with pytest.raises(ParamException) as exc:
        await service.delete_image("i1")
    assert exc.value.code == 2027


@pytest.mark.asyncio
async def test_delete_image_success(service, task_repo, image_repo, blob_repo):
    img = _image(status="succeeded", available=False)
    image_repo.find_by_id.return_value = img
    task_repo.find_by_id.return_value = _task()
    image_repo.list_by_task.return_value = []

    out = await service.delete_image("i1")
    blob_repo.delete_by_image.assert_awaited_once_with("i1")
    image_repo.delete.assert_awaited_once_with(img)
    assert out["images_total"] == 0
    assert out["task_business_status"] == "pending"


# ---------- get_image_bytes ----------


@pytest.mark.asyncio
async def test_get_image_bytes_none(service, blob_repo):
    blob_repo.get_bytes.return_value = None
    assert await service.get_image_bytes("nope") is None


@pytest.mark.asyncio
async def test_get_image_bytes_returns_payload(service, blob_repo):
    blob_repo.get_bytes.return_value = (b"payload", "image/webp")
    payload, mime = await service.get_image_bytes("i1")
    assert payload == b"payload"
    assert mime == "image/webp"

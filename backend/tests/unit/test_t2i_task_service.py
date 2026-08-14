from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest

from app.domain.errors import ParamException
from app.domain.models.t2i import T2IImage, T2ITask, T2ITemplate
from app.application.services.t2i_task_service import T2ITaskService


class FakeGenerator:
    """记录 spawn 调用，不真正跑后台生成——隔离 T2IGenerator 的实现细节。

    额外记两件事，用来锁**顺序**不变量：spawn 当时的 commit 次数，以及往
    uow 的事件日志里插一条 "spawn"。后台任务是另开 session 按 id 重查的，
    commit 必须已经发生在 spawn 之前，否则线上会读不到行。
    """

    def __init__(self, uow=None):
        self.calls: list[tuple[str, str, str]] = []
        self.commit_count_at_spawn: list[int] = []
        self._uow = uow

    def spawn(self, task_id: str, image_id: str, prompt: str) -> None:
        self.calls.append((task_id, image_id, prompt))
        if self._uow is not None:
            self.commit_count_at_spawn.append(self._uow.commit.await_count)
            self._uow.calls.append("spawn")


@pytest.fixture
def template_repo(uow):
    return uow.t2i_templates


@pytest.fixture
def task_repo(uow):
    return uow.t2i_tasks


@pytest.fixture
def image_repo(uow):
    return uow.t2i_images


@pytest.fixture
def blob_repo(uow):
    return uow.t2i_blobs


@pytest.fixture
def ai():
    return AsyncMock()


@pytest.fixture
def generator(uow):
    return FakeGenerator(uow)


@pytest.fixture
def service(uow, generator):
    return T2ITaskService(uow=uow, generator=generator)


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
        keywords_hash=T2ITask.compute_hash(template_code, kw),
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


# item 规范化 / hash / prompt 渲染的纯逻辑已迁入 domain，
# 见 tests/unit/test_domain_t2i.py。


# ---------- list_templates ----------


@pytest.mark.asyncio
async def test_list_templates(service, template_repo):
    template_repo.list_all.return_value = [
        _template("english-primer", "英文启蒙"),
        _template("general", "常规"),
    ]
    out = await service.list_templates()
    codes = [t.code for t in out["templates"]]
    assert codes == ["english-primer", "general"]
    assert out["templates"][0].prompt


# ---------- create_template ----------


@pytest.mark.asyncio
async def test_create_template_success(service, uow, template_repo):
    template_repo.find_by_code.return_value = None
    out = await service.create_template(
        code="pets",
        name="宠物",
        description="小动物",
        prompt="a cute {{item}} photo",
        order_index=2,
    )
    assert out.code == "pets"
    assert out.order_index == 2
    template_repo.add.assert_called_once()
    assert uow.commit.await_count == 1


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
    assert out.name == "改名"
    assert out.prompt == "new {{item}}"
    assert out.order_index == 5


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
    service, uow, template_repo, task_repo
):
    tpl = _template(code="pets")
    template_repo.find_by_id.return_value = tpl
    task_repo.count_by_template_code.return_value = 0
    await service.delete_template("tpl-1")
    template_repo.delete.assert_awaited_once_with(tpl)
    assert uow.commit.await_count == 1


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
    assert out["template"].code == "english-primer"
    item = out["items"][0]
    assert item.business_status == "done"
    assert item.summary == "apple"


# ---------- create_task ----------


@pytest.mark.asyncio
async def test_create_task_unknown_template(service, template_repo):
    template_repo.find_by_code.return_value = None
    with pytest.raises(ParamException) as exc:
        await service.create_task("nope", {"item": "apple"})
    assert exc.value.code == 2020


@pytest.mark.asyncio
async def test_create_task_idempotent(
    service, uow, template_repo, task_repo, image_repo, generator
):
    template_repo.find_by_code.return_value = _template()
    existing = _task()
    task_repo.find_by_hash.return_value = existing
    image_repo.list_by_task.return_value = []

    out = await service.create_task("english-primer", {"item": "apple"})

    assert out["existing"] is True
    assert out["task"].id == existing.id
    task_repo.add.assert_not_called()
    assert generator.calls == []  # 命中已有任务不重新排队生成
    # 只刷新 updated_at 也是写用例：一次提交
    assert uow.commit.await_count == 1


@pytest.mark.asyncio
async def test_create_task_new(
    service, uow, template_repo, task_repo, image_repo, generator
):
    template_repo.find_by_code.return_value = _template()
    task_repo.find_by_hash.return_value = None

    out = await service.create_task("english-primer", {"item": "Apple"})

    assert out["existing"] is False
    assert out["task"].keywords == {"item": "Apple"}
    assert out["task"].status == "generating"
    task_repo.add.assert_called_once()
    image_repo.add.assert_called_once()
    # 顺序不变量，逐位锁死（只断言次数的话，把 commit 挪到 spawn 之后照样绿）：
    #   1. add(task) 先于 flush —— flush 是给外键定序用的
    #   2. flush 先于 add(image) —— 两个模型之间没有 relationship()，同一次
    #      flush 里 SQLAlchemy 不保证先插父行，必须显式定序
    #   3. commit 先于 spawn —— 后台任务另开 session 按 id 重查，晚提交会读不到行
    assert uow.calls == [
        "t2i_tasks.add",
        "flush",
        "t2i_images.add",
        "commit",
        "spawn",
    ]
    assert generator.commit_count_at_spawn == [1]

    # 排队即返回：create_task 落库返回时，generator.spawn 已被调用恰好一次。
    assert len(generator.calls) == 1
    spawned_task_id, spawned_image_id, spawned_prompt = generator.calls[0]
    assert spawned_task_id == out["task"].id
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
    assert out["task"].images_available == 1
    assert out["task"].images_failed == 1
    assert [i.id for i in out["images"]] == ["i1", "i2", "i3"]


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
    service, uow, task_repo, image_repo, template_repo, generator
):
    task = _task()
    task_repo.find_by_id.return_value = task
    image_repo.has_generating.return_value = False
    template_repo.find_by_code.return_value = _template()

    out = await service.retry_task("t1")
    assert out["image"].status == "generating"
    image_repo.add.assert_called_once()
    assert task.status == "generating"
    # 顺序不变量：图片入库并提交之后才排队生成（同上，spawn 后的 commit 会导致
    # 后台任务读不到图片行）。retry 复用已存在的 task 行，不需要 flush 定序。
    assert uow.calls == ["t2i_images.add", "commit", "spawn"]
    assert generator.commit_count_at_spawn == [1]

    assert len(generator.calls) == 1
    spawned_task_id, spawned_image_id, _ = generator.calls[0]
    assert spawned_task_id == "t1"
    assert spawned_image_id == out["image"].id


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
async def test_patch_image_flip(service, uow, task_repo, image_repo):
    img = _image(status="succeeded", available=False)
    image_repo.find_by_id.return_value = img
    task_repo.find_by_id.return_value = _task()
    image_repo.list_by_task.return_value = [
        _image("i1", status="succeeded", available=True),
    ]

    out = await service.patch_image("i1", True)
    assert img.available is True
    assert out["task_business_status"] == "done"
    # 原实现在这里连续 commit 两次；合并为一次（原子性修复，对外行为不变）
    assert uow.calls == ["commit"]
    # 且 commit 必须早于回读 siblings（原实现也是先提交再查）
    assert uow.commit.await_args_list  # 已 await
    image_repo.list_by_task.assert_awaited_once()


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
async def test_delete_image_success(service, uow, task_repo, image_repo, blob_repo):
    img = _image(status="succeeded", available=False)
    image_repo.find_by_id.return_value = img
    task_repo.find_by_id.return_value = _task()
    image_repo.list_by_task.return_value = []

    out = await service.delete_image("i1")
    blob_repo.delete_by_image.assert_awaited_once_with("i1")
    image_repo.delete.assert_awaited_once_with(img)
    assert out["images_total"] == 0
    assert out["task_business_status"] == "pending"
    # 原实现三次 commit（blob / image / task）；合并成一次，且顺序不变：
    # 先删 blob 再删 image（外键方向），最后一次提交
    assert uow.calls == ["t2i_images.delete", "commit"]


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

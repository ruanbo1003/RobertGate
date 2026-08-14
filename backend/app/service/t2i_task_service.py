"""文生图任务化 service：模板 CRUD + 任务/图片 + 异步生图。

模板从 DB 读取（t2i_templates 表），提示词用单一 `{{item}}` 占位符，
服务端做纯字符串替换。
"""

from __future__ import annotations

import hashlib
import json
import re
import uuid
from datetime import datetime, timezone
from typing import Any

from app.core.exceptions import ParamException
from app.domain.models.t2i import T2IImage, T2ITask, T2ITemplate
from app.infrastructure.repositories.t2i_repo import (
    T2IImageBlobRepo,
    T2IImageRepo,
    T2ITaskRepo,
    T2ITemplateRepo,
)
from app.service.ai_client import AIClient
from app.service.t2i_generation import T2IGenerator


ITEM_MAX_LENGTH = 100
CODE_RE = re.compile(r"^[a-z][a-z0-9-]{1,63}$")
ITEM_PLACEHOLDER = "{{item}}"


# ---------- 工具函数 ----------


def _iso(dt: datetime) -> str:
    return dt.isoformat()


def _canonical_hash(template_code: str, keywords: dict[str, str]) -> str:
    canonical = json.dumps(
        keywords, sort_keys=True, ensure_ascii=False, separators=(",", ":")
    )
    payload = f"{template_code}|{canonical}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _normalize_item(raw: dict[str, Any]) -> dict[str, str]:
    """校验并规范化任务关键词。单变量 `item`。"""
    value = raw.get("item")
    if value is None:
        raise ParamException(2022, "item 不能为空")
    if not isinstance(value, str):
        raise ParamException(2022, "item 必须是字符串")
    value = value.strip()
    if not value:
        raise ParamException(2022, "item 不能为空")
    if len(value) > ITEM_MAX_LENGTH:
        raise ParamException(2022, f"item 超长（最大 {ITEM_MAX_LENGTH} 字符）")
    return {"item": value}


def _build_prompt(template_prompt: str, keywords: dict[str, str]) -> str:
    return template_prompt.replace(ITEM_PLACEHOLDER, keywords["item"])


def _business_status(images: list[T2IImage]) -> str:
    return "done" if any(i.available for i in images) else "pending"


def _template_dict(t: T2ITemplate) -> dict:
    return {
        "id": t.id,
        "code": t.code,
        "name": t.name,
        "description": t.description,
        "prompt": t.prompt,
        "order_index": t.order_index,
        "is_builtin": t.is_builtin,
        "created_at": _iso(t.created_at),
        "updated_at": _iso(t.updated_at),
    }


def _task_summary_dict(task: T2ITask, images: list[T2IImage]) -> dict:
    succeeded = [i for i in images if i.status == "succeeded"]
    generating = [i for i in images if i.status == "generating"]
    available = [i for i in succeeded if i.available]
    thumbs = [f"/api/v1/ai/t2i/images/{i.id}" for i in succeeded[:4]]
    status = "generating" if generating else task.status
    return {
        "id": task.id,
        "template_code": task.template_code,
        "keywords": task.keywords,
        "summary": task.keywords.get("item", ""),
        "status": status,
        "business_status": _business_status(images),
        "images_total": len(succeeded) + len(generating),
        "images_available": len(available),
        "last_failed": task.last_failed,
        "thumbnails": thumbs,
        "created_at": _iso(task.created_at),
        "updated_at": _iso(task.updated_at),
    }


def _image_dict(img: T2IImage) -> dict:
    return {
        "id": img.id,
        "status": img.status,
        "available": img.available,
        "url": f"/api/v1/ai/t2i/images/{img.id}" if img.status == "succeeded" else None,
        "created_at": _iso(img.created_at),
    }


# ---------- Service ----------


class T2ITaskService:
    def __init__(
        self,
        template_repo: T2ITemplateRepo,
        task_repo: T2ITaskRepo,
        image_repo: T2IImageRepo,
        blob_repo: T2IImageBlobRepo,
        ai: AIClient,
        generator: T2IGenerator,
    ) -> None:
        self.template_repo = template_repo
        self.task_repo = task_repo
        self.image_repo = image_repo
        self.blob_repo = blob_repo
        self.ai = ai
        self.generator = generator

    # ---- Templates ----

    async def list_templates(self) -> dict:
        rows = await self.template_repo.list_all()
        return {"templates": [_template_dict(t) for t in rows]}

    async def create_template(
        self,
        code: str,
        name: str,
        description: str | None,
        prompt: str,
        order_index: int | None,
    ) -> dict:
        code = (code or "").strip().lower()
        name = (name or "").strip()
        prompt = (prompt or "").strip()

        if not CODE_RE.match(code):
            raise ParamException(
                2030, "code 只允许小写字母/数字/连字符，须以字母开头，长度 2-64"
            )
        if not name:
            raise ParamException(2031, "name 不能为空")
        if len(name) > 64:
            raise ParamException(2031, "name 超长（最大 64 字符）")
        if not prompt:
            raise ParamException(2032, "prompt 不能为空")
        if ITEM_PLACEHOLDER not in prompt:
            raise ParamException(2032, f"prompt 必须包含占位符 {ITEM_PLACEHOLDER}")

        existing = await self.template_repo.find_by_code(code)
        if existing is not None:
            raise ParamException(2033, "code 已存在")

        now = datetime.now(timezone.utc)
        tpl = T2ITemplate(
            id=str(uuid.uuid4()),
            code=code,
            name=name,
            description=(description or None),
            prompt=prompt,
            order_index=order_index if order_index is not None else 0,
            is_builtin=False,
            created_at=now,
            updated_at=now,
        )
        await self.template_repo.save(tpl)
        return _template_dict(tpl)

    async def update_template(
        self,
        template_id: str,
        name: str,
        description: str | None,
        prompt: str,
        order_index: int | None,
    ) -> dict:
        tpl = await self.template_repo.find_by_id(template_id)
        if tpl is None:
            raise ParamException(2034, "模板不存在")
        if tpl.is_builtin:
            raise ParamException(2035, "内置模板不可修改")

        name = (name or "").strip()
        prompt = (prompt or "").strip()
        if not name:
            raise ParamException(2031, "name 不能为空")
        if len(name) > 64:
            raise ParamException(2031, "name 超长（最大 64 字符）")
        if not prompt:
            raise ParamException(2032, "prompt 不能为空")
        if ITEM_PLACEHOLDER not in prompt:
            raise ParamException(2032, f"prompt 必须包含占位符 {ITEM_PLACEHOLDER}")

        tpl.name = name
        tpl.description = (description or "").strip() or None
        tpl.prompt = prompt
        if order_index is not None:
            tpl.order_index = order_index
        tpl.updated_at = datetime.now(timezone.utc)
        await self.template_repo.update(tpl)
        return _template_dict(tpl)

    async def delete_template(self, template_id: str) -> None:
        tpl = await self.template_repo.find_by_id(template_id)
        if tpl is None:
            raise ParamException(2034, "模板不存在")
        if tpl.is_builtin:
            raise ParamException(2035, "内置模板不可删除")

        used = await self.task_repo.count_by_template_code(tpl.code)
        if used > 0:
            raise ParamException(
                2036, f"该模板下已有 {used} 个任务，请先删除任务再删除模板"
            )
        await self.template_repo.delete(tpl)

    # ---- Tasks ----

    async def list_tasks(
        self, template_code: str, page: int, page_size: int
    ) -> dict:
        tpl = await self.template_repo.find_by_code(template_code)
        if tpl is None:
            raise ParamException(2020, "template_code 不存在")
        if page < 1 or page_size < 1 or page_size > 50:
            raise ParamException(2021, "分页参数非法")

        tasks, total = await self.task_repo.list_by_template(
            template_code, page, page_size
        )
        items = []
        for t in tasks:
            imgs = await self.image_repo.list_by_task(t.id)
            items.append(_task_summary_dict(t, imgs))

        return {
            "template": {"code": tpl.code, "name": tpl.name},
            "page": page,
            "page_size": page_size,
            "total": total,
            "items": items,
        }

    async def create_task(
        self, template_code: str, raw_keywords: dict[str, Any]
    ) -> dict:
        tpl = await self.template_repo.find_by_code(template_code)
        if tpl is None:
            raise ParamException(2020, "template_code 不存在")

        keywords = _normalize_item(raw_keywords)
        h = _canonical_hash(template_code, keywords)

        existing = await self.task_repo.find_by_hash(h)
        if existing is not None:
            existing.updated_at = datetime.now(timezone.utc)
            await self.task_repo.update(existing)
            imgs = await self.image_repo.list_by_task(existing.id)
            return {"existing": True, "task": _task_summary_dict(existing, imgs)}

        now = datetime.now(timezone.utc)
        task = T2ITask(
            id=str(uuid.uuid4()),
            template_code=template_code,
            keywords=keywords,
            keywords_hash=h,
            status="generating",
            last_failed=False,
            created_at=now,
            updated_at=now,
        )
        await self.task_repo.save(task)

        image = T2IImage(
            id=str(uuid.uuid4()),
            task_id=task.id,
            status="generating",
            available=False,
            mime=None,
            created_at=now,
        )
        await self.image_repo.save(image)

        prompt = _build_prompt(tpl.prompt, keywords)
        self.generator.spawn(task.id, image.id, prompt)

        return {"existing": False, "task": _task_summary_dict(task, [image])}

    async def get_task(self, task_id: str) -> dict:
        task = await self.task_repo.find_by_id(task_id)
        if task is None:
            raise ParamException(2023, "任务不存在")
        images = await self.image_repo.list_by_task(task_id)
        summary = _task_summary_dict(task, images)
        summary["images_failed"] = sum(1 for i in images if i.status == "failed")
        return {
            "task": summary,
            "images": [_image_dict(i) for i in images],
        }

    async def retry_task(self, task_id: str) -> dict:
        task = await self.task_repo.find_by_id(task_id)
        if task is None:
            raise ParamException(2023, "任务不存在")
        if await self.image_repo.has_generating(task_id):
            raise ParamException(2024, "已有正在生成的图片，请稍候")

        tpl = await self.template_repo.find_by_code(task.template_code)
        if tpl is None:
            raise ParamException(2020, "任务所属模板已删除")

        now = datetime.now(timezone.utc)
        image = T2IImage(
            id=str(uuid.uuid4()),
            task_id=task_id,
            status="generating",
            available=False,
            mime=None,
            created_at=now,
        )
        await self.image_repo.save(image)

        task.status = "generating"
        task.updated_at = now
        await self.task_repo.update(task)

        prompt = _build_prompt(tpl.prompt, task.keywords)
        self.generator.spawn(task_id, image.id, prompt)

        return {"image": _image_dict(image)}

    # ---- Images ----

    async def patch_image(self, image_id: str, available: bool) -> dict:
        image = await self.image_repo.find_by_id(image_id)
        if image is None:
            raise ParamException(2025, "图片不存在")
        if image.status != "succeeded":
            raise ParamException(2026, "只有已生成的图片可以标记")

        image.available = available
        await self.image_repo.update(image)

        task = await self.task_repo.find_by_id(image.task_id)
        if task is not None:
            task.updated_at = datetime.now(timezone.utc)
            await self.task_repo.update(task)

        siblings = await self.image_repo.list_by_task(image.task_id)
        return {
            "id": image.id,
            "available": image.available,
            "task_id": image.task_id,
            "task_business_status": _business_status(siblings),
        }

    async def delete_image(self, image_id: str) -> dict:
        image = await self.image_repo.find_by_id(image_id)
        if image is None:
            raise ParamException(2025, "图片不存在")
        if image.available:
            raise ParamException(2027, "可用图片不可删除，请先取消可用")

        task_id = image.task_id
        await self.blob_repo.delete_by_image(image_id)
        await self.image_repo.delete(image)

        task = await self.task_repo.find_by_id(task_id)
        if task is not None:
            task.updated_at = datetime.now(timezone.utc)
            await self.task_repo.update(task)

        siblings = await self.image_repo.list_by_task(task_id)
        succeeded = [i for i in siblings if i.status == "succeeded"]
        available = [i for i in succeeded if i.available]
        return {
            "id": image_id,
            "task_id": task_id,
            "images_total": len(siblings),
            "images_available": len(available),
            "task_business_status": _business_status(siblings),
        }

    async def get_image_bytes(self, image_id: str) -> tuple[bytes, str] | None:
        row = await self.blob_repo.get_bytes(image_id)
        if row is None:
            return None
        payload, mime = row
        return payload, mime or "image/png"

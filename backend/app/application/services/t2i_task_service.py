"""文生图任务化 service：模板 CRUD + 任务/图片 + 异步生图。

模板从 DB 读取（t2i_templates 表），提示词用单一 `{{item}}` 占位符，
服务端做纯字符串替换。
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from app.application.ports import AIClient
from app.application.services.t2i_generation import T2IGenerator
from app.domain.errors import ParamException, codes, ensure_found
from app.domain.models.t2i import (
    T2IImage,
    T2ITask,
    T2ITemplate,
    business_status,
    normalize_keywords,
)
from app.domain.repositories.uow import UnitOfWork


# ---------- 工具函数 ----------


def _iso(dt: datetime) -> str:
    return dt.isoformat()


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
        "business_status": business_status(images),
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
        uow: UnitOfWork,
        ai: AIClient,
        generator: T2IGenerator,
    ) -> None:
        self.uow = uow
        self.ai = ai
        self.generator = generator

    # ---- Templates ----

    async def list_templates(self) -> dict:
        rows = await self.uow.t2i_templates.list_all()
        return {"templates": [_template_dict(t) for t in rows]}

    async def create_template(
        self,
        code: str,
        name: str,
        description: str | None,
        prompt: str,
        order_index: int | None,
    ) -> dict:
        tpl = T2ITemplate.create(code, name, description, prompt, order_index)

        existing = await self.uow.t2i_templates.find_by_code(tpl.code)
        if existing is not None:
            raise ParamException(codes.T2I_TEMPLATE_CODE_TAKEN, "code 已存在")

        self.uow.t2i_templates.add(tpl)
        await self.uow.commit()
        return _template_dict(tpl)

    async def update_template(
        self,
        template_id: str,
        name: str,
        description: str | None,
        prompt: str,
        order_index: int | None,
    ) -> dict:
        tpl = ensure_found(
            await self.uow.t2i_templates.find_by_id(template_id),
            codes.T2I_TEMPLATE_NOT_FOUND,
            "模板不存在",
        )
        tpl.ensure_editable()

        tpl.apply_update(name, description, prompt, order_index)
        await self.uow.commit()
        return _template_dict(tpl)

    async def delete_template(self, template_id: str) -> None:
        tpl = ensure_found(
            await self.uow.t2i_templates.find_by_id(template_id),
            codes.T2I_TEMPLATE_NOT_FOUND,
            "模板不存在",
        )
        tpl.ensure_deletable()

        used = await self.uow.t2i_tasks.count_by_template_code(tpl.code)
        if used > 0:
            raise ParamException(
                codes.T2I_TEMPLATE_IN_USE,
                f"该模板下已有 {used} 个任务，请先删除任务再删除模板",
            )
        await self.uow.t2i_templates.delete(tpl)
        await self.uow.commit()

    # ---- Tasks ----

    async def list_tasks(
        self, template_code: str, page: int, page_size: int
    ) -> dict:
        tpl = ensure_found(
            await self.uow.t2i_templates.find_by_code(template_code),
            codes.T2I_TEMPLATE_CODE_NOT_FOUND,
            "template_code 不存在",
        )
        if page < 1 or page_size < 1 or page_size > 50:
            raise ParamException(codes.T2I_PAGINATION_INVALID, "分页参数非法")

        tasks, total = await self.uow.t2i_tasks.list_by_template(
            template_code, page, page_size
        )
        items = []
        for t in tasks:
            imgs = await self.uow.t2i_images.list_by_task(t.id)
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
        tpl = ensure_found(
            await self.uow.t2i_templates.find_by_code(template_code),
            codes.T2I_TEMPLATE_CODE_NOT_FOUND,
            "template_code 不存在",
        )

        keywords = normalize_keywords(raw_keywords)
        h = T2ITask.compute_hash(template_code, keywords)

        existing = await self.uow.t2i_tasks.find_by_hash(h)
        if existing is not None:
            existing.touch()
            await self.uow.commit()
            imgs = await self.uow.t2i_images.list_by_task(existing.id)
            return {"existing": True, "task": _task_summary_dict(existing, imgs)}

        task = T2ITask.create(template_code, keywords)
        self.uow.t2i_tasks.add(task)
        # t2i_images.task_id 外键指向 t2i_tasks，而两个模型之间没有
        # relationship()，同一次 flush 里 SQLAlchemy 不保证先插任务再插图片。
        # 显式 flush 定序；事务不结束，两条写仍然原子。
        await self.uow.flush()

        image = T2IImage.create(task.id)
        self.uow.t2i_images.add(image)
        await self.uow.commit()

        prompt = tpl.render_prompt(keywords)
        self.generator.spawn(task.id, image.id, prompt)

        return {"existing": False, "task": _task_summary_dict(task, [image])}

    async def get_task(self, task_id: str) -> dict:
        task = ensure_found(
            await self.uow.t2i_tasks.find_by_id(task_id),
            codes.T2I_TASK_NOT_FOUND,
            "任务不存在",
        )
        images = await self.uow.t2i_images.list_by_task(task_id)
        summary = _task_summary_dict(task, images)
        summary["images_failed"] = sum(1 for i in images if i.status == "failed")
        return {
            "task": summary,
            "images": [_image_dict(i) for i in images],
        }

    async def retry_task(self, task_id: str) -> dict:
        task = ensure_found(
            await self.uow.t2i_tasks.find_by_id(task_id),
            codes.T2I_TASK_NOT_FOUND,
            "任务不存在",
        )
        if await self.uow.t2i_images.has_generating(task_id):
            raise ParamException(codes.T2I_TASK_GENERATING, "已有正在生成的图片，请稍候")

        tpl = ensure_found(
            await self.uow.t2i_templates.find_by_code(task.template_code),
            codes.T2I_TEMPLATE_CODE_NOT_FOUND,
            "任务所属模板已删除",
        )

        image = T2IImage.create(task_id)
        self.uow.t2i_images.add(image)

        task.mark_generating()
        await self.uow.commit()

        prompt = tpl.render_prompt(task.keywords)
        self.generator.spawn(task_id, image.id, prompt)

        return {"image": _image_dict(image)}

    # ---- Images ----

    async def patch_image(self, image_id: str, available: bool) -> dict:
        image = ensure_found(
            await self.uow.t2i_images.find_by_id(image_id),
            codes.T2I_IMAGE_NOT_FOUND,
            "图片不存在",
        )
        image.set_available(available)

        task = await self.uow.t2i_tasks.find_by_id(image.task_id)
        if task is not None:
            task.touch()
        await self.uow.commit()

        siblings = await self.uow.t2i_images.list_by_task(image.task_id)
        return {
            "id": image.id,
            "available": image.available,
            "task_id": image.task_id,
            "task_business_status": business_status(siblings),
        }

    async def delete_image(self, image_id: str) -> dict:
        image = ensure_found(
            await self.uow.t2i_images.find_by_id(image_id),
            codes.T2I_IMAGE_NOT_FOUND,
            "图片不存在",
        )
        image.ensure_deletable()

        task_id = image.task_id
        await self.uow.t2i_blobs.delete_by_image(image_id)
        await self.uow.t2i_images.delete(image)

        task = await self.uow.t2i_tasks.find_by_id(task_id)
        if task is not None:
            task.touch()
        await self.uow.commit()

        siblings = await self.uow.t2i_images.list_by_task(task_id)
        succeeded = [i for i in siblings if i.status == "succeeded"]
        available = [i for i in succeeded if i.available]
        return {
            "id": image_id,
            "task_id": task_id,
            "images_total": len(siblings),
            "images_available": len(available),
            "task_business_status": business_status(siblings),
        }

    async def get_image_bytes(self, image_id: str) -> tuple[bytes, str] | None:
        row = await self.uow.t2i_blobs.get_bytes(image_id)
        if row is None:
            return None
        payload, mime = row
        return payload, mime or "image/png"

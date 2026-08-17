"""文生图模块出参 DTO。

计算字段（业务状态、缩略图 URL、聚合计数）统一收在 `build()` 里，service 只
负责取数。图片 URL 的拼接规则与路由 `GET /api/v1/ai/t2i/images/{image_id}`
一一对应。
"""

from __future__ import annotations

from typing import Any

from app.application.dto.base import DTO, IsoDt
from app.domain.models.t2i import T2IImage, T2ITask, T2ITemplate, business_status

IMAGE_URL_PREFIX = "/api/v1/ai/t2i/images"


def _image_url(image_id: str) -> str:
    return f"{IMAGE_URL_PREFIX}/{image_id}"


class TemplateBrief(DTO):
    """任务列表里的模板摘要。"""

    code: str
    name: str

    @classmethod
    def build(cls, template: T2ITemplate) -> TemplateBrief:
        return cls(code=template.code, name=template.name)


class TemplateOut(DTO):
    id: str
    code: str
    name: str
    description: str | None
    prompt: str
    order_index: int
    is_builtin: bool
    created_at: IsoDt
    updated_at: IsoDt


class ImageOut(DTO):
    id: str
    status: str
    available: bool
    url: str | None
    created_at: IsoDt

    @classmethod
    def build(cls, image: T2IImage) -> ImageOut:
        return cls(
            id=image.id,
            status=image.status,
            available=image.available,
            url=_image_url(image.id) if image.status == "succeeded" else None,
            created_at=image.created_at,
        )


def _summary_fields(task: T2ITask, images: list[T2IImage]) -> dict[str, Any]:
    succeeded = [i for i in images if i.status == "succeeded"]
    generating = [i for i in images if i.status == "generating"]
    available = [i for i in succeeded if i.available]
    return {
        "id": task.id,
        "template_code": task.template_code,
        "keywords": task.keywords,
        "summary": task.keywords.get("item", ""),
        # 只要还有图在生成，任务对外就是 generating（覆盖行上的 status）
        "status": "generating" if generating else task.status,
        "business_status": business_status(images),
        "images_total": len(succeeded) + len(generating),
        "images_available": len(available),
        "last_failed": task.last_failed,
        "thumbnails": [_image_url(i.id) for i in succeeded[:4]],
        "created_at": task.created_at,
        "updated_at": task.updated_at,
    }


class TaskSummary(DTO):
    id: str
    template_code: str
    keywords: dict
    summary: str
    status: str
    business_status: str
    images_total: int
    images_available: int
    last_failed: bool
    thumbnails: list[str]
    created_at: IsoDt
    updated_at: IsoDt

    @classmethod
    def build(cls, task: T2ITask, images: list[T2IImage]) -> TaskSummary:
        return cls(**_summary_fields(task, images))


class TaskDetail(TaskSummary):
    """任务详情：比列表项多一个失败计数。"""

    images_failed: int

    @classmethod
    def build(cls, task: T2ITask, images: list[T2IImage]) -> TaskDetail:
        return cls(
            **_summary_fields(task, images),
            images_failed=sum(1 for i in images if i.status == "failed"),
        )

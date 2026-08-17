from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import Response

from app.application.services.t2i_task_service import T2ITaskService
from app.interfaces.api.deps import get_t2i_task_service, require_admin
from app.interfaces.api.response import success
from app.interfaces.api.schemas.t2i import (
    CreateTemplateRequest,
    PatchImageRequest,
    UpdateTemplateRequest,
)

router = APIRouter(prefix="/ai/t2i", tags=["ai-t2i"])


# ---- Templates ----


@router.get("/templates")
async def list_templates(
    service: T2ITaskService = Depends(get_t2i_task_service),
):
    return success(await service.list_templates())


@router.post("/templates")
async def create_template(
    body: CreateTemplateRequest,
    service: T2ITaskService = Depends(get_t2i_task_service),
    _admin_id: str = Depends(require_admin),
):
    return success(
        await service.create_template(
            code=body.code,
            name=body.name,
            description=body.description,
            prompt=body.prompt,
            order_index=body.order_index,
        )
    )


@router.put("/templates/{template_id}")
async def update_template(
    template_id: str,
    body: UpdateTemplateRequest,
    service: T2ITaskService = Depends(get_t2i_task_service),
    _admin_id: str = Depends(require_admin),
):
    return success(
        await service.update_template(
            template_id=template_id,
            name=body.name,
            description=body.description,
            prompt=body.prompt,
            order_index=body.order_index,
        )
    )


@router.delete("/templates/{template_id}")
async def delete_template(
    template_id: str,
    service: T2ITaskService = Depends(get_t2i_task_service),
    _admin_id: str = Depends(require_admin),
):
    await service.delete_template(template_id)
    return success({"id": template_id})


# ---- Tasks ----


@router.get("/templates/{code}/tasks")
async def list_tasks(
    code: str,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=50),
    service: T2ITaskService = Depends(get_t2i_task_service),
):
    return success(await service.list_tasks(code, page, page_size))


@router.post("/templates/{code}/tasks")
async def create_task(
    code: str,
    request: Request,
    service: T2ITaskService = Depends(get_t2i_task_service),
    _admin_id: str = Depends(require_admin),
):
    body = await request.json()
    if not isinstance(body, dict):
        body = {}
    return success(await service.create_task(code, body))


@router.get("/tasks/{task_id}")
async def get_task(
    task_id: str,
    service: T2ITaskService = Depends(get_t2i_task_service),
):
    return success(await service.get_task(task_id))


@router.post("/tasks/{task_id}/retry")
async def retry_task(
    task_id: str,
    service: T2ITaskService = Depends(get_t2i_task_service),
    _admin_id: str = Depends(require_admin),
):
    return success(await service.retry_task(task_id))


# ---- Images ----


@router.get("/images/{image_id}")
async def get_image(
    image_id: str,
    service: T2ITaskService = Depends(get_t2i_task_service),
):
    row = await service.get_image_bytes(image_id)
    if row is None:
        return Response(status_code=404)
    payload, mime = row
    return Response(content=payload, media_type=mime)


@router.patch("/images/{image_id}")
async def patch_image(
    image_id: str,
    body: PatchImageRequest,
    service: T2ITaskService = Depends(get_t2i_task_service),
    _admin_id: str = Depends(require_admin),
):
    return success(await service.patch_image(image_id, body.available))


@router.delete("/images/{image_id}")
async def delete_image(
    image_id: str,
    service: T2ITaskService = Depends(get_t2i_task_service),
    _admin_id: str = Depends(require_admin),
):
    return success(await service.delete_image(image_id))

from __future__ import annotations

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.t2i import T2IImage, T2IImageBlob, T2ITask, T2ITemplate


class T2ITemplateRepo:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def find_by_id(self, template_id: str) -> T2ITemplate | None:
        r = await self.session.execute(
            select(T2ITemplate).where(T2ITemplate.id == template_id)
        )
        return r.scalar_one_or_none()

    async def find_by_code(self, code: str) -> T2ITemplate | None:
        r = await self.session.execute(
            select(T2ITemplate).where(T2ITemplate.code == code)
        )
        return r.scalar_one_or_none()

    async def list_all(self) -> list[T2ITemplate]:
        r = await self.session.execute(
            select(T2ITemplate).order_by(
                T2ITemplate.order_index.asc(), T2ITemplate.created_at.asc()
            )
        )
        return list(r.scalars().all())

    async def save(self, template: T2ITemplate) -> None:
        self.session.add(template)
        await self.session.commit()

    async def update(self, template: T2ITemplate) -> None:  # noqa: ARG002
        await self.session.commit()

    async def delete(self, template: T2ITemplate) -> None:
        await self.session.delete(template)
        await self.session.commit()


class T2ITaskRepo:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def find_by_id(self, task_id: str) -> T2ITask | None:
        r = await self.session.execute(select(T2ITask).where(T2ITask.id == task_id))
        return r.scalar_one_or_none()

    async def find_by_hash(self, keywords_hash: str) -> T2ITask | None:
        r = await self.session.execute(
            select(T2ITask).where(T2ITask.keywords_hash == keywords_hash)
        )
        return r.scalar_one_or_none()

    async def count_by_template_code(self, template_code: str) -> int:
        r = await self.session.execute(
            select(func.count(T2ITask.id)).where(
                T2ITask.template_code == template_code
            )
        )
        return int(r.scalar_one() or 0)

    async def list_by_template(
        self, template_code: str, page: int, page_size: int
    ) -> tuple[list[T2ITask], int]:
        base = select(T2ITask).where(T2ITask.template_code == template_code)
        total_row = await self.session.execute(
            select(func.count()).select_from(base.subquery())
        )
        total = int(total_row.scalar_one() or 0)
        offset = (page - 1) * page_size
        rows = await self.session.execute(
            base.order_by(T2ITask.updated_at.desc()).limit(page_size).offset(offset)
        )
        return list(rows.scalars().all()), total

    async def save(self, task: T2ITask) -> None:
        self.session.add(task)
        await self.session.commit()

    async def update(self, task: T2ITask) -> None:
        await self.session.commit()


class T2IImageRepo:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def find_by_id(self, image_id: str) -> T2IImage | None:
        r = await self.session.execute(select(T2IImage).where(T2IImage.id == image_id))
        return r.scalar_one_or_none()

    async def list_by_task(self, task_id: str) -> list[T2IImage]:
        r = await self.session.execute(
            select(T2IImage)
            .where(T2IImage.task_id == task_id)
            .order_by(T2IImage.created_at.desc())
        )
        return list(r.scalars().all())

    async def has_generating(self, task_id: str) -> bool:
        r = await self.session.execute(
            select(func.count(T2IImage.id)).where(
                T2IImage.task_id == task_id, T2IImage.status == "generating"
            )
        )
        return int(r.scalar_one() or 0) > 0

    async def save(self, image: T2IImage) -> None:
        self.session.add(image)
        await self.session.commit()

    async def update(self, image: T2IImage) -> None:
        await self.session.commit()

    async def delete(self, image: T2IImage) -> None:
        await self.session.delete(image)
        await self.session.commit()


class T2IImageBlobRepo:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_bytes(self, image_id: str) -> tuple[bytes, str | None] | None:
        r = await self.session.execute(
            select(T2IImageBlob.bytes_, T2IImage.mime)
            .join(T2IImage, T2IImage.id == T2IImageBlob.image_id)
            .where(T2IImageBlob.image_id == image_id)
        )
        row = r.first()
        if row is None:
            return None
        return bytes(row[0]), row[1]

    async def save(self, blob: T2IImageBlob) -> None:
        self.session.add(blob)
        await self.session.commit()

    async def delete_by_image(self, image_id: str) -> None:
        await self.session.execute(
            delete(T2IImageBlob).where(T2IImageBlob.image_id == image_id)
        )
        await self.session.commit()

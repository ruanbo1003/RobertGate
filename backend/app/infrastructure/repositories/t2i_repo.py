from __future__ import annotations

from sqlalchemy import delete, func, select

from app.domain.models.t2i import T2IImage, T2IImageBlob, T2ITask, T2ITemplate
from app.infrastructure.repositories.base import SqlRepo


class T2ITemplateRepo(SqlRepo[T2ITemplate]):
    model = T2ITemplate

    async def find_by_code(self, code: str) -> T2ITemplate | None:
        return await self._one(select(T2ITemplate).where(T2ITemplate.code == code))

    async def list_all(self) -> list[T2ITemplate]:
        return await self._all(
            select(T2ITemplate).order_by(
                T2ITemplate.order_index.asc(), T2ITemplate.created_at.asc()
            )
        )


class T2ITaskRepo(SqlRepo[T2ITask]):
    model = T2ITask

    async def find_by_hash(self, keywords_hash: str) -> T2ITask | None:
        return await self._one(
            select(T2ITask).where(T2ITask.keywords_hash == keywords_hash)
        )

    async def count_by_template_code(self, template_code: str) -> int:
        return await self._count(
            select(func.count(T2ITask.id)).where(
                T2ITask.template_code == template_code
            )
        )

    async def list_by_template(
        self, template_code: str, page: int, page_size: int
    ) -> tuple[list[T2ITask], int]:
        base = select(T2ITask).where(T2ITask.template_code == template_code)
        total = await self._count(select(func.count()).select_from(base.subquery()))
        offset = (page - 1) * page_size
        rows = await self._all(
            base.order_by(T2ITask.updated_at.desc()).limit(page_size).offset(offset)
        )
        return rows, total


class T2IImageRepo(SqlRepo[T2IImage]):
    model = T2IImage

    async def list_by_task(self, task_id: str) -> list[T2IImage]:
        return await self._all(
            select(T2IImage)
            .where(T2IImage.task_id == task_id)
            .order_by(T2IImage.created_at.desc())
        )

    async def has_generating(self, task_id: str) -> bool:
        count = await self._count(
            select(func.count(T2IImage.id)).where(
                T2IImage.task_id == task_id, T2IImage.status == "generating"
            )
        )
        return count > 0


class T2IImageBlobRepo(SqlRepo[T2IImageBlob]):
    model = T2IImageBlob

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

    async def delete_by_image(self, image_id: str) -> None:
        await self.session.execute(
            delete(T2IImageBlob).where(T2IImageBlob.image_id == image_id)
        )

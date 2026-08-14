"""相册 service：目录扫描 + 缩略图生成。

Pillow 处理是阻塞 IO，同步私有方法通过 asyncio.to_thread 移出事件循环。
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from PIL import Image, ImageOps

from app.core.exceptions import ServerException

logger = logging.getLogger(__name__)

SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}


class GalleryService:
    def __init__(self, photo_dir: Path, thumb_dir: Path, thumb_width: int) -> None:
        self._photo_dir = photo_dir
        self._thumb_dir = thumb_dir
        self._thumb_width = thumb_width
        self._dimension_cache: dict[str, tuple[int, int]] = {}

    async def list_photos(self) -> dict:
        return await asyncio.to_thread(self._list_photos_sync)

    # ---------- 同步私有方法（阻塞 IO / Pillow） ----------

    def _list_photos_sync(self) -> dict:
        if not self._photo_dir.exists():
            raise ServerException(5001, "照片目录不存在")

        if not self._photo_dir.is_dir():
            raise ServerException(5002, "照片目录读取失败")

        try:
            files = sorted(
                [
                    f
                    for f in self._photo_dir.iterdir()
                    if f.is_file()
                    and f.suffix.lower() in SUPPORTED_EXTENSIONS
                    and f.name != "thumbs"
                ],
                key=lambda f: f.stat().st_mtime,
                reverse=True,
            )
        except OSError:
            raise ServerException(5002, "照片目录读取失败")

        photos = []
        for f in files:
            width, height = self._get_dimensions(f)
            self._ensure_thumbnail(f)
            photos.append(
                {
                    "filename": f.name,
                    "url": f"/photos/{f.name}",
                    "thumbnail_url": f"/photos/thumbs/{f.name}",
                    "width": width,
                    "height": height,
                }
            )

        return {"photos": photos, "total": len(photos)}

    def _load_and_orient(self, filepath: Path) -> Image.Image:
        """Open image and apply EXIF orientation to pixel data."""
        img = Image.open(filepath)
        img.load()
        oriented = ImageOps.exif_transpose(img)
        if oriented is not img:
            img.close()
        return oriented

    def _get_dimensions(self, filepath: Path) -> tuple[int, int]:
        key = str(filepath)
        if key in self._dimension_cache:
            return self._dimension_cache[key]
        try:
            img = self._load_and_orient(filepath)
            dims = img.size
            img.close()
            self._dimension_cache[key] = dims
            return dims
        except OSError:
            logger.warning("读取图片尺寸失败: %s", filepath, exc_info=True)
            return (0, 0)

    def _ensure_thumbnail(self, filepath: Path) -> None:
        """Generate thumbnail if it doesn't exist."""
        thumb_path = self._thumb_dir / filepath.name
        if thumb_path.exists():
            return
        try:
            self._thumb_dir.mkdir(exist_ok=True)
            img = self._load_and_orient(filepath)
            ratio = self._thumb_width / img.width
            thumb_height = int(img.height * ratio)
            thumb = img.resize((self._thumb_width, thumb_height), Image.LANCZOS)
            img.close()
            if thumb.mode in ("RGBA", "P"):
                thumb = thumb.convert("RGB")
            thumb.save(thumb_path, quality=80)
            thumb.close()
        except OSError:
            logger.warning("生成缩略图失败: %s", filepath, exc_info=True)

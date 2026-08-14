"""相册 service：目录扫描 + 缩略图生成。

Pillow 处理是阻塞 IO，同步私有方法通过 asyncio.to_thread 移出事件循环。
"""

from __future__ import annotations

import asyncio
import logging
import os
import uuid
from pathlib import Path

from PIL import Image, ImageOps

from app.domain.errors import ServerException

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
        except Exception:
            # 单张坏图（如 Pillow 的 DecompressionBombError、非法尺寸导致的
            # ZeroDivisionError 等非 OSError 异常）只应降级，不能让整个相册
            # 列表跟着 500——同样记录日志，不静默吞掉。
            logger.warning("读取图片尺寸失败（非 OSError）: %s", filepath, exc_info=True)
            return (0, 0)

    def _ensure_thumbnail(self, filepath: Path) -> None:
        """Generate thumbnail if it doesn't exist.

        写入采用"临时文件 + os.replace 原子改名"：list_photos() 现在跑在
        线程池里（见 list_photos），并发请求可能同时给同一张缺缩略图的照片
        生成缩略图；直接写目标路径会被交叉写坏，且 exists() 检查会让坏文件
        永不重生成。每次生成用唯一临时文件名，即使并发也不会互相覆盖，最终
        只有已完整写好的文件会被原子地摆到目标路径上。
        """
        thumb_path = self._thumb_dir / filepath.name
        if thumb_path.exists():
            return
        # 后缀必须保留原扩展名（Pillow 靠文件名后缀推断保存格式），
        # 用 "~" 前缀 + uuid 标记为临时文件，方便识别/清理孤儿文件。
        tmp_path = self._thumb_dir / f"~{uuid.uuid4().hex}-{filepath.name}"
        try:
            self._thumb_dir.mkdir(exist_ok=True)
            img = self._load_and_orient(filepath)
            ratio = self._thumb_width / img.width
            thumb_height = int(img.height * ratio)
            thumb = img.resize((self._thumb_width, thumb_height), Image.LANCZOS)
            img.close()
            if thumb.mode in ("RGBA", "P"):
                thumb = thumb.convert("RGB")
            thumb.save(tmp_path, quality=80)
            thumb.close()
            os.replace(tmp_path, thumb_path)
        except OSError:
            logger.warning("生成缩略图失败: %s", filepath, exc_info=True)
        except Exception:
            logger.warning("生成缩略图失败（非 OSError）: %s", filepath, exc_info=True)
        finally:
            tmp_path.unlink(missing_ok=True)

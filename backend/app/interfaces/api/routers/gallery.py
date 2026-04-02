import os
from pathlib import Path

from fastapi import APIRouter
from PIL import Image

from app.interfaces.api.response import error, success

router = APIRouter(prefix="/gallery", tags=["gallery"])

PHOTO_DIR = Path("/home/ubuntu/photos")
SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}

_dimension_cache: dict[str, tuple[int, int]] = {}


def _get_dimensions(filepath: Path) -> tuple[int, int]:
    key = str(filepath)
    if key in _dimension_cache:
        return _dimension_cache[key]
    try:
        with Image.open(filepath) as img:
            dims = img.size
        _dimension_cache[key] = dims
        return dims
    except Exception:
        return (0, 0)


@router.get("/photos")
async def list_photos():
    if not PHOTO_DIR.exists():
        return error(5001, "照片目录不存在")

    if not PHOTO_DIR.is_dir():
        return error(5002, "照片目录读取失败")

    try:
        files = sorted(
            [
                f
                for f in PHOTO_DIR.iterdir()
                if f.is_file() and f.suffix.lower() in SUPPORTED_EXTENSIONS
            ],
            key=lambda f: f.stat().st_mtime,
            reverse=True,
        )
    except OSError:
        return error(5002, "照片目录读取失败")

    photos = []
    for f in files:
        width, height = _get_dimensions(f)
        photos.append(
            {
                "filename": f.name,
                "url": f"/photos/{f.name}",
                "width": width,
                "height": height,
            }
        )

    return success({"photos": photos, "total": len(photos)})

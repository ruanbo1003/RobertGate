import os
from pathlib import Path

from fastapi import APIRouter
from PIL import Image, ImageOps

from app.interfaces.api.response import error, success

router = APIRouter(prefix="/gallery", tags=["gallery"])

PHOTO_DIR = Path(os.environ.get("PHOTO_DIR", "/home/ubuntu/photos"))
THUMB_DIR = PHOTO_DIR / "thumbs"
THUMB_WIDTH = 400
SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}

_dimension_cache: dict[str, tuple[int, int]] = {}


def _load_and_orient(filepath: Path) -> Image.Image:
    """Open image and apply EXIF orientation to pixel data."""
    img = Image.open(filepath)
    img.load()  # Force read all pixel data from disk
    oriented = ImageOps.exif_transpose(img)
    if oriented is not img:
        img.close()
    return oriented


def _get_dimensions(filepath: Path) -> tuple[int, int]:
    key = str(filepath)
    if key in _dimension_cache:
        return _dimension_cache[key]
    try:
        img = _load_and_orient(filepath)
        dims = img.size  # width, height after rotation
        img.close()
        _dimension_cache[key] = dims
        return dims
    except Exception:
        return (0, 0)


def _ensure_thumbnail(filepath: Path) -> None:
    """Generate thumbnail if it doesn't exist."""
    thumb_path = THUMB_DIR / filepath.name
    if thumb_path.exists():
        return
    try:
        THUMB_DIR.mkdir(exist_ok=True)
        img = _load_and_orient(filepath)
        ratio = THUMB_WIDTH / img.width
        thumb_height = int(img.height * ratio)
        thumb = img.resize((THUMB_WIDTH, thumb_height), Image.LANCZOS)
        img.close()
        if thumb.mode in ("RGBA", "P"):
            thumb = thumb.convert("RGB")
        thumb.save(thumb_path, quality=80)
        thumb.close()
    except Exception:
        pass


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
                if f.is_file()
                and f.suffix.lower() in SUPPORTED_EXTENSIONS
                and f.name != "thumbs"
            ],
            key=lambda f: f.stat().st_mtime,
            reverse=True,
        )
    except OSError:
        return error(5002, "照片目录读取失败")

    photos = []
    for f in files:
        width, height = _get_dimensions(f)
        _ensure_thumbnail(f)
        photos.append(
            {
                "filename": f.name,
                "url": f"/photos/{f.name}",
                "thumbnail_url": f"/photos/thumbs/{f.name}",
                "width": width,
                "height": height,
            }
        )

    return success({"photos": photos, "total": len(photos)})

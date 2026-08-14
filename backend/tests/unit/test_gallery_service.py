from pathlib import Path

import pytest
from PIL import Image

from app.core.exceptions import ServerException
from app.service.gallery_service import GalleryService


def _create_test_image(directory: Path, name: str, width: int, height: int) -> None:
    img = Image.new("RGB", (width, height), color="red")
    img.save(directory / name)


def _make_service(tmp_path: Path, thumb_width: int = 400) -> tuple[GalleryService, Path, Path]:
    photo_dir = tmp_path / "photos"
    photo_dir.mkdir()
    thumb_dir = photo_dir / "thumbs"
    return (
        GalleryService(photo_dir=photo_dir, thumb_dir=thumb_dir, thumb_width=thumb_width),
        photo_dir,
        thumb_dir,
    )


@pytest.mark.asyncio
async def test_list_photos_success(tmp_path):
    service, photo_dir, _ = _make_service(tmp_path)
    _create_test_image(photo_dir, "photo1.jpg", 4032, 3024)
    _create_test_image(photo_dir, "photo2.png", 1080, 1920)

    result = await service.list_photos()

    assert result["total"] == 2
    names = {p["filename"] for p in result["photos"]}
    assert names == {"photo1.jpg", "photo2.png"}
    for p in result["photos"]:
        assert p["url"] == f"/photos/{p['filename']}"
        assert p["thumbnail_url"] == f"/photos/thumbs/{p['filename']}"
        assert p["width"] > 0
        assert p["height"] > 0


@pytest.mark.asyncio
async def test_list_photos_empty_directory(tmp_path):
    service, _, _ = _make_service(tmp_path)

    result = await service.list_photos()

    assert result == {"photos": [], "total": 0}


@pytest.mark.asyncio
async def test_list_photos_directory_missing(tmp_path):
    photo_dir = tmp_path / "does-not-exist"
    thumb_dir = photo_dir / "thumbs"
    service = GalleryService(photo_dir=photo_dir, thumb_dir=thumb_dir, thumb_width=400)

    with pytest.raises(ServerException) as exc:
        await service.list_photos()

    assert exc.value.code == 5001
    assert exc.value.message == "照片目录不存在"


@pytest.mark.asyncio
async def test_list_photos_directory_not_readable(tmp_path):
    # 用一个"文件"当作 photo_dir 传入，触发 is_dir() 为 False 的分支。
    not_a_dir = tmp_path / "not-a-dir"
    not_a_dir.write_text("x")
    service = GalleryService(
        photo_dir=not_a_dir, thumb_dir=tmp_path / "thumbs", thumb_width=400
    )

    with pytest.raises(ServerException) as exc:
        await service.list_photos()

    assert exc.value.code == 5002
    assert exc.value.message == "照片目录读取失败"


@pytest.mark.asyncio
async def test_list_photos_generates_thumbnail(tmp_path):
    service, photo_dir, thumb_dir = _make_service(tmp_path, thumb_width=200)
    _create_test_image(photo_dir, "photo1.jpg", 800, 600)

    await service.list_photos()

    thumb_path = thumb_dir / "photo1.jpg"
    assert thumb_path.exists()
    with Image.open(thumb_path) as thumb:
        assert thumb.width == 200
        assert thumb.height == 150


@pytest.mark.asyncio
async def test_list_photos_dimension_cache_hit(tmp_path):
    service, photo_dir, _ = _make_service(tmp_path)
    _create_test_image(photo_dir, "photo1.jpg", 800, 600)

    await service.list_photos()
    assert len(service._dimension_cache) == 1

    # 第二次调用直接命中缓存，即便文件被替换成不同尺寸也返回缓存值。
    _create_test_image(photo_dir, "photo1.jpg", 100, 100)
    result = await service.list_photos()

    photo = result["photos"][0]
    assert photo["width"] == 800
    assert photo["height"] == 600

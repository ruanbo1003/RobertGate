import asyncio
from pathlib import Path

import pytest
from PIL import Image

from app.domain.errors import ServerException
from app.application.services.gallery_service import GalleryService
import app.application.services.gallery_service as gallery_service_module


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
    names = {p.filename for p in result["photos"]}
    assert names == {"photo1.jpg", "photo2.png"}
    for p in result["photos"]:
        assert p.url == f"/photos/{p.filename}"
        assert p.thumbnail_url == f"/photos/thumbs/{p.filename}"
        assert p.width > 0
        assert p.height > 0


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
    assert photo.width == 800
    assert photo.height == 600


# ---------- Finding 1：非 OSError 异常必须降级而非让整个接口 5000 ----------


@pytest.mark.asyncio
async def test_list_photos_degrades_on_non_oserror_pillow_exception(tmp_path, monkeypatch):
    """单张坏图触发非 OSError 异常（如 DecompressionBombError/ZeroDivisionError）时，
    列表整体仍应正常返回（尺寸记 0、跳过缩略图），不能让 500 波及整个接口。"""
    service, photo_dir, thumb_dir = _make_service(tmp_path)
    _create_test_image(photo_dir, "photo1.jpg", 800, 600)

    def _boom(self, filepath):
        raise Image.DecompressionBombError("image too large")

    monkeypatch.setattr(GalleryService, "_load_and_orient", _boom)

    result = await service.list_photos()

    assert result["total"] == 1
    photo = result["photos"][0]
    assert photo.width == 0
    assert photo.height == 0
    assert not (thumb_dir / "photo1.jpg").exists()


def test_get_dimensions_non_oserror_returns_zero(tmp_path, monkeypatch):
    service, photo_dir, _ = _make_service(tmp_path)
    _create_test_image(photo_dir, "photo1.jpg", 800, 600)

    def _boom(self, filepath):
        raise ValueError("corrupt pixel data")

    monkeypatch.setattr(GalleryService, "_load_and_orient", _boom)

    assert service._get_dimensions(photo_dir / "photo1.jpg") == (0, 0)


def test_ensure_thumbnail_non_oserror_skips_silently(tmp_path, monkeypatch):
    service, photo_dir, thumb_dir = _make_service(tmp_path)
    _create_test_image(photo_dir, "photo1.jpg", 800, 600)

    def _boom(self, filepath):
        raise ZeroDivisionError("width is zero")

    monkeypatch.setattr(GalleryService, "_load_and_orient", _boom)

    service._ensure_thumbnail(photo_dir / "photo1.jpg")

    assert not (thumb_dir / "photo1.jpg").exists()


# ---------- Finding 2：缩略图写入必须原子，避免并发交错写坏 ----------


@pytest.mark.asyncio
async def test_ensure_thumbnail_writes_via_tmp_file_then_atomic_replace(
    tmp_path, monkeypatch
):
    service, photo_dir, thumb_dir = _make_service(tmp_path, thumb_width=200)
    _create_test_image(photo_dir, "photo1.jpg", 800, 600)

    real_replace = gallery_service_module.os.replace
    captured: list[tuple[Path, Path]] = []

    def spy_replace(src, dst):
        src, dst = Path(src), Path(dst)
        captured.append((src, dst))
        assert src != dst, "必须先写临时文件，再原子改名到目标路径"
        assert src.exists()
        assert not dst.exists()
        return real_replace(src, dst)

    monkeypatch.setattr(gallery_service_module.os, "replace", spy_replace)

    await service.list_photos()

    assert len(captured) == 1
    tmp_src, final_dst = captured[0]
    assert final_dst == thumb_dir / "photo1.jpg"
    assert not tmp_src.exists()
    assert final_dst.exists()


@pytest.mark.asyncio
async def test_concurrent_list_photos_does_not_corrupt_thumbnail(tmp_path):
    """两个并发请求同时给同一张缺缩略图的照片生成缩略图，不应交错写坏文件，
    也不应留下孤儿临时文件。"""
    service, photo_dir, thumb_dir = _make_service(tmp_path, thumb_width=200)
    _create_test_image(photo_dir, "photo1.jpg", 800, 600)

    results = await asyncio.gather(
        service.list_photos(),
        service.list_photos(),
        service.list_photos(),
    )

    for r in results:
        assert r["total"] == 1

    thumb_path = thumb_dir / "photo1.jpg"
    assert thumb_path.exists()
    with Image.open(thumb_path) as thumb:
        thumb.load()  # 完整可解码，证明没有被并发写坏
        assert thumb.width == 200
        assert thumb.height == 150

    assert list(thumb_dir.glob("~*")) == []

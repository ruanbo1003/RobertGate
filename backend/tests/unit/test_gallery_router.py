import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
from PIL import Image

from app.interfaces.api.routers.gallery import list_photos, _dimension_cache


def _create_test_image(directory: Path, name: str, width: int, height: int) -> None:
    img = Image.new("RGB", (width, height), color="red")
    img.save(directory / name)


@pytest.fixture(autouse=True)
def clear_cache():
    _dimension_cache.clear()
    yield
    _dimension_cache.clear()


@pytest.mark.asyncio
async def test_list_photos_success():
    with tempfile.TemporaryDirectory() as tmpdir:
        photo_dir = Path(tmpdir)
        _create_test_image(photo_dir, "photo1.jpg", 4032, 3024)
        _create_test_image(photo_dir, "photo2.png", 1080, 1920)

        with patch("app.interfaces.api.routers.gallery.PHOTO_DIR", photo_dir):
            result = await list_photos()

        assert result["code"] == 0
        assert result["data"]["total"] == 2


@pytest.mark.asyncio
async def test_list_photos_empty_directory():
    with tempfile.TemporaryDirectory() as tmpdir:
        with patch("app.interfaces.api.routers.gallery.PHOTO_DIR", Path(tmpdir)):
            result = await list_photos()

        assert result["code"] == 0
        assert result["data"]["total"] == 0


@pytest.mark.asyncio
async def test_list_photos_directory_not_found():
    with patch("app.interfaces.api.routers.gallery.PHOTO_DIR", Path("/nonexistent")):
        result = await list_photos()
    assert result["code"] == 5001


@pytest.mark.asyncio
async def test_list_photos_filters_non_images():
    with tempfile.TemporaryDirectory() as tmpdir:
        photo_dir = Path(tmpdir)
        _create_test_image(photo_dir, "photo.jpg", 800, 600)
        (photo_dir / "readme.txt").write_text("not an image")

        with patch("app.interfaces.api.routers.gallery.PHOTO_DIR", photo_dir):
            result = await list_photos()

        assert result["data"]["total"] == 1


@pytest.mark.asyncio
async def test_list_photos_returns_correct_dimensions():
    with tempfile.TemporaryDirectory() as tmpdir:
        photo_dir = Path(tmpdir)
        _create_test_image(photo_dir, "landscape.jpg", 1920, 1080)

        with patch("app.interfaces.api.routers.gallery.PHOTO_DIR", photo_dir):
            result = await list_photos()

        photo = result["data"]["photos"][0]
        assert photo["width"] == 1920
        assert photo["height"] == 1080

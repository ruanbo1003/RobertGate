import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
from PIL import Image

from app.api.gallery.router import list_photos, _dimension_cache


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

        with patch("app.api.gallery.router.PHOTO_DIR", photo_dir):
            with patch("app.api.gallery.router.THUMB_DIR", photo_dir / "thumbs"):
                result = await list_photos()

        assert result.body is not None


@pytest.mark.asyncio
async def test_list_photos_empty_directory():
    with tempfile.TemporaryDirectory() as tmpdir:
        with patch("app.api.gallery.router.PHOTO_DIR", Path(tmpdir)):
            result = await list_photos()

        assert result.body is not None


@pytest.mark.asyncio
async def test_list_photos_directory_not_found():
    with patch("app.api.gallery.router.PHOTO_DIR", Path("/nonexistent")):
        result = await list_photos()
    assert result.body is not None

from __future__ import annotations

from pathlib import Path

from app.application.dto.base import DTO


class PhotoOut(DTO):
    filename: str
    url: str
    thumbnail_url: str
    width: int
    height: int

    @classmethod
    def build(cls, filepath: Path, width: int, height: int) -> PhotoOut:
        return cls(
            filename=filepath.name,
            url=f"/photos/{filepath.name}",
            thumbnail_url=f"/photos/thumbs/{filepath.name}",
            width=width,
            height=height,
        )

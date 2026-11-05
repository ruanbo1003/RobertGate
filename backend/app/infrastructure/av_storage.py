"""ai-videos 产物文件存储（本地磁盘，根目录 settings.AV_DATA_DIR）。

实现 application/services/av_queue.AvStorage 协议；所有相对路径限定在
根目录内（防目录穿越），absolute() 是文件路由与合成器取绝对路径的唯一入口。
"""

from __future__ import annotations

import logging
import shutil
from pathlib import Path

from app.infrastructure.av_compose import probe_duration as _probe

logger = logging.getLogger(__name__)


class FsAvStorage:
    def __init__(self, base_dir: Path) -> None:
        self._base = base_dir.resolve()
        self._base.mkdir(parents=True, exist_ok=True)

    def absolute(self, rel_path: str) -> Path:
        path = (self._base / rel_path).resolve()
        if not path.is_relative_to(self._base):
            raise ValueError(f"非法路径：{rel_path}")
        return path

    def save(self, rel_path: str, data: bytes) -> str:
        path = self.absolute(rel_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return rel_path

    def read(self, rel_path: str) -> bytes:
        return self.absolute(rel_path).read_bytes()

    def delete(self, rel_path: str) -> None:
        try:
            self.absolute(rel_path).unlink(missing_ok=True)
        except OSError:
            logger.warning("删除文件失败：%s", rel_path, exc_info=True)

    def delete_tree(self, rel_dir: str) -> None:
        try:
            path = self.absolute(rel_dir)
            if path.is_dir():
                shutil.rmtree(path, ignore_errors=True)
        except ValueError:
            logger.warning("删除目录失败：%s", rel_dir, exc_info=True)

    async def probe_duration(self, rel_path: str) -> float | None:
        return await _probe(self.absolute(rel_path))

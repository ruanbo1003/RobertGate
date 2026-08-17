import asyncio
import logging
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import text

from app.infrastructure.database.session import engine

logger = logging.getLogger(__name__)

# backend/ 目录（alembic.ini 所在）
_BACKEND_DIR = Path(__file__).resolve().parents[3]
_ALEMBIC_INI = _BACKEND_DIR / "alembic.ini"
assert _ALEMBIC_INI.exists(), f"alembic.ini not found: {_ALEMBIC_INI}"


async def wait_for_db(retries: int = 30, delay: float = 1.0) -> None:
    """轮询直到数据库可以响应 SELECT 1，用于处理 docker-compose 启动竞态。"""
    last_err: Exception | None = None
    for i in range(retries):
        try:
            async with engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
            return
        except Exception as e:  # noqa: BLE001
            last_err = e
            logger.info("等待数据库就绪... (%d/%d)", i + 1, retries)
            await asyncio.sleep(delay)
    raise RuntimeError(
        f"数据库在 {retries * delay:.0f}s 内未就绪"
    ) from last_err


def _run_upgrade_sync() -> None:
    config = Config(str(_ALEMBIC_INI))
    command.upgrade(config, "head")


async def run_migrations() -> None:
    """在线程池中执行 alembic upgrade head。

    env.py 里会自行 asyncio.run() 起一个新的事件循环运行 async 迁移，
    因此必须通过 to_thread 隔离，避免与 FastAPI 当前的事件循环冲突。
    """
    logger.info("运行数据库迁移 (alembic upgrade head) ...")
    await asyncio.to_thread(_run_upgrade_sync)
    logger.info("数据库迁移完成")

"""Seed script: create an admin user + a sample level with characters.

Usage (from backend/):
    uv run python -m scripts.seed_hanzi
    uv run python scripts/seed_hanzi.py

Idempotent: re-running only inserts what's missing.
"""

from __future__ import annotations

import asyncio
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

# 让脚本能直接用 `python scripts/seed_hanzi.py` 运行（而非只能 -m）
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select  # noqa: E402

from app.domain.models.hanzi import HanziCharacter, HanziLevel  # noqa: E402
from app.domain.models.user import User  # noqa: E402
from app.infrastructure.database.session import async_session  # noqa: E402
from app.infrastructure.security.password import BcryptHasher  # noqa: E402

ADMIN_USERNAME = "admin"
ADMIN_EMAIL = "admin@example.com"
ADMIN_PASSWORD = "admin123456"

SAMPLE_LEVEL = {
    "name": "启蒙 · Level 1",
    "description": "最基础的 10 个常用汉字",
    "order_index": 0,
}

SAMPLE_CHARACTERS = [
    ("人", "rén", ["人类", "人口", "大人", "人们"]),
    ("口", "kǒu", ["口水", "开口", "门口", "人口"]),
    ("大", "dà", ["大小", "大人", "大门", "大家"]),
    ("小", "xiǎo", ["小心", "小孩", "小时", "大小"]),
    ("上", "shàng", ["上面", "上班", "早上", "向上"]),
    ("下", "xià", ["下面", "下雨", "下班", "下午"]),
    ("山", "shān", ["山水", "山上", "高山", "山口"]),
    ("水", "shuǐ", ["水果", "喝水", "山水", "水口"]),
    ("日", "rì", ["日子", "生日", "日出", "今日"]),
    ("月", "yuè", ["月亮", "月光", "每月", "岁月"]),
]


async def ensure_admin() -> str:
    async with async_session() as session:
        existing = await session.scalar(
            select(User).where(User.username == ADMIN_USERNAME)
        )
        if existing:
            if existing.role != "admin":
                existing.role = "admin"
                await session.commit()
            print(f"[admin] already exists (id={existing.id}, role={existing.role})")
            return existing.id

        user = User(
            id=str(uuid.uuid4()),
            username=ADMIN_USERNAME,
            email=ADMIN_EMAIL,
            hashed_password=BcryptHasher().hash(ADMIN_PASSWORD),
            role="admin",
            created_at=datetime.now(timezone.utc),
        )
        session.add(user)
        await session.commit()
        print(
            f"[admin] created — username={ADMIN_USERNAME} "
            f"password={ADMIN_PASSWORD} email={ADMIN_EMAIL}"
        )
        return user.id


async def ensure_level_and_characters() -> None:
    async with async_session() as session:
        level = await session.scalar(
            select(HanziLevel).where(HanziLevel.name == SAMPLE_LEVEL["name"])
        )
        now = datetime.now(timezone.utc)
        if not level:
            level = HanziLevel(
                id=str(uuid.uuid4()),
                name=SAMPLE_LEVEL["name"],
                description=SAMPLE_LEVEL["description"],
                order_index=SAMPLE_LEVEL["order_index"],
                created_at=now,
                updated_at=now,
            )
            session.add(level)
            await session.flush()
            print(f"[level] created — {level.name} (id={level.id})")
        else:
            print(f"[level] already exists (id={level.id})")

        # 全局唯一 char，先查已存在的
        existing_chars = await session.scalars(
            select(HanziCharacter.char).where(
                HanziCharacter.char.in_([c[0] for c in SAMPLE_CHARACTERS])
            )
        )
        existing_set = set(existing_chars.all())

        added = 0
        for idx, (ch, py, words) in enumerate(SAMPLE_CHARACTERS):
            if ch in existing_set:
                continue
            session.add(
                HanziCharacter(
                    id=str(uuid.uuid4()),
                    level_id=level.id,
                    char=ch,
                    pinyin=py,
                    example_words=words,
                    order_index=idx,
                    created_at=now,
                    updated_at=now,
                )
            )
            added += 1
        await session.commit()
        print(f"[characters] +{added} added ({len(existing_set)} already existed)")


async def main() -> None:
    await ensure_admin()
    await ensure_level_and_characters()
    print("Done.")


if __name__ == "__main__":
    asyncio.run(main())

from __future__ import annotations

import asyncio
import re
import uuid
from datetime import datetime, timezone

from app.core.exceptions import ParamException
from app.models.hanzi_character import HanziCharacter
from app.models.hanzi_level import HanziLevel
from app.repository.hanzi_character_repo import HanziCharacterRepo
from app.repository.hanzi_level_repo import HanziLevelRepo
from app.service.ai_client import AIClient

HANZI_RE = re.compile(r"^[\u4e00-\u9fa5]$")
HANZI_EXTRACT_RE = re.compile(r"[\u4e00-\u9fa5]")
AI_CONCURRENCY = 5


def _iso(dt: datetime | None) -> str | None:
    return dt.isoformat() if dt else None


def _level_dict(level: HanziLevel, total: int) -> dict:
    return {
        "id": level.id,
        "name": level.name,
        "description": level.description,
        "order_index": level.order_index,
        "total": total,
        "created_at": _iso(level.created_at),
        "updated_at": _iso(level.updated_at),
    }


def _character_dict(c: HanziCharacter) -> dict:
    return {
        "id": c.id,
        "char": c.char,
        "pinyin": c.pinyin,
        "example_words": c.example_words or [],
        "order_index": c.order_index,
        "created_at": _iso(c.created_at),
        "updated_at": _iso(c.updated_at),
    }


def _extract_chars(text: str) -> list[str]:
    """从任意文本抽取汉字，按出现顺序去重。"""
    seen: set[str] = set()
    result: list[str] = []
    for ch in HANZI_EXTRACT_RE.findall(text):
        if ch not in seen:
            seen.add(ch)
            result.append(ch)
    return result


class AdminHanziService:
    def __init__(
        self,
        level_repo: HanziLevelRepo,
        character_repo: HanziCharacterRepo,
        ai: AIClient,
    ) -> None:
        self.level_repo = level_repo
        self.character_repo = character_repo
        self.ai = ai

    # ---------- Levels ----------

    async def list_levels(self) -> dict:
        levels = await self.level_repo.list_all()
        totals = await self.character_repo.count_by_levels([lv.id for lv in levels])
        return {"levels": [_level_dict(lv, totals.get(lv.id, 0)) for lv in levels]}

    async def create_level(
        self, name: str, description: str | None, order_index: int
    ) -> dict:
        if await self.level_repo.find_by_name(name):
            raise ParamException(2011, "级别名称已存在")

        now = datetime.now(timezone.utc)
        level = HanziLevel(
            id=str(uuid.uuid4()),
            name=name,
            description=description,
            order_index=order_index,
            created_at=now,
            updated_at=now,
        )
        await self.level_repo.save(level)
        return _level_dict(level, 0)

    async def update_level(
        self,
        level_id: str,
        name: str | None,
        description: str | None,
        description_set: bool,
        order_index: int | None,
    ) -> dict:
        level = await self.level_repo.find_by_id(level_id)
        if not level:
            raise ParamException(2010, "级别不存在")

        if name is not None and name != level.name:
            duplicate = await self.level_repo.find_by_name(name)
            if duplicate and duplicate.id != level_id:
                raise ParamException(2011, "级别名称已存在")
            level.name = name

        if description_set:
            level.description = description

        if order_index is not None:
            level.order_index = order_index

        level.updated_at = datetime.now(timezone.utc)
        await self.level_repo.update(level)

        total = await self.character_repo.count_by_level(level_id)
        return _level_dict(level, total)

    async def delete_level(self, level_id: str) -> None:
        level = await self.level_repo.find_by_id(level_id)
        if not level:
            raise ParamException(2010, "级别不存在")

        total = await self.character_repo.count_by_level(level_id)
        if total > 0:
            raise ParamException(2012, "级别下仍有字条，请先清空")

        await self.level_repo.delete(level)

    # ---------- Characters ----------

    async def list_characters(self, level_id: str) -> dict:
        level = await self.level_repo.find_by_id(level_id)
        if not level:
            raise ParamException(2010, "级别不存在")
        characters = await self.character_repo.list_by_level(level_id)
        return {
            "level": {
                "id": level.id,
                "name": level.name,
                "description": level.description,
                "order_index": level.order_index,
            },
            "characters": [_character_dict(c) for c in characters],
        }

    async def create_character(
        self,
        level_id: str,
        char: str,
        pinyin: str,
        example_words: list[str] | None,
        order_index: int | None,
    ) -> dict:
        level = await self.level_repo.find_by_id(level_id)
        if not level:
            raise ParamException(2010, "级别不存在")

        if await self.character_repo.find_by_char(char):
            raise ParamException(2011, "该字已存在（全局唯一）")

        if order_index is None:
            order_index = await self.character_repo.max_order_index(level_id) + 1

        now = datetime.now(timezone.utc)
        character = HanziCharacter(
            id=str(uuid.uuid4()),
            level_id=level_id,
            char=char,
            pinyin=pinyin,
            example_words=example_words or [],
            order_index=order_index,
            created_at=now,
            updated_at=now,
        )
        await self.character_repo.save(character)
        return _character_dict(character)

    async def ai_add(self, level_id: str, text: str) -> dict:
        """从文本抽取汉字，用 AI 生成拼音+例词，批量入库。"""
        level = await self.level_repo.find_by_id(level_id)
        if not level:
            raise ParamException(2010, "级别不存在")

        chars = _extract_chars(text)
        if not chars:
            return {"ok": 0, "added": [], "skipped": [], "failed": []}

        existing = await self.character_repo.existing_chars(chars)
        skipped = [{"char": c, "reason": "已存在"} for c in chars if c in existing]
        to_generate = [c for c in chars if c not in existing]

        # 并发调 AI，最多 AI_CONCURRENCY 个 in-flight
        sem = asyncio.Semaphore(AI_CONCURRENCY)

        async def fetch(char: str) -> tuple[str, dict | Exception]:
            async with sem:
                try:
                    info = await self.ai.character_info(char)
                    return char, info
                except Exception as e:  # noqa: BLE001
                    return char, e

        results = await asyncio.gather(*(fetch(c) for c in to_generate))

        added: list[dict] = []
        failed: list[dict] = []
        to_insert: list[HanziCharacter] = []
        next_order = await self.character_repo.max_order_index(level_id) + 1
        now = datetime.now(timezone.utc)

        for char, info in results:
            if isinstance(info, Exception):
                failed.append({"char": char, "reason": f"AI 服务不可用: {info}"})
                continue
            pinyin = str(info.get("pinyin") or "").strip()
            words_raw = info.get("words") or []
            words = [str(w).strip() for w in words_raw if str(w).strip()][:4]
            if not pinyin or not words:
                failed.append({"char": char, "reason": "AI 返回格式不完整"})
                continue
            character = HanziCharacter(
                id=str(uuid.uuid4()),
                level_id=level_id,
                char=char,
                pinyin=pinyin,
                example_words=words,
                order_index=next_order,
                created_at=now,
                updated_at=now,
            )
            to_insert.append(character)
            added.append(_character_dict(character))
            next_order += 1

        if to_insert:
            await self.character_repo.save_many(to_insert)

        return {
            "ok": len(added),
            "added": added,
            "skipped": skipped,
            "failed": failed,
        }

    async def update_character(
        self,
        character_id: str,
        char: str | None,
        pinyin: str | None,
        example_words: list[str] | None,
        example_words_set: bool,
        order_index: int | None,
    ) -> dict:
        character = await self.character_repo.find_by_id(character_id)
        if not character:
            raise ParamException(2010, "字条不存在")

        if char is not None and char != character.char:
            duplicate = await self.character_repo.find_by_char(char)
            if duplicate and duplicate.id != character_id:
                raise ParamException(2011, "该字已存在（全局唯一）")
            character.char = char

        if pinyin is not None:
            character.pinyin = pinyin

        if example_words_set:
            character.example_words = example_words or []

        if order_index is not None:
            character.order_index = order_index

        character.updated_at = datetime.now(timezone.utc)
        await self.character_repo.update(character)
        return _character_dict(character)

    async def delete_character(self, character_id: str) -> None:
        character = await self.character_repo.find_by_id(character_id)
        if not character:
            raise ParamException(2010, "字条不存在")
        await self.character_repo.delete(character)

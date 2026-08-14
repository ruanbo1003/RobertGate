from __future__ import annotations

import asyncio
from datetime import datetime

from app.application.ports import AIClient
from app.domain.errors import ParamException, codes, ensure_found
from app.domain.models.hanzi import HanziCharacter, HanziLevel, extract_hanzi
from app.domain.repositories.uow import UnitOfWork

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


class AdminHanziService:
    def __init__(self, uow: UnitOfWork, ai: AIClient) -> None:
        self.uow = uow
        self.ai = ai

    # ---------- Levels ----------

    async def list_levels(self) -> dict:
        levels = await self.uow.hanzi_levels.list_all()
        totals = await self.uow.hanzi_characters.count_by_levels(
            [lv.id for lv in levels]
        )
        return {"levels": [_level_dict(lv, totals.get(lv.id, 0)) for lv in levels]}

    async def create_level(
        self, name: str, description: str | None, order_index: int
    ) -> dict:
        if await self.uow.hanzi_levels.find_by_name(name):
            raise ParamException(codes.HANZI_DUPLICATE, "级别名称已存在")

        level = HanziLevel.new(name, description, order_index)
        self.uow.hanzi_levels.add(level)
        await self.uow.commit()
        return _level_dict(level, 0)

    async def update_level(
        self,
        level_id: str,
        name: str | None,
        description: str | None,
        description_set: bool,
        order_index: int | None,
    ) -> dict:
        level = ensure_found(
            await self.uow.hanzi_levels.find_by_id(level_id),
            codes.HANZI_NOT_FOUND,
            "级别不存在",
        )

        if name is not None and name != level.name:
            duplicate = await self.uow.hanzi_levels.find_by_name(name)
            if duplicate and duplicate.id != level_id:
                raise ParamException(codes.HANZI_DUPLICATE, "级别名称已存在")
            level.name = name

        if description_set:
            level.description = description

        if order_index is not None:
            level.order_index = order_index

        level.touch()
        await self.uow.commit()

        total = await self.uow.hanzi_characters.count_by_level(level_id)
        return _level_dict(level, total)

    async def delete_level(self, level_id: str) -> None:
        level = ensure_found(
            await self.uow.hanzi_levels.find_by_id(level_id),
            codes.HANZI_NOT_FOUND,
            "级别不存在",
        )

        total = await self.uow.hanzi_characters.count_by_level(level_id)
        if total > 0:
            raise ParamException(codes.HANZI_LEVEL_NOT_EMPTY, "级别下仍有字条，请先清空")

        await self.uow.hanzi_levels.delete(level)
        await self.uow.commit()

    # ---------- Characters ----------

    async def list_characters(self, level_id: str) -> dict:
        level = ensure_found(
            await self.uow.hanzi_levels.find_by_id(level_id),
            codes.HANZI_NOT_FOUND,
            "级别不存在",
        )
        characters = await self.uow.hanzi_characters.list_by_level(level_id)
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
        level = ensure_found(
            await self.uow.hanzi_levels.find_by_id(level_id),
            codes.HANZI_NOT_FOUND,
            "级别不存在",
        )

        if await self.uow.hanzi_characters.find_by_char(char):
            raise ParamException(codes.HANZI_DUPLICATE, "该字已存在（全局唯一）")

        if order_index is None:
            order_index = await self.uow.hanzi_characters.max_order_index(level_id) + 1

        character = HanziCharacter.new(
            level_id, char, pinyin, example_words, order_index
        )
        self.uow.hanzi_characters.add(character)
        await self.uow.commit()
        return _character_dict(character)

    async def ai_add(self, level_id: str, text: str) -> dict:
        """从文本抽取汉字，用 AI 生成拼音+例词，批量入库。"""
        level = ensure_found(
            await self.uow.hanzi_levels.find_by_id(level_id),
            codes.HANZI_NOT_FOUND,
            "级别不存在",
        )

        chars = extract_hanzi(text)
        if not chars:
            return {"ok": 0, "added": [], "skipped": [], "failed": []}

        existing = await self.uow.hanzi_characters.existing_chars(chars)
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
        next_order = await self.uow.hanzi_characters.max_order_index(level_id) + 1

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
            character = HanziCharacter.new(
                level_id, char, pinyin, words, next_order
            )
            to_insert.append(character)
            added.append(_character_dict(character))
            next_order += 1

        if to_insert:
            self.uow.hanzi_characters.add_many(to_insert)
            await self.uow.commit()

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
        character = ensure_found(
            await self.uow.hanzi_characters.find_by_id(character_id),
            codes.HANZI_NOT_FOUND,
            "字条不存在",
        )

        if char is not None and char != character.char:
            duplicate = await self.uow.hanzi_characters.find_by_char(char)
            if duplicate and duplicate.id != character_id:
                raise ParamException(codes.HANZI_DUPLICATE, "该字已存在（全局唯一）")
            character.char = char

        if pinyin is not None:
            character.pinyin = pinyin

        if example_words_set:
            character.example_words = example_words or []

        if order_index is not None:
            character.order_index = order_index

        character.touch()
        await self.uow.commit()
        return _character_dict(character)

    async def delete_character(self, character_id: str) -> None:
        character = ensure_found(
            await self.uow.hanzi_characters.find_by_id(character_id),
            codes.HANZI_NOT_FOUND,
            "字条不存在",
        )
        await self.uow.hanzi_characters.delete(character)
        await self.uow.commit()

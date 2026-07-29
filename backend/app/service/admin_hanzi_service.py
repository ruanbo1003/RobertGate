from __future__ import annotations

import re
import uuid
from datetime import datetime, timezone

from app.core.exceptions import ParamException
from app.models.hanzi_character import HanziCharacter
from app.models.hanzi_level import HanziLevel
from app.repository.hanzi_character_repo import HanziCharacterRepo
from app.repository.hanzi_level_repo import HanziLevelRepo

HANZI_RE = re.compile(r"^[\u4e00-\u9fa5]$")


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
        "meaning": c.meaning,
        "order_index": c.order_index,
        "created_at": _iso(c.created_at),
        "updated_at": _iso(c.updated_at),
    }


class AdminHanziService:
    def __init__(
        self,
        level_repo: HanziLevelRepo,
        character_repo: HanziCharacterRepo,
    ) -> None:
        self.level_repo = level_repo
        self.character_repo = character_repo

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
        meaning: str | None,
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
            meaning=meaning,
            order_index=order_index,
            created_at=now,
            updated_at=now,
        )
        await self.character_repo.save(character)
        return _character_dict(character)

    async def batch_import(
        self, level_id: str, items: list[dict]
    ) -> dict:
        level = await self.level_repo.find_by_id(level_id)
        if not level:
            raise ParamException(2010, "级别不存在")

        # 1) validate format + collect chars for global-unique check
        prepared: list[dict] = []
        failed: list[dict] = []
        seen_in_batch: set[str] = set()
        for it in items:
            char = (it.get("char") or "").strip()
            pinyin = (it.get("pinyin") or "").strip()
            meaning = it.get("meaning")
            if isinstance(meaning, str):
                meaning = meaning.strip() or None
            if not char or not HANZI_RE.match(char):
                failed.append({"char": char, "reason": "char 必须为单个汉字"})
                continue
            if not pinyin:
                failed.append({"char": char, "reason": "pinyin 不能为空"})
                continue
            if char in seen_in_batch:
                failed.append({"char": char, "reason": "批次内重复"})
                continue
            seen_in_batch.add(char)
            prepared.append({"char": char, "pinyin": pinyin, "meaning": meaning})

        # 2) global uniqueness check via DB
        if prepared:
            existing = await self.character_repo.existing_chars(
                [p["char"] for p in prepared]
            )
        else:
            existing = set()

        # 3) allocate order_index from max+1
        next_order = await self.character_repo.max_order_index(level_id) + 1
        now = datetime.now(timezone.utc)
        to_insert: list[HanziCharacter] = []
        for p in prepared:
            if p["char"] in existing:
                failed.append({"char": p["char"], "reason": "已存在（全局唯一）"})
                continue
            to_insert.append(
                HanziCharacter(
                    id=str(uuid.uuid4()),
                    level_id=level_id,
                    char=p["char"],
                    pinyin=p["pinyin"],
                    meaning=p["meaning"],
                    order_index=next_order,
                    created_at=now,
                    updated_at=now,
                )
            )
            next_order += 1

        if to_insert:
            await self.character_repo.save_many(to_insert)

        return {"ok": len(to_insert), "failed": failed}

    async def update_character(
        self,
        character_id: str,
        char: str | None,
        pinyin: str | None,
        meaning: str | None,
        meaning_set: bool,
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

        if meaning_set:
            character.meaning = meaning

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

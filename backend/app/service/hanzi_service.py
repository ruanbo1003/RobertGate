from __future__ import annotations

import uuid
from datetime import datetime, timezone

from app.core.exceptions import ParamException
from app.domain.models.hanzi import HanziUserProgress
from app.infrastructure.repositories.hanzi_character_repo import HanziCharacterRepo
from app.infrastructure.repositories.hanzi_level_repo import HanziLevelRepo
from app.infrastructure.repositories.hanzi_progress_repo import HanziProgressRepo
from app.service.ai_client import AIClient


def _iso(dt: datetime | None) -> str | None:
    return dt.isoformat() if dt else None


class HanziService:
    """用户侧：查看级别、字表、切换学习状态。"""

    def __init__(
        self,
        level_repo: HanziLevelRepo,
        character_repo: HanziCharacterRepo,
        progress_repo: HanziProgressRepo,
        ai: AIClient,
    ) -> None:
        self.level_repo = level_repo
        self.character_repo = character_repo
        self.progress_repo = progress_repo
        self.ai = ai

    async def list_levels_with_progress(self, user_id: str) -> dict:
        levels = await self.level_repo.list_all()
        level_ids = [lv.id for lv in levels]
        totals = await self.character_repo.count_by_levels(level_ids)
        learned = await self.progress_repo.learned_count_by_levels(user_id, level_ids)
        return {
            "levels": [
                {
                    "id": lv.id,
                    "name": lv.name,
                    "description": lv.description,
                    "order_index": lv.order_index,
                    "total": totals.get(lv.id, 0),
                    "learned": learned.get(lv.id, 0),
                    "created_at": _iso(lv.created_at),
                    "updated_at": _iso(lv.updated_at),
                }
                for lv in levels
            ]
        }

    async def list_characters_for_user(self, user_id: str, level_id: str) -> dict:
        level = await self.level_repo.find_by_id(level_id)
        if not level:
            raise ParamException(2010, "级别不存在")

        characters = await self.character_repo.list_by_level(level_id)
        progress_map = await self.progress_repo.progress_map_by_level(
            user_id, level_id
        )
        return {
            "level": {
                "id": level.id,
                "name": level.name,
                "description": level.description,
                "order_index": level.order_index,
            },
            "characters": [
                {
                    "id": c.id,
                    "char": c.char,
                    "pinyin": c.pinyin,
                    "example_words": c.example_words or [],
                    "order_index": c.order_index,
                    "learned": c.id in progress_map,
                    "learned_at": _iso(
                        progress_map[c.id].learned_at if c.id in progress_map else None
                    ),
                }
                for c in characters
            ],
        }

    async def update_progress(
        self, user_id: str, character_id: str, learned: bool
    ) -> dict:
        character = await self.character_repo.find_by_id(character_id)
        if not character:
            raise ParamException(2010, "字条不存在")

        existing = await self.progress_repo.find(user_id, character_id)
        if learned:
            if existing:
                return {
                    "character_id": character_id,
                    "learned": True,
                    "learned_at": _iso(existing.learned_at),
                }
            now = datetime.now(timezone.utc)
            progress = HanziUserProgress(
                id=str(uuid.uuid4()),
                user_id=user_id,
                character_id=character_id,
                learned_at=now,
            )
            await self.progress_repo.save(progress)
            return {
                "character_id": character_id,
                "learned": True,
                "learned_at": _iso(now),
            }

        if existing:
            await self.progress_repo.delete(existing)
        return {
            "character_id": character_id,
            "learned": False,
            "learned_at": None,
        }

    async def generate_practice_text(self, user_id: str, level_id: str) -> dict:
        level = await self.level_repo.find_by_id(level_id)
        if not level:
            raise ParamException(2010, "级别不存在")

        characters = await self.character_repo.list_by_level(level_id)
        progress_map = await self.progress_repo.progress_map_by_level(
            user_id, level_id
        )
        learned_chars = [c.char for c in characters if c.id in progress_map]

        if len(learned_chars) < 3:
            raise ParamException(
                2013,
                f"至少学完 3 个字才能开始组合练习（当前 {len(learned_chars)}）",
            )

        try:
            raw = await self.ai.practice_text(learned_chars)
        except Exception as e:
            raise ParamException(5000, f"AI 生成失败：{e}") from e

        text = str(raw.get("text") or "").strip()
        if not text:
            raise ParamException(5000, "AI 返回文本为空")

        annotations_raw = raw.get("annotations") or []
        annotations: list[dict] = []
        if isinstance(annotations_raw, list):
            for item in annotations_raw:
                if not isinstance(item, dict):
                    continue
                ch = str(item.get("char") or "").strip()
                py = str(item.get("pinyin") or "").strip()
                if ch and py:
                    annotations.append({"char": ch, "pinyin": py})

        new_chars_raw = raw.get("new_chars") or []
        new_chars = (
            [str(c).strip() for c in new_chars_raw if str(c).strip()]
            if isinstance(new_chars_raw, list)
            else []
        )

        return {"text": text, "annotations": annotations, "new_chars": new_chars}

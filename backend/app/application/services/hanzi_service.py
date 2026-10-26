from __future__ import annotations

from app.application.dto.hanzi import (
    CharacterForUser,
    LevelBrief,
    LevelForUser,
    ProgressOut,
)
from app.application.ports import AIClient
from app.application.services._ai import ai_call
from app.domain.errors import ParamException, codes, ensure_found
from app.domain.models.hanzi import HanziUserProgress
from app.domain.repositories.uow import UnitOfWork


class HanziService:
    """用户侧：查看级别、字表、切换学习状态。"""

    def __init__(self, uow: UnitOfWork, ai: AIClient) -> None:
        self.uow = uow
        self.ai = ai

    async def list_levels_with_progress(self, user_id: str) -> dict:
        levels = await self.uow.hanzi_levels.list_all()
        level_ids = [lv.id for lv in levels]
        totals = await self.uow.hanzi_characters.count_by_levels(level_ids)
        learned = await self.uow.hanzi_progress.learned_count_by_levels(
            user_id, level_ids
        )
        return {
            "levels": [
                LevelForUser.build(lv, totals.get(lv.id, 0), learned.get(lv.id, 0))
                for lv in levels
            ]
        }

    async def list_characters_for_user(self, user_id: str, level_id: str) -> dict:
        level = ensure_found(
            await self.uow.hanzi_levels.find_by_id(level_id),
            codes.HANZI_NOT_FOUND,
            "级别不存在",
        )

        characters = await self.uow.hanzi_characters.list_by_level(level_id)
        progress_map = await self.uow.hanzi_progress.progress_map_by_level(
            user_id, level_id
        )
        return {
            "level": LevelBrief.model_validate(level),
            "characters": [
                CharacterForUser.build(c, progress_map.get(c.id)) for c in characters
            ],
        }

    async def update_progress(
        self, user_id: str, character_id: str, learned: bool
    ) -> ProgressOut:
        character = ensure_found(
            await self.uow.hanzi_characters.find_by_id(character_id),
            codes.HANZI_NOT_FOUND,
            "字条不存在",
        )

        existing = await self.uow.hanzi_progress.find(user_id, character_id)
        if learned:
            if existing:
                return ProgressOut(
                    character_id=character_id,
                    learned=True,
                    learned_at=existing.learned_at,
                )
            progress = HanziUserProgress.new(user_id, character_id)
            self.uow.hanzi_progress.add(progress)
            await self.uow.commit()
            return ProgressOut(
                character_id=character_id,
                learned=True,
                learned_at=progress.learned_at,
            )

        if existing:
            await self.uow.hanzi_progress.delete(existing)
            await self.uow.commit()
        return ProgressOut(character_id=character_id, learned=False, learned_at=None)

    async def generate_practice_text(self, user_id: str, level_id: str) -> dict:
        level = ensure_found(
            await self.uow.hanzi_levels.find_by_id(level_id),
            codes.HANZI_NOT_FOUND,
            "级别不存在",
        )

        characters = await self.uow.hanzi_characters.list_by_level(level_id)
        progress_map = await self.uow.hanzi_progress.progress_map_by_level(
            user_id, level_id
        )
        learned_chars = [c.char for c in characters if c.id in progress_map]

        if len(learned_chars) < 3:
            raise ParamException(
                codes.HANZI_TOO_FEW_LEARNED,
                f"至少学完 3 个字才能开始组合练习（当前 {len(learned_chars)}）",
            )

        raw = await ai_call(
            self.ai.practice_text(learned_chars),
            code=codes.AI_GENERATE_FAILED,
            message="AI 生成失败",
            sep="：",
            exc=ParamException,
        )

        text = str(raw.get("text") or "").strip()
        if not text:
            raise ParamException(codes.AI_GENERATE_FAILED, "AI 返回文本为空")

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

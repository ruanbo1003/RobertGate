from __future__ import annotations

import uuid
from datetime import datetime, timezone

from app.core.exceptions import ParamException, ServerException
from app.models.hanzi_entry import HanziEntry
from app.repository.hanzi_repo import HanziRepo
from app.service.ai_client import AIClient


def _extract_chinese_chars(text: str) -> list[str]:
    """从任意文本提取汉字并保持首次出现顺序、去重。"""
    seen: set[str] = set()
    result: list[str] = []
    for c in text:
        if "\u4e00" <= c <= "\u9fff" and c not in seen:
            seen.add(c)
            result.append(c)
    return result


class HanziService:
    def __init__(self, repo: HanziRepo, ai: AIClient) -> None:
        self.repo = repo
        self.ai = ai

    # ---------- 字库 ----------

    async def list_library(self, user_id: str) -> dict:
        entries = await self.repo.list_by_user(user_id)
        items = [
            {
                "char": e.char,
                "learned": e.learned,
                "created_at": e.created_at.isoformat(),
                "learned_at": e.learned_at.isoformat() if e.learned_at else None,
            }
            for e in entries
        ]
        return {
            "total": len(items),
            "learned": sum(1 for i in items if i["learned"]),
            "items": items,
        }

    async def add_from_text(self, user_id: str, text: str) -> dict:
        chars = _extract_chinese_chars(text)
        if not chars:
            raise ParamException(2004, "未识别到有效汉字")

        existing = await self.repo.existing_chars(user_id, chars)
        now = datetime.now(timezone.utc)
        added: list[str] = []
        duplicated: list[str] = []
        new_entries: list[HanziEntry] = []
        for c in chars:
            if c in existing:
                duplicated.append(c)
            else:
                added.append(c)
                new_entries.append(
                    HanziEntry(
                        id=str(uuid.uuid4()),
                        user_id=user_id,
                        char=c,
                        learned=False,
                        created_at=now,
                        learned_at=None,
                    )
                )
        if new_entries:
            await self.repo.add_many(new_entries)

        entries = await self.repo.list_by_user(user_id)
        return {"added": added, "duplicated": duplicated, "total": len(entries)}

    async def update_learned(self, user_id: str, char: str, learned: bool) -> dict:
        entry = await self.repo.find(user_id, char)
        if not entry:
            raise ParamException(2005, "字不在字库中")
        entry.learned = learned
        entry.learned_at = datetime.now(timezone.utc) if learned else None
        await self.repo.update(entry)
        return {
            "char": entry.char,
            "learned": entry.learned,
            "learned_at": entry.learned_at.isoformat() if entry.learned_at else "",
        }

    async def delete(self, user_id: str, char: str) -> dict:
        entry = await self.repo.find(user_id, char)
        if not entry:
            raise ParamException(2005, "字不在字库中")
        await self.repo.delete(entry)
        entries = await self.repo.list_by_user(user_id)
        return {"char": char, "total": len(entries)}

    # ---------- AI 内容 ----------

    async def character_info(self, char: str) -> dict:
        try:
            info = await self.ai.character_info(char)
        except Exception as e:
            raise ServerException(5001, f"AI 服务不可用: {e}") from e
        return {
            "char": char,
            "pinyin": info["pinyin"],
            "words": info["words"],
            "sentence": info["sentence"],
            "sentence_pinyin": info["sentence_pinyin"],
        }

    async def compose_sentence(self, known_chars: list[str]) -> dict:
        try:
            info = await self.ai.compose_sentence(known_chars)
        except Exception as e:
            raise ServerException(5001, f"AI 服务不可用: {e}") from e
        known_set = set(known_chars)
        # 提取库外字（仅统计汉字）
        out_of_vocab = [
            c
            for c in info["sentence"]
            if ("\u4e00" <= c <= "\u9fff") and c not in known_set
        ]
        # 去重
        seen: set[str] = set()
        uniq_ooc: list[str] = []
        for c in out_of_vocab:
            if c not in seen:
                seen.add(c)
                uniq_ooc.append(c)
        return {
            "sentence": info["sentence"],
            "pinyin": info["pinyin"],
            "translation": info["translation"],
            "out_of_vocab": uniq_ooc,
        }

"""汉字模块出参 DTO。

user 侧与 admin 侧字段**故意不同**，与改造前的手写 dict 保持一致：
  - 级别：user 侧多 `learned`（该用户已学字数），admin 侧只有 `total`；
  - 字条：user 侧带 `learned` / `learned_at`，admin 侧带 `created_at` / `updated_at`。
不要图省事把两边合并成一个模型——那会给对方端点凭空加字段。
"""

from __future__ import annotations

from app.application.dto.base import DTO, IsoDtOpt
from app.domain.models.hanzi import HanziCharacter, HanziLevel, HanziUserProgress


class LevelBrief(DTO):
    """字表接口里的级别摘要（user / admin 两侧同形，无时间字段）。"""

    id: str
    name: str
    description: str | None
    order_index: int


class LevelForUser(DTO):
    id: str
    name: str
    description: str | None
    order_index: int
    total: int
    learned: int
    created_at: IsoDtOpt
    updated_at: IsoDtOpt

    @classmethod
    def build(cls, level: HanziLevel, total: int, learned: int) -> LevelForUser:
        return cls(
            id=level.id,
            name=level.name,
            description=level.description,
            order_index=level.order_index,
            total=total,
            learned=learned,
            created_at=level.created_at,
            updated_at=level.updated_at,
        )


class LevelForAdmin(DTO):
    id: str
    name: str
    description: str | None
    order_index: int
    total: int
    created_at: IsoDtOpt
    updated_at: IsoDtOpt

    @classmethod
    def build(cls, level: HanziLevel, total: int) -> LevelForAdmin:
        return cls(
            id=level.id,
            name=level.name,
            description=level.description,
            order_index=level.order_index,
            total=total,
            created_at=level.created_at,
            updated_at=level.updated_at,
        )


class CharacterForUser(DTO):
    id: str
    char: str
    pinyin: str
    example_words: list[str]
    order_index: int
    learned: bool
    learned_at: IsoDtOpt

    @classmethod
    def build(
        cls, character: HanziCharacter, progress: HanziUserProgress | None
    ) -> CharacterForUser:
        return cls(
            id=character.id,
            char=character.char,
            pinyin=character.pinyin,
            example_words=character.example_words or [],
            order_index=character.order_index,
            learned=progress is not None,
            learned_at=progress.learned_at if progress else None,
        )


class CharacterForAdmin(DTO):
    id: str
    char: str
    pinyin: str
    example_words: list[str]
    order_index: int
    created_at: IsoDtOpt
    updated_at: IsoDtOpt

    @classmethod
    def build(cls, character: HanziCharacter) -> CharacterForAdmin:
        return cls(
            id=character.id,
            char=character.char,
            pinyin=character.pinyin,
            example_words=character.example_words or [],
            order_index=character.order_index,
            created_at=character.created_at,
            updated_at=character.updated_at,
        )


class ProgressOut(DTO):
    character_id: str
    learned: bool
    learned_at: IsoDtOpt

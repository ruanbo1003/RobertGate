"""法律咨询出参 DTO。"""

from __future__ import annotations

from app.application.dto.base import DTO, IsoDt


class CitationDTO(DTO):
    article_no: int
    label: str


class LegalMessageDTO(DTO):
    id: str
    role: str
    content: str
    citations: list[CitationDTO]
    created_at: IsoDt


class LegalMessagesDTO(DTO):
    messages: list[LegalMessageDTO]


class LawArticleDTO(DTO):
    article_no: int
    label: str
    content: str


class LawArticleDataDTO(DTO):
    article: LawArticleDTO

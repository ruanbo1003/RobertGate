"""应用层端口（AI Client / 密码哈希 / 令牌）。

具体实现及全局单例装配在 infrastructure/ 下，
本模块只定义契约，不得反向 import infrastructure。
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Callable, Coroutine
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from app.application.dto.invest_report import (
    ChapterDraft,
    ChatOutcome,
    ImpactDraft,
    ResearchContext,
    TemplateDraft,
)
from app.domain.models.legal import LawArticle


class AIClient(Protocol):
    async def translate(self, text: str) -> tuple[str, str, str]:
        """返回 (source_lang, target_lang, result)。"""
        ...

    async def grammar_correct(self, text: str) -> str: ...

    async def rewrite_native(self, text: str) -> str: ...

    async def character_info(self, char: str) -> dict:
        """返回 {pinyin, words, sentence, sentence_pinyin}."""
        ...

    async def practice_text(self, learned_chars: list[str]) -> dict:
        """返回 {text, annotations: [{char, pinyin}], new_chars: [char]}."""
        ...

    async def generate_image(self, prompt: str) -> str:
        """返回图片 URL 或路径。"""
        ...


class PasswordHasher(Protocol):
    def hash(self, password: str) -> str: ...

    def verify(self, plain: str, hashed: str) -> bool: ...


class TokenProvider(Protocol):
    def create(self, user_id: str) -> str:
        """签发访问令牌。"""
        ...

    def decode(self, token: str) -> str | None:
        """解出 user_id；令牌非法或过期返回 None。"""
        ...

    @property
    def ttl_seconds(self) -> int:
        """令牌有效期（秒），用于 login/register 的 expires_in。"""
        ...


class TaskRunner(Protocol):
    def spawn(self, coro: Coroutine[Any, Any, Any]) -> None: ...


class LegalKnowledgeBase(Protocol):
    """民法典知识库：按条切分的向量检索 + 条文精确查询。"""

    @property
    def ready(self) -> bool:
        """索引是否已构建完成。"""
        ...

    async def retrieve(self, query: str, top_k: int) -> list[LawArticle]:
        """按相似度返回 top_k 条相关条文（可能为空）。"""
        ...

    def get_article(self, article_no: int) -> LawArticle | None: ...


class LegalChatClient(Protocol):
    """法律咨询流式对话客户端（OpenAI 兼容 messages 格式）。"""

    def stream_chat(self, messages: list[dict[str, str]]) -> AsyncIterator[str]: ...


class AvGenClient(Protocol):
    """ai-videos 生成客户端（OpenRouter：t2i / i2v / tts / llm-json）。

    上游失败约定抛 ServerException：余额/Key 全局性错误用
    codes.AV_UPSTREAM_QUOTA，其余用 codes.AV_UPSTREAM_FAILED。
    """

    async def generate_image(
        self, prompt: str, model: str, reference_images: list[bytes] | None = None
    ) -> bytes:
        """文生图（多参考图模型带 reference_images），返回图片 bytes。"""
        ...

    async def generate_video(
        self, image: bytes, prompt: str, model: str, duration_seconds: int = 5
    ) -> bytes:
        """图生视频（提交 + 轮询），prompt 为动作/运镜提示，返回 mp4 bytes。"""
        ...

    async def generate_speech(self, text: str, model: str, voice: str) -> bytes:
        """TTS，返回 mp3 bytes。"""
        ...

    async def generate_json(self, system: str, user: str, model: str) -> dict:
        """LLM JSON 输出（剧本生成 / 拆分镜）。"""
        ...

    async def generate_dialogue_video(
        self, image: bytes, prompt: str, duration_seconds: int
    ) -> tuple[bytes, str]:
        """对白镜（音视同出，多角色轮流说话+口型同步），返回 (mp4 bytes, 实际使用渠道:模型)。"""
        ...


class DocumentParser(Protocol):
    """invest-reports 文档/URL 解析端口（实现：infrastructure/ir_parsers.py）。"""

    async def parse_document(self, path: Path, agent: "IrAgent") -> tuple[str, str]:
        """返回 (text, quality)；quality: ok | low。"""
        ...

    async def parse_url(self, url: str) -> str: ...


class IrAgent(Protocol):
    """invest-reports Agent 端口（实现：infrastructure/ai/ir_agent_*）。

    上游失败约定：余额/Key 全局错误抛 ServerException(codes.IR_UPSTREAM_QUOTA)，
    其余抛 ServerException(codes.IR_UPSTREAM_FAILED)。
    """

    async def learn_template(self, samples_text: list[str], report_type: str) -> "TemplateDraft":
        """从范本全文归纳模板（章节骨架 + 写作要点）。"""
        ...

    async def research_chapter(
        self,
        ctx: "ResearchContext",
        on_event: Callable[[str, str, str | None], None],
    ) -> "ChapterDraft":
        """逐章研究写作；on_event(kind, text, url) 回调研究动作。"""
        ...

    async def rewrite_paragraph(
        self, paragraph_text: str, instruction: str, citations_catalog: list[dict]
    ) -> str:
        """重写单段；只允许沿用 catalog 中既有的全局 ⟦c:id⟧ 标记。"""
        ...

    async def chat(
        self, ctx_summary: str, chapter: dict | None, message: str
    ) -> "ChatOutcome":
        """对话；指定章节且需要改稿时返回 updated=True 与整章新段落。"""
        ...

    async def analyze_impact(
        self, source_text: str, done_chapters: list[dict]
    ) -> "ImpactDraft":
        """新资料影响分析：返回建议更新的章节 key 与理由。"""
        ...

    async def parse_image(self, image_bytes: bytes, hint: str) -> str:
        """多模态解析图片/扫描件为文本（OCR/描述）。"""
        ...


@dataclass(frozen=True)
class ComposeItem:
    """合成输入：单镜的视频绝对路径 + 可选音频（None=用视频自带音轨）+ 字幕条目。

    subtitles 为该镜内部相对时间 [(text, start, end), ...]（0 起点）；
    全局字幕偏移由合成器按各镜时长累加。
    """

    video: Path
    audio: Path | None
    subtitles: list[tuple[str, float, float]]


class VideoComposer(Protocol):
    """成片合成器（ffmpeg 实现见 infrastructure/av_compose.py）。"""

    async def compose(self, items: list[ComposeItem], out_path: Path) -> None: ...

    async def probe_duration(self, path: Path) -> float | None:
        """探测媒体文件时长（秒）；探测失败返回 None。"""
        ...


class AudioWordAligner(Protocol):
    """字幕用词级时间戳转写（faster-whisper 实现见 infrastructure/av_whisper.py）。"""

    def transcribe_words(self, media: Path) -> list[tuple[str, float, float]]: ...

"""民法典知识库：PDF 按条切分 + SiliconFlow BGE-M3 向量检索。

索引构建一次后缓存为 JSON（articles + vectors），进程重启直接加载；
缓存不存在时在后台任务里解析 PDF → 分批 embedding → 落盘。
"""

from __future__ import annotations

import json
import logging
import math
from pathlib import Path

from app.domain.models.legal import LawArticle
from app.infrastructure.legal.law_text import split_articles

logger = logging.getLogger(__name__)

_EMBED_BATCH = 32
_INDEX_VERSION = 1


def top_k_by_cosine(
    query: list[float],
    vectors: list[tuple[int, list[float]]],
    top_k: int,
    min_score: float,
) -> list[tuple[int, float]]:
    """按余弦相似度降序返回 (article_no, score)，过滤低于 min_score 的结果。"""
    qnorm = math.sqrt(sum(x * x for x in query))
    if qnorm == 0:
        return []
    scored: list[tuple[int, float]] = []
    for article_no, vec in vectors:
        vnorm = math.sqrt(sum(x * x for x in vec))
        if vnorm == 0:
            continue
        dot = sum(a * b for a, b in zip(query, vec))
        score = dot / (qnorm * vnorm)
        if score >= min_score:
            scored.append((article_no, score))
    scored.sort(key=lambda item: item[1], reverse=True)
    return scored[:top_k]


def load_articles_from_pdf(pdf_path: Path) -> list[LawArticle]:
    """解析民法典 PDF，按条返回条文列表。"""
    from pypdf import PdfReader

    reader = PdfReader(str(pdf_path))
    text = "\n".join(page.extract_text() or "" for page in reader.pages)
    return [
        LawArticle(article_no=p.article_no, label=p.label, content=p.content)
        for p in split_articles(text)
        if p.content
    ]


class SiliconFlowLegalKB:
    """真实知识库：embedding 走 SiliconFlow（OpenAI 兼容）。"""

    def __init__(
        self,
        api_key: str,
        base_url: str,
        embedding_model: str,
        pdf_path: Path,
        index_path: Path,
        min_score: float,
    ) -> None:
        self._embedding_model = embedding_model
        self._pdf_path = pdf_path
        self._index_path = index_path
        self._min_score = min_score
        self._articles: dict[int, LawArticle] = {}
        self._vectors: list[tuple[int, list[float]]] = []
        self._ready = False

        from openai import AsyncOpenAI

        self._client = AsyncOpenAI(api_key=api_key, base_url=base_url)

    @property
    def ready(self) -> bool:
        return self._ready

    async def build_index(self) -> None:
        """加载缓存或重建索引。供应用启动时在后台任务中调用。"""
        try:
            if self._load_cache():
                logger.info("legal KB loaded from cache: %d articles", len(self._articles))
                self._ready = True
                return
            articles = load_articles_from_pdf(self._pdf_path)
            if not articles:
                logger.error("legal KB: no articles parsed from %s", self._pdf_path)
                return
            vectors: list[tuple[int, list[float]]] = []
            for i in range(0, len(articles), _EMBED_BATCH):
                batch = articles[i : i + _EMBED_BATCH]
                embeddings = await self._embed([f"{a.label}　{a.content}" for a in batch])
                vectors.extend(
                    (a.article_no, emb) for a, emb in zip(batch, embeddings)
                )
            self._articles = {a.article_no: a for a in articles}
            self._vectors = vectors
            self._save_cache(articles)
            self._ready = True
            logger.info("legal KB index built: %d articles", len(articles))
        except Exception:
            logger.exception("legal KB index build failed")

    async def retrieve(self, query: str, top_k: int) -> list[LawArticle]:
        embeddings = await self._embed([query])
        ranked = top_k_by_cosine(embeddings[0], self._vectors, top_k, self._min_score)
        return [self._articles[no] for no, _ in ranked]

    def get_article(self, article_no: int) -> LawArticle | None:
        return self._articles.get(article_no)

    # ---------- 内部 ----------

    async def _embed(self, texts: list[str]) -> list[list[float]]:
        response = await self._client.embeddings.create(
            model=self._embedding_model, input=texts
        )
        return [item.embedding for item in response.data]

    def _load_cache(self) -> bool:
        if not self._index_path.exists():
            return False
        try:
            data = json.loads(self._index_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return False
        if data.get("version") != _INDEX_VERSION:
            return False
        self._articles = {
            a["article_no"]: LawArticle(
                article_no=a["article_no"], label=a["label"], content=a["content"]
            )
            for a in data["articles"]
        }
        self._vectors = [(int(no), vec) for no, vec in data["vectors"].items()]
        return bool(self._articles) and bool(self._vectors)

    def _save_cache(self, articles: list[LawArticle]) -> None:
        payload = {
            "version": _INDEX_VERSION,
            "articles": [
                {"article_no": a.article_no, "label": a.label, "content": a.content}
                for a in articles
            ],
            "vectors": {str(no): vec for no, vec in self._vectors},
        }
        self._index_path.parent.mkdir(parents=True, exist_ok=True)
        self._index_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


class MockLegalKB:
    """无 API Key 时的兜底：条文仍从 PDF 解析（精确查询可用），检索退化为字符重合打分。"""

    def __init__(self, pdf_path: Path) -> None:
        self._pdf_path = pdf_path
        self._articles: dict[int, LawArticle] = {}
        self._ready = False

    @property
    def ready(self) -> bool:
        return self._ready

    async def build_index(self) -> None:
        try:
            articles = load_articles_from_pdf(self._pdf_path)
            self._articles = {a.article_no: a for a in articles}
            self._ready = bool(self._articles)
            logger.info("mock legal KB loaded: %d articles", len(self._articles))
        except Exception:
            logger.exception("mock legal KB load failed")

    async def retrieve(self, query: str, top_k: int) -> list[LawArticle]:
        chars = set(query)
        scored = [
            (len(chars & set(a.content)) / (len(chars) or 1), a)
            for a in self._articles.values()
        ]
        scored.sort(key=lambda item: item[0], reverse=True)
        return [a for score, a in scored[:top_k] if score > 0.3]

    def get_article(self, article_no: int) -> LawArticle | None:
        return self._articles.get(article_no)

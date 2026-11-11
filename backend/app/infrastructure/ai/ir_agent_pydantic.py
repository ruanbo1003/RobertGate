"""invest-reports 真实 Agent（Pydantic AI + OpenRouter）。

- 研究写作 Agent：typed tools（web_search / read_url / query_sources）+ 结构化输出
  ChapterDraft；工具调用经 deps 回调研究进度事件（feed）。
- web_search 为显式工具：内部调 OpenRouter 的 `:online` 检索模型，解析
  message.annotations 的 url_citation —— 每次检索都是可记录、可回放的研究动作。
- learn/rewrite/chat/impact 为单次结构化调用；parse_image 为多模态消息。
- 错误收口：401/402/429+credit → IR_UPSTREAM_QUOTA，其余 → IR_UPSTREAM_FAILED。
"""

from __future__ import annotations

import base64
import logging
from dataclasses import dataclass
from typing import Callable

import httpx
from pydantic import BaseModel
from pydantic_ai import Agent, BinaryContent, RunContext
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider

from app.application.dto.invest_report import (
    ChapterDraft,
    ChatOutcome,
    ImpactDraft,
    ResearchContext,
    TemplateDraft,
)
from app.domain.errors import ServerException, codes
from app.infrastructure.ir_parsers import parse_url

logger = logging.getLogger(__name__)

_QUOTA_STATUS = {401, 402}
_NONSTANDARD_FIELDS = ("service_tier",)  # OpenRouter 扩展值会撞 openai SDK 字面量校验


class _SanitizeTransport(httpx.AsyncBaseTransport):
    """剥除 chat/completions 响应中 openai SDK 不认的非标字段（如 service_tier=provisioned）。"""

    def __init__(self, inner: httpx.AsyncBaseTransport) -> None:
        self._inner = inner

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        import json as _json

        response = await self._inner.handle_async_request(request)
        if "chat/completions" not in str(request.url):
            return response
        if "application/json" not in response.headers.get("content-type", ""):
            return response
        body = await response.aread()
        try:
            data = _json.loads(body)
        except ValueError:
            return httpx.Response(
                response.status_code, headers=response.headers, content=body,
                request=request,
            )
        for field in _NONSTANDARD_FIELDS:
            data.pop(field, None)
        headers = dict(response.headers)
        headers.pop("content-length", None)
        headers.pop("content-encoding", None)
        return httpx.Response(
            response.status_code, headers=headers,
            content=_json.dumps(data).encode(), request=request,
        )
_READ_URL_LIMIT = 8_000
_SNIPPET_RADIUS = 300

_RESEARCH_SYSTEM = (
    "You are an investment research analyst writing one chapter of a Chinese "
    "{report_kind}. Write in professional Chinese.\n"
    "Rules:\n"
    "1. Research first: use query_sources for uploaded materials, web_search for "
    "public facts, read_url to read a promising result before citing it.\n"
    "2. Every number or verifiable fact in your prose MUST carry an inline marker "
    "⟦c:N⟧ where N is the 1-based index into your `citations` list. Each citation "
    "needs an exact `quote` and `captured_at` (YYYY-MM).\n"
    "3. If you cannot find a reliable source for a needed number, do NOT invent it: "
    "put the marker ⟦tbd:N⟧ (1-based index into `tbds`) in place of the number and "
    "record the reason.\n"
    "4. Citations from uploaded materials use source_type='file' with the given "
    "source id; web citations use source_type='web' with the URL.\n"
    "5. Follow the chapter brief and the style notes. 3-6 paragraphs."
)


@dataclass
class ResearchDeps:
    ctx: ResearchContext
    on_event: Callable[[str, str, str | None], None]
    agent: "PydanticIrAgent"


class _ChatModelOut(BaseModel):
    reply: str
    updated: bool = False
    paragraphs: list[str] | None = None


def _raise_upstream(status: int, body: str) -> None:
    if status in _QUOTA_STATUS or (status == 429 and ("credit" in body.lower() or "balance" in body.lower())):
        raise ServerException(codes.IR_UPSTREAM_QUOTA, "OpenRouter 余额不足或 Key 失效")
    raise ServerException(codes.IR_UPSTREAM_FAILED, f"检索上游失败 (HTTP {status})")


class PydanticIrAgent:
    def __init__(
        self,
        api_key: str,
        base_url: str,
        model: str,
        search_model: str,
        search_transport: httpx.AsyncBaseTransport | None = None,
        llm_transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._api_key = api_key
        self._base = base_url.rstrip("/")
        self._search_model = search_model
        self._search_transport = search_transport
        # 显式 transport 会绕过 httpx 的 trust_env 代理解析——必须手动继承环境代理，
        # 否则直连出口可能触发 OpenRouter 地区限制（见 Task 10 冒烟记录）
        import os

        proxy = os.environ.get("HTTPS_PROXY") or os.environ.get("https_proxy")
        inner = llm_transport or httpx.AsyncHTTPTransport(proxy=proxy)
        http_client = httpx.AsyncClient(
            timeout=300.0,
            transport=_SanitizeTransport(inner),
        )
        provider = OpenAIProvider(base_url=self._base, api_key=api_key, http_client=http_client)
        self._model = OpenAIChatModel(model, provider=provider)

        self.research_agent: Agent[ResearchDeps, ChapterDraft] = Agent(
            self._model,
            deps_type=ResearchDeps,
            output_type=ChapterDraft,
            retries=2,
        )
        self._register_tools()

        self.simple_agents: dict[str, Agent] = {
            "learn": Agent(self._model, output_type=TemplateDraft, retries=2),
            "rewrite": Agent(self._model, output_type=str),
            "chat": Agent(self._model, output_type=_ChatModelOut, retries=2),
            "impact": Agent(self._model, output_type=ImpactDraft, retries=2),
            "vision": Agent(self._model, output_type=str),
        }

    # ---------------- 工具 ----------------

    def _register_tools(self) -> None:
        @self.research_agent.tool
        async def web_search(ctx: RunContext[ResearchDeps], query: str) -> list[dict]:
            """Search the public web. Returns a list of {title, url, snippet}."""
            return await ctx.deps.agent.web_search_impl(ctx.deps.on_event, query)

        @self.research_agent.tool
        async def read_url(ctx: RunContext[ResearchDeps], url: str) -> str:
            """Fetch and read one http(s) web page's text (truncated). Only for URLs
            returned by web_search — uploaded materials must use query_sources."""
            ctx.deps.on_event("read_url", f"读取网页：{url[:80]}", url)
            return await ctx.deps.agent.read_url_impl(url)

        @self.research_agent.tool
        async def query_sources(ctx: RunContext[ResearchDeps], keyword: str) -> list[dict]:
            """Search the uploaded project materials. Returns {source_id, source, snippet}."""
            ctx.deps.on_event("read_source", f"查资料「{keyword}」", None)
            return ctx.deps.agent.query_sources_impl(ctx.deps.ctx, keyword)

    async def web_search_impl(self, on_event, query: str) -> list[dict]:
        """检索失败返回错误条目（模型可换关键词重试）；仅配额错误穿透以暂停队列。"""
        if on_event is not None:
            on_event("search", f"检索「{query}」", None)
        try:
            results = await self.search_web(query)
        except ServerException as e:
            if e.code == codes.IR_UPSTREAM_QUOTA:
                raise
            logger.warning("web_search 失败：%s", e.message)
            return [{"title": "检索失败", "url": "", "snippet": f"{e.message}；请换关键词或改用 query_sources"}]
        if on_event is not None:
            for r in results[:3]:
                if r.get("url"):
                    on_event("read_url", f"命中：{r['title']}", r["url"])
        return results

    async def read_url_impl(self, url: str) -> str:
        """抓取失败返回错误文本（不抛异常——工具层失败不应终结整章研究）。"""
        if not url.startswith(("http://", "https://")):
            return (
                f"（抓取失败：{url} 不是 http(s) 网址。上传资料请用 query_sources 工具，"
                "网页只接受 web_search 返回的 URL）"
            )
        try:
            text = await parse_url(url)
        except Exception as e:  # noqa: BLE001
            return f"（抓取失败：{e}。请换其他来源，或改用 query_sources 查上传资料）"
        return text[:_READ_URL_LIMIT]

    def query_sources_impl(self, ctx: ResearchContext, keyword: str) -> list[dict]:
        hits: list[dict] = []
        for doc in ctx.sources:
            idx = doc.text.find(keyword)
            if idx >= 0:
                start = max(0, idx - _SNIPPET_RADIUS)
                hits.append(
                    {
                        "source_id": doc.id,
                        "source": doc.name,
                        "snippet": doc.text[start : idx + _SNIPPET_RADIUS],
                    }
                )
        if not hits:
            # 未命中关键词时给每份资料开头，避免模型反复盲查
            hits = [
                {"source_id": d.id, "source": d.name, "snippet": d.text[:_SNIPPET_RADIUS]}
                for d in ctx.sources[:3]
            ]
        return hits

    async def search_web(self, query: str) -> list[dict]:
        """OpenRouter `:online` 检索：返回 [{title, url, snippet}]，解析 url_citation。"""
        payload = {
            "model": self._search_model,
            "messages": [{"role": "user", "content": query}],
        }
        try:
            async with httpx.AsyncClient(
                timeout=60.0, transport=self._search_transport
            ) as client:
                resp = await client.post(
                    f"{self._base}/chat/completions",
                    json=payload,
                    headers={"Authorization": f"Bearer {self._api_key}"},
                )
        except httpx.HTTPError as e:
            raise ServerException(codes.IR_UPSTREAM_FAILED, f"检索网络错误：{e}") from e
        if resp.status_code >= 400:
            _raise_upstream(resp.status_code, resp.text[:300])
        message = (resp.json().get("choices") or [{}])[0].get("message") or {}
        results: list[dict] = []
        for ann in message.get("annotations") or []:
            cite = ann.get("url_citation") or {}
            if cite.get("url"):
                results.append(
                    {
                        "title": cite.get("title") or cite["url"],
                        "url": cite["url"],
                        "snippet": (cite.get("content") or "")[:400],
                    }
                )
        if not results and message.get("content"):
            results.append({"title": "检索摘要", "url": "", "snippet": message["content"][:400]})
        return results

    # ---------------- IrAgent 接口 ----------------

    async def research_chapter(
        self, ctx: ResearchContext, on_event: Callable[[str, str, str | None], None]
    ) -> ChapterDraft:
        deps = ResearchDeps(ctx=ctx, on_event=on_event, agent=self)
        sources_brief = "\n".join(
            f"- source_id={d.id} name={d.name} chars={len(d.text)}" for d in ctx.sources
        ) or "（无上传资料）"
        prompt = (
            f"报告：{ctx.project_title}\n"
            f"本章：{ctx.chapter_title}（key={ctx.chapter_key}）\n"
            f"章节要点：{ctx.chapter_brief or '按标题撰写'}\n"
            f"写作风格：{ctx.style_notes or '专业、数据先行'}\n"
            f"已完成章节：{'、'.join(ctx.prior_chapter_titles) or '无'}\n"
            f"可用上传资料：\n{sources_brief}\n"
            "请研究并撰写本章。"
        )
        on_event("write", f"开始研究「{ctx.chapter_title}」", None)
        kind = "投资建议书" if ctx.report_type == "advice" else "尽调报告"
        try:
            result = await self.research_agent.run(
                prompt,
                deps=deps,
                model_settings=None,
                instructions=_RESEARCH_SYSTEM.format(report_kind=kind),
            )
        except ServerException:
            raise
        except Exception as e:  # noqa: BLE001
            raise _map_exception(e) from e
        return result.output

    async def learn_template(self, samples_text: list[str], report_type: str) -> TemplateDraft:
        kind = "投资建议书" if report_type == "advice" else "尽调报告"
        joined = "\n\n===== 范本分隔 =====\n\n".join(samples_text)
        prompt = (
            f"以下是若干份{kind}的全文范本。请归纳出一份模板：\n"
            "1. chapters：章节骨架（key 用英文短词，title 保留中文编号样式，brief 一句话写作要点）；"
            "归纳共性结构，不要逐份照抄。\n"
            "2. style_notes：写作风格要点（数据呈现习惯、小结方式、语气）。\n\n" + joined
        )
        try:
            result = await self.simple_agents["learn"].run(prompt)
        except Exception as e:  # noqa: BLE001
            raise _map_exception(e) from e
        return result.output

    async def rewrite_paragraph(
        self, paragraph_text: str, instruction: str, citations_catalog: list[dict]
    ) -> str:
        catalog = "\n".join(
            f"- ⟦c:{c['id']}⟧ {c['title']}：{c['quote'][:80]}" for c in citations_catalog
        ) or "（本章暂无引用）"
        prompt = (
            "重写下面这段投资报告正文。只输出重写后的正文字符串。\n"
            f"重写指令：{instruction}\n"
            "规则：只允许沿用下方目录中已有的 ⟦c:id⟧ 引用标记，禁止编造新标记或新数据；"
            "无依据的数据不要写。\n"
            f"引用目录：\n{catalog}\n\n原文：{paragraph_text}"
        )
        try:
            result = await self.simple_agents["rewrite"].run(prompt)
        except Exception as e:  # noqa: BLE001
            raise _map_exception(e) from e
        return result.output

    async def chat(self, ctx_summary: str, chapter: dict | None, message: str) -> ChatOutcome:
        if chapter is None:
            prompt = (
                f"你是投资报告写作助手（项目：{ctx_summary}）。回答用户问题；"
                "不涉及具体章节改稿时 updated=false。\n用户：" + message
            )
        else:
            paras = "\n".join(p["text"] for p in chapter.get("paragraphs", []))
            cites = "\n".join(
                f"⟦c:{c['id']}⟧ {c['title']}" for c in chapter.get("citations", [])
            )
            prompt = (
                f"你是投资报告写作助手（项目：{ctx_summary}）。用户在讨论章节"
                f"「{chapter.get('title')}」。若用户要求修改/补充本章，updated=true 并给出"
                "整章新的 paragraphs（字符串数组，保留仍然成立的 ⟦c:id⟧ 标记，"
                "禁止编造新引用或新数据）；否则 updated=false 只回复。\n"
                f"本章现有引用：\n{cites or '无'}\n本章正文：\n{paras}\n\n用户：{message}"
            )
        try:
            result = await self.simple_agents["chat"].run(prompt)
        except Exception as e:  # noqa: BLE001
            raise _map_exception(e) from e
        out = result.output
        return ChatOutcome(reply=out.reply, updated=out.updated, paragraphs=out.paragraphs)

    async def analyze_impact(self, source_text: str, done_chapters: list[dict]) -> ImpactDraft:
        listing = "\n".join(f"- key={c['key']} {c['title']}" for c in done_chapters)
        prompt = (
            "一份新资料刚上传到投资报告项目。判断它会影响哪些已完成章节需要更新，"
            "只在确有相关信息时列出（chapter_key 取自下方列表，reason 一句话）。\n"
            f"已完成章节：\n{listing}\n\n新资料内容（节选）：\n{source_text}"
        )
        try:
            result = await self.simple_agents["impact"].run(prompt)
        except Exception as e:  # noqa: BLE001
            raise _map_exception(e) from e
        return result.output

    async def parse_image(self, image_bytes: bytes, hint: str) -> str:
        media = "image/png" if image_bytes[:4] == b"\x89PNG" else (
            "application/pdf" if image_bytes[:4] == b"%PDF" else "image/jpeg"
        )
        try:
            result = await self.simple_agents["vision"].run(
                [
                    f"这是投资尽调资料（{hint}）。请把其中全部文字与表格内容完整转写为纯文本，"
                    "保留数字与结构，不要总结。",
                    BinaryContent(data=image_bytes, media_type=media),
                ]
            )
        except Exception as e:  # noqa: BLE001
            raise _map_exception(e) from e
        return result.output


def _map_exception(e: Exception) -> ServerException:
    text = str(e)
    status = getattr(e, "status_code", None)
    if status in _QUOTA_STATUS or "402" in text[:40] or "credit" in text.lower():
        return ServerException(codes.IR_UPSTREAM_QUOTA, "OpenRouter 余额不足或 Key 失效")
    logger.warning("ir agent 上游失败：%s", text[:300])
    return ServerException(codes.IR_UPSTREAM_FAILED, f"LLM 调用失败：{text[:200]}")

"""PydanticIrAgent 单测：TestModel 驱动（不走网络）+ web_search 的 MockTransport 验证。"""

from __future__ import annotations

import httpx
import pytest
from pydantic_ai.models.test import TestModel

from app.application.dto.invest_report import ChapterDraft, ResearchContext, SourceDoc
from app.domain.errors import ServerException, codes
from app.infrastructure.ai.ir_agent_pydantic import PydanticIrAgent

BASE = "https://openrouter.test/api/v1"


def make_agent(handler=None) -> PydanticIrAgent:
    return PydanticIrAgent(
        api_key="sk-or-test",
        base_url=BASE,
        model="google/gemini-3.8-flash",
        search_model="google/gemini-3.8-flash:online",
        search_transport=httpx.MockTransport(handler) if handler else None,
    )


def _ctx() -> ResearchContext:
    return ResearchContext(
        project_title="云帆科技 · A 轮",
        report_type="advice",
        chapter_key="industry",
        chapter_title="三、行业分析",
        chapter_brief="市场规模与增速",
        style_notes="数据先行",
        prior_chapter_titles=[],
        sources=[SourceDoc(id=11, name="BP.pdf", text="2025 年营收 3.2 亿元")],
    )


async def test_research_chapter_returns_draft_via_testmodel():
    agent = make_agent()
    events: list[tuple] = []
    with agent.research_agent.override(model=TestModel(call_tools=[])):
        draft = await agent.research_chapter(_ctx(), lambda k, t, u: events.append((k, t, u)))
    assert isinstance(draft, ChapterDraft)
    assert len(draft.paragraphs) >= 1
    kinds = [e[0] for e in events]
    assert "write" in kinds  # 开始写作事件由实现侧发出


async def test_query_sources_tool_finds_snippets():
    agent = make_agent()
    hits = agent.query_sources_impl(_ctx(), "营收")
    assert hits and "3.2 亿元" in hits[0]["snippet"]
    assert hits[0]["source"] == "BP.pdf"


async def test_web_search_parses_annotations_and_stays_on_openrouter():
    seen: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["host"] = request.url.host
        seen["auth"] = request.headers.get("authorization", "")
        return httpx.Response(
            200,
            json={
                "choices": [{
                    "message": {
                        "content": "总结……",
                        "annotations": [
                            {"type": "url_citation",
                             "url_citation": {"url": "https://idc.com/r1", "title": "IDC 报告",
                                              "content": "规模 4562 亿元"}},
                            {"type": "url_citation",
                             "url_citation": {"url": "https://36kr.com/a", "title": "36kr",
                                              "content": "竞对融资"}},
                        ],
                    }
                }]
            },
        )

    agent = make_agent(handler)
    results = await agent.search_web("行业云 市场规模")
    assert seen["host"] == "openrouter.test"
    assert seen["auth"].startswith("Bearer ")
    assert len(results) == 2
    assert results[0] == {"title": "IDC 报告", "url": "https://idc.com/r1", "snippet": "规模 4562 亿元"}


async def test_web_search_quota_maps_to_ir_quota():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(402, json={"error": "credits"})

    agent = make_agent(handler)
    with pytest.raises(ServerException) as e:
        await agent.search_web("x")
    assert e.value.code == codes.IR_UPSTREAM_QUOTA


async def test_learn_template_via_testmodel():
    agent = make_agent()
    with agent.simple_agents["learn"].override(model=TestModel()):
        draft = await agent.learn_template(["范本全文一", "范本全文二"], "advice")
    assert draft.chapters  # TestModel 生成合法结构


async def test_llm_response_with_nonstandard_service_tier_is_sanitized():
    """OpenRouter 会返回 service_tier='provisioned'，openai SDK 字面量不认——传输层剥除。"""
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "id": "gen-1", "object": "chat.completion", "created": 1,
                "model": "google/gemini-3.8-flash",
                "service_tier": "provisioned",
                "choices": [{"index": 0, "finish_reason": "stop",
                             "message": {"role": "assistant", "content": "重写后的段落。"}}],
                "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
            },
        )

    agent = PydanticIrAgent(
        api_key="sk-or-test", base_url=BASE,
        model="google/gemini-3.8-flash", search_model="m:online",
        llm_transport=httpx.MockTransport(handler),
    )
    out = await agent.rewrite_paragraph("原文", "更简洁", [])
    assert out == "重写后的段落。"


async def test_read_url_impl_never_raises_on_bad_input(monkeypatch):
    """模型会拿 file:///x、文件名当 URL 读——工具必须返回错误文本而不是炸掉整章。"""
    agent = make_agent()
    out1 = await agent.read_url_impl("file:///2")
    assert "抓取失败" in out1 or "无法读取" in out1

    import app.infrastructure.ai.ir_agent_pydantic as mod

    async def boom(url):
        raise ServerException(codes.IR_UPSTREAM_FAILED, "URL 抓取失败 (HTTP 403)")

    monkeypatch.setattr(mod, "parse_url", boom)
    out2 = await agent.read_url_impl("https://example.com/blocked")
    assert "403" in out2 and "query_sources" in out2


async def test_web_search_tool_swallows_failures_but_propagates_quota(monkeypatch):
    agent = make_agent()

    async def fail_search(query):
        raise ServerException(codes.IR_UPSTREAM_FAILED, "检索上游失败 (HTTP 500)")

    monkeypatch.setattr(agent, "search_web", fail_search)
    out = await agent.web_search_impl(None, "q")  # on_event 为 None 时内部跳过
    assert out and "检索失败" in out[0]["title"]

    async def quota(query):
        raise ServerException(codes.IR_UPSTREAM_QUOTA, "余额不足")

    monkeypatch.setattr(agent, "search_web", quota)
    with pytest.raises(ServerException) as e:
        await agent.web_search_impl(None, "q")
    assert e.value.code == codes.IR_UPSTREAM_QUOTA

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

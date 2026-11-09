"""DialogueVideoRouter 单测：primary 成功直采、primary 失败兜底、双挂异常冒泡。"""

from __future__ import annotations

import pytest

from app.domain.errors import ServerException, codes
from app.infrastructure.ai.av_dialogue_router import DialogueVideoRouter

MP4_PRIMARY = b"primary-mp4"
MP4_FALLBACK = b"fallback-mp4"


class FakePrimary:
    def __init__(self, fail: bool = False):
        self.fail = fail
        self.calls: list[tuple] = []

    async def generate_dialogue_video(self, image, prompt, duration_seconds):
        self.calls.append((image, prompt, duration_seconds))
        if self.fail:
            raise ServerException(codes.AV_UPSTREAM_FAILED, "kie boom")
        return MP4_PRIMARY


def make_fallback(fail: bool = False):
    calls: list[tuple] = []

    async def fallback_video(image, prompt, duration_seconds):
        calls.append((image, prompt, duration_seconds))
        if fail:
            raise ServerException(codes.AV_UPSTREAM_FAILED, "seedance boom")
        return MP4_FALLBACK

    return fallback_video, calls


async def test_primary_success_returns_primary_tag():
    primary = FakePrimary(fail=False)
    fallback, fallback_calls = make_fallback()
    router = DialogueVideoRouter(
        primary=primary,
        fallback_video=fallback,
        primary_tag="kie:gemini-omni-video",
        fallback_tag="openrouter:bytedance/seedance-2.0-fast",
        fallback_ladder=(4, 6, 8, 10),
    )
    video, tag = await router.generate_dialogue_video(b"img", "p", 8)
    assert video == MP4_PRIMARY
    assert tag == "kie:gemini-omni-video"
    assert not fallback_calls


async def test_primary_failure_falls_back_with_snapped_duration():
    primary = FakePrimary(fail=True)
    fallback, fallback_calls = make_fallback()
    router = DialogueVideoRouter(
        primary=primary,
        fallback_video=fallback,
        primary_tag="kie:gemini-omni-video",
        fallback_tag="openrouter:bytedance/seedance-2.0-fast",
        fallback_ladder=(4, 6, 8, 10),
    )
    video, tag = await router.generate_dialogue_video(b"img", "p", 7)
    assert video == MP4_FALLBACK
    assert tag == "openrouter:bytedance/seedance-2.0-fast"
    assert fallback_calls == [(b"img", "p", 8)]  # 7 二次 snap 到 8


async def test_both_fail_propagates_fallback_exception():
    primary = FakePrimary(fail=True)
    fallback, _ = make_fallback(fail=True)
    router = DialogueVideoRouter(
        primary=primary,
        fallback_video=fallback,
        primary_tag="kie:gemini-omni-video",
        fallback_tag="openrouter:bytedance/seedance-2.0-fast",
        fallback_ladder=(4, 6, 8, 10),
    )
    with pytest.raises(ServerException) as e:
        await router.generate_dialogue_video(b"img", "p", 5)
    assert "seedance boom" in e.value.message


async def test_no_primary_goes_straight_to_fallback():
    fallback, fallback_calls = make_fallback()
    router = DialogueVideoRouter(
        primary=None,
        fallback_video=fallback,
        primary_tag="kie:gemini-omni-video",
        fallback_tag="openrouter:bytedance/seedance-2.0-fast",
        fallback_ladder=(4, 6, 8, 10),
    )
    video, tag = await router.generate_dialogue_video(b"img", "p", 5)
    assert video == MP4_FALLBACK
    assert tag == "openrouter:bytedance/seedance-2.0-fast"
    assert fallback_calls == [(b"img", "p", 6)]

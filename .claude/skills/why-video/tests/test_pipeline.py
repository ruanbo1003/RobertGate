"""pipeline.py 纯逻辑层测试：slug、key 加载、断点续跑、字幕分行与 SRT。"""

import pytest

from pipeline import (
    build_srt,
    load_api_key,
    load_board,
    make_slug,
    save_board,
    scenes_todo,
    split_lines,
)


# ---------- make_slug ----------


def test_make_slug_strips_illegal_chars():
    assert make_slug("地球为什么是圆的？") == "地球为什么是圆的"


def test_make_slug_collapses_and_truncates():
    assert make_slug("why?? is   the sky blue!", max_len=10) == "why-is-the"


# ---------- load_api_key ----------


def test_load_api_key_env_wins(monkeypatch, tmp_path):
    monkeypatch.setenv("SILICONFLOW_API_KEY", "sk-env")
    assert load_api_key(repo_root=tmp_path) == "sk-env"


def test_load_api_key_from_env_local(monkeypatch, tmp_path):
    monkeypatch.delenv("SILICONFLOW_API_KEY", raising=False)
    env_file = tmp_path / "backend" / ".env.local"
    env_file.parent.mkdir(parents=True)
    env_file.write_text("DEBUG=true\nLLM_API_KEY=sk-file\n", encoding="utf-8")
    assert load_api_key(repo_root=tmp_path) == "sk-file"


def test_load_api_key_missing_raises(monkeypatch, tmp_path):
    monkeypatch.delenv("SILICONFLOW_API_KEY", raising=False)
    with pytest.raises(RuntimeError):
        load_api_key(repo_root=tmp_path)


# ---------- scenes_todo ----------


def _board(statuses: list[str]) -> dict:
    return {
        "scenes": [
            {"id": i + 1, "status": s, "narration": f"第{i + 1}段"}
            for i, s in enumerate(statuses)
        ]
    }


def test_scenes_todo_skips_done():
    data = _board(["done", "pending"])
    assert [s["id"] for s in scenes_todo(data)] == [2]


def test_scenes_todo_includes_failed():
    data = _board(["failed", "done", "audio_done"])
    assert [s["id"] for s in scenes_todo(data)] == [1, 3]


def test_scenes_todo_redo_resets_only_named():
    data = _board(["done", "done", "done"])
    todo = scenes_todo(data, redo_ids=[3])
    assert [s["id"] for s in todo] == [3]
    assert data["scenes"][2]["status"] == "pending"
    assert data["scenes"][0]["status"] == "done"
    assert data["scenes"][1]["status"] == "done"


# ---------- split_lines ----------


def test_split_prefers_punctuation():
    assert split_lines("地球很大很大，像一个超级大皮球！") == [
        "地球很大很大",
        "像一个超级大皮球",
    ]


def test_split_keeps_numbers_intact():
    lines = split_lines("它有8000公里那么宽", max_chars=6)
    for line in lines:
        assert "8000" not in line or "8000公里" in line, f"数字单位被拆开: {lines}"
    assert all(lines), f"出现空行: {lines}"


def test_split_no_empty_lines():
    assert split_lines("。。！，") == []


# ---------- build_srt ----------


def test_build_srt_offsets_accumulate():
    scenes = [
        {"narration": "第一镜的旁白词", "audio_duration": 3.0, "status": "done"},
        {"narration": "第二镜的旁白词", "audio_duration": 2.0, "status": "done"},
    ]
    srt = build_srt(scenes)
    assert "00:00:03,000" in srt
    assert srt.strip().startswith("1")


def test_build_srt_timestamp_format():
    scenes = [{"narration": "一句话", "audio_duration": 65.5, "status": "done"}]
    srt = build_srt(scenes)
    assert "00:01:05,500" in srt


# ---------- save/load board ----------


def test_save_then_load_roundtrip(tmp_path):
    path = tmp_path / "storyboard.json"
    data = {"question": "天为什么是蓝的", "scenes": [{"id": 1, "status": "pending"}]}
    save_board(path, data)
    assert load_board(path) == data

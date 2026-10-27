"""pipeline.py 测试：纯逻辑层 + 外部环节（mock HTTP / 真 ffmpeg）。"""

import shutil
import subprocess

import pytest

import pipeline
from pipeline import (
    VideoGenError,
    build_srt,
    cmd_generate,
    load_api_key,
    load_board,
    make_slug,
    poll_video,
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


# ---------- poll_video ----------


def test_poll_video_returns_url_on_succeed(monkeypatch):
    seq = [
        {"status": "InProgress"},
        {"status": "Succeed", "results": {"videos": [{"url": "http://v.mp4"}]}},
    ]
    monkeypatch.setattr(pipeline, "_request", lambda *a, **k: seq.pop(0))
    assert poll_video("sk", "req", timeout_s=5, interval_s=0) == "http://v.mp4"


def test_poll_video_raises_on_failed_status(monkeypatch):
    monkeypatch.setattr(
        pipeline, "_request", lambda *a, **k: {"status": "Failed", "reason": "boom"}
    )
    with pytest.raises(VideoGenError):
        poll_video("sk", "req", timeout_s=5, interval_s=0)


def test_poll_video_times_out(monkeypatch):
    calls = {"n": 0}

    def fake(*a, **k):
        calls["n"] += 1
        return {"status": "InProgress"}

    monkeypatch.setattr(pipeline, "_request", fake)
    with pytest.raises(VideoGenError):
        poll_video("sk", "req", timeout_s=0, interval_s=0)
    assert calls["n"] <= 2, "超时后不得继续轮询"


# ---------- cmd_generate ----------


def _generate_project(tmp_path, statuses):
    (tmp_path / "clips").mkdir()
    board = {
        "question": "q",
        "slug": "q",
        "voice": "v",
        "video_model": "m",
        "scenes": [
            {
                "id": i + 1,
                "narration": f"第{i + 1}段旁白",
                "visual_zh": "画面",
                "visual_prompt_en": f"scene {i + 1}",
                "status": s,
                "audio_file": f"clips/scene-{i + 1}.mp3",
                "clip_file": f"clips/scene-{i + 1}.mp4",
                "audio_duration": 0.0,
                "error": "",
            }
            for i, s in enumerate(statuses)
        ],
    }
    save_board(tmp_path / "storyboard.json", board)
    return tmp_path


def _patch_generate_deps(monkeypatch, fail_scene_prompts=()):
    """mock 全部外部调用；fail_scene_prompts 里的 prompt 对应视频永远失败。"""
    calls = {"submit": []}
    monkeypatch.setattr(pipeline, "load_api_key", lambda repo_root=None: "sk-test")

    def fake_tts(api_key, text, voice, out_path, model=None):
        out_path.write_bytes(b"mp3")
        return 2.0

    def fake_submit(api_key, prompt, model, image_size):
        calls["submit"].append(prompt)
        return f"req::{prompt}"

    def fake_poll(api_key, request_id, timeout_s=900, interval_s=10):
        prompt = request_id.split("::", 1)[1]
        if prompt in fail_scene_prompts:
            raise VideoGenError("生成失败")
        return "http://video"

    def fake_download(url, out_path):
        out_path.write_bytes(b"mp4")

    monkeypatch.setattr(pipeline, "tts_to_file", fake_tts)
    monkeypatch.setattr(pipeline, "submit_video", fake_submit)
    monkeypatch.setattr(pipeline, "poll_video", fake_poll)
    monkeypatch.setattr(pipeline, "download", fake_download)
    return calls


def test_generate_continues_after_failure(tmp_path, monkeypatch):
    project = _generate_project(tmp_path, ["pending", "pending"])
    _patch_generate_deps(monkeypatch, fail_scene_prompts={"scene 1"})
    code = cmd_generate(project, redo_ids=None, assume_yes=True)
    board = load_board(project / "storyboard.json")
    assert code == 1
    assert board["scenes"][0]["status"] == "failed"
    assert board["scenes"][0]["error"]
    assert board["scenes"][1]["status"] == "done"
    assert board["scenes"][1]["audio_duration"] == 2.0


def test_generate_failure_retries_once(tmp_path, monkeypatch):
    project = _generate_project(tmp_path, ["pending"])
    calls = _patch_generate_deps(monkeypatch, fail_scene_prompts={"scene 1"})
    cmd_generate(project, redo_ids=None, assume_yes=True)
    assert len(calls["submit"]) == 2, "失败应自动重试 1 次（共提交 2 次）"


def test_generate_resume_skips_done(tmp_path, monkeypatch):
    project = _generate_project(tmp_path, ["done", "pending"])
    calls = _patch_generate_deps(monkeypatch)
    code = cmd_generate(project, redo_ids=None, assume_yes=True)
    assert code == 0
    assert calls["submit"] == ["scene 2"], "已 done 的分镜不得重新提交"


# ---------- assemble（真 ffmpeg） ----------

ffmpeg_missing = shutil.which(pipeline.FFMPEG) is None or shutil.which(pipeline.FFPROBE) is None


@pytest.mark.skipif(ffmpeg_missing, reason="本机无 ffmpeg/ffprobe")
def test_align_outputs_1080x1920(tmp_path):
    clip = tmp_path / "clip.mp4"
    audio = tmp_path / "audio.mp3"
    out = tmp_path / "seg.mp4"
    subprocess.run(
        [pipeline.FFMPEG, "-y", "-f", "lavfi", "-i", "color=c=blue:size=640x480:d=2",
         "-c:v", "libx264", str(clip)],
        check=True, capture_output=True,
    )
    subprocess.run(
        [pipeline.FFMPEG, "-y", "-f", "lavfi", "-i", "sine=frequency=440:duration=3",
         str(audio)],
        check=True, capture_output=True,
    )
    pipeline.align_scene(clip, audio, 3.0, out)
    probe = subprocess.run(
        [pipeline.FFPROBE, "-v", "error", "-select_streams", "v:0",
         "-show_entries", "stream=width,height", "-show_entries", "format=duration",
         "-of", "csv=p=0", str(out)],
        check=True, capture_output=True, text=True,
    ).stdout
    assert "1080,1920" in probe
    duration = float(probe.strip().splitlines()[-1])
    assert abs(duration - 3.0) < 0.3


def test_assemble_requires_all_done(tmp_path):
    project = _generate_project(tmp_path, ["done", "pending"])
    assert pipeline.cmd_assemble(project) == 1

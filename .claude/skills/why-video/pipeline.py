"""why-video 流水线：科普短视频的验证 / 生成 / 合成。

storyboard.json schema（机器状态唯一来源，存于每个项目目录）：
{
  "question": "地球为什么是圆的",
  "slug": "地球为什么是圆的",
  "created": "YYYY-MM-DD",
  "voice": "TTS 音色",
  "video_model": "视频模型 id",
  "scenes": [{
    "id": 1,
    "narration": "一句或两句旁白词",
    "visual_zh": "画面中文描述（给 Robert 看）",
    "visual_prompt_en": "english prompt for the video model",
    "status": "pending|audio_done|done|failed",
    "audio_file": "clips/scene-1.mp3",
    "clip_file": "clips/scene-1.mp4",
    "audio_duration": 0.0,
    "error": ""
  }]
}
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path

# ---------- 纯逻辑层 ----------

# 中文/英文标点与空白：字幕断行与 slug 的分隔依据
_PUNCT_SPLIT = re.compile(r"[，。！？；：、…,.!?;:\s]+")
# 不可拆单元：数字(含小数)带至多两个单位字符 / 英文单词 / 单个字符
_TOKEN = re.compile(r"\d+(?:\.\d+)?[^\s\d，。！？；：、…,.!?;:]{0,2}|[A-Za-z]+|.")
_SLUG_KEEP = re.compile(r"[一-鿿A-Za-z0-9]+")


def make_slug(question: str, max_len: int = 24) -> str:
    """问题 → 安全目录名：保留中文/字母/数字，其余折叠为 -，截断。"""
    parts = _SLUG_KEEP.findall(question)
    slug = "-".join(parts)[:max_len].rstrip("-")
    return slug


def load_api_key(repo_root: Path | None = None) -> str:
    """env SILICONFLOW_API_KEY 优先，否则读 backend/.env.local 的 LLM_API_KEY。"""
    key = os.environ.get("SILICONFLOW_API_KEY", "").strip()
    if key:
        return key
    root = repo_root or Path(__file__).resolve().parents[3]
    env_file = root / "backend" / ".env.local"
    if env_file.is_file():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith("LLM_API_KEY=") and line.split("=", 1)[1].strip():
                return line.split("=", 1)[1].strip()
    raise RuntimeError("未找到 SiliconFlow API key（env SILICONFLOW_API_KEY 或 backend/.env.local 的 LLM_API_KEY）")


def scenes_todo(data: dict, redo_ids: list[int] | None = None) -> list[dict]:
    """待生成分镜。redo_ids 给出时仅重置并返回这些 id；否则返回未 done 的。"""
    scenes = data["scenes"]
    if redo_ids:
        picked = [s for s in scenes if s["id"] in redo_ids]
        for s in picked:
            s["status"] = "pending"
            s["error"] = ""
        return picked
    return [s for s in scenes if s["status"] != "done"]


def split_lines(text: str, max_chars: int = 14) -> list[str]:
    """旁白 → 字幕行：标点优先断行，超长按不可拆单元硬切，无空行。"""
    lines: list[str] = []
    for seg in _PUNCT_SPLIT.split(text):
        if not seg:
            continue
        if len(seg) <= max_chars:
            lines.append(seg)
            continue
        current = ""
        for token in _TOKEN.findall(seg):
            if current and len(current) + len(token) > max_chars:
                lines.append(current)
                current = token
            else:
                current += token
        if current:
            lines.append(current)
    return lines


def _srt_timestamp(seconds: float) -> str:
    ms = round(seconds * 1000)
    h, rem = divmod(ms, 3_600_000)
    m, rem = divmod(rem, 60_000)
    s, ms = divmod(rem, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def build_srt(scenes: list[dict]) -> str:
    """全部分镜 → SRT 文本。分镜起始时间累计，镜内各行按字符数占比分配时长。"""
    entries: list[str] = []
    cursor = 0.0
    index = 1
    for scene in scenes:
        duration = float(scene["audio_duration"])
        lines = split_lines(scene["narration"])
        total_chars = sum(len(line) for line in lines) or 1
        start = cursor
        for line in lines:
            end = start + duration * len(line) / total_chars
            entries.append(f"{index}\n{_srt_timestamp(start)} --> {_srt_timestamp(end)}\n{line}\n")
            start = end
            index += 1
        cursor += duration
    return "\n".join(entries)


def save_board(path: Path, data: dict) -> None:
    """原子写 storyboard.json：临时文件 + rename，中断不损坏状态。"""
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, path)


def load_board(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))

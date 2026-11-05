"""ai-videos 成片合成：ffmpeg 分段对齐 + concat + SRT 字幕烧录。

流程（每镜时长 = max(视频, 音频)，视频不足末帧定格补齐）：
1. 每镜：视频 tpad 末帧定格 + 配音混流，裁到目标时长 → seg_N.mp4
2. concat demuxer 拼接 → merged.mp4
3. 按台词与分段时长生成 SRT，subtitles 滤镜烧录 → final.mp4

纯函数（srt / 命令构建）单测覆盖；subprocess 执行层保持薄。
"""

from __future__ import annotations

import asyncio
import json
import logging
import shutil
import tempfile
from pathlib import Path

from app.application.ports import ComposeItem

logger = logging.getLogger(__name__)

__all__ = ["ComposeItem", "FfmpegComposer", "probe_duration", "build_srt",
           "build_segment_cmd", "format_srt_timestamp", "ComposeError"]


class ComposeError(RuntimeError):
    pass


# ---------------- 纯函数 ----------------


def format_srt_timestamp(seconds: float) -> str:
    ms = round(seconds * 1000)
    h, rem = divmod(ms, 3_600_000)
    m, rem = divmod(rem, 60_000)
    s, ms = divmod(rem, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def build_srt(entries: list[tuple[str, float]]) -> str:
    """(台词, 分段时长) 列表 → SRT 文本；空台词跳过字幕块但时间照常推进。"""
    blocks: list[str] = []
    cursor = 0.0
    index = 1
    for line, duration in entries:
        start, end = cursor, cursor + duration
        cursor = end
        if not line.strip():
            continue
        blocks.append(
            f"{index}\n{format_srt_timestamp(start)} --> {format_srt_timestamp(end)}\n{line.strip()}"
        )
        index += 1
    return "\n\n".join(blocks) + "\n"


def build_segment_cmd(video: Path, audio: Path, duration: float, out: Path) -> list[str]:
    """单镜分段命令：归一化到 720x1280（各模型出图/出视频分辨率不一，
    concat 阶段 -c copy 要求分段同参数），视频末帧定格补齐到 duration，与配音混流。"""
    return [
        "ffmpeg",
        "-y",
        "-i", str(video),
        "-i", str(audio),
        "-filter_complex",
        (
            "[0:v]scale=720:1280:force_original_aspect_ratio=decrease,"
            "pad=720:1280:(ow-iw)/2:(oh-ih)/2:black,setsar=1,"
            f"tpad=stop_mode=clone:stop_duration={duration}[v]"
        ),
        "-map", "[v]",
        "-map", "1:a",
        "-t", str(duration),
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-r", "30",
        str(out),
    ]


# ---------------- 执行层 ----------------


async def _run_cmd(cmd: list[str]) -> None:
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    _, stderr = await proc.communicate()
    if proc.returncode != 0:
        tail = stderr.decode(errors="replace")[-500:]
        raise ComposeError(f"{cmd[0]} 失败（exit {proc.returncode}）：{tail}")


async def probe_duration(path: Path) -> float | None:
    """ffprobe 读媒体时长（秒）；ffprobe 不可用或解析失败返回 None。"""
    if shutil.which("ffprobe") is None:
        return None
    try:
        proc = await asyncio.create_subprocess_exec(
            "ffprobe", "-v", "quiet", "-print_format", "json",
            "-show_format", str(path),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await proc.communicate()
        if proc.returncode != 0:
            return None
        data = json.loads(stdout.decode())
        duration = float(data.get("format", {}).get("duration", 0))
        return round(duration, 2) if duration > 0 else None
    except Exception:  # noqa: BLE001
        logger.warning("ffprobe 解析失败：%s", path, exc_info=True)
        return None


class FfmpegComposer:
    """VideoComposer 的 ffmpeg 实现。"""

    async def compose(self, items: list[ComposeItem], out_path: Path) -> None:
        if shutil.which("ffmpeg") is None:
            raise ComposeError("ffmpeg 不可用：请先安装 ffmpeg（含 libx264 的完整版本）")
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="av-compose-") as tmp:
            work = Path(tmp)
            durations: list[float] = []
            segments: list[Path] = []
            for i, item in enumerate(items):
                video_dur = await probe_duration(item.video) or 5.0
                audio_dur = await probe_duration(item.audio) or video_dur
                duration = round(max(video_dur, audio_dur), 2)
                seg = work / f"seg_{i:03d}.mp4"
                await _run_cmd(build_segment_cmd(item.video, item.audio, duration, seg))
                durations.append(duration)
                segments.append(seg)

            concat_list = work / "list.txt"
            concat_list.write_text(
                "".join(f"file '{seg.as_posix()}'\n" for seg in segments), encoding="utf-8"
            )
            merged = work / "merged.mp4"
            await _run_cmd(
                ["ffmpeg", "-y", "-f", "concat", "-safe", "0",
                 "-i", str(concat_list), "-c", "copy", str(merged)]
            )

            srt = work / "subs.srt"
            srt.write_text(
                build_srt([(item.line_en, d) for item, d in zip(items, durations)]),
                encoding="utf-8",
            )
            await _run_cmd(
                ["ffmpeg", "-y", "-i", str(merged),
                 "-vf", f"subtitles={srt.as_posix()}",
                 "-c:a", "copy", str(out_path)]
            )

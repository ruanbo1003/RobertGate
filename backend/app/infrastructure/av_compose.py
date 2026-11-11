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

__all__ = ["ComposeItem", "FfmpegComposer", "probe_duration", "has_audio_stream",
           "build_srt", "build_segment_cmd", "format_srt_timestamp", "offset_subtitles",
           "ComposeError"]


class ComposeError(RuntimeError):
    pass


# ---------------- 纯函数 ----------------


def format_srt_timestamp(seconds: float) -> str:
    ms = round(seconds * 1000)
    h, rem = divmod(ms, 3_600_000)
    m, rem = divmod(rem, 60_000)
    s, ms = divmod(rem, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def build_srt(entries: list[tuple[str, float, float]]) -> str:
    """(台词, 起, 止) 列表 → SRT 文本；空台词跳过字幕块。全局偏移由调用方累加好传入。"""
    blocks: list[str] = []
    index = 1
    for line, start, end in entries:
        if not line.strip():
            continue
        blocks.append(
            f"{index}\n{format_srt_timestamp(start)} --> {format_srt_timestamp(end)}\n{line.strip()}"
        )
        index += 1
    return "\n\n".join(blocks) + "\n"


def offset_subtitles(
    segments: list[tuple[list[tuple[str, float, float]], float]]
) -> list[tuple[str, float, float]]:
    """把各镜内部字幕（相对 0 起点）按镜时长累加成全局时间轴。"""
    out: list[tuple[str, float, float]] = []
    cursor = 0.0
    for subtitles, duration in segments:
        for text, start, end in subtitles:
            out.append((text, cursor + start, cursor + end))
        cursor += duration
    return out


def build_segment_cmd(
    video: Path,
    audio: Path | None,
    duration: float,
    out: Path,
    ffmpeg_bin: str = "ffmpeg",
    has_embedded_audio: bool = True,
) -> list[str]:
    """单镜分段命令：归一化到 720x1280（各模型出图/出视频分辨率不一，
    concat 阶段 -c copy 要求分段同参数），视频末帧定格补齐到 duration。

    audio 为 Path：与独立配音混流（旧 TTS 链路）。audio 为 None：
    has_embedded_audio=True（对白镜，视频自带音轨）→ 映射 0:a；
    has_embedded_audio=False（纯画面镜，视频本身无音轨）→ 补一路
    anullsrc 静音输入，保证所有分段流结构一致（否则 concat -c copy
    会因为有声/无声分段混杂而破坏输出，见 Task 终审 P0-2）。
    """
    extra_audio_input: list[str] = []
    if audio is not None:
        inputs = [str(video), str(audio)]
        audio_map = "1:a"
    elif has_embedded_audio:
        inputs = [str(video)]
        audio_map = "0:a?"
    else:
        inputs = [str(video)]
        extra_audio_input = [
            "-f", "lavfi", "-i", f"anullsrc=channel_layout=stereo:sample_rate=48000",
        ]
        audio_map = "1:a"  # anullsrc 是第二路输入
    cmd = [ffmpeg_bin, "-y"]
    for path in inputs:
        cmd += ["-i", path]
    cmd += extra_audio_input
    cmd += [
        "-filter_complex",
        (
            "[0:v]scale=720:1280:force_original_aspect_ratio=decrease,"
            "pad=720:1280:(ow-iw)/2:(oh-ih)/2:black,setsar=1,"
            f"tpad=stop_mode=clone:stop_duration={duration}[v]"
        ),
        "-map", "[v]",
        "-map", audio_map,
        "-t", str(duration),
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-r", "30",
        str(out),
    ]
    return cmd


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


async def probe_duration(path: Path, ffprobe_bin: str = "ffprobe") -> float | None:
    """ffprobe 读媒体时长（秒）；ffprobe 不可用或解析失败返回 None。"""
    if shutil.which(ffprobe_bin) is None:
        return None
    try:
        proc = await asyncio.create_subprocess_exec(
            ffprobe_bin, "-v", "quiet", "-print_format", "json",
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


async def has_audio_stream(path: Path, ffprobe_bin: str = "ffprobe") -> bool:
    """探测媒体文件是否含音频流；ffprobe 不可用或探测失败按"有音轨"处理
    （更安全的默认——漏判成无声比误加静音源更不容易被发现）。"""
    if shutil.which(ffprobe_bin) is None:
        return True
    try:
        proc = await asyncio.create_subprocess_exec(
            ffprobe_bin, "-v", "error", "-select_streams", "a",
            "-show_entries", "stream=codec_type", "-of", "csv=p=0", str(path),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await proc.communicate()
        if proc.returncode != 0:
            return True
        return bool(stdout.decode().strip())
    except Exception:  # noqa: BLE001
        logger.warning("ffprobe 探测音轨失败：%s", path, exc_info=True)
        return True


class FfmpegComposer:
    """VideoComposer 的 ffmpeg 实现。

    ffmpeg_bin/ffprobe_bin 可配置（AV_FFMPEG_BIN/AV_FFPROBE_BIN）：macOS 上
    Homebrew 瘦身版 ffmpeg 没有烧字幕所需的 subtitles/libass，需指向 ffmpeg-full。
    """

    def __init__(self, ffmpeg_bin: str = "ffmpeg", ffprobe_bin: str = "ffprobe") -> None:
        self._ffmpeg = ffmpeg_bin
        self._ffprobe = ffprobe_bin

    async def probe_duration(self, path: Path) -> float | None:
        return await probe_duration(path, self._ffprobe)

    async def compose(self, items: list[ComposeItem], out_path: Path) -> None:
        if shutil.which(self._ffmpeg) is None:
            raise ComposeError("ffmpeg 不可用：请先安装 ffmpeg（含 libx264/libass 的完整版本）")
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="av-compose-") as tmp:
            work = Path(tmp)
            segments: list[Path] = []
            durations: list[float] = []
            for i, item in enumerate(items):
                video_dur = await probe_duration(item.video, self._ffprobe) or 5.0
                if item.audio is not None:
                    audio_dur = await probe_duration(item.audio, self._ffprobe) or video_dur
                    duration = round(max(video_dur, audio_dur), 2)
                    has_embedded_audio = True  # 未使用（audio 非 None 分支忽略该参数）
                else:
                    duration = round(video_dur, 2)
                    has_embedded_audio = await has_audio_stream(item.video, self._ffprobe)
                seg = work / f"seg_{i:03d}.mp4"
                await _run_cmd(
                    build_segment_cmd(
                        item.video, item.audio, duration, seg, self._ffmpeg,
                        has_embedded_audio=has_embedded_audio,
                    )
                )
                durations.append(duration)
                segments.append(seg)

            all_subtitles = offset_subtitles(
                [(item.subtitles, d) for item, d in zip(items, durations)]
            )

            concat_list = work / "list.txt"
            concat_list.write_text(
                "".join(f"file '{seg.as_posix()}'\n" for seg in segments), encoding="utf-8"
            )
            merged = work / "merged.mp4"
            await _run_cmd(
                [self._ffmpeg, "-y", "-f", "concat", "-safe", "0",
                 "-i", str(concat_list), "-c", "copy", str(merged)]
            )

            srt = work / "subs.srt"
            srt.write_text(build_srt(all_subtitles), encoding="utf-8")
            await _run_cmd(
                [self._ffmpeg, "-y", "-i", str(merged),
                 "-vf", f"subtitles={srt.as_posix()}",
                 "-c:a", "copy", str(out_path)]
            )

"""ffmpeg 合成器纯函数测试：SRT 字幕构建、时间戳格式、分段命令。"""

from __future__ import annotations

from pathlib import Path

from app.infrastructure.av_compose import (
    build_segment_cmd,
    build_srt,
    format_srt_timestamp,
)


class TestSrtTimestamp:
    def test_zero(self):
        assert format_srt_timestamp(0.0) == "00:00:00,000"

    def test_fractional_and_carry(self):
        assert format_srt_timestamp(5.25) == "00:00:05,250"
        assert format_srt_timestamp(61.5) == "00:01:01,500"
        assert format_srt_timestamp(3601.001) == "01:00:01,001"


class TestBuildSrt:
    def test_sequential_entries_accumulate_time(self):
        srt = build_srt([("Hello!", 2.0), ("Bye bye!", 3.0)])
        blocks = srt.strip().split("\n\n")
        assert len(blocks) == 2
        assert blocks[0].splitlines() == [
            "1",
            "00:00:00,000 --> 00:00:02,000",
            "Hello!",
        ]
        assert blocks[1].splitlines() == [
            "2",
            "00:00:02,000 --> 00:00:05,000",
            "Bye bye!",
        ]

    def test_empty_line_skipped_but_time_advances(self):
        srt = build_srt([("", 2.0), ("Hi!", 1.0)])
        blocks = srt.strip().split("\n\n")
        assert len(blocks) == 1
        assert "00:00:02,000 --> 00:00:03,000" in blocks[0]


class TestSegmentCmd:
    def test_pads_video_to_audio_duration(self):
        cmd = build_segment_cmd(
            video=Path("v.mp4"),
            audio=Path("a.mp3"),
            duration=6.5,
            out=Path("seg.mp4"),
        )
        assert cmd[0] == "ffmpeg"
        joined = " ".join(cmd)
        assert "tpad=stop_mode=clone" in joined
        assert "-t 6.5" in joined
        assert str(Path("seg.mp4")) == cmd[-1]


class TestSegmentNormalization:
    def test_segment_normalizes_to_720x1280_before_pad(self):
        cmd = build_segment_cmd(Path("v.mp4"), Path("a.mp3"), 5.0, Path("out.mp4"))
        fc = cmd[cmd.index("-filter_complex") + 1]
        assert "scale=720:1280:force_original_aspect_ratio=decrease" in fc
        assert "pad=720:1280:(ow-iw)/2:(oh-ih)/2" in fc
        assert "setsar=1" in fc
        # 归一化在前，末帧定格在后
        assert fc.index("scale=720:1280") < fc.index("tpad=")

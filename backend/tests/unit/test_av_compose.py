"""ffmpeg 合成器纯函数测试：SRT 字幕构建、时间戳格式、分段命令。"""

from __future__ import annotations

from pathlib import Path

from app.infrastructure.av_compose import (
    build_segment_cmd,
    build_srt,
    format_srt_timestamp,
    offset_subtitles,
)


class TestSrtTimestamp:
    def test_zero(self):
        assert format_srt_timestamp(0.0) == "00:00:00,000"

    def test_fractional_and_carry(self):
        assert format_srt_timestamp(5.25) == "00:00:05,250"
        assert format_srt_timestamp(61.5) == "00:01:01,500"
        assert format_srt_timestamp(3601.001) == "01:00:01,001"


class TestBuildSrt:
    def test_explicit_start_end_entries(self):
        srt = build_srt([("Hello!", 0.0, 2.0), ("Bye bye!", 2.0, 5.0)])
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

    def test_empty_line_skipped(self):
        srt = build_srt([("", 2.0, 3.0), ("Hi!", 3.0, 4.0)])
        blocks = srt.strip().split("\n\n")
        assert len(blocks) == 1
        assert "00:00:03,000 --> 00:00:04,000" in blocks[0]

    def test_offsets_are_not_recomputed_by_build_srt(self):
        # 全局偏移由调用方（compose 组装阶段）累加好，build_srt 只管格式化
        srt = build_srt([("Mid-clip line", 10.5, 12.0)])
        assert "00:00:10,500 --> 00:00:12,000" in srt


class TestOffsetSubtitles:
    def test_offsets_accumulate_by_preceding_duration(self):
        result = offset_subtitles([
            ([("Hi", 0.0, 2.0)], 5.0),
            ([("Bye", 0.0, 3.0)], 3.0),
        ])
        assert result == [("Hi", 0.0, 2.0), ("Bye", 5.0, 8.0)]

    def test_mixed_mux_and_dialogue_offsets_correctly(self):
        # 镜1 走 mux（单条字幕覆盖全镜），镜2 走对白对齐（多条子字幕）——混排项目的全局偏移
        result = offset_subtitles([
            ([("Line one", 0.0, 4.0)], 4.0),
            ([("Hello", 0.0, 1.0), ("Hi", 1.0, 2.5)], 2.5),
        ])
        assert result == [
            ("Line one", 0.0, 4.0),
            ("Hello", 4.0, 5.0),
            ("Hi", 5.0, 6.5),
        ]


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

    def test_audio_none_omits_second_input_and_maps_embedded_audio(self):
        cmd = build_segment_cmd(
            video=Path("v.mp4"), audio=None, duration=8.0, out=Path("seg.mp4")
        )
        # 只有一个 -i（视频），没有第二路音频输入
        assert cmd.count("-i") == 1
        joined = " ".join(cmd)
        assert "a.mp3" not in joined
        assert "-map 0:a?" in joined
        assert "-map [v]" in joined
        assert "-c:a aac" in joined


class TestSegmentNormalization:
    def test_segment_normalizes_to_720x1280_before_pad(self):
        cmd = build_segment_cmd(Path("v.mp4"), Path("a.mp3"), 5.0, Path("out.mp4"))
        fc = cmd[cmd.index("-filter_complex") + 1]
        assert "scale=720:1280:force_original_aspect_ratio=decrease" in fc
        assert "pad=720:1280:(ow-iw)/2:(oh-ih)/2" in fc
        assert "setsar=1" in fc
        # 归一化在前，末帧定格在后
        assert fc.index("scale=720:1280") < fc.index("tpad=")

    def test_segment_cmd_uses_configured_ffmpeg_bin(self):
        cmd = build_segment_cmd(
            Path("v.mp4"), Path("a.mp3"), 5.0, Path("out.mp4"),
            ffmpeg_bin="/opt/ffmpeg-full/bin/ffmpeg",
        )
        assert cmd[0] == "/opt/ffmpeg-full/bin/ffmpeg"

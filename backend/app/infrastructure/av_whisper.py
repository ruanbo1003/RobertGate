"""对白镜字幕：faster-whisper 词级时间戳转写（薄执行层，纯算法见 av_subtitle.py）。

模型懒加载（首次调用才下载/加载，CPU 可跑，small 档够用）；不进单测，
集成行为由真机冒烟（Task 11）验证。

音频解码走项目自带 ffmpeg 命令行（非 faster-whisper 内置的 PyAV 路径）：
PyAV 新版本（19.x）移除了 faster-whisper 硬编码调用的 `metadata_errors`
参数，装哪个版本都可能和系统 ffmpeg 头文件冲突编译失败。传 numpy 数组
给 `model.transcribe()` 会完全跳过 PyAV 解码分支，绕开这个上游兼容性坑。
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import numpy as np


class WhisperAligner:
    def __init__(self, model_size: str = "small", ffmpeg_bin: str = "ffmpeg") -> None:
        self._model_size = model_size
        self._ffmpeg_bin = ffmpeg_bin
        self._model = None

    def _get_model(self):
        if self._model is None:
            from faster_whisper import WhisperModel

            self._model = WhisperModel(self._model_size, device="cpu", compute_type="int8")
        return self._model

    def _decode_mono16k(self, media: Path) -> np.ndarray:
        cmd = [
            self._ffmpeg_bin, "-v", "error", "-i", str(media),
            "-f", "f32le", "-ar", "16000", "-ac", "1", "pipe:1",
        ]
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if proc.returncode != 0:
            raise RuntimeError(f"ffmpeg 音频解码失败：{proc.stderr.decode(errors='replace')[:300]}")
        return np.frombuffer(proc.stdout, dtype=np.float32)

    def transcribe_words(self, media: Path) -> list[tuple[str, float, float]]:
        """返回媒体文件里识别出的词序列 [(word, start, end), ...]，按时间顺序。"""
        model = self._get_model()
        audio = self._decode_mono16k(media)
        segments, _info = model.transcribe(audio, word_timestamps=True)
        words: list[tuple[str, float, float]] = []
        for segment in segments:
            for word in segment.words or []:
                words.append((word.word.strip(), word.start, word.end))
        return words

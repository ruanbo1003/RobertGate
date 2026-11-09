"""对白镜字幕：faster-whisper 词级时间戳转写（薄执行层，纯算法见 av_subtitle.py）。

模型懒加载（首次调用才下载/加载，CPU 可跑，small 档够用）；不进单测，
集成行为由真机冒烟（Task 11）验证。
"""

from __future__ import annotations

from pathlib import Path


class WhisperAligner:
    def __init__(self, model_size: str = "small") -> None:
        self._model_size = model_size
        self._model = None

    def _get_model(self):
        if self._model is None:
            from faster_whisper import WhisperModel

            self._model = WhisperModel(self._model_size, device="cpu", compute_type="int8")
        return self._model

    def transcribe_words(self, media: Path) -> list[tuple[str, float, float]]:
        """返回媒体文件里识别出的词序列 [(word, start, end), ...]，按时间顺序。"""
        model = self._get_model()
        segments, _info = model.transcribe(str(media), word_timestamps=True)
        words: list[tuple[str, float, float]] = []
        for segment in segments:
            for word in segment.words or []:
                words.append((word.word.strip(), word.start, word.end))
        return words

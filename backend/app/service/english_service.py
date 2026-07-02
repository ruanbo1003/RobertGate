from __future__ import annotations

import random

from app.core.exceptions import ParamException
from app.data.english_data import ENGLISH_THEMES, get_theme


class EnglishService:
    def list_themes(self) -> dict:
        # 直接返回预定义元数据
        return {"themes": ENGLISH_THEMES}

    def generate_quiz(self, theme_id: str, count: int = 10) -> dict:
        theme = get_theme(theme_id)
        if not theme:
            raise ParamException(2008, "theme_id 不存在")
        if not theme["ready"]:
            raise ParamException(2009, "主题尚未准备完毕")

        # 收集所有主题的图片作为潜在干扰项
        all_images = [
            w["image_url"] for t in ENGLISH_THEMES for w in t["words"]
        ]

        rng = random.Random()
        theme_words = theme["words"]
        if not theme_words:
            raise ParamException(2009, "主题尚未准备完毕")

        questions = []
        for i in range(count):
            target = theme_words[i % len(theme_words)]
            distractor_pool = [u for u in all_images if u != target["image_url"]]
            distractors = rng.sample(distractor_pool, k=min(3, len(distractor_pool)))
            options = [target["image_url"], *distractors]
            rng.shuffle(options)
            correct_index = options.index(target["image_url"])
            questions.append(
                {
                    "word": target["word"],
                    "translation": target["translation"],
                    "options": options,
                    "correct_index": correct_index,
                }
            )
        return {"theme_id": theme_id, "questions": questions}

"""英文启蒙主题 / 单词 / 图片元数据。

图片文件预生成存于 /root/images/english/{theme_id}/{word}.png，
后端通过静态挂载对外提供 URL：/images/english/{theme_id}/{word}.png。
"""

from typing import TypedDict


class WordItem(TypedDict):
    word: str
    translation: str
    image_url: str


class ThemeItem(TypedDict):
    id: str
    name_en: str
    name_zh: str
    emoji: str
    ready: bool
    words: list[WordItem]


def _word(theme: str, word: str, zh: str) -> WordItem:
    return {
        "word": word,
        "translation": zh,
        "image_url": f"/images/english/{theme}/{word}.png",
    }


ENGLISH_THEMES: list[ThemeItem] = [
    {
        "id": "colors",
        "name_en": "Colors",
        "name_zh": "颜色",
        "emoji": "🎨",
        "ready": True,
        "words": [
            _word("colors", "red", "红色"),
            _word("colors", "blue", "蓝色"),
            _word("colors", "yellow", "黄色"),
            _word("colors", "green", "绿色"),
        ],
    },
    {
        "id": "animals",
        "name_en": "Animals",
        "name_zh": "动物",
        "emoji": "🐶",
        "ready": True,
        "words": [
            _word("animals", "dog", "狗"),
            _word("animals", "cat", "猫"),
            _word("animals", "bird", "鸟"),
            _word("animals", "fish", "鱼"),
        ],
    },
    {
        "id": "shapes",
        "name_en": "Shapes",
        "name_zh": "形状",
        "emoji": "🔷",
        "ready": True,
        "words": [
            _word("shapes", "circle", "圆形"),
            _word("shapes", "square", "方形"),
            _word("shapes", "triangle", "三角形"),
            _word("shapes", "star", "星形"),
        ],
    },
    {
        "id": "fruits",
        "name_en": "Fruits",
        "name_zh": "水果",
        "emoji": "🍎",
        "ready": False,
        "words": [],
    },
]


def get_theme(theme_id: str) -> ThemeItem | None:
    return next((t for t in ENGLISH_THEMES if t["id"] == theme_id), None)

"""基于 LangChain + OpenRouter 的 AIClient 实现。

只覆盖翻译相关的三个方法（translate / grammar_correct / rewrite_native）。
其余 AIClient Protocol 方法（practice_text / generate_image）
委托给内嵌的 MockAIClient，避免影响 hanzi / t2i 等其它模块。
"""

from __future__ import annotations

from langchain_core.output_parsers import JsonOutputParser, StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from app.service.ai_client import MockAIClient, _is_chinese


# --- Prompts ---

TRANSLATE_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "你是一名专业翻译。请把用户输入的文本进行{direction}。\n"
            "要求：\n"
            "1. 只输出翻译结果本身，不要添加任何解释、注释、引号或 markdown。\n"
            "2. 保留原文的语气、标点风格和段落结构。\n"
            "3. 遇到专有名词、代码、数字、URL 保持不变。",
        ),
        ("user", "{text}"),
    ]
)

GRAMMAR_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "你是一名英语语言老师。请修正用户输入的英文段落里的语法、拼写和用词错误。\n"
            "要求：\n"
            "1. 只输出修正后的完整文本，不要解释、不要标注修改位置、不要 markdown。\n"
            "2. 保留原意和作者的语气，不要过度改写。\n"
            "3. 如果原文没有错误，原样返回。",
        ),
        ("user", "{text}"),
    ]
)

NATIVE_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "你是一位英语母语作家。请把用户输入的英文改写得更地道、自然、符合母语者表达习惯。\n"
            "要求：\n"
            "1. 只输出改写后的完整文本，不要解释、不要 markdown、不要引号。\n"
            "2. 意思不变，风格可以更自然口语化或书面化，视原文场景而定。\n"
            "3. 避免过度修饰，保持简洁清晰。",
        ),
        ("user", "{text}"),
    ]
)

CHARACTER_INFO_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "你是一名中文教师，请为下面这个汉字生成学习资料。\n"
            "要求：\n"
            "1. 只输出 JSON，字段固定为 pinyin（string，带声调的拼音，多音字取最常用读音）"
            "和 words（长度恰好为 4 的 string 数组，每个是包含该字的常见双字词）。\n"
            "2. words 要贴近日常，避免生僻词、成语、专有名词。\n"
            "3. 不要解释、不要 markdown、不要额外键。\n"
            "示例：输入「字」→ {{\"pinyin\": \"zì\", \"words\": [\"文字\", \"字体\", \"字幕\", \"汉字\"]}}",
        ),
        ("user", "{char}"),
    ]
)

PRACTICE_TEXT_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "你是一名儿童中文启蒙老师，请为 4-8 岁小朋友生成一段练习短文。\n"
            "已学字（他们能认得的字）：{learned_chars}\n"
            "要求：\n"
            "1. 生成一段 20-40 个汉字的简单短文，尽量使用已学字。\n"
            "2. 允许出现少量（约 10-20%）的常见简单新字，让内容自然。\n"
            "3. 主题贴近生活：家庭、动物、天气、食物、玩耍等。\n"
            "4. 只输出 JSON，字段：text（string，短文本身，可以含标点），"
            "annotations（数组，text 中每个汉字给出 {{char, pinyin}}，非汉字跳过），"
            "new_chars（数组，本次用到的、不在已学字里的汉字，去重）。\n"
            "5. pinyin 必须带声调，不加空格。\n"
            "6. 不要 markdown、不要解释、不要额外字段。",
        ),
        (
            "user",
            "已学字数量：{count}。请生成一段简单练习短文。",
        ),
    ]
)


class OpenRouterAIClient:
    """真实 AI 客户端：翻译 3 个动作走 OpenRouter，其余方法委托给 Mock。"""

    def __init__(self, api_key: str, model: str, base_url: str) -> None:
        self._llm = ChatOpenAI(
            model=model,
            api_key=api_key,
            base_url=base_url,
            temperature=0.3,
            timeout=30,
        )
        self._fallback = MockAIClient()

    async def _run(self, prompt: ChatPromptTemplate, variables: dict) -> str:
        chain = prompt | self._llm | StrOutputParser()
        out = await chain.ainvoke(variables)
        return out.strip()

    async def translate(self, text: str) -> tuple[str, str, str]:
        if _is_chinese(text):
            source, target = "zh", "en"
            direction = "中文翻译成英文"
        else:
            source, target = "en", "zh"
            direction = "英文翻译成中文"
        result = await self._run(TRANSLATE_PROMPT, {"text": text, "direction": direction})
        return source, target, result

    async def grammar_correct(self, text: str) -> str:
        return await self._run(GRAMMAR_PROMPT, {"text": text})

    async def rewrite_native(self, text: str) -> str:
        return await self._run(NATIVE_PROMPT, {"text": text})

    async def character_info(self, char: str) -> dict:
        """返回 {pinyin, words: [4 词]}。上层用不到 sentence/sentence_pinyin，置空。"""
        chain = (
            CHARACTER_INFO_PROMPT
            | self._llm.bind(response_format={"type": "json_object"})
            | JsonOutputParser()
        )
        out = await chain.ainvoke({"char": char})
        pinyin = str(out.get("pinyin", "")).strip()
        words_raw = out.get("words", []) or []
        words = [str(w).strip() for w in words_raw if str(w).strip()][:4]
        if not pinyin:
            raise ValueError("AI 返回缺少 pinyin")
        if len(words) < 1:
            raise ValueError("AI 返回缺少 words")
        return {
            "pinyin": pinyin,
            "words": words,
            "sentence": "",
            "sentence_pinyin": "",
        }

    # --- 未实现的能力，委托给 Mock ---

    async def practice_text(self, learned_chars: list[str]) -> dict:
        """返回 {text, annotations: [{char, pinyin}], new_chars}."""
        chain = (
            PRACTICE_TEXT_PROMPT
            | self._llm.bind(response_format={"type": "json_object"})
            | JsonOutputParser()
        )
        out = await chain.ainvoke(
            {
                "learned_chars": "、".join(learned_chars) if learned_chars else "（无）",
                "count": len(learned_chars),
            }
        )
        text = str(out.get("text") or "").strip()
        if not text:
            raise ValueError("AI 返回缺少 text")
        annotations = out.get("annotations") or []
        new_chars = out.get("new_chars") or []
        return {
            "text": text,
            "annotations": annotations if isinstance(annotations, list) else [],
            "new_chars": new_chars if isinstance(new_chars, list) else [],
        }

    async def generate_image(self, prompt: str) -> str:
        return await self._fallback.generate_image(prompt)

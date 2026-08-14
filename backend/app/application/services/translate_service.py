from app.application.ports import AIClient
from app.application.services._ai import ai_call


class TranslateService:
    def __init__(self, ai: AIClient) -> None:
        self.ai = ai

    async def translate(self, text: str) -> dict:
        source, target, result = await ai_call(self.ai.translate(text))
        return {"source_lang": source, "target_lang": target, "result": result}

    async def grammar(self, text: str) -> dict:
        result = await ai_call(self.ai.grammar_correct(text))
        return {"source_lang": "en", "target_lang": "en", "result": result}

    async def native(self, text: str) -> dict:
        result = await ai_call(self.ai.rewrite_native(text))
        return {"source_lang": "en", "target_lang": "en", "result": result}

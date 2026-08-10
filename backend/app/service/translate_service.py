from app.core.exceptions import ServerException
from app.service.ai_client import AIClient


class TranslateService:
    def __init__(self, ai: AIClient) -> None:
        self.ai = ai

    async def translate(self, text: str) -> dict:
        try:
            source, target, result = await self.ai.translate(text)
        except ServerException:
            raise
        except Exception as e:
            raise ServerException(5001, f"AI 服务不可用: {e}") from e
        return {"source_lang": source, "target_lang": target, "result": result}

    async def grammar(self, text: str) -> dict:
        try:
            result = await self.ai.grammar_correct(text)
        except ServerException:
            raise
        except Exception as e:
            raise ServerException(5001, f"AI 服务不可用: {e}") from e
        return {"source_lang": "en", "target_lang": "en", "result": result}

    async def native(self, text: str) -> dict:
        try:
            result = await self.ai.rewrite_native(text)
        except ServerException:
            raise
        except Exception as e:
            raise ServerException(5001, f"AI 服务不可用: {e}") from e
        return {"source_lang": "en", "target_lang": "en", "result": result}

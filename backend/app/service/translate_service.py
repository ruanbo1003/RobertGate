from app.core.exceptions import ServerException
from app.schemas.ai_tools import TranslateAction
from app.service.ai_client import AIClient


class TranslateService:
    def __init__(self, ai: AIClient) -> None:
        self.ai = ai

    async def process(self, text: str, action: TranslateAction) -> dict:
        try:
            if action == "translate":
                source, target, result = await self.ai.translate(text)
            elif action == "grammar":
                source, target = "en", "en"
                result = await self.ai.grammar_correct(text)
            elif action == "native":
                source, target = "en", "en"
                result = await self.ai.rewrite_native(text)
            else:
                raise ValueError("action 非法")
        except ServerException:
            raise
        except Exception as e:
            raise ServerException(5001, f"AI 服务不可用: {e}") from e

        return {
            "action": action,
            "source_lang": source,
            "target_lang": target,
            "result": result,
        }

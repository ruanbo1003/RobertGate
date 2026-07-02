from datetime import datetime, timezone

from app.core.exceptions import ServerException
from app.service.ai_client import AIClient


class T2IService:
    def __init__(self, ai: AIClient) -> None:
        self.ai = ai

    async def generate(self, prompt: str) -> dict:
        try:
            url = await self.ai.generate_image(prompt)
        except Exception as e:
            raise ServerException(5001, f"AI 服务不可用: {e}") from e
        return {
            "prompt": prompt,
            "image_url": url,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

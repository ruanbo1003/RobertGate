from datetime import datetime, timezone

from app.application.ports import AIClient
from app.application.services._ai import ai_call


class T2IService:
    def __init__(self, ai: AIClient) -> None:
        self.ai = ai

    async def generate(self, prompt: str) -> dict:
        url = await ai_call(self.ai.generate_image(prompt))
        return {
            "prompt": prompt,
            "image_url": url,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

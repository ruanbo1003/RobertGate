from pydantic import BaseModel


class PatchImageRequest(BaseModel):
    available: bool


class CreateTemplateRequest(BaseModel):
    code: str
    name: str
    description: str | None = None
    prompt: str
    order_index: int | None = None


class UpdateTemplateRequest(BaseModel):
    """PUT 语义：全量替换。description 传空串等价于清空。"""

    name: str
    description: str | None = None
    prompt: str
    order_index: int | None = None

from unittest.mock import AsyncMock

import pytest

from app.core.exceptions import ServerException
from app.service.t2i_service import T2IService


@pytest.fixture
def ai():
    return AsyncMock()


@pytest.fixture
def service(ai):
    return T2IService(ai=ai)


@pytest.mark.asyncio
async def test_generate_success(service, ai):
    ai.generate_image.return_value = "/images/t2i/x.png"

    result = await service.generate("a watercolor cat")

    assert result["prompt"] == "a watercolor cat"
    assert result["image_url"] == "/images/t2i/x.png"
    assert result["created_at"]


@pytest.mark.asyncio
async def test_generate_ai_failure(service, ai):
    ai.generate_image.side_effect = RuntimeError("gen down")
    with pytest.raises(ServerException) as exc_info:
        await service.generate("cat")
    assert exc_info.value.code == 5001

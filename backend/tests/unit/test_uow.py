"""SqlUnitOfWork：仓储惰性创建、同一 session 复用、commit/rollback 转发。"""

from unittest.mock import AsyncMock

import pytest

from app.infrastructure.repositories.uow import SqlUnitOfWork

REPO_ATTRS = (
    "users",
    "hanzi_levels",
    "hanzi_characters",
    "hanzi_progress",
    "t2i_templates",
    "t2i_tasks",
    "t2i_images",
    "t2i_blobs",
)


@pytest.fixture
def session():
    return AsyncMock()


@pytest.fixture
def uow(session):
    return SqlUnitOfWork(session)


@pytest.mark.parametrize("attr", REPO_ATTRS)
def test_repo_is_cached_and_shares_session(uow, session, attr):
    repo = getattr(uow, attr)
    assert getattr(uow, attr) is repo  # cached_property：同一实例
    assert repo.session is session


def test_all_uow_repos_present(uow):
    for attr in REPO_ATTRS:
        assert getattr(uow, attr) is not None


@pytest.mark.asyncio
async def test_commit_delegates_to_session(uow, session):
    await uow.commit()
    session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_rollback_delegates_to_session(uow, session):
    await uow.rollback()
    session.rollback.assert_awaited_once()

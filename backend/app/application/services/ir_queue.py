"""invest-reports 章节研究队列（Task 6 实现真实队列；当前为装配占位）。"""

from __future__ import annotations

from functools import lru_cache


class _NoopQueue:
    """占位实现：Task 6 落地 IrResearchQueue 后由 deps 换装。"""

    def counts(self, project_id: int) -> tuple[int, int]:
        return (0, 0)

    def cancel_project(self, project_id: int) -> int:
        return 0


@lru_cache
def get_noop_queue() -> _NoopQueue:
    return _NoopQueue()

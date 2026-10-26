"""知识库检索排序（余弦相似度 top-k）。"""

from __future__ import annotations

from app.infrastructure.legal.knowledge_base import top_k_by_cosine


class TestTopKByCosine:
    def test_ranks_by_similarity_descending(self) -> None:
        vectors = [
            (1, [1.0, 0.0]),
            (2, [0.0, 1.0]),
            (3, [0.9, 0.1]),
        ]
        result = top_k_by_cosine([1.0, 0.0], vectors, top_k=2, min_score=0.0)
        assert [no for no, _ in result] == [1, 3]

    def test_min_score_filters_irrelevant(self) -> None:
        vectors = [(1, [0.0, 1.0])]
        result = top_k_by_cosine([1.0, 0.0], vectors, top_k=4, min_score=0.3)
        assert result == []

    def test_top_k_caps_result_count(self) -> None:
        vectors = [(i, [1.0, 0.0]) for i in range(10)]
        result = top_k_by_cosine([1.0, 0.0], vectors, top_k=3, min_score=0.0)
        assert len(result) == 3

    def test_zero_vector_scores_zero(self) -> None:
        vectors = [(1, [0.0, 0.0])]
        result = top_k_by_cosine([1.0, 0.0], vectors, top_k=1, min_score=0.1)
        assert result == []

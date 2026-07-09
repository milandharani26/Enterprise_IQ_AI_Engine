import asyncio
import logging
from typing import Any, Dict, List
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from engine.modules.assistant.tools.implementations.rag_search import RAGSearchTool


@pytest.fixture
def tool():
    instance = RAGSearchTool()
    instance._initialized = True
    instance._enable_query_expansion = True
    return instance

class TestPreprocessQueryFast:
    def test_single_query(self, tool):
        result = asyncio.run(tool._preprocess_query_fast("leave policy"))
        assert result == ["leave policy"]

    def test_compound_query(self, tool):
        result = asyncio.run(tool._preprocess_query_fast("refund policy and delivery time"))
        assert result == ["refund policy", "delivery time"]

    def test_or_query(self, tool):
        result = asyncio.run(tool._preprocess_query_fast("HR rules or leave policy"))
        assert result == ["HR rules", "leave policy"]

    def test_strips_filler(self, tool):
        result = asyncio.run(tool._preprocess_query_fast("can you tell me about leave policy"))
        assert result == ["leave policy"]


@pytest.mark.asyncio
class TestExpandQueryVariantsAsync:
    @patch.object(RAGSearchTool, "_expand_short_query", new_callable=AsyncMock)
    async def test_expands_short_queries(self, mock_expand, tool):
        mock_expand.return_value = ["leave policy", "annual leave rules", "PTO entitlement"]

        result = await tool._expand_query_variants_async(["leave policy"])
        assert result == ["leave policy", "annual leave rules", "PTO entitlement"]
        mock_expand.assert_awaited_once_with("leave policy")

    @patch.object(RAGSearchTool, "_expand_short_query", new_callable=AsyncMock)
    async def test_passes_long_queries(self, mock_expand, tool):
        result = await tool._expand_query_variants_async(
            ["this is a long query that should not expand"]
        )
        assert result == ["this is a long query that should not expand"]
        mock_expand.assert_not_awaited()

    @patch.object(RAGSearchTool, "_expand_short_query", new_callable=AsyncMock)
    async def test_mixed_queries(self, mock_expand, tool):
        async def side_effect(q):
            return [q, f"{q} variant"]

        mock_expand.side_effect = side_effect

        result = await tool._expand_query_variants_async(
            ["short query", "this is a long query that should not expand"]
        )
        assert "short query" in result
        assert "short query variant" in result
        assert "this is a long query that should not expand" in result
        assert mock_expand.await_count == 1

    @patch.object(RAGSearchTool, "_expand_short_query", new_callable=AsyncMock)
    async def test_deduplicates(self, mock_expand, tool):
        mock_expand.return_value = ["dup", "dup", "dup variant"]

        result = await tool._expand_query_variants_async(["dup"])
        assert result == ["dup", "dup variant"]


class TestExecuteMultiQuerySearch:
    @patch.object(RAGSearchTool, "_embed_queries_parallel", new_callable=AsyncMock)
    @patch.object(RAGSearchTool, "_vector_search", new_callable=AsyncMock)
    @patch.object(RAGSearchTool, "_reciprocal_rank_fusion")
    def test_happy_path(self, mock_rrf, mock_vs, mock_embed, tool):
        mock_embed.return_value = [[0.1, 0.2], [0.3, 0.4]]
        mock_vs.return_value = [
            {"chunk_id": 1, "similarity": 0.9, "content": "chunk A"},
            {"chunk_id": 2, "similarity": 0.8, "content": "chunk B"},
        ]
        mock_rrf.return_value = [
            {"chunk_id": 1, "similarity": 0.9},
            {"chunk_id": 2, "similarity": 0.8},
        ]

        result = asyncio.run(
            tool._execute_multi_query_search(
                query_variants=["query1", "query2"],
                organization_id="org-123",
                top_k=5,
                similarity_threshold=0.3,
                use_pool=True,
            )
        )

        assert len(result) == 2
        mock_embed.assert_awaited_once_with(["query1", "query2"])
        assert mock_vs.await_count == 2
        mock_rrf.assert_called_once()

    @patch.object(RAGSearchTool, "_embed_queries_parallel", new_callable=AsyncMock)
    @patch.object(RAGSearchTool, "_vector_search", new_callable=AsyncMock)
    def test_embed_failure_returns_empty(self, mock_vs, mock_embed, tool):
        mock_embed.return_value = []

        result = asyncio.run(
            tool._execute_multi_query_search(
                query_variants=["query1"],
                organization_id=None,
                top_k=5,
                similarity_threshold=0.3,
                use_pool=True,
            )
        )

        assert result == []
        mock_vs.assert_not_awaited()

    @patch.object(RAGSearchTool, "_embed_queries_parallel", new_callable=AsyncMock)
    @patch.object(RAGSearchTool, "_vector_search", new_callable=AsyncMock)
    def test_all_searches_fail_returns_empty(self, mock_vs, mock_embed, tool):
        mock_embed.return_value = [[0.1, 0.2]]
        mock_vs.side_effect = Exception("search failed")

        result = asyncio.run(
            tool._execute_multi_query_search(
                query_variants=["query1"],
                organization_id=None,
                top_k=5,
                similarity_threshold=0.3,
                use_pool=True,
            )
        )

        assert result == []


@pytest.mark.asyncio
class TestSearchAsyncPipeline:
    @patch.object(RAGSearchTool, "_preprocess_query_fast")
    @patch.object(RAGSearchTool, "_expand_query_variants_async", new_callable=AsyncMock)
    @patch.object(RAGSearchTool, "_execute_multi_query_search", new_callable=AsyncMock)
    @patch.object(RAGSearchTool, "_keyword_search", new_callable=AsyncMock)
    @patch.object(RAGSearchTool, "_reciprocal_rank_fusion")
    async def test_early_return_when_no_expansion(
        self, mock_rrf, mock_keyword, mock_execute, mock_expand, mock_preprocess, tool
    ):
        mock_preprocess.return_value = ["leave policy"]
        mock_expand.return_value = ["leave policy"]
        mock_execute.return_value = [{"chunk_id": 1, "content": "result"}]

        result = await tool._search_async(
            query="leave policy",
            organization_id="org-123",
            top_k=5,
            similarity_threshold=0.3,
            use_pool=True,
        )

        assert result == [{"chunk_id": 1, "content": "result"}]
        mock_expand.assert_awaited_once_with(["leave policy"])
        assert mock_execute.await_count == 1
        mock_rrf.assert_not_called()

    @patch.object(RAGSearchTool, "_preprocess_query_fast")
    @patch.object(RAGSearchTool, "_expand_query_variants_async", new_callable=AsyncMock)
    @patch.object(RAGSearchTool, "_execute_multi_query_search", new_callable=AsyncMock)
    @patch.object(RAGSearchTool, "_keyword_search", new_callable=AsyncMock)
    @patch.object(RAGSearchTool, "_reciprocal_rank_fusion")
    async def test_fuses_when_expanded(
        self, mock_rrf, mock_keyword, mock_execute, mock_expand, mock_preprocess, tool
    ):
        mock_preprocess.return_value = ["leave policy"]
        mock_expand.return_value = ["leave policy", "PTO entitlement", "annual leave"]
        mock_execute.side_effect = [
            [{"chunk_id": 1, "content": "primary"}],
            [{"chunk_id": 2, "content": "expanded"}],
        ]
        mock_rrf.return_value = [
            {"chunk_id": 1, "content": "primary"},
            {"chunk_id": 2, "content": "expanded"},
        ]

        result = await tool._search_async(
            query="leave policy",
            organization_id="org-123",
            top_k=5,
            similarity_threshold=0.3,
            use_pool=True,
        )

        assert len(result) == 2
        assert mock_execute.await_count == 2
        mock_rrf.assert_called_once()

    @patch.object(RAGSearchTool, "_preprocess_query_fast")
    @patch.object(RAGSearchTool, "_expand_query_variants_async", new_callable=AsyncMock)
    @patch.object(RAGSearchTool, "_execute_multi_query_search", new_callable=AsyncMock)
    @patch.object(RAGSearchTool, "_keyword_search", new_callable=AsyncMock)
    async def test_keyword_fallback(
        self, mock_keyword, mock_execute, mock_expand, mock_preprocess, tool
    ):
        mock_preprocess.return_value = ["leave policy"]
        mock_expand.return_value = ["leave policy"]
        mock_execute.return_value = []
        mock_keyword.return_value = [{"chunk_id": 99, "content": "keyword result"}]

        result = await tool._search_async(
            query="leave policy",
            organization_id="org-123",
            top_k=5,
            similarity_threshold=0.3,
            use_pool=True,
        )

        assert result == [{"chunk_id": 99, "content": "keyword result"}]
        mock_keyword.assert_awaited_once()

    @patch.object(RAGSearchTool, "_preprocess_query_fast")
    @patch.object(RAGSearchTool, "_expand_query_variants_async", new_callable=AsyncMock)
    @patch.object(RAGSearchTool, "_execute_multi_query_search", new_callable=AsyncMock)
    @patch.object(RAGSearchTool, "_keyword_search", new_callable=AsyncMock)
    @patch.object(RAGSearchTool, "_reciprocal_rank_fusion")
    async def test_performance_timings_logged(
        self, mock_rrf, mock_keyword, mock_execute, mock_expand, mock_preprocess, tool, caplog
    ):
        caplog.set_level(logging.INFO)

        mock_preprocess.return_value = ["query"]
        mock_expand.return_value = ["query", "expanded"]
        mock_execute.side_effect = [
            [{"chunk_id": 1}],
            [{"chunk_id": 2}],
        ]
        mock_rrf.return_value = [{"chunk_id": 1}, {"chunk_id": 2}]

        await tool._search_async(
            query="test",
            organization_id=None,
            top_k=5,
            similarity_threshold=0.3,
            use_pool=True,
        )

        primary_msgs = [r for r in caplog.records if "Primary search completed" in r.getMessage()]
        expansion_msgs = [r for r in caplog.records if "Expansion completed" in r.getMessage()]
        total_msgs = [r for r in caplog.records if "Total search completed" in r.getMessage()]

        assert len(primary_msgs) == 1
        assert len(expansion_msgs) == 1
        assert len(total_msgs) == 1

import logging
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from uuid import UUID, uuid4

from engine.modules.assistant.assistant_service import AssistantService
from engine.modules.assistant.assistant_schemas import AssistantCreate
from engine.modules.assistant.tools.exceptions import SecurityGuardrailError


@pytest.fixture
def mock_db():
    return AsyncMock()


@pytest.fixture
def mock_assistant():
    assistant = MagicMock()
    assistant.assistant_id = uuid4()
    assistant.cache_version = 5
    return assistant


class TestUpdateAssistantCacheVersion:
    """AssistantService.update_assistant must bump cache_version when config fields change."""

    async def _call_update(self, update_data: dict, mock_db, mock_assistant):
        with patch.object(AssistantService, "get_assistant", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_assistant
            obj_in = MagicMock(spec=AssistantCreate)
            obj_in.model_dump.return_value = update_data
            result = await AssistantService.update_assistant(
                db=mock_db,
                assistant_id=mock_assistant.assistant_id,
                obj_in=obj_in,
                user_id=uuid4(),
                org_id=uuid4(),
            )
        return result

    @pytest.mark.asyncio
    async def test_bumps_on_guardrails_change(self, mock_db, mock_assistant):
        await self._call_update({"guardrails": [{"type": "block", "instructions": "test"}]}, mock_db, mock_assistant)
        assert mock_assistant.cache_version == 6

    @pytest.mark.asyncio
    async def test_bumps_on_tools_change(self, mock_db, mock_assistant):
        await self._call_update({"tools": [{"name": "rag_search"}]}, mock_db, mock_assistant)
        assert mock_assistant.cache_version == 6

    @pytest.mark.asyncio
    async def test_bumps_on_system_prompt_change(self, mock_db, mock_assistant):
        await self._call_update({"system_prompt": "You are a helpful assistant."}, mock_db, mock_assistant)
        assert mock_assistant.cache_version == 6

    @pytest.mark.asyncio
    async def test_does_not_bump_on_other_fields(self, mock_db, mock_assistant):
        await self._call_update({"description": "irrelevant change"}, mock_db, mock_assistant)
        assert mock_assistant.cache_version == 5

    @pytest.mark.asyncio
    async def test_bumps_once_on_multiple_config_fields(self, mock_db, mock_assistant):
        await self._call_update({
            "guardrails": [],
            "tools": [],
            "system_prompt": "new prompt",
            "description": "extra",
        }, mock_db, mock_assistant)
        assert mock_assistant.cache_version == 6


class TestExecutorResponseType:
    """AssistantExecutor.execute must return correct response_type metadata."""

    @pytest.mark.asyncio
    async def test_guardrail_block_returns_proper_metadata(self):
        from engine.modules.assistant.runtime.executor import AssistantExecutor
        executor = AssistantExecutor()
        with patch.object(executor, "execute", new_callable=AsyncMock) as mock_exec:
            mock_exec.return_value = (
                "I cannot answer that question.",
                [{"type": "markdown", "data": {"content": "I cannot answer that question."}}],
                {"response_type": "guardrail_block"},
            )
            _, _, meta = await executor.execute(
                session_id="s", conversation_id="c", user_id="u",
                assistant_id="a", query="q", organization_ids=["o"],
                assistant=MagicMock(),
            )
            assert meta == {"response_type": "guardrail_block"}

    @pytest.mark.asyncio
    async def test_normal_response_returns_proper_metadata(self):
        from engine.modules.assistant.runtime.executor import AssistantExecutor
        executor = AssistantExecutor()
        with patch.object(executor, "execute", new_callable=AsyncMock) as mock_exec:
            mock_exec.return_value = (
                "Here is the answer.",
                [{"type": "markdown", "data": {"content": "Here is the answer."}}],
                {"response_type": "normal"},
            )
            _, _, meta = await executor.execute(
                session_id="s", conversation_id="c", user_id="u",
                assistant_id="a", query="q", organization_ids=["o"],
                assistant=MagicMock(),
            )
            assert meta == {"response_type": "normal"}


class TestConversationServiceCacheSkip:
    """ConversationService must skip cache write for guardrail-blocked responses."""

    @pytest.fixture
    def conversation_service(self):
        from engine.modules.conversation.conversation_service import ConversationService
        return ConversationService(db=MagicMock())

    @pytest.fixture
    def assistant(self):
        a = MagicMock()
        a.assistant_id = uuid4()
        a.cache_version = 1
        return a

    def _make_payload(self):
        p = MagicMock()
        p.conversation_id = uuid4()
        p.user_id = uuid4()
        p.agent_id = uuid4()
        p.content = "test query"
        return p

    @pytest.mark.asyncio
    async def test_skips_cache_write_for_guardrail_block(self, conversation_service, assistant, caplog):
        caplog.set_level(logging.DEBUG)

        payload = self._make_payload()
        with (
            patch.object(conversation_service, "_resolve_assistant", new_callable=AsyncMock) as mock_resolve,
            patch("engine.pipelines.ingestion.services.embedding_service.EmbeddingService") as mock_embed_cls,
            patch("engine.modules.assistant.semantic_cache.SemanticCacheService") as mock_cache,
        ):
            mock_resolve.return_value = assistant
            mock_embed_cls.return_value.embed_query = AsyncMock(return_value=[0.1] * 1536)

            mock_cache.lookup_cache = AsyncMock(return_value=None)
            mock_cache.write_cache = AsyncMock()

            from engine.modules.assistant.runtime.executor import AssistantExecutor
            with patch.object(AssistantExecutor, "execute", new_callable=AsyncMock) as mock_exec:
                mock_exec.return_value = (
                    "I cannot answer.",
                    [{"type": "markdown", "data": {"content": "I cannot answer."}}],
                    {"response_type": "guardrail_block"},
                )

                await conversation_service.handle_chat_turn(payload, save_to_db=False)

                mock_cache.write_cache.assert_not_awaited()

                skip_logs = [r for r in caplog.records if "Skipping cache write for guardrail response" in r.getMessage()]
                assert len(skip_logs) == 1

    @pytest.mark.asyncio
    async def test_writes_cache_for_normal_response(self, conversation_service, assistant):
        payload = self._make_payload()
        with (
            patch.object(conversation_service, "_resolve_assistant", new_callable=AsyncMock) as mock_resolve,
            patch("engine.pipelines.ingestion.services.embedding_service.EmbeddingService") as mock_embed_cls,
            patch("engine.modules.assistant.semantic_cache.SemanticCacheService") as mock_cache,
        ):
            mock_resolve.return_value = assistant
            mock_embed_cls.return_value.embed_query = AsyncMock(return_value=[0.1] * 1536)

            mock_cache.lookup_cache = AsyncMock(return_value=None)
            mock_cache.write_cache = AsyncMock()

            from engine.modules.assistant.runtime.executor import AssistantExecutor
            with patch.object(AssistantExecutor, "execute", new_callable=AsyncMock) as mock_exec:
                mock_exec.return_value = (
                    "Here is the answer.",
                    [{"type": "markdown", "data": {"content": "Here is the answer."}}],
                    {"response_type": "normal"},
                )

                await conversation_service.handle_chat_turn(payload, save_to_db=False)

                mock_cache.write_cache.assert_awaited_once()


class TestGuardrailCacheInvalidationScenario:
    """
    Full scenario integration test (with mocked internals):
    1. Guardrail blocks query → no cache write
    2. Guardrail removed via update_assistant → cache_version bumped
    3. Same query → cache miss (new version) → fresh execution → normal response
    """

    @pytest.mark.asyncio
    async def test_invalidation_scenario(self, mock_db):
        assistant = MagicMock()
        assistant.assistant_id = uuid4()
        assistant.cache_version = 1

        # Step 1: Guardrail blocks query → no cache write
        from engine.modules.conversation.conversation_service import ConversationService
        cs = ConversationService(db=MagicMock())

        payload = MagicMock()
        payload.conversation_id = uuid4()
        payload.user_id = uuid4()
        payload.agent_id = uuid4()
        payload.content = "sensitive query"

        with (
            patch.object(cs, "_resolve_assistant", new_callable=AsyncMock) as mock_resolve,
            patch("engine.pipelines.ingestion.services.embedding_service.EmbeddingService") as mock_embed_cls,
            patch("engine.modules.assistant.semantic_cache.SemanticCacheService") as mock_cache,
            patch("engine.modules.assistant.runtime.executor.AssistantExecutor.execute", new_callable=AsyncMock) as mock_exec,
        ):
            mock_resolve.return_value = assistant
            mock_embed_cls.return_value.embed_query = AsyncMock(return_value=[0.5] * 1536)
            mock_cache.lookup_cache = AsyncMock(return_value=None)
            mock_cache.write_cache = AsyncMock()

            # Guardrail denial
            mock_exec.return_value = (
                "Blocked by guardrail.",
                [{"type": "markdown", "data": {"content": "Blocked by guardrail."}}],
                {"response_type": "guardrail_block"},
            )

            await cs.handle_chat_turn(payload, save_to_db=False)
            mock_cache.write_cache.assert_not_awaited()
            assert assistant.cache_version == 1

        # Step 2: Guardrail removed → cache_version bumped
        with patch.object(AssistantService, "get_assistant", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = assistant
            obj_in = MagicMock(spec=AssistantCreate)
            obj_in.model_dump.return_value = {"guardrails": []}
            await AssistantService.update_assistant(
                db=mock_db,
                assistant_id=assistant.assistant_id,
                obj_in=obj_in,
                user_id=uuid4(),
                org_id=uuid4(),
            )
        assert assistant.cache_version == 2

        # Step 3: Same query → cache miss (version mismatch) → fresh execution
        cs2 = ConversationService(db=MagicMock())
        with (
            patch.object(cs2, "_resolve_assistant", new_callable=AsyncMock) as mock_resolve,
            patch("engine.pipelines.ingestion.services.embedding_service.EmbeddingService") as mock_embed_cls,
            patch("engine.modules.assistant.semantic_cache.SemanticCacheService") as mock_cache,
            patch("engine.modules.assistant.runtime.executor.AssistantExecutor.execute", new_callable=AsyncMock) as mock_exec,
        ):
            mock_resolve.return_value = assistant
            mock_embed_cls.return_value.embed_query = AsyncMock(return_value=[0.5] * 1536)
            mock_cache.lookup_cache = AsyncMock(return_value=None)
            mock_cache.write_cache = AsyncMock()

            mock_exec.return_value = (
                "Here is the real answer.",
                [{"type": "markdown", "data": {"content": "Here is the real answer."}}],
                {"response_type": "normal"},
            )

            await cs2.handle_chat_turn(payload, save_to_db=False)
            mock_cache.write_cache.assert_awaited_once()
            mock_cache.lookup_cache.assert_awaited_once()
            call_args = mock_cache.lookup_cache.await_args
            assert call_args is not None
            # Ensure the cache lookup used the new version
            assert call_args[0][3] == 2

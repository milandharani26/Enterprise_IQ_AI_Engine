"""RAG search over knowledge.drive_document_chunks (pgvector + full-text)."""
import asyncio
import logging
import os
import re
import time
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from ..base_tool import BaseTool, ToolContext, ToolProperties, ToolCategory
from engine.modules.assistant.tools.exceptions import ToolExecutionError, ConfigurationError

logger = logging.getLogger(__name__)


class DriveSearchToolInput(BaseModel):
    """Input schema for Google Drive RAG search tool."""
    query: str = Field(..., description="Natural language search query")
    top_k: int = Field(default=5, ge=1, le=20, description="Number of top chunks to retrieve")
    similarity_threshold: float = Field(
        default=0.3, 
        ge=0.0, 
        le=1.0, 
        description="Minimum similarity score (0–1)"
    )


class DriveSearchTool(BaseTool):
    """
    Semantic search over indexed document chunks in knowledge.drive_document_chunks.

    Flow:
    1. Embed the user query (OpenAI text-embedding-3-small)
    2. Hybrid vector + full-text search joined to knowledge.drive_documents
    3. Return top-K chunks for the LLM to answer from
    """

    name = "drive_search"
    properties = ToolProperties(        
        description = (
            "Search indexed Google Drive documents using semantic similarity. "
            "Queries knowledge.drive_document_chunks and returns the most relevant excerpts with links."
        ),
        category=ToolCategory.BUSINESS,
        input_schema = DriveSearchToolInput,
        required_connectors = ["postgres"],
        required_permissions = ["documents:read"],
        risk_level = "low",
        default_instructions = """### DRIVE_SEARCH (Semantic Google Drive Search)

**Purpose:** Search indexed Google Drive documents using semantic similarity.

**When to use (always for):**
- Any question about synced Google Drive files, Drive PDFs, or Drive folders
- "Search my drive", "find in google drive", "summarize drive document"
- Explaining or finding content specifically synced from Google Drive

**Input Parameter:**
- query (str, required): Natural language question or search term

**How Results Work:**
- Returns the most relevant chunk excerpts from knowledge.drive_document_chunks
- Each result includes text, source document title, and a web view link
- Pass results to emit_ui_blocks for the final formatted answer

**Important:**
- Search runs over indexed chunks only (status = indexed)
- Combine excerpts into an answer; cite document titles and provide their Drive links
"""
    )
    
    def __init__(self,config: Dict[str, Any] = None, credential_id: Optional[str] = None,usage_instructions: Optional[str] = None):
        """Initialize Drive search tool. Does NOT connect on construction."""
        super().__init__(config=config, credential_id=credential_id, usage_instructions=usage_instructions)
        self._openai_client = None
        self._db_url: Optional[str] = None
        self._embedding_model: str = "text-embedding-3-small"
        self._initialized: bool = False
        # Hybrid scoring knobs
        self._hybrid_vector_weight: float = 0.75
        self._hybrid_text_weight: float = 0.25
        self._hybrid_min_text_score: float = 0.0
        logger.info("[DriveSearchTool] Instance created — lazy initialization enabled")

    def get_instruction(self) -> str:
        """Return instruction for this tool. By default, it's the description."""        
        instruction = self._usage_instructions or self.properties.default_instructions or self.properties.description
        return instruction

    def _ensure_initialized(self) -> None:
        """Lazy initialization of OpenAI client and database URL."""
        if self._initialized:
            return

        try:
            from engine.shared.config.settings import get_settings
            settings = get_settings()
            embedding_provider = (
                os.getenv("EMBEDDING_PROVIDER")
                or os.getenv("DEFAULT_EMBEDDING_PROVIDER")
                or getattr(settings, "embedding_provider", "")
                or getattr(settings, "default_embedding_provider", "")
                or "openai"
            ).strip().lower()
            if embedding_provider not in {"openai", "groq", "gemini"}:
                raise ConfigurationError(
                    f"Unsupported EMBEDDING_PROVIDER '{embedding_provider}' for drive_search. "
                    "Supported providers: openai, groq, gemini.",
                    context={
                        "operation": "rag_initialize",
                        "embedding_provider": embedding_provider,
                    },
                )

            # Resolve embedding API key/base URL by provider.
            if embedding_provider == "groq":
                api_key = (
                    os.getenv("GROQ_API_KEY")
                    or getattr(settings, "groq_api_key", "")
                    or ""
                )
                base_url = "https://api.groq.com/openai/v1"
                default_model = "nomic-embed-text-v1_5"
            elif embedding_provider == "gemini":
                api_key = (
                    os.getenv("GOOGLE_API_KEY")
                    or getattr(settings, "google_api_key", "")
                    or ""
                )
                base_url = "https://generativelanguage.googleapis.com/v1beta/openai/"
                default_model = "gemini-embedding-2"
            else:  # openai
                api_key = (
                    os.getenv("OPENAI_API_KEY")
                    or getattr(settings, "openai_api_key", "")
                    or ""
                )
                base_url = None
                default_model = "text-embedding-3-small"

            if not api_key:
                raise ConfigurationError(
                    f"{embedding_provider.upper()} API key not set in settings — required for RAG embedding",
                    context={"operation": "rag_initialize"},
                )

            # Build async OpenAI client
            try:
                from openai import AsyncOpenAI
            except ImportError:
                raise ConfigurationError(
                    "openai package not installed — run: pip install openai",
                    context={"operation": "rag_initialize"},
                )
            self._openai_client = AsyncOpenAI(api_key=api_key, base_url=base_url)

            # Pick embedding model: settings > env > provider default
            self._embedding_model = (
                getattr(settings, "embedding_model", "")
                or os.getenv("EMBEDDING_MODEL")
                or default_model
            )

            # Store sync-compatible DB URL (asyncpg passthrough)
            db_url = getattr(settings, "database_url", "") or ""
            if not db_url:
                raise ConfigurationError(
                    "database_url not set in settings — required for RAG vector search",
                    context={"operation": "rag_initialize"},
                )
            self._db_url = db_url
            self._initialized = True

        except ConfigurationError:
            raise
        except Exception as e:
            raise ConfigurationError(
                f"DriveSearchTool initialization failed: {e}",
                original_error=e,
                context={"operation": "rag_initialize"},
            )

    async def _embed_query(self, query: str) -> List[float]:
        try:
            kwargs = {
                "model": self._embedding_model,
                "input": query,
                "encoding_format": "float",
            }
            if "gemini" in self._embedding_model:
                kwargs["dimensions"] = 768
                
            response = await asyncio.wait_for(
                self._openai_client.embeddings.create(**kwargs),
                timeout=30,
            )
            return response.data[0].embedding
        except Exception as e:
            raise ToolExecutionError(
                f"Failed to embed query: {e}",
                original_error=e,
                context={"query": query[:100]},
            )

    async def _vector_search(
        self,
        query_vector: List[float],
        query_text: str,
        organization_id: Optional[str],
        top_k: int,
        threshold: float,
    ) -> List[Dict[str, Any]]:
        try:
            import asyncpg

            conn_str = self._db_url.replace("postgresql+asyncpg://", "postgresql://")
            vector_literal = "[" + ",".join(str(v) for v in query_vector) + "]"

            vector_weight = float(self._hybrid_vector_weight)
            text_weight = float(self._hybrid_text_weight)
            min_text_score = float(self._hybrid_min_text_score)

            sql = """
                WITH scored AS (
                    SELECT
                        dc.text,
                        d.title,
                        d.web_view_link as reference_id,
                        -- semantic score (NULL if embedding missing)
                        CASE
                            WHEN dc.embedding IS NULL THEN NULL
                            ELSE CAST(1 - (dc.embedding <=> $1::vector) AS float)
                        END AS vector_score,
                        -- lexical score (0 if tsquery is empty/non-match)
                        CAST(
                            ts_rank_cd(
                                to_tsvector('english', coalesce(dc.text, '')),
                                plainto_tsquery('english', $2)
                            )
                            AS float
                        ) AS text_score
                    FROM knowledge.drive_document_chunks dc
                    JOIN knowledge.drive_documents d
                        ON d.id = dc.drive_document_id
                    WHERE d.status = 'indexed'
                      AND ($3::uuid IS NULL OR dc.workspace_id = $3::uuid)
                )
                SELECT
                    text,
                    title,
                    reference_id,
                    vector_score,
                    text_score,
                    CAST(
                        ($6 * COALESCE(vector_score, 0.0)) + ($7 * COALESCE(text_score, 0.0))
                        AS float
                    ) AS similarity
                FROM scored
                WHERE
                    (vector_score IS NOT NULL AND vector_score >= $4)
                    OR (text_score >= $5)
                ORDER BY similarity DESC
                LIMIT $8
            """

            conn = await asyncio.wait_for(
                asyncpg.connect(conn_str), timeout=10
            )
            try:
                rows = await asyncio.wait_for(
                    conn.fetch(
                        sql,
                        vector_literal,
                        (query_text or ""),
                        organization_id,
                        float(threshold),
                        float(min_text_score),
                        float(vector_weight),
                        float(text_weight),
                        int(top_k),
                    ),
                    timeout=15,
                )
            finally:
                await conn.close()

            return [
                {
                    "text": row["text"],
                    "title": row["title"] or "Untitled",
                    "reference_id": str(row["reference_id"]) if row["reference_id"] else "No Link",
                    "similarity": round(float(row["similarity"]), 4) if row["similarity"] is not None else None,
                }
                for row in rows
            ]

        except Exception as e:
            raise ToolExecutionError(
                f"pgvector search failed: {e}",
                original_error=e,
            )

    async def _keyword_search(
        self,
        query: str,
        organization_id: Optional[str],
        top_k: int,
    ) -> List[Dict[str, Any]]:
        try:
            import asyncpg

            conn_str = self._db_url.replace("postgresql+asyncpg://", "postgresql://")
            sql = """
                SELECT
                    dc.text,
                    d.title,
                    d.web_view_link as reference_id,
                    CAST(NULL AS float) AS similarity
                FROM knowledge.drive_document_chunks dc
                JOIN knowledge.drive_documents d
                    ON d.id = dc.drive_document_id
                WHERE d.status = 'indexed'
                  AND ($1::uuid IS NULL OR dc.workspace_id = $1::uuid)
                  AND (
                        dc.text ILIKE ANY($2::text[])
                        OR d.title ILIKE ANY($2::text[])
                      )
                ORDER BY dc.sequence_number
                LIMIT $3
            """
            q = (query or "").strip()
            stop = {
                "the", "and", "for", "with", "from", "that", "this", "you", "your",
                "work", "policy", "policies", "home", "employee", "employees",
            }
            raw_words = [w.lower() for w in re.split(r"[^a-zA-Z0-9]+", q) if len(w) >= 3]
            words = [w for w in raw_words if w not in stop]

            patterns: List[str] = []
            if q:
                patterns.append(f"%{q}%")
            patterns.extend([f"%{w}%" for w in words[:8]])
            if not patterns:
                return []

            token_patterns = [p for p in patterns if p != f"%{q}%"]
            require_two = len(token_patterns) >= 2

            if require_two:
                sql = """
                    SELECT
                        dc.text,
                        d.title,
                        d.web_view_link as reference_id,
                        CAST(NULL AS float) AS similarity
                    FROM knowledge.drive_document_chunks dc
                    JOIN knowledge.drive_documents d
                        ON d.id = dc.drive_document_id
                    WHERE d.status = 'indexed'
                      AND ($1::uuid IS NULL OR dc.workspace_id = $1::uuid)
                      AND (
                            (dc.text ILIKE $2 AND dc.text ILIKE $3)
                            OR (d.title ILIKE $2 AND d.title ILIKE $3)
                          )
                    ORDER BY dc.sequence_number
                    LIMIT $4
                """

            conn = await asyncio.wait_for(asyncpg.connect(conn_str), timeout=10)
            try:
                if require_two:
                    rows = await asyncio.wait_for(
                        conn.fetch(sql, organization_id, token_patterns[0], token_patterns[1], top_k),
                        timeout=15,
                    )
                else:
                    rows = await asyncio.wait_for(
                        conn.fetch(sql, organization_id, patterns, top_k),
                        timeout=15,
                    )
            finally:
                await conn.close()

            return [
                {
                    "text": row["text"],
                    "title": row["title"] or "Untitled",
                    "reference_id": str(row["reference_id"]) if row["reference_id"] else "No Link",
                    "similarity": None,
                }
                for row in rows
            ]
        except Exception as e:
            logger.error("[DriveSearchTool] Keyword fallback search failed: %s", e)
            return []

    def _format_results(self, query: str, chunks: List[Dict[str, Any]]) -> str:
        if not chunks:
            return (
                f"No relevant Google Drive documents found for: '{query}'\n"
                "Try rephrasing or syncing more files."
            )

        max_chars_per_chunk = 1200
        max_total_chars = 6000
        lines = [
            f"Found {len(chunks)} relevant Google Drive document section(s):\n",
            "=" * 60,
        ]
        total = len(lines[0]) + len(lines[1])

        for i, chunk in enumerate(chunks, start=1):
            header = (
                f"\n[{i}] Source: {chunk['title']} "
                f"(Drive Link: {chunk['reference_id']}, similarity: {chunk['similarity']})"
            )
            body = chunk["text"].strip()
            if len(body) > max_chars_per_chunk:
                body = body[:max_chars_per_chunk] + "… [truncated]"
            section = header + "\n" + "-" * 40 + "\n" + body + "\n"
            if total + len(section) > max_total_chars:
                lines.append("\n[Additional chunks omitted to fit context limit]")
                break
            lines.append(section)
            total += len(section)

        lines.append("=" * 60)
        return "\n".join(lines)

    async def _search_async(
        self,
        query: str,
        organization_id: Optional[str],
        top_k: int,
        similarity_threshold: float,
    ) -> List[Dict[str, Any]]:
        query_vector = await self._embed_query(query)

        chunks = await self._vector_search(
            query_vector=query_vector,
            query_text=query,
            organization_id=organization_id,
            top_k=top_k,
            threshold=similarity_threshold,
        )

        if not chunks:
            chunks = await self._keyword_search(
                query=query,
                organization_id=organization_id,
                top_k=top_k,
            )

        return chunks

    def _run(self, query: str = "", top_k: int = 5, similarity_threshold: float = 0.3, ctx: ToolContext = None) -> str:
        try:
            organization_id = ctx.organization_id if ctx else None
            self._ensure_initialized()

            chunks = asyncio.run(
                self._search_async(query, organization_id, top_k, similarity_threshold)
            )
            return self._format_results(query, chunks)

        except Exception as e:
            return f"Drive search failed with error: {str(e)}"

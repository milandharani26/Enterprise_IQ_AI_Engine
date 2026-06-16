"""RAG search over knowledge.document_chunks (pgvector + full-text)."""
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


class RAGSearchToolInput(BaseModel):
    """Input schema for RAG search tool."""
    query: str = Field(..., description="Natural language search query")
    top_k: int = Field(default=5, ge=1, le=20, description="Number of top chunks to retrieve")
    similarity_threshold: float = Field(
        default=0.3, 
        ge=0.0, 
        le=1.0, 
        description="Minimum similarity score (0–1)"
    )


class RAGSearchTool(BaseTool):
    """
    Semantic search over indexed document chunks in knowledge.document_chunks.

    Flow:
    1. Embed the user query (OpenAI text-embedding-3-small)
    2. Hybrid vector + full-text search joined to knowledge.documents
    3. Return top-K chunks for the LLM to answer from
    """

    name = "rag_search"
    properties = ToolProperties(        
        description = (
            "Search indexed organization documents using semantic similarity. "
            "Queries knowledge.document_chunks and returns the most relevant excerpts."
        ),
        category=ToolCategory.BUSINESS,
        # connectors=["postgres"],
        input_schema = RAGSearchToolInput,
        required_connectors = ["postgres"],
        required_permissions = ["documents:read"],
        risk_level = "low",
        default_instructions = """### RAG_SEARCH (Semantic Document Search)

**Purpose:** Search indexed documents in knowledge.document_chunks using semantic similarity.

**When to use (always for):**
- Any question about uploaded documents, files, PDFs, or the knowledge base
- "What documents do you have?", "list my files", "summarize my uploads"
- Explaining or finding content in organization documents

**Input Parameter:**
- query (str, required): Natural language question or search term

**How Results Work:**
- Returns the most relevant chunk excerpts from knowledge.document_chunks
- Each result includes text and source document title
- Pass results to emit_ui_blocks for the final formatted answer

**Important:**
- Search runs over indexed chunks only (status = indexed)
- Combine excerpts into an answer; cite document titles
"""
    )
    
    def __init__(self,config: Dict[str, Any] = None, credential_id: Optional[str] = None,usage_instructions: Optional[str] = None):
        """Initialize RAG search tool. Does NOT connect on construction."""
        super().__init__(config=config, credential_id=credential_id, usage_instructions=usage_instructions)
        self._openai_client = None
        self._db_url: Optional[str] = None
        self._embedding_model: str = "text-embedding-3-small"
        self._initialized: bool = False
        # Hybrid scoring knobs (no DB changes required; tune for your corpus)
        self._hybrid_vector_weight: float = 0.75
        self._hybrid_text_weight: float = 0.25
        self._hybrid_min_text_score: float = 0.0
        logger.info("[RAGSearchTool] Instance created — lazy initialization enabled")

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
            if embedding_provider not in {"openai", "groq"}:
                raise ConfigurationError(
                    f"Unsupported EMBEDDING_PROVIDER '{embedding_provider}' for rag_search. "
                    "Supported providers: openai, groq.",
                    context={"operation": "rag_initialize", "embedding_provider": embedding_provider},
                )

            # Resolve embedding API key/base URL by provider.
            if embedding_provider == "groq":
                api_key = os.getenv("GROQ_API_KEY") or getattr(settings, "groq_api_key", "") or ""
                base_url = "https://api.groq.com/openai/v1"
            else:
                api_key = os.getenv("OPENAI_API_KEY") or getattr(settings, "openai_api_key", "") or ""
                base_url = None
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

            # Store sync-compatible DB URL (asyncpg passthrough)
            db_url = getattr(settings, "database_url", "") or ""
            if not db_url:
                raise ConfigurationError(
                    "database_url not set in settings — required for RAG vector search",
                    context={"operation": "rag_initialize"},
                )
            self._db_url = db_url
            self._initialized = True
            logger.info(
                "[RAGSearchTool] ✓ Initialized with model=%s (hybrid weights: vec=%.2f text=%.2f min_text=%.3f)",
                self._embedding_model,
                self._hybrid_vector_weight,
                self._hybrid_text_weight,
                self._hybrid_min_text_score,
            )

        except ConfigurationError:
            raise
        except Exception as e:
            raise ConfigurationError(
                f"RAGSearchTool initialization failed: {e}",
                original_error=e,
                context={"operation": "rag_initialize"},
            )

    async def _embed_query(self, query: str) -> List[float]:
        """
        Embed query text using OpenAI embeddings API.

        Args:
            query: Text to embed

        Returns:
            1536-dim float vector

        Raises:
            ToolExecutionError: If OpenAI call fails
        """
        try:
            response = await asyncio.wait_for(
                self._openai_client.embeddings.create(
                    model=self._embedding_model,
                    input=query,
                    encoding_format="float",
                ),
                timeout=30,
            )
            vector = response.data[0].embedding
            logger.debug("[RAGSearchTool] Query embedded: %d dims", len(vector))
            return vector
        except asyncio.TimeoutError as e:
            raise ToolExecutionError(
                "OpenAI embedding timed out (30s)",
                original_error=e,
                context={"query": query[:100]},
            )
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
        """
        Hybrid search: pgvector similarity + Postgres full-text ranking.

        organization_id: optional filter (maps to knowledge.documents.workspace_id).
        When None, searches all indexed document chunks.
        """
        try:
            import asyncpg

            # Convert asyncpg URL format
            # postgresql+asyncpg://... → postgresql://... for asyncpg driver
            conn_str = self._db_url.replace("postgresql+asyncpg://", "postgresql://")

            # Format vector as pgvector literal: '[0.1,0.2,...]'
            vector_literal = "[" + ",".join(str(v) for v in query_vector) + "]"

            # Hybrid scoring:
            # - vector_score: semantic match (0..1)
            # - text_score: lexical match (ts_rank_cd, ~0..1+ depending on doc)
            # - final_score: weighted sum
            vector_weight = float(self._hybrid_vector_weight)
            text_weight = float(self._hybrid_text_weight)
            min_text_score = float(self._hybrid_min_text_score)

            sql = """
                WITH scored AS (
                    SELECT
                        dc.text,
                        d.title,
                        d.reference_id,
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
                    FROM knowledge.document_chunks dc
                    JOIN knowledge.documents d
                        ON d.id = dc.document_id
                    WHERE d.deleted_at IS NULL
                      AND d.status = 'indexed'
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
                        float(threshold),        # $4 min_vector
                        float(min_text_score),   # $5 min_text
                        float(vector_weight),    # $6
                        float(text_weight),      # $7
                        int(top_k),              # $8
                    ),
                    timeout=15,
                )
            finally:
                await conn.close()

            return [
                {
                    "text": row["text"],
                    "title": row["title"] or "Untitled",
                    "reference_id": str(row["reference_id"]),
                    "similarity": round(float(row["similarity"]), 4) if row["similarity"] is not None else None,
                    "vector_score": round(float(row["vector_score"]), 4) if row["vector_score"] is not None else None,
                    "text_score": round(float(row["text_score"]), 4) if row["text_score"] is not None else None,
                }
                for row in rows
            ]

        except ToolExecutionError:
            raise
        except Exception as e:
            raise ToolExecutionError(
                f"pgvector search failed: {e}",
                original_error=e,
                context={
                    "organization_id": organization_id,
                    "top_k": top_k,
                    "threshold": threshold,
                },
            )

    async def _keyword_search(
        self,
        query: str,
        organization_id: Optional[str],
        top_k: int,
    ) -> List[Dict[str, Any]]:
        """Fallback ILIKE search on chunk text when vector search returns no hits."""
        try:
            import asyncpg

            conn_str = self._db_url.replace("postgresql+asyncpg://", "postgresql://")
            sql = """
                SELECT
                    dc.text,
                    d.title,
                    d.reference_id,
                    CAST(NULL AS float) AS similarity
                FROM knowledge.document_chunks dc
                JOIN knowledge.documents d
                    ON d.id = dc.document_id
                WHERE d.deleted_at IS NULL
                  AND d.status = 'indexed'
                  AND ($1::uuid IS NULL OR dc.workspace_id = $1::uuid)
                  AND (
                        dc.text ILIKE ANY($2::text[])
                        OR d.title ILIKE ANY($2::text[])
                      )
                ORDER BY dc.sequence_number
                LIMIT $3
            """
            q = (query or "").strip()
            # Match on meaningful tokens (avoid overly-broad retrieval like "work"/"policy").
            stop = {
                "the", "and", "for", "with", "from", "that", "this", "you", "your",
                "work", "policy", "policies", "home", "employee", "employees",
            }
            raw_words = [w.lower() for w in re.split(r"[^a-zA-Z0-9]+", q) if len(w) >= 3]
            words = [w for w in raw_words if w not in stop]

            # Prefer phrase match if present.
            patterns: List[str] = []
            if q:
                patterns.append(f"%{q}%")

            # If phrase is too generic, fall back to token patterns.
            patterns.extend([f"%{w}%" for w in words[:8]])
            if not patterns:
                return []

            # Require at least 2 token hits when we have multiple tokens; otherwise retrieval is too noisy.
            token_patterns = [p for p in patterns if p != f"%{q}%"]
            require_two = len(token_patterns) >= 2

            if require_two:
                # Overwrite SQL to enforce two token matches in chunk text/title.
                sql = """
                    SELECT
                        dc.text,
                        d.title,
                        d.reference_id,
                        CAST(NULL AS float) AS similarity
                    FROM knowledge.document_chunks dc
                    JOIN knowledge.documents d
                        ON d.id = dc.document_id
                    WHERE d.deleted_at IS NULL
                      AND d.status = 'indexed'
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
                    "reference_id": str(row["reference_id"]),
                    "similarity": None,
                }
                for row in rows
            ]
        except Exception as e:
            # If keyword search also fails, just return no chunks; caller will show no-results message.
            logger.error("[RAGSearchTool] Keyword fallback search failed: %s", e)
            return []

    def _format_results(self, query: str, chunks: List[Dict[str, Any]]) -> str:
        """
        Format retrieved chunks as a readable context string for the LLM.
        Truncates per-chunk and total length so multi-turn agents stay within token budget.
        """
        if not chunks:
            return (
                f"No relevant documents found for: '{query}'\n"
                "No indexed documents match this query. "
                "Try rephrasing or upload files on the Documents page."
            )

        max_chars_per_chunk = 1200
        max_total_chars = 6000
        lines = [
            f"Found {len(chunks)} relevant document section(s):\n",
            "=" * 60,
        ]
        total = len(lines[0]) + len(lines[1])

        for i, chunk in enumerate(chunks, start=1):
            header = (
                f"\n[{i}] Source: {chunk['title']} "
                f"(ref: {chunk['reference_id']}, similarity: {chunk['similarity']})"
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

    # def get_input_schema(self):
    #     """Return input schema for RAG search tool."""
    #     return RAGSearchToolInput

    async def _search_async(
        self,
        query: str,
        organization_id: Optional[str],
        top_k: int,
        similarity_threshold: float,
    ) -> List[Dict[str, Any]]:
        """Embed query and search knowledge.document_chunks."""
        query_vector = await self._embed_query(query)

        chunks = await self._vector_search(
            query_vector=query_vector,
            query_text=query,
            organization_id=organization_id,
            top_k=top_k,
            threshold=similarity_threshold,
        )

        if not chunks:
            logger.info(
                "[RAGSearchTool] No vector hits; falling back to keyword search (org=%s)",
                organization_id,
            )
            chunks = await self._keyword_search(
                query=query,
                organization_id=organization_id,
                top_k=top_k,
            )

        logger.info(
            "[RAGSearchTool] Found %d chunks (organization_id=%s)",
            len(chunks),
            organization_id,
        )
        return chunks

    def _run(self, query: str = "", top_k: int = 5, similarity_threshold: float = 0.3, ctx: ToolContext = None) -> str:
        """Search document chunks and return formatted context for the LLM."""
        start_time = time.time()
        try:
            organization_id = ctx.organization_id if ctx else None
            self._ensure_initialized()

            logger.info(
                "[RAGSearchTool] query=%r organization_id=%s",
                query[:80],
                organization_id,
            )

            chunks = asyncio.run(
                self._search_async(query, organization_id, top_k, similarity_threshold)
            )
            
            elapsed = time.time() - start_time
            logger.info(
                "[RAGSearchTool] Search completed in %.2fs (%d chunks retrieved)",
                elapsed,
                len(chunks),
            )
            return self._format_results(query, chunks)

        except ToolExecutionError as e:
            elapsed = time.time() - start_time
            logger.error("[RAGSearchTool] Execution error after %.2fs: %s", elapsed, e)
            return f"RAG search failed: {str(e)}"
        except Exception as e:
            elapsed = time.time() - start_time
            logger.error("[RAGSearchTool] Unexpected error after %.2fs: %s", elapsed, e)
            return f"RAG search failed with unexpected error: {str(e)}"
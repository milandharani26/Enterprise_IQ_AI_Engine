"""RAG search over knowledge.document_chunks (pgvector + full-text).

Phase 1 additions (Query Preprocessing & Expansion):
─────────────────────────────────────────────────────
_strip_filler(query)
    Removes common conversational filler from the user query before embedding.
    e.g. "can you tell me about leave policy" → "leave policy"
    Filler words carry no semantic signal and add noise to the embedding vector.

_expand_short_query(query) → List[str]
    For queries of 1–3 words, asks the LLM to generate 2 semantic variants.
    e.g. "leave policy" → ["leave policy", "annual leave rules", "PTO entitlement"]
    Short queries produce narrow embeddings; variants widen the search cone.

_decompose_compound_query(query) → List[str]
    Splits queries joined by "and"/"or" into sub-queries.
    e.g. "refund policy and delivery time" → ["refund policy", "delivery time"]
    Each sub-query is searched independently and results are merged with RRF.

_reciprocal_rank_fusion(result_lists, k=60) → List[Dict]
    Merges multiple ranked result lists into one without needing score calibration.
    Standard RRF formula: score = Σ 1/(k + rank). Works well for combining
    results from multiple query variants that may have different score ranges.

_preprocess_query(query) → List[str]
    Orchestrates: strip filler → try compound decompose → try short expansion.
    Returns a list of query strings (1 to N) to search in parallel.

_search_async() updated:
    Calls _preprocess_query() first, then embeds + searches each variant in
    parallel using asyncio.gather(), merges with RRF, and returns top_k results.
"""

import asyncio
import logging
import os
import re
import time
from typing import Any, Dict, List, Optional, Tuple

import asyncpg
from pydantic import BaseModel, Field

from ..base_tool import BaseTool, ToolContext, ToolProperties, ToolCategory
from engine.modules.assistant.tools.exceptions import (
    ToolExecutionError,
    ConfigurationError,
)

logger = logging.getLogger(__name__)

# ─── Filler phrases stripped before embedding ────────────────────────────────
# These add no semantic signal and produce noisier embedding vectors.
_FILLER_PATTERNS: List[re.Pattern] = [
    re.compile(p, re.IGNORECASE)
    for p in [
        r"^can you (?:tell|show|give|explain|find|search for|look up|help me (?:find|with|understand))?\s*(?:me\s+)?(?:about\s+)?",
        r"^(?:please\s+)?(?:find|search for|look up|tell me about|show me|give me|explain)\s+",
        r"^(?:what is|what are|what's|whats|how (?:does|do|is|are)|where (?:is|are)|who is|who are)\s+",
        r"^(?:i (?:want|need|would like)\s+(?:to know|to find|information)\s+(?:about\s+)?)",
        r"^(?:do you have (?:any )?(?:information|info|details)?\s+(?:about|on|regarding)\s+)",
        r"\s+(?:please|thanks|thank you)[\s?]*$",
        r"^(?:hey|hi|hello)[,\s]+",
    ]
]


class RAGSearchToolInput(BaseModel):
    """Input schema for RAG search tool."""

    query: str = Field(..., description="Natural language search query")
    top_k: int = Field(
        default=5, ge=1, le=20, description="Number of top chunks to retrieve"
    )
    similarity_threshold: float = Field(
        default=0.3, ge=0.0, le=1.0, description="Minimum similarity score (0–1)"
    )


class RAGSearchTool(BaseTool):
    """
    Semantic search over indexed document chunks in knowledge.document_chunks.

    Flow:
    1. Preprocess query  (Phase 1: strip filler, expand short, decompose compound)
    2. Embed each query variant in parallel
    3. Hybrid vector + full-text search for each variant
    4. Merge results with Reciprocal Rank Fusion
    5. Return top-K chunks for the LLM to answer from

    Connection strategy:
    - _arun()  (async, FastAPI / async context) → shared asyncpg pool via _get_pool()
    - _run()   (sync, LangGraph worker thread)  → fresh connection per call
      Reason: asyncpg pools are bound to the event loop they were created on.
      LangGraph runs _run() in a worker thread with asyncio.run(), which creates a
      brand-new loop each time — sharing the pool across loops causes "Event loop is closed".
    """

    name = "rag_search"
    properties = ToolProperties(
        description=(
            "Search indexed organization documents using semantic similarity. "
            "Queries knowledge.document_chunks and returns the most relevant excerpts."
        ),
        category=ToolCategory.BUSINESS,
        input_schema=RAGSearchToolInput,
        required_connectors=["postgres"],
        required_permissions=["documents:read"],
        risk_level="low",
        default_instructions="""### RAG_SEARCH (Semantic Document Search)

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
""",
    )

    def __init__(
        self,
        config: Dict[str, Any] = None,
        credential_id: Optional[str] = None,
        usage_instructions: Optional[str] = None,
    ):
        """Initialize RAG search tool. Does NOT connect on construction."""
        super().__init__(
            config=config,
            credential_id=credential_id,
            usage_instructions=usage_instructions,
        )
        self._openai_client = None
        self._db_url: Optional[str] = None
        self._embedding_model: str = ""  # set during _ensure_initialized from settings
        self._initialized: bool = False
        self._pool: Optional[asyncpg.Pool] = None  # shared pool — async path only

        # Hybrid scoring knobs
        self._hybrid_vector_weight: float = 0.75
        self._hybrid_text_weight: float = 0.25
        self._hybrid_min_text_score: float = 0.0

        # Phase 1: query expansion toggle (set False to disable LLM expansion call for lower latency)
        self._enable_query_expansion: bool = False

        logger.info("[RAGSearchTool] Instance created — lazy initialization enabled")

    def get_instruction(self) -> str:
        return (
            self._usage_instructions
            or self.properties.default_instructions
            or self.properties.description
        )

    # ─────────────────────────────────────────────────────────────────────────
    # Initialization
    # ─────────────────────────────────────────────────────────────────────────

    def _ensure_initialized(self) -> None:
        """Lazy initialization of OpenAI client and database URL."""
        if self._initialized:
            return

        try:
            from engine.shared.config.settings import get_settings

            settings = get_settings()

            embedding_provider = (
                (
                    os.getenv("EMBEDDING_PROVIDER")
                    or os.getenv("DEFAULT_EMBEDDING_PROVIDER")
                    or getattr(settings, "embedding_provider", "")
                    or getattr(settings, "default_embedding_provider", "")
                    or "openai"
                )
                .strip()
                .lower()
            )

            if embedding_provider not in {"openai", "groq", "gemini"}:
                raise ConfigurationError(
                    f"Unsupported EMBEDDING_PROVIDER '{embedding_provider}' for rag_search. "
                    "Supported providers: openai, groq, gemini.",
                    context={
                        "operation": "rag_initialize",
                        "embedding_provider": embedding_provider,
                    },
                )

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

            db_url = getattr(settings, "database_url", "") or ""
            if not db_url:
                raise ConfigurationError(
                    "database_url not set in settings — required for RAG vector search",
                    context={"operation": "rag_initialize"},
                )
            self._db_url = db_url
            self._initialized = True

            logger.info(
                "[RAGSearchTool] ✓ Initialized (model=%s, vec=%.2f, text=%.2f, expansion=%s)",
                self._embedding_model,
                self._hybrid_vector_weight,
                self._hybrid_text_weight,
                self._enable_query_expansion,
            )

        except ConfigurationError:
            raise
        except Exception as e:
            raise ConfigurationError(
                f"RAGSearchTool initialization failed: {e}",
                original_error=e,
                context={"operation": "rag_initialize"},
            )

    # ─────────────────────────────────────────────────────────────────────────
    # Connection helpers
    # ─────────────────────────────────────────────────────────────────────────

    def _get_conn_str(self) -> str:
        return self._db_url.replace("postgresql+asyncpg://", "postgresql://")

    async def _get_pool(self) -> asyncpg.Pool:
        """Shared pool — ONLY safe from _arun() (same event loop)."""
        if self._pool is None or self._pool._closed:
            self._pool = await asyncpg.create_pool(
                self._get_conn_str(),
                min_size=2,
                max_size=10,
                command_timeout=15,
            )
            logger.debug("[RAGSearchTool] Connection pool created")
        return self._pool

    async def _get_fresh_connection(self) -> asyncpg.Connection:
        """Fresh connection per call — safe for threads with isolated event loops."""
        return await asyncpg.connect(self._get_conn_str(), command_timeout=15)

    @classmethod
    async def close_pool(cls) -> None:
        if hasattr(cls, "_pool") and cls._pool and not cls._pool._closed:
            await cls._pool.close()
            logger.info("[RAGSearchTool] Connection pool closed")

    # ─────────────────────────────────────────────────────────────────────────
    # Phase 1 — Query preprocessing
    # ─────────────────────────────────────────────────────────────────────────

    def _strip_filler(self, query: str) -> str:
        """
        Remove conversational filler from the start/end of a query.

        Filler words like "can you tell me about" carry zero semantic signal
        and add noise to the embedding vector, pushing it toward generic
        language-model space rather than the topic space.

        Examples:
            "can you tell me about leave policy"  → "leave policy"
            "what is the refund process"          → "refund process"
            "hey, find me the HR policy please"   → "HR policy"
        """
        cleaned = query.strip()
        for pattern in _FILLER_PATTERNS:
            cleaned = pattern.sub("", cleaned).strip()
        # Collapse any double spaces left after substitution
        cleaned = re.sub(r"\s{2,}", " ", cleaned).strip(" ,?")
        result = cleaned if len(cleaned) >= 3 else query.strip()
        if result != query.strip():
            logger.debug(
                "[RAGSearchTool] Filler stripped: %r → %r",
                query[:60],
                result[:60],
            )
        return result

    async def _expand_short_query(self, query: str) -> List[str]:
        """
        Generate 2 semantic variants for short queries (1–3 words).

        Short queries like "leave policy" produce narrow embedding vectors.
        Asking the LLM for synonymous phrasings widens the search cone and
        improves recall for documents that use different terminology.

        Returns the original query + up to 2 variants.
        Falls back to [query] silently on any LLM error (non-blocking).

        Example:
            "leave policy" → ["leave policy", "annual leave rules", "PTO entitlement"]
        """
        if not self._enable_query_expansion:
            return [query]

        prompt = (
            f'Generate 2 alternative search queries for: "{query}"\n'
            "Rules:\n"
            "- Keep each under 8 words\n"
            "- Use different but semantically equivalent phrasing\n"
            "- Return ONLY a JSON array of 2 strings, nothing else\n"
            'Example output: ["annual leave rules", "PTO entitlement policy"]'
        )

        try:
            response = await asyncio.wait_for(
                self._openai_client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.3,
                    max_tokens=80,
                ),
                timeout=8,  # short timeout — expansion is best-effort
            )
            raw = response.choices[0].message.content.strip()
            # Strip markdown code fences if present
            raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw).strip()
            import json

            variants = json.loads(raw)
            if isinstance(variants, list):
                valid = [
                    v.strip() for v in variants if isinstance(v, str) and v.strip()
                ][:2]
                result = [query] + valid
                logger.debug(
                    "[RAGSearchTool] Query expanded: %r → %r",
                    query,
                    result,
                )
                return result
        except Exception as e:
            logger.debug("[RAGSearchTool] Query expansion skipped (non-fatal): %s", e)

        return [query]

    def _decompose_compound_query(self, query: str) -> List[str]:
        """
        Split compound queries joined by 'and'/'or' into sub-queries.

        Compound queries like "refund policy and delivery time" embed into a
        blended vector that may not rank well for either topic individually.
        Splitting and searching separately then merging with RRF gives better
        precision for both sub-topics.

        Only splits on standalone 'and'/'or' between meaningful segments
        (not inside phrases like "terms and conditions").

        Examples:
            "refund policy and delivery time"  → ["refund policy", "delivery time"]
            "HR rules or leave policy"         → ["HR rules", "leave policy"]
            "terms and conditions"             → ["terms and conditions"]  (no split)
        """
        # Match ' and ' or ' or ' only between segments of ≥2 words each
        # to avoid splitting "terms and conditions", "black and white", etc.
        pattern = re.compile(r"\s+(?:and|or)\s+", re.IGNORECASE)
        parts = pattern.split(query)

        # Only decompose if every part has at least 2 words (avoids splitting
        # noun phrases like "search and rescue" or "black or white")
        if len(parts) >= 2 and all(len(p.split()) >= 2 for p in parts):
            stripped = [p.strip() for p in parts if p.strip()]
            if len(stripped) >= 2:
                logger.debug(
                    "[RAGSearchTool] Compound query decomposed: %r → %r",
                    query,
                    stripped,
                )
                return stripped

        return [query]

    async def _preprocess_query_fast(self, raw_query: str) -> List[str]:
        """
        Fast preprocessing pipeline for a raw user query (no LLM expansion).

        Steps (in order):
        1. Strip filler words
        2. Try compound decomposition (splits on 'and'/'or')

        Does NOT call _expand_short_query() — faster but no variant generation.
        """
        cleaned = self._strip_filler(raw_query)
        parts = self._decompose_compound_query(cleaned)
        return parts

    async def _expand_query_variants_async(
        self,
        base_queries: List[str],
    ) -> List[str]:
        """
        Expand short queries (≤3 words) with LLM-generated variants.

        Used as a background task — fast path skips this entirely,
        but when invoked it adds recall-boosting paraphrases for
        short segments while leaving longer queries untouched.
        """
        expanded: List[str] = []
        for query in base_queries:
            if len(query.split()) <= 3:
                variants = await self._expand_short_query(query)
                expanded.extend(variants)
            else:
                expanded.append(query)

        seen: set = set()
        result: List[str] = []
        for q in expanded:
            key = q.lower().strip()
            if key not in seen:
                seen.add(key)
                result.append(q)

        return result

    async def _preprocess_query(self, raw_query: str) -> List[str]:
        """
        Full preprocessing pipeline for a raw user query.

        Steps (in order):
        1. Strip filler words
        2. Try compound decomposition (splits on 'and'/'or')
        3. If still a single short query (≤3 words), expand with LLM variants

        Returns a list of 1–N query strings to be embedded and searched in parallel.
        """
        # Step 1: strip filler
        cleaned = self._strip_filler(raw_query)

        # Step 2: try compound decomposition
        parts = self._decompose_compound_query(cleaned)

        # Step 3: expand any short parts
        expanded: List[str] = []
        for part in parts:
            word_count = len(part.split())
            if word_count <= 3:
                variants = await self._expand_short_query(part)
                expanded.extend(variants)
            else:
                expanded.append(part)

        # Deduplicate while preserving order
        seen: set = set()
        result: List[str] = []
        for q in expanded:
            key = q.lower().strip()
            if key not in seen:
                seen.add(key)
                result.append(q)

        logger.info(
            "[RAGSearchTool] Query preprocessing: %r → %r",
            raw_query[:80],
            result,
        )

        logger.info("Raw Query: %s", raw_query)
        logger.info("Processed Queries: %s", result)

        return result or [cleaned]

    # ─────────────────────────────────────────────────────────────────────────
    # Phase 1 — Reciprocal Rank Fusion
    # ─────────────────────────────────────────────────────────────────────────

    def _reciprocal_rank_fusion(
        self,
        result_lists: List[List[Dict[str, Any]]],
        top_k: int,
        k: int = 60,
    ) -> List[Dict[str, Any]]:
        """
        Merge multiple ranked result lists into one using Reciprocal Rank Fusion.

        RRF formula: score(doc) = Σ 1 / (k + rank)
        where rank is 1-based position in each result list.

        Why RRF instead of score averaging:
        - Different query variants may return results with very different score
          ranges (e.g. similarity 0.85 vs 0.42). Averaging raw scores would
          unfairly weight the higher-scoring list.
        - RRF uses only rank position, not score magnitude, so it's robust to
          score scale differences across query variants.
        - k=60 is the standard value from the original RRF paper (Cormack 2009).

        Args:
            result_lists: Each inner list is the ranked results for one query variant.
            top_k: How many results to return.
            k: RRF smoothing constant (default 60).

        Returns:
            Merged, deduplicated, re-ranked list of top_k chunks.
        """
        # Key: (reference_id, first 80 chars of text) — deduplicate same chunk
        # returned by multiple query variants
        scores: Dict[Tuple[str, str], float] = {}
        best_chunk: Dict[Tuple[str, str], Dict[str, Any]] = {}

        for result_list in result_lists:
            for rank, chunk in enumerate(result_list, start=1):
                key = (
                    chunk.get("reference_id", ""),
                    (chunk.get("text") or "")[:80],
                )
                rrf_score = 1.0 / (k + rank)
                scores[key] = scores.get(key, 0.0) + rrf_score
                # Keep the chunk with the highest individual similarity score
                if key not in best_chunk:
                    best_chunk[key] = chunk
                else:
                    existing_sim = best_chunk[key].get("similarity") or 0.0
                    new_sim = chunk.get("similarity") or 0.0
                    if new_sim > existing_sim:
                        best_chunk[key] = chunk

        sorted_keys = sorted(scores.keys(), key=lambda k_: scores[k_], reverse=True)

        merged: List[Dict[str, Any]] = []
        for key in sorted_keys[:top_k]:
            chunk = dict(best_chunk[key])
            chunk["rrf_score"] = round(scores[key], 6)
            merged.append(chunk)

        logger.debug(
            "[RAGSearchTool] RRF merged %d lists → %d unique chunks → top %d",
            len(result_lists),
            len(scores),
            len(merged),
        )
        return merged

    # ─────────────────────────────────────────────────────────────────────────
    # Embedding
    # ─────────────────────────────────────────────────────────────────────────

    async def _embed_query(self, query: str) -> List[float]:
        """
        Embed a single query string. Returns 1536-dim float vector.
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
            logger.debug(
                "[RAGSearchTool] Embedded query (%d dims): %r", len(vector), query[:50]
            )
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

    async def _embed_queries_parallel(self, queries: List[str]) -> List[List[float]]:
        """
        Embed multiple query variants in parallel.
        Uses asyncio.gather so all embedding API calls fire simultaneously.
        """
        vectors = await asyncio.gather(
            *[self._embed_query(q) for q in queries],
            return_exceptions=True,
        )
        results: List[List[float]] = []
        for i, v in enumerate(vectors):
            if isinstance(v, Exception):
                logger.warning(
                    "[RAGSearchTool] Embedding failed for variant %r: %s — skipping",
                    queries[i][:50],
                    v,
                )
            else:
                results.append(v)
        return results

    # ─────────────────────────────────────────────────────────────────────────
    # Search — vector (hybrid)
    # ─────────────────────────────────────────────────────────────────────────

    async def _vector_search(
        self,
        query_vector: List[float],
        query_text: str,
        organization_id: Optional[str],
        top_k: int,
        threshold: float,
        use_pool: bool = True,
    ) -> List[Dict[str, Any]]:
        """
        Hybrid search: pgvector cosine similarity + Postgres GIN full-text ranking.

        Phase 2 improvements:
        - Uses stored text_search_vector GIN column (no per-row to_tsvector recompute)
        - Normalizes text_score to [0,1] before combining with vector_score
        - Dynamic weight override for keyword-style queries

        Args:
            use_pool: True → shared pool (_arun). False → fresh conn (_run/thread).
        """
        try:
            vector_literal = "[" + ",".join(str(v) for v in query_vector) + "]"

            vector_weight = float(self._hybrid_vector_weight)
            text_weight = float(self._hybrid_text_weight)
            min_text_score = float(self._hybrid_min_text_score)

            # Dynamic weight override for keyword-style queries
            is_keyword_query = bool(
                re.search(r"\b[A-Z]{2,}-\d+\b", query_text)
                or re.match(r'^".*"$', query_text.strip())
                or len(query_text.split()) <= 1
            )
            if is_keyword_query:
                vector_weight = 0.4
                text_weight = 0.6
                logger.debug(
                    "[RAGSearchTool] Keyword-mode: %r → text_weight=0.6",
                    query_text[:50],
                )

            sql = """
                WITH scored AS (
                    SELECT
                        dc.text,
                        d.title,
                        d.reference_id,
                        CASE
                            WHEN dc.embedding IS NULL THEN NULL
                            ELSE CAST(1 - (dc.embedding <=> $1::vector) AS float)
                        END AS raw_vector_score,
                        CAST(
                            ts_rank_cd(
                                dc.text_search_vector,
                                plainto_tsquery('english', $2)
                            )
                            AS float
                        ) AS raw_text_score
                    FROM knowledge.document_chunks dc
                    JOIN knowledge.documents d ON d.id = dc.document_id
                    WHERE d.deleted_at IS NULL
                      AND d.status = 'indexed'
                      AND ($3::uuid IS NULL OR dc.workspace_id = $3::uuid)
                      AND (
                          dc.embedding IS NOT NULL
                          OR (
                              dc.text_search_vector IS NOT NULL
                              AND dc.text_search_vector @@ plainto_tsquery('english', $2)
                          )
                      )
                ),
                normalized AS (
                    SELECT
                        text,
                        title,
                        reference_id,
                        COALESCE(raw_vector_score, 0.0) AS vector_score,
                        CASE
                            WHEN MAX(raw_text_score) OVER () > 0
                            THEN raw_text_score / MAX(raw_text_score) OVER ()
                            ELSE 0.0
                        END AS text_score
                    FROM scored
                )
                SELECT
                    text,
                    title,
                    reference_id,
                    vector_score,
                    text_score,
                    CAST(($6 * vector_score) + ($7 * text_score) AS float) AS similarity
                FROM normalized
                WHERE (vector_score >= $4) OR (text_score >= $5)
                ORDER BY similarity DESC
                LIMIT $8
            """

            params = (
                vector_literal,
                (query_text or ""),
                organization_id,
                float(threshold),
                float(min_text_score),
                float(vector_weight),
                float(text_weight),
                int(top_k),
            )

            if use_pool:
                pool = await self._get_pool()
                async with pool.acquire() as conn:
                    rows = await asyncio.wait_for(conn.fetch(sql, *params), timeout=15)
            else:
                conn = await asyncio.wait_for(self._get_fresh_connection(), timeout=10)
                try:
                    rows = await asyncio.wait_for(conn.fetch(sql, *params), timeout=15)
                finally:
                    await conn.close()

            return [
                {
                    "text": row["text"],
                    "title": row["title"] or "Untitled",
                    "reference_id": str(row["reference_id"]),
                    "similarity": round(float(row["similarity"]), 4)
                    if row["similarity"] is not None
                    else None,
                    "vector_score": round(float(row["vector_score"]), 4)
                    if row["vector_score"] is not None
                    else None,
                    "text_score": round(float(row["text_score"]), 4)
                    if row["text_score"] is not None
                    else None,
                }
                for row in rows
            ]

        except ToolExecutionError:
            raise
        except Exception as e:
            raise ToolExecutionError(
                f"pgvector search failed: {e}",
                original_error=e,
                context={"organization_id": organization_id, "top_k": top_k},
            )

    # ─────────────────────────────────────────────────────────────────────────
    # Search — keyword fallback
    # ─────────────────────────────────────────────────────────────────────────

    async def _keyword_search(
        self,
        query: str,
        organization_id: Optional[str],
        top_k: int,
        use_pool: bool = True,
    ) -> List[Dict[str, Any]]:
        """ILIKE fallback when vector search returns no hits."""
        try:
            sql_single = """
                SELECT dc.text, d.title, d.reference_id, CAST(NULL AS float) AS similarity
                FROM knowledge.document_chunks dc
                JOIN knowledge.documents d ON d.id = dc.document_id
                WHERE d.deleted_at IS NULL AND d.status = 'indexed'
                  AND ($1::uuid IS NULL OR dc.workspace_id = $1::uuid)
                  AND (dc.text ILIKE ANY($2::text[]) OR d.title ILIKE ANY($2::text[]))
                ORDER BY dc.sequence_number
                LIMIT $3
            """
            sql_two_tokens = """
                SELECT dc.text, d.title, d.reference_id, CAST(NULL AS float) AS similarity
                FROM knowledge.document_chunks dc
                JOIN knowledge.documents d ON d.id = dc.document_id
                WHERE d.deleted_at IS NULL AND d.status = 'indexed'
                  AND ($1::uuid IS NULL OR dc.workspace_id = $1::uuid)
                  AND (
                      (dc.text ILIKE $2 AND dc.text ILIKE $3)
                      OR (d.title ILIKE $2 AND d.title ILIKE $3)
                  )
                ORDER BY dc.sequence_number
                LIMIT $4
            """

            q = (query or "").strip()
            stop = {
                "the",
                "and",
                "for",
                "with",
                "from",
                "that",
                "this",
                "you",
                "your",
                "work",
                "policy",
                "policies",
                "home",
                "employee",
                "employees",
            }
            raw_words = [
                w.lower() for w in re.split(r"[^a-zA-Z0-9]+", q) if len(w) >= 3
            ]
            words = [w for w in raw_words if w not in stop]

            patterns: List[str] = []
            if q:
                patterns.append(f"%{q}%")
            patterns.extend([f"%{w}%" for w in words[:8]])
            if not patterns:
                return []

            token_patterns = [p for p in patterns if p != f"%{q}%"]
            require_two = len(token_patterns) >= 2

            async def _run_query(conn: asyncpg.Connection) -> list:
                if require_two:
                    return await asyncio.wait_for(
                        conn.fetch(
                            sql_two_tokens,
                            organization_id,
                            token_patterns[0],
                            token_patterns[1],
                            top_k,
                        ),
                        timeout=15,
                    )
                return await asyncio.wait_for(
                    conn.fetch(sql_single, organization_id, patterns, top_k),
                    timeout=15,
                )

            if use_pool:
                pool = await self._get_pool()
                async with pool.acquire() as conn:
                    rows = await _run_query(conn)
            else:
                conn = await asyncio.wait_for(self._get_fresh_connection(), timeout=10)
                try:
                    rows = await _run_query(conn)
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
            logger.error("[RAGSearchTool] Keyword fallback failed: %s", e)
            return []

    # ─────────────────────────────────────────────────────────────────────────
    # Format
    # ─────────────────────────────────────────────────────────────────────────

    def _format_results(self, query: str, chunks: List[Dict[str, Any]]) -> str:
        if not chunks:
            return (
                f"No relevant documents found for: '{query}'\n"
                "No indexed documents match this query. "
                "Try rephrasing or upload files on the Documents page."
            )

        max_chars_per_chunk = 2500
        max_total_chars = 12500
        lines = [f"Found {len(chunks)} relevant document section(s):\n", "=" * 60]
        total = sum(len(l) for l in lines)

        for i, chunk in enumerate(chunks, start=1):
            header = (
                f"\n[{i}] Source: {chunk['title']} "
                f"(ref: {chunk['reference_id']}, similarity: {chunk.get('similarity')})"
            )
            body = (chunk["text"] or "").strip()
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

    # ─────────────────────────────────────────────────────────────────────────
    # Search orchestration — Phase 1 multi-query with RRF
    # ─────────────────────────────────────────────────────────────────────────

    async def _execute_multi_query_search(
        self,
        query_variants: List[str],
        organization_id: Optional[str],
        top_k: int,
        similarity_threshold: float,
        use_pool: bool = True,
    ) -> List[Dict[str, Any]]:
        """
        Execute parallel multi-query vector search with RRF merge.

        Given preprocessed query variants, this method:
        1. Embeds all variants in parallel
        2. Searches all variants in parallel
        3. Merges results with Reciprocal Rank Fusion

        Does NOT perform preprocessing or keyword fallback — those are
        the caller's responsibility.
        """
        # Over-fetch per variant so RRF has enough candidates to rerank
        fetch_k = min(top_k * 3, 20)

        vectors = await self._embed_queries_parallel(query_variants)
        if not vectors:
            logger.warning("[RAGSearchTool] All embeddings failed")
            return []

        search_tasks = [
            self._vector_search(
                query_vector=vec,
                query_text=query_variants[i],
                organization_id=organization_id,
                top_k=fetch_k,
                threshold=similarity_threshold,
                use_pool=use_pool,
            )
            for i, vec in enumerate(vectors)
        ]

        raw_results = await asyncio.gather(*search_tasks, return_exceptions=True)

        result_lists: List[List[Dict[str, Any]]] = []
        for i, res in enumerate(raw_results):
            if isinstance(res, Exception):
                logger.warning(
                    "[RAGSearchTool] Search failed for variant %r: %s — skipping",
                    query_variants[i][:50],
                    res,
                )
            elif res:
                result_lists.append(res)

        if not result_lists:
            return []

        if len(result_lists) == 1:
            return result_lists[0][:top_k]

        return self._reciprocal_rank_fusion(result_lists, top_k)

    async def _search_async(
        self,
        query: str,
        organization_id: Optional[str],
        top_k: int,
        similarity_threshold: float,
        use_pool: bool = True,
    ) -> List[Dict[str, Any]]:
        """
        Phase 1 multi-query search with Reciprocal Rank Fusion.

        Steps:
        1. Preprocess raw query → list of 1–N query strings
        2. Delegate to _execute_multi_query_search for embed/search/RRF
        3. Fallback to keyword search if no vector results at all
        """
        search_start = time.perf_counter()
        base_queries = await self._preprocess_query_fast(query)
        expansion_task = asyncio.create_task(
            self._expand_query_variants_async(base_queries)
        )

        primary_chunks = await self._execute_multi_query_search(
            query_variants=base_queries,
            organization_id=organization_id,
            top_k=top_k,
            similarity_threshold=similarity_threshold,
            use_pool=use_pool,
        )

        if not primary_chunks:
            logger.info(
                "[RAGSearchTool] No vector hits for any variant — keyword fallback (org=%s)",
                organization_id,
            )
            primary_chunks = await self._keyword_search(query, organization_id, top_k, use_pool)

        logger.info(
            "Primary search completed in %.2fs",
            time.perf_counter() - search_start,
        )

        try:
            expanded_queries = await asyncio.wait_for(expansion_task, timeout=3)
        except Exception:
            expanded_queries = base_queries

        logger.info(
            "Expansion completed in %.2fs",
            time.perf_counter() - search_start,
        )

        if set(expanded_queries) == set(base_queries):
            return primary_chunks

        expanded_chunks = await self._execute_multi_query_search(
            query_variants=expanded_queries,
            organization_id=organization_id,
            top_k=top_k,
            similarity_threshold=similarity_threshold,
            use_pool=use_pool,
        )

        final_chunks = self._reciprocal_rank_fusion(
            [primary_chunks, expanded_chunks],
            top_k,
        )

        logger.info(
            "Total search completed in %.2fs",
            time.perf_counter() - search_start,
        )

        logger.info(
            "[RAGSearchTool] Final: %d chunks (variants=%d, expanded=%d, org=%s)",
            len(final_chunks),
            len(base_queries),
            len(expanded_queries),
            organization_id,
        )
        return final_chunks

    # ─────────────────────────────────────────────────────────────────────────
    # Public entry points
    # ─────────────────────────────────────────────────────────────────────────

    async def _arun(
        self,
        query: str = "",
        top_k: int = 5,
        similarity_threshold: float = 0.3,
        run_manager: Any = None,
        ctx: ToolContext = None,
    ) -> str:
        """Async path — FastAPI / async context. Uses shared pool."""
        self._ensure_initialized()
        organization_id = ctx.organization_id if ctx else None
        logger.info(
            "[RAGSearchTool] _arun query=%r org=%s", query[:80], organization_id
        )
        chunks = await self._search_async(
            query, organization_id, top_k, similarity_threshold, use_pool=True
        )
        return self._format_results(query, chunks)

    def _run(
        self,
        query: str = "",
        top_k: int = 5,
        similarity_threshold: float = 0.3,
        run_manager: Any = None,
        ctx: ToolContext = None,
    ) -> str:
        """
        Sync path — LangGraph worker thread.
        Uses asyncio.run() + fresh connections (no shared pool) to avoid
        'Event loop is closed' when called from a thread-isolated event loop.
        """
        start_time = time.time()
        try:
            self._ensure_initialized()
            organization_id = ctx.organization_id if ctx else None
            logger.info(
                "[RAGSearchTool] _run query=%r org=%s", query[:80], organization_id
            )

            chunks = asyncio.run(
                self._search_async(
                    query, organization_id, top_k, similarity_threshold, use_pool=False
                )
            )

            elapsed = time.time() - start_time
            logger.info(
                "[RAGSearchTool] _run done in %.2fs (%d chunks)", elapsed, len(chunks)
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

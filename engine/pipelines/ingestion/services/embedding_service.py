"""OpenAI embedding service: batch embed text chunks to 1536-dim vectors."""

import asyncio
import logging
import os
from typing import List, Optional

from engine.pipelines.ingestion.exceptions import EmbeddingError

logger = logging.getLogger(__name__)


def _get_settings():
    try:
        from engine.shared.config.settings import get_settings
    except ImportError:
        from engine.shared.config.settings import get_settings
    return get_settings()


class EmbeddingService:
    """
    Convert text chunks to 1536-dim embeddings via OpenAI.
    Batch: 100 chunks per API call. Retry with exponential backoff.
    """

    def __init__(self):
        s = _get_settings()
        raw_provider = (
            os.getenv("EMBEDDING_PROVIDER")
            or os.getenv("DEFAULT_EMBEDDING_PROVIDER")
            or getattr(s, "embedding_provider", "")
            or getattr(s, "default_embedding_provider", "")
            or "openai"
        )
        self.provider = raw_provider.strip().lower()
        if self.provider not in {"openai", "groq", "gemini"}:
            raise EmbeddingError(
                f"Unsupported EMBEDDING_PROVIDER '{self.provider}'. "
                "Supported providers: openai, groq, gemini."
            )
        self._api_key = (
            (os.getenv("GROQ_API_KEY") or getattr(s, "groq_api_key", "") or "")
            if self.provider == "groq"
            else (os.getenv("GOOGLE_API_KEY") or getattr(s, "google_api_key", "") or "")
            if self.provider == "gemini"
            else (os.getenv("OPENAI_API_KEY") or getattr(s, "openai_api_key", "") or "")
        )
        self._base_url = (
            "https://api.groq.com/openai/v1"
            if self.provider == "groq"
            else "https://generativelanguage.googleapis.com/v1beta/openai/"
            if self.provider == "gemini"
            else None
        )
        self.model = os.getenv("EMBEDDING_MODEL") or ("gemini-embedding-2" if self.provider == "gemini" else "text-embedding-3-small")
        self.batch_size = getattr(s, "embedding_batch_size", 100)
        self.max_retries = getattr(s, "embedding_max_retries", 10)
        self.timeout = getattr(s, "embedding_timeout_seconds", 120)
        self._client = None

    def _get_client(self):
        if self._client is None:
            try:
                from openai import AsyncOpenAI
            except ImportError:
                raise EmbeddingError("openai package required; pip install openai")
            self._client = AsyncOpenAI(api_key=self._api_key, base_url=self._base_url)
        return self._client
    
    async def embed_query(self, query: str) -> List[float]:
        """
        Embed a single query string.
        Used by attachment_context_fetch tool and other single-query use cases.
        """
        if not query or not query.strip():
            raise ValueError("Query cannot be empty")

        logger.debug("Embedding single query (length: %d)", len(query))

        try:
            embeddings = await self._embed_batch([query.strip()])
            return embeddings[0] 
        except Exception as e:
            logger.error(f"Failed to embed query: {e}")
            raise EmbeddingError(f"Failed to embed query: {e}") from e

    async def embed_chunks(
        self,
        texts: List[str],
        batch_size: Optional[int] = None,
    ) -> List[List[float]]:
        """Embed texts in batches. Returns list of 1536-dim vectors in same order."""
        batch_size = batch_size or self.batch_size
        if not texts:
            return []
        logger.info("Embedding %s texts in batches of %s", len(texts), batch_size)
        all_embeddings = []
        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            vectors = await self._embed_batch(batch)
            all_embeddings.extend(vectors)
        logger.info("Embedded %s vectors", len(all_embeddings))
        return all_embeddings

    async def _embed_batch(self, texts: List[str]) -> List[List[float]]:
        client = self._get_client()
        for attempt in range(1, self.max_retries + 1):
            try:
                kwargs = {
                    "model": self.model,
                    "input": texts,
                    "encoding_format": "float",
                }
                if self.provider == "gemini":
                    kwargs["dimensions"] = 768
                    
                resp = await asyncio.wait_for(
                    client.embeddings.create(**kwargs),
                    timeout=self.timeout,
                )
                return [item.embedding for item in resp.data]
            except asyncio.TimeoutError as e:
                logger.warning("Embedding attempt %s timed out", attempt)
                if attempt == self.max_retries:
                    raise EmbeddingError(f"Embedding timed out after {self.max_retries} attempts") from e
                await asyncio.sleep(2 ** attempt)
            except Exception as e:
                err_str = str(e).lower()
                if "429" in str(e) or "rate" in err_str:
                    logger.warning("Rate limited (attempt %s)", attempt)
                    if attempt == self.max_retries:
                        raise EmbeddingError(f"Rate limited after {self.max_retries} attempts") from e
                    await asyncio.sleep(35)
                elif "400" in str(e) or "invalid" in err_str:
                    raise EmbeddingError(f"Invalid request: {e}") from e
                else:
                    logger.exception("Embedding attempt %s failed", attempt)
                    if attempt == self.max_retries:
                        raise EmbeddingError(f"Embedding failed: {e}") from e
                    await asyncio.sleep(2 ** attempt)
        raise EmbeddingError("Unexpected: retry loop exited")

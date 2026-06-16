"""
Chunking service: token-based text splitting for document ingestion.

Uses LangChain's RecursiveCharacterTextSplitter (which is the same algorithm
specified by the Phase 1 LlamaIndex integration docs as RecursiveCharacterTextSplitter).
The method `create_chunks_with_llamaindex` is the canonical name from Phase 1 docs;
`create_chunks` is kept as an alias for backward compatibility.
"""

import logging
from typing import Any, Dict, List, Optional
from uuid import UUID

from langchain_text_splitters import RecursiveCharacterTextSplitter

logger = logging.getLogger(__name__)

# Token encoder for GPT-style token counting (cl100k_base used by GPT-3.5/GPT-4)
_TIKTOKEN_ENCODING_NAME = "cl100k_base"


def _get_encoder():
    """Lazy-load tiktoken encoder to avoid import cost at module load."""
    import tiktoken
    return tiktoken.get_encoding(_TIKTOKEN_ENCODING_NAME)


class ChunkingService:
    """
    Token-based text chunking using RecursiveCharacterTextSplitter.

    Aligned with Phase 1 LlamaIndex integration spec:
    - RecursiveCharacterTextSplitter: 512 tokens/chunk, 50-token overlap
    - Preserves semantic boundaries (paragraphs → sentences → words)
    - LlamaIndex reader metadata (page_label, section, row_index, etc.) can be
      passed into create_chunks_with_llamaindex() and is stored in each chunk's
      embedding_metadata field.
    """

    def __init__(
        self,
        chunk_size_tokens: int = 512,
        chunk_overlap_tokens: int = 50,
        max_chunk_size_tokens: int = 2048,
    ):
        self.chunk_size_tokens = chunk_size_tokens
        self.chunk_overlap_tokens = chunk_overlap_tokens
        self.max_chunk_size_tokens = max_chunk_size_tokens
        self._encoder = None
        self._splitter = None

    def _ensure_splitter(self) -> RecursiveCharacterTextSplitter:
        if self._splitter is None:
            self._splitter = RecursiveCharacterTextSplitter.from_tiktoken_encoder(
                encoding_name=_TIKTOKEN_ENCODING_NAME,
                chunk_size=self.chunk_size_tokens,
                chunk_overlap=self.chunk_overlap_tokens,
            )
        return self._splitter

    def count_tokens(self, text: str) -> int:
        """Count tokens using tiktoken (cl100k_base)."""
        if self._encoder is None:
            self._encoder = _get_encoder()
        return len(self._encoder.encode(text))

    def chunk_text(self, text: str) -> List[str]:
        """Split text into chunks using RecursiveCharacterTextSplitter."""
        if not (text and text.strip()):
            return []
        splitter = self._ensure_splitter()
        chunks = splitter.split_text(text.strip())
        for i, chunk in enumerate(chunks):
            n = self.count_tokens(chunk)
            if n > self.max_chunk_size_tokens:
                logger.warning(
                    "Chunk %s exceeds max size: %s > %s tokens",
                    i, n, self.max_chunk_size_tokens,
                )
        return chunks

    def create_chunks_with_llamaindex(
        self,
        text: str,
        document_id: UUID,
        workspace_id: UUID,
        sequence_offset: int = 0,
        loader_metadata: Optional[Dict[str, Any]] = None,
    ) -> List[dict]:
        """
        Convert document text to chunk dicts, preserving LlamaIndex reader metadata.

        Args:
            text: Full document text from LlamaIndex reader.
            document_id: Document UUID.
            workspace_id: Workspace UUID.
            sequence_offset: Starting sequence number.
            loader_metadata: LlamaIndex reader metadata dict (page_label, section,
                             row_index, file_name, etc.) to attach to each chunk.

        Returns:
            List of chunk dicts compatible with DocumentService.save_chunks.
            Each chunk includes embedding_metadata with loader_metadata.
        """
        chunk_strings = self.chunk_text(text)
        chunks_data: List[dict] = []

        # Base embedding_metadata from LlamaIndex reader metadata
        base_embedding_meta: Dict[str, Any] = {}
        if loader_metadata:
            # Keep only LlamaIndex-style fields
            for key in ("page_label", "section", "row_index", "file_name", "source", "author"):
                if key in loader_metadata:
                    base_embedding_meta[key] = loader_metadata[key]

        for i, chunk_text in enumerate(chunk_strings):
            token_count = self.count_tokens(chunk_text)
            embedding_meta = {**base_embedding_meta, "chunk_index": sequence_offset + i}
            chunks_data.append({
                "sequence_number": sequence_offset + i,
                "text": chunk_text,
                "token_count": token_count,
                "embedding": None,
                "embedding_model": None,
                "embedding_metadata": embedding_meta or None,
            })

        logger.debug(
            "Created %s chunks from document %s (total tokens ~%s)",
            len(chunks_data), document_id, sum(c["token_count"] for c in chunks_data),
        )
        return chunks_data

    def create_chunks(
        self,
        text: str,
        document_id: UUID,
        workspace_id: UUID,
        sequence_offset: int = 0,
    ) -> List[dict]:
        """
        Backward-compatible alias for create_chunks_with_llamaindex (no loader metadata).
        Prefer create_chunks_with_llamaindex when loader metadata is available.
        """
        return self.create_chunks_with_llamaindex(
            text=text,
            document_id=document_id,
            workspace_id=workspace_id,
            sequence_offset=sequence_offset,
            loader_metadata=None,
        )


def get_chunking_service(
    chunk_size_tokens: int = 512,
    chunk_overlap_tokens: int = 50,
    max_chunk_size_tokens: int = 2048,
) -> ChunkingService:
    """Factory for ChunkingService (e.g. from settings)."""
    return ChunkingService(
        chunk_size_tokens=chunk_size_tokens,
        chunk_overlap_tokens=chunk_overlap_tokens,
        max_chunk_size_tokens=max_chunk_size_tokens,
    )

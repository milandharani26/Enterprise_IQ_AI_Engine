# Document Ingestion & RAG — Implementation Guide

> **Purpose:** Port the ai-platform document ingestion pipeline and RAG chat flow into another project.  
> **Scope (Phase 1):** Database tables, ingestion APIs, loaders, chunking, embeddings, `rag_search` tool, and chat APIs.  
> **Scope (Phase 2):** Frontend integration (out of scope for this doc; API contracts are defined here).

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [Implementation Phases](#2-implementation-phases)
3. [Database Schema](#3-database-schema)
4. [Environment Variables](#4-environment-variables)
5. [Python Dependencies](#5-python-dependencies)
6. [Source Files to Port](#6-source-files-to-port)
7. [Document Ingestion API](#7-document-ingestion-api)
8. [Document Loaders (All MIME Types)](#8-document-loaders-all-mime-types)
9. [Text Splitting & Chunking](#9-text-splitting--chunking)
10. [Embedding Service](#10-embedding-service)
11. [Indexing Pipeline](#11-indexing-pipeline)
12. [RAG Search Tool](#12-rag-search-tool)
13. [Chat & LLM Integration](#13-chat--llm-integration)
14. [API Reference & cURL Examples](#14-api-reference--curl-examples)
15. [Implementation Checklist](#15-implementation-checklist)
16. [Testing Plan](#16-testing-plan)
17. [Troubleshooting](#17-troubleshooting)

---

## 1. Architecture Overview

```mermaid
flowchart TB
    subgraph ingest [Document Ingestion]
        A[POST /documents/ingest] --> B[Create/Upsert knowledge.documents]
        B --> C[Background Indexing Task]
        C --> D[Fetch bytes from S3/GCS/HTTP]
        D --> E[MIME-based Loader Registry]
        E --> F[ChunkingService - 512 tokens / 50 overlap]
        F --> G[EmbeddingService - text-embedding-3-small]
        G --> H[Save knowledge.document_chunks + pgvector]
        H --> I[status = indexed]
    end

    subgraph chat [RAG Chat]
        J[POST /chat/conversations/messages] --> K[AssistantExecutor]
        K --> L[LangGraph + LLM]
        L --> M{Needs document context?}
        M -->|yes| N[rag_search tool]
        N --> O[Embed query]
        O --> P[Hybrid pgvector + full-text search]
        P --> Q[Return chunks to LLM]
        Q --> L
        M -->|no| R[Direct answer]
        L --> S[Assistant response + content_blocks]
    end

    H -.-> P
```

### Key design decisions (match ai-platform exactly)

| Decision | Value |
|----------|-------|
| Schema | `knowledge` |
| Tables | `documents`, `document_chunks` |
| Vector store | PostgreSQL + `pgvector` extension |
| Embedding model | `text-embedding-3-small` (1536 dimensions) |
| Similarity metric | Cosine (`<=>` operator, score = `1 - distance`) |
| Chunk size | 512 tokens, 50 token overlap |
| Token encoder | `tiktoken` `cl100k_base` |
| Text splitter | LangChain `RecursiveCharacterTextSplitter` |
| Document ID | Client-supplied `reference_id` (UUID) becomes `documents.id` |
| Indexing mode | Async background task (FastAPI `BackgroundTasks`) by default |
| RAG retrieval | Hybrid: 75% vector + 25% Postgres full-text (`ts_rank_cd`) |

---

## 2. Implementation Phases

### Phase 1 — Backend APIs (do this first)

1. Create `knowledge` schema + `documents` + `document_chunks` tables (Alembic migration).
2. Port ORM models, Pydantic schemas, and `DocumentService`.
3. Port loader registry + all MIME loaders + `fetch.py`.
4. Port `ChunkingService` and `EmbeddingService`.
5. Port `run_index_document_task` indexing pipeline.
6. Expose document routes: ingest, get, status, update, delete.
7. Port `RAGSearchTool` and register it on assistants that need document Q&A.
8. Wire chat: `ConversationService` → `AssistantExecutor` → LangGraph with `rag_search`.
9. Test end-to-end with cURL/Postman.

### Phase 2 — Frontend (later)

1. Document upload UI → call ingest API with `reference_id` + `source_url`.
2. Poll `GET /documents/ingestion-status/{document_id}` until `indexed`.
3. Chat UI → `POST /chat/conversations/messages` with `workspace_ids`.
4. Render `content_blocks` from assistant response.

---

## 3. Database Schema

### 3.1 Prerequisites

```sql
CREATE EXTENSION IF NOT EXISTS vector;
CREATE SCHEMA IF NOT EXISTS knowledge;
```

### 3.2 Table: `knowledge.documents`

Master record for each ingested document.

| Column | Type | Notes |
|--------|------|-------|
| `id` | UUID PK | Defaults to `gen_random_uuid()`; **ingest uses client `reference_id` as PK** |
| `workspace_id` | UUID NOT NULL | Tenant/workspace scope |
| `reference_id` | VARCHAR(255) NOT NULL | Client correlation ID (string form of UUID) |
| `title` | VARCHAR(512) | Human-readable title |
| `source` | VARCHAR(100) | `s3`, `gcs`, or `api` (derived from URL) |
| `source_url` | VARCHAR(2048) | `s3://`, `gs://`, `http://`, or `https://` |
| `file_path` | VARCHAR(1024) | Optional local path |
| `mime_type` | VARCHAR(100) | Detected at load time |
| `file_size_bytes` | BIGINT | Optional |
| `status` | VARCHAR(50) | `draft` \| `processing` \| `indexed` \| `failed` |
| `processing_error` | TEXT | Error message when `failed` |
| `processing_started_at` | TIMESTAMP | Set when status → `processing` |
| `processing_completed_at` | TIMESTAMP | Set when status → `indexed` or `failed` |
| `content` | TEXT | Optional full extracted text |
| `metadata` | JSONB | Custom tags, author, etc. |
| `chunk_count` | INT DEFAULT 0 | Denormalized count |
| `version` | INT DEFAULT 1 | Auto-incremented on title collision |
| `created_at` | TIMESTAMP | `now()` |
| `updated_at` | TIMESTAMP | `now()` |
| `created_by` | UUID | Optional |
| `deleted_at` | TIMESTAMP | Soft delete (upsert can revive) |

**Constraints:**
- `status IN ('draft', 'processing', 'indexed', 'failed')`
- `UNIQUE (workspace_id, reference_id)`
- `UNIQUE (workspace_id, title, version)`

**Indexes:**
- `idx_documents_workspace_id`
- `idx_documents_status`
- `idx_documents_created_at`
- `idx_documents_source`

### 3.3 Table: `knowledge.document_chunks`

Chunked text + vector embeddings for RAG retrieval.

| Column | Type | Notes |
|--------|------|-------|
| `id` | UUID PK | `gen_random_uuid()` |
| `document_id` | UUID FK → `documents.id` ON DELETE CASCADE | Parent document |
| `workspace_id` | UUID NOT NULL | Denormalized for fast workspace filtering |
| `sequence_number` | INT NOT NULL | 0-based order within document |
| `text` | TEXT NOT NULL | Chunk content (null bytes stripped) |
| `token_count` | INT | tiktoken count |
| `embedding` | `vector(1536)` | pgvector column |
| `embedding_model` | VARCHAR(255) | e.g. `text-embedding-3-small` |
| `embedding_created_at` | TIMESTAMP | Optional |
| `embedding_metadata` | JSONB | `page_label`, `section`, `chunk_index`, etc. |
| `created_at` | TIMESTAMP | |
| `updated_at` | TIMESTAMP | |

**Constraints:**
- `UNIQUE (document_id, sequence_number)`

**Indexes:**
- `idx_document_chunks_document_id`
- `idx_document_chunks_embedding_ivfflat` — IVFFlat cosine index:

```sql
CREATE INDEX idx_document_chunks_embedding_ivfflat
ON knowledge.document_chunks
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);
```

> **Note:** IVFFlat is approximate. For small corpora (<10k chunks), a sequential scan may be fine during development. Rebuild the index after bulk inserts in production.

### 3.4 Reference migration

Copy from ai-platform:

```
engine/alembic/versions/be362d8427dc_add_knowledge_schema_and_tables.py
engine/shared/models/document_model.py
```

---

## 4. Environment Variables

Add these to your `.env` (values from ai-platform `engine/shared/config/settings.py`):

```bash
# Database (must support pgvector)
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/yourdb

# Embeddings
EMBEDDING_PROVIDER=openai          # or groq
EMBEDDING_MODEL=text-embedding-3-small
EMBEDDING_DIMENSIONS=1536
EMBEDDING_BATCH_SIZE=100
EMBEDDING_MAX_RETRIES=3
EMBEDDING_TIMEOUT_SECONDS=120
OPENAI_API_KEY=sk-...

# Chunking
CHUNK_SIZE_TOKENS=512
CHUNK_OVERLAP_TOKENS=50
MAX_CHUNK_SIZE_TOKENS=2048

# Indexing
ENABLE_ASYNC_INDEXING=true
USE_CELERY_FOR_INDEXING=false      # set true only if you port Celery tasks
INDEXING_TASK_TIMEOUT_SECONDS=3600

# Cloud storage (for s3:// and gs:// URLs)
AWS_S3_ENABLED=true
AWS_S3_BUCKET=
AWS_S3_REGION=us-east-1
# AWS credentials via standard boto3 env/IAM

GCS_ENABLED=false
GCS_PROJECT_ID=
GCS_BUCKET=
GCS_CREDENTIALS_PATH=

# pgvector
PGVECTOR_SEARCH_TYPE=cosine
PGVECTOR_IVF_LISTS=100

# LLM (for chat — separate from embeddings)
# Configure per your assistant's llm_config in DB
```

---

## 5. Python Dependencies

Minimum packages (from `engine/pyproject.toml` ingestion-related subset):

```
fastapi
uvicorn
sqlalchemy
asyncpg
psycopg2-binary
alembic
pgvector
pydantic-settings
python-dotenv

# Chunking & embeddings
tiktoken
langchain-text-splitters
openai

# Loaders
llama-index-readers-file    # PDF via PDFReader
pymupdf
python-docx
docx2txt
python-pptx
openpyxl
beautifulsoup4
chardet
httpx
boto3
google-cloud-storage

# Chat / RAG
langchain-core
langchain
langgraph
langchain-openai          # or langchain-groq, etc.

# Optional: legacy Office formats (.doc, .xls, .ppt) need LibreOffice installed on server
```

**LibreOffice requirement:** `.doc`, `.xls`, `.ppt` loaders convert to modern formats via LibreOffice headless. Install on the server:

```bash
# Ubuntu/Debian
apt-get install libreoffice

# macOS
brew install --cask libreoffice
```

---

## 6. Source Files to Port

Copy these directories/files from ai-platform and adjust import paths for your project package name.

### 6.1 Database & schemas

| File | Purpose |
|------|---------|
| `engine/shared/models/document_model.py` | SQLAlchemy `Document`, `DocumentChunk` |
| `engine/shared/schemas/document_schema.py` | Request/response Pydantic models |
| `engine/alembic/versions/be362d8427dc_add_knowledge_schema_and_tables.py` | Migration |

### 6.2 Document service & routes

| File | Purpose |
|------|---------|
| `engine/domains/workspaces/documents/documents_service.py` | CRUD, load, chunk save, MIME detection |
| `engine/domains/workspaces/documents/documents_routes.py` | REST endpoints |

### 6.3 Ingestion pipeline

| File | Purpose |
|------|---------|
| `engine/pipelines/ingestion/indexing.py` | `run_index_document_task` |
| `engine/pipelines/ingestion/exceptions.py` | Error types |
| `engine/pipelines/ingestion/services/chunking_service.py` | Token-based splitting |
| `engine/pipelines/ingestion/services/embedding_service.py` | OpenAI/Groq embeddings |
| `engine/pipelines/ingestion/loaders/` | **Entire directory** (see §8) |

### 6.4 RAG & chat

| File | Purpose |
|------|---------|
| `engine/domains/assistants/tools/implementations/rag_search.py` | `rag_search` tool |
| `engine/domains/assistants/tools/base_tool.py` | `ToolContext`, `BaseTool` |
| `engine/domains/assistants/tools/tool_registry.py` | Register `RAGSearchTool` |
| `engine/domains/assistants/runtime/executor.py` | `AssistantExecutor.execute()` |
| `engine/services/chat_service.py` | `ChatService.chat()` / `chat_stream()` |
| `engine/domains/conversations/conversation_service.py` | `process_and_execute_message()` |
| `engine/domains/conversations/conversation_routes.py` | Chat conversation APIs |
| `engine/routes/v1/chat_route.py` | Streaming chat endpoint |
| `engine/shared/schemas/chat.py` | `ChatRequest`, `ChatResponse`, etc. |

### 6.5 App startup

Register loaders at startup (same as Celery worker does):

```python
from your_project.pipelines.ingestion.loaders import register_all_loaders

register_all_loaders()
```

In ai-platform this is called from `engine/pipelines/ingestion/celery_tasks.py` and should also run in your FastAPI `lifespan` or `on_startup` hook.

---

## 7. Document Ingestion API

**Base path:** `/api/v1/documents`  
**Auth:** Bearer token via `get_current_user` (adapt to your auth).

### 7.1 `POST /documents/ingest` — Queue document for indexing

**Status:** `202 Accepted`

**Query params:**
- `workspace_id` (UUID, required)

**Request body:**

```json
{
  "reference_id": "550e8400-e29b-41d4-a716-446655440000",
  "source_url": "s3://my-bucket/policies/handbook.pdf",
  "title": "Employee Handbook 2026",
  "metadata": {
    "department": "HR",
    "tags": ["policy", "onboarding"]
  }
}
```

**Validation rules:**
- `reference_id`: UUID (becomes `documents.id`)
- `source_url`: must start with `s3://`, `gs://`, `http://`, or `https://`
- `title`: non-empty, max 500 chars
- `metadata`: max 10 keys; string values max 500 chars

**Response:**

```json
{
  "status_code": 202,
  "message": "Document queued for indexing",
  "data": {
    "doc_id": "550e8400-e29b-41d4-a716-446655440000",
    "reference_id": "550e8400-e29b-41d4-a716-446655440000",
    "status": "draft",
    "message": "Document queued for indexing",
    "task_id": null
  }
}
```

**Upsert behavior:** If `(workspace_id, reference_id)` already exists:
1. Update metadata/title/source_url
2. Clear old chunks
3. Reset status to `draft`
4. Re-queue indexing

### 7.2 `GET /documents/ingestion-status/{document_id}`

Poll until `status` is `indexed` or `failed`.

```json
{
  "status_code": 200,
  "message": "Document ingestion status retrieved successfully",
  "data": {
    "document_id": "550e8400-e29b-41d4-a716-446655440000",
    "status": "indexed"
  }
}
```

**Status lifecycle:**

```
draft → processing → indexed
                   ↘ failed (processing_error set)
```

### 7.3 Other document endpoints

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/documents/{id}?workspace_id=` | Get document details |
| `PATCH` | `/documents/{id}?workspace_id=` | Update metadata/status |
| `DELETE` | `/documents/{id}` | Hard delete (chunks cascade) |

### 7.4 Indexing flow (background task)

Implemented in `run_index_document_task(doc_id, workspace_id)`:

```
1. Fetch document row
2. set_processing_status("processing")
3. load_document(source_url)  → text + loader_metadata
4. chunking.create_chunks_with_llamaindex(text, doc_id, workspace_id, loader_metadata)
5. embedding_service.embed_chunks(chunk_texts)
6. Attach vectors to chunk dicts
7. save_chunks(doc_id, workspace_id, chunks_data)
8. set_processing_status("indexed")
```

On embedding failure: chunks are saved without vectors, status → `failed` with error message.

---

## 8. Document Loaders (All MIME Types)

### 8.1 Architecture

```
LoaderRegistry (singleton)
  └── MIME type → DocumentLoader class

DocumentLoader (abstract)
  └── load_from_url(uri) → (text: str, metadata: dict)

fetch_bytes_from_uri(uri)  → raw bytes from s3/gs/http/file
```

### 8.2 Registered MIME types

| MIME Type(s) | Loader Class | Parser / Library |
|--------------|--------------|------------------|
| `application/pdf` | `PDFLoader` | LlamaIndex `PDFReader` (PyMuPDF) |
| `application/vnd.openxmlformats-officedocument.wordprocessingml.document` | `DocxLoader` | LlamaIndex / python-docx |
| `application/msword`, `application/vnd.ms-word`, `application/x-msword` | `DocLoader` | LibreOffice → DOCX → DocxLoader |
| `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`, `application/vnd.ms-excel` | `XlsxLoader` | openpyxl |
| `application/vnd.ms-excel`, `application/x-msexcel`, `application/vnd.ms-excel.sheet.macroEnabled.12` | `XlsLoader` | LibreOffice → XLSX → XlsxLoader |
| `application/vnd.openxmlformats-officedocument.presentationml.presentation` | `PptxLoader` | python-pptx |
| `application/vnd.ms-powerpoint`, `application/x-mspowerpoint` | `PptLoader` | LibreOffice → PPTX → PptxLoader |
| `text/csv` | `CsvLoader` | LlamaIndex `SimpleCSVReader` |
| `text/plain`, `text/markdown` | `TxtLoader` | chardet encoding detection |
| `text/html`, `application/xhtml+xml` | `HtmlLoader` | BeautifulSoup |
| `application/json`, `text/json` | `JsonLoader` | Python `json` |

Registration (`register_all_loaders()`):

```python
LoaderRegistry.register(["application/pdf"], PDFLoader)
LoaderRegistry.register(
    ["application/vnd.openxmlformats-officedocument.wordprocessingml.document"],
    DocxLoader,
)
# ... see engine/pipelines/ingestion/loaders/__init__.py for full list
```

### 8.3 URI fetch support

`fetch_bytes_from_uri` supports:

| Scheme | Method |
|--------|--------|
| `s3://bucket/key` | boto3 `get_object` |
| `gs://bucket/path` | google-cloud-storage |
| `http://` / `https://` | httpx (with S3 virtual-hosted URL boto3 fallback for PutObject presigns) |
| `file://` | local file read (used for upload temp files) |

### 8.4 MIME detection

`DocumentService._detect_mime_type(uri)` uses, in order:

1. URL path extension (`mimetypes.guess_type`)
2. S3 presigned `response-content-disposition` filename
3. Query params: `filename`, `file`, `name`, `key`, `path`
4. Extension sniff on full decoded URI

Fallback: `application/octet-stream` → loader lookup fails with `UnsupportedMimetypeError`.

### 8.5 Loader metadata preserved in chunks

PDF example metadata keys propagated to `embedding_metadata`:

- `page_label`, `section`, `row_index`, `file_name`, `source`, `author`, `chunk_index`

---

## 9. Text Splitting & Chunking

**File:** `engine/pipelines/ingestion/services/chunking_service.py`

### Algorithm

- **Splitter:** LangChain `RecursiveCharacterTextSplitter.from_tiktoken_encoder`
- **Encoding:** `cl100k_base` (GPT-3.5/4 compatible)
- **Chunk size:** 512 tokens (configurable via `CHUNK_SIZE_TOKENS`)
- **Overlap:** 50 tokens (`CHUNK_OVERLAP_TOKENS`)
- **Max chunk warning:** 2048 tokens (`MAX_CHUNK_SIZE_TOKENS`)

### Canonical method

```python
chunks_data = chunking.create_chunks_with_llamaindex(
    text=content,
    document_id=doc_id,
    workspace_id=workspace_id,
    loader_metadata=loader_metadata,  # optional, from loader
)
```

### Output shape (per chunk)

```python
{
    "sequence_number": 0,
    "text": "...",
    "token_count": 487,
    "embedding": None,           # filled after embed step
    "embedding_model": None,
    "embedding_metadata": {
        "page_label": "3",
        "chunk_index": 0
    }
}
```

### save_chunks notes

- Strips `\x00` null bytes from text (Postgres UTF-8 safety)
- Deletes existing chunks before insert (supports re-index)
- Updates `documents.chunk_count`

---

## 10. Embedding Service

**File:** `engine/pipelines/ingestion/services/embedding_service.py`

| Setting | Default |
|---------|---------|
| Provider | `openai` (or `groq`) |
| Model | `text-embedding-3-small` |
| Dimensions | 1536 |
| Batch size | 100 |
| Retries | 3 with exponential backoff |
| Timeout | 120s per batch |

**Methods:**
- `embed_chunks(texts: List[str])` → `List[List[float]]` (batch)
- `embed_query(query: str)` → `List[float]` (single, used by RAG)

**Important:** Use the **same model** for ingestion and RAG query embedding. Mismatched models break similarity search.

---

## 11. Indexing Pipeline

### Option A — FastAPI BackgroundTasks (recommended for Phase 1)

```python
# In documents_routes.py ingest handler:
if settings.enable_async_indexing:
    background_tasks.add_task(run_index_document_task, doc.id, workspace_id)
```

### Option B — Celery (optional, Phase 2)

Set `USE_CELERY_FOR_INDEXING=true` and port:
- `engine/pipelines/ingestion/celery_tasks.py`

Celery task runs: load → chunk → save → embed → persist → optional webhook.

---

## 12. RAG Search Tool

**File:** `engine/domains/assistants/tools/implementations/rag_search.py`  
**Tool name:** `rag_search`

### 12.1 Input schema

```python
class RAGSearchToolInput(BaseModel):
    query: str                          # required
    top_k: int = 5                      # 1–20
    similarity_threshold: float = 0.3   # 0.0–1.0
```

### 12.2 Execution flow

```
1. Validate ctx.workspace_ids is present
2. Embed query (text-embedding-3-small, 1536-dim)
3. Hybrid SQL search on knowledge.document_chunks JOIN knowledge.documents
4. If no vector hits → keyword ILIKE fallback
5. Format results as multi-line context string for LLM
```

### 12.3 Hybrid search SQL (core logic)

Semantic score: `1 - (embedding <=> query_vector)`  
Text score: `ts_rank_cd(to_tsvector('english', text), plainto_tsquery('english', query))`  
Final score: `0.75 * vector_score + 0.25 * text_score`

Filters:
- `dc.workspace_id = ANY(workspace_ids)`
- `d.deleted_at IS NULL`
- Vector score ≥ threshold OR text score ≥ min_text_score

### 12.4 Tool context requirement

`rag_search` **requires** `workspace_ids` in `ToolContext`:

```python
ToolContext(
    workspace_ids=["uuid-1", "uuid-2"],
    conversation_id="...",
    assistant_id="...",
    user_id="...",
)
```

Without workspace IDs the tool returns:  
`"Document search failed: workspace_ids missing from request context"`

### 12.5 Register tool on assistant

In your assistant config / tool list, include `rag_search`:

```json
{
  "tools": ["rag_search", "emit_ui_blocks"]
}
```

Register in code:

```python
from your_project.tools.tool_registry import ToolRegistryNew
from your_project.tools.implementations.rag_search import RAGSearchTool

ToolRegistryNew.register_tool(RAGSearchTool)
```

### 12.6 Optional: standalone search API (not in ai-platform yet)

For testing without LLM, expose a thin wrapper:

```
POST /api/v1/documents/search
{
  "workspace_ids": ["..."],
  "query": "refund policy",
  "top_k": 5,
  "similarity_threshold": 0.3
}
```

Internally call `RAGSearchTool._search_async()` and return JSON chunks instead of formatted text.

---

## 13. Chat & LLM Integration

### 13.1 Two chat entry points in ai-platform

| Endpoint | Use case |
|----------|----------|
| `POST /api/v1/chat/stream` | NDJSON streaming via `ChatService.chat_stream()` |
| `POST /api/v1/chat/conversations/messages` | Full conversation DB + `ConversationService.process_and_execute_message()` |

**For your project:** Start with the conversations API — it persists messages and is what the cpanel frontend uses.

### 13.2 Conversation message flow

```
POST /chat/conversations/messages
  → ConversationService.process_and_execute_message()
    → Save user message to chat.conversation_messages
    → AssistantExecutor.execute(
         workspace_ids=...,
         query=...,
         assistant=...,
       )
      → Build ToolContext(workspace_ids=...)
      → AssistantFactory.get_assistant(config)
      → build_graph(config, ctx=context)
      → graph.invoke(messages)
        → LLM may call rag_search tool
        → Tool receives ctx.workspace_ids
        → Returns document chunks as context
      → extract content_blocks + token_usage
    → Save assistant message
    → Return AssistantExecutionResponse
```

### 13.3 ChatRequest shape (direct chat API)

```json
{
  "workspace_ids": ["workspace-uuid"],
  "assistant_id": "assistant-uuid-or-code",
  "session_id": "redis-session-id",
  "user_id": "user-123",
  "message": "What is our refund policy?",
  "history": [],
  "context": {},
  "completed_tasks": []
}
```

**Critical:** `workspace_ids` must match the workspace where documents were ingested. RAG is scoped per workspace.

### 13.4 MessageCreate shape (conversations API)

```json
{
  "conv_id": "conversation-uuid-or-null-for-new",
  "workspace_ids": ["workspace-uuid"],
  "user_id": "user-123",
  "assistant_id": "assistant-uuid",
  "message": {
    "query": "What is our refund policy?",
    "text": "What is our refund policy?",
    "attachment": false,
    "attachment_ids": []
  }
}
```

### 13.5 How LLM uses RAG results

1. User asks a document question.
2. LLM (via system prompt + tool instructions) calls `rag_search(query="...")`.
3. Tool returns formatted text with numbered excerpts + source titles.
4. LLM synthesizes answer from retrieved chunks.
5. LLM calls `emit_ui_blocks` to return structured markdown/table blocks.

Ensure your assistant system prompt instructs:
- Use `rag_search` for workspace document questions
- Cite source document titles from tool results
- Do not hallucinate when no chunks are found

### 13.6 AssistantExecutor state metadata

When building graph state, pass workspace context:

```python
"metadata": {
    "workspace_id": primary_workspace_id,
    "workspace_ids": effective_workspace_ids,
    "session_id": session_id,
    "assistant_id": assistant_id,
    "user_id": user_id,
}
```

---

## 14. API Reference & cURL Examples

Replace `BASE_URL`, `TOKEN`, and UUIDs with your values.

### 14.1 Ingest a document

```bash
curl -X POST "${BASE_URL}/api/v1/documents/ingest?workspace_id=${WORKSPACE_ID}" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "reference_id": "550e8400-e29b-41d4-a716-446655440000",
    "source_url": "https://example.com/sample.pdf",
    "title": "Sample PDF",
    "metadata": {"source": "test"}
  }'
```

### 14.2 Poll ingestion status

```bash
curl "${BASE_URL}/api/v1/documents/ingestion-status/550e8400-e29b-41d4-a716-446655440000" \
  -H "Authorization: Bearer ${TOKEN}"
```

### 14.3 Chat with RAG (conversations API)

```bash
# 1. Create conversation (optional — can pass conv_id=null in message)
curl -X POST "${BASE_URL}/api/v1/chat/conversations" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "workspace_ids": ["'"${WORKSPACE_ID}"'"],
    "user_id": "user-1",
    "assistant_id": "'"${ASSISTANT_ID}"'",
    "title": "Policy Q&A"
  }'

# 2. Send message (triggers assistant + rag_search)
curl -X POST "${BASE_URL}/api/v1/chat/conversations/messages" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "conv_id": "'"${CONVERSATION_ID}"'",
    "workspace_ids": ["'"${WORKSPACE_ID}"'"],
    "user_id": "user-1",
    "assistant_id": "'"${ASSISTANT_ID}"'",
    "message": {
      "query": "Summarize the refund policy from our documents",
      "text": "Summarize the refund policy from our documents"
    }
  }'
```

### 14.4 Streaming chat (alternative)

```bash
curl -N -X POST "${BASE_URL}/api/v1/chat/stream" \
  -H "Content-Type: application/json" \
  -d '{
    "workspace_ids": ["'"${WORKSPACE_ID}"'"],
    "assistant_id": "finance-reporting-001",
    "session_id": "test-session-1",
    "user_id": "user-1",
    "message": "What does our handbook say about remote work?"
  }'
```

Response: newline-delimited JSON chunks (`chunk_type`: `text`, `tool_call`, `tool_result`, `done`).

---

## 15. Implementation Checklist

### Database
- [ ] Enable `pgvector` extension
- [ ] Create `knowledge` schema
- [ ] Create `documents` table with constraints + indexes
- [ ] Create `document_chunks` table with FK cascade
- [ ] Create IVFFlat index on `embedding`

### Ingestion
- [ ] Port `Document` / `DocumentChunk` models
- [ ] Port `DocumentIngestRequest` schema + validation
- [ ] Port `DocumentService` (create, load, save_chunks, status)
- [ ] Port entire `loaders/` package
- [ ] Call `register_all_loaders()` at app startup
- [ ] Port `ChunkingService`
- [ ] Port `EmbeddingService`
- [ ] Port `run_index_document_task`
- [ ] Wire `POST /documents/ingest` with `BackgroundTasks`
- [ ] Wire `GET /documents/ingestion-status/{id}`

### RAG
- [ ] Port `RAGSearchTool`
- [ ] Register tool in tool registry
- [ ] Add `rag_search` to assistant tool config in DB
- [ ] Verify `ToolContext.workspace_ids` is passed from chat layer
- [ ] (Optional) Add standalone `POST /documents/search` for debugging

### Chat
- [ ] Port `ChatService` or `AssistantExecutor` (minimum: executor + graph builder)
- [ ] Port conversation routes or `/chat/stream`
- [ ] Ensure assistant has `rag_search` in tools list
- [ ] Configure LLM API keys and assistant `llm_config`

### Ops
- [ ] Set all env vars (§4)
- [ ] Install LibreOffice if supporting `.doc`/`.xls`/`.ppt`
- [ ] Configure AWS/GCS credentials for cloud URLs
- [ ] Run Alembic migration

---

## 16. Testing Plan

### Unit tests
1. **MIME detection** — presigned S3 URLs, query-param filenames, extension fallback
2. **Chunking** — empty text, long text, metadata propagation
3. **Embedding** — batch order preserved, empty list
4. **Loader registry** — each MIME type resolves to correct loader

### Integration tests
1. **Ingest PDF** → poll until `indexed` → `chunk_count > 0`
2. **Re-ingest same reference_id** → old chunks replaced
3. **rag_search** — query returns chunks from correct workspace only
4. **Cross-workspace isolation** — workspace A docs not visible in workspace B search
5. **Chat E2E** — ingest doc → ask question → answer references doc content

### Manual smoke test script

```
1. POST /documents/ingest (PDF in S3 or HTTPS)
2. GET /documents/ingestion-status/{id} every 2s until indexed
3. POST /chat/conversations/messages with workspace_ids
4. Verify response content_blocks mention document content
5. DELETE /documents/{id}
6. Confirm rag_search returns no results for deleted doc
```

---

## 17. Troubleshooting

| Symptom | Likely cause | Fix |
|---------|--------------|-----|
| `No loader for MIME type` | Unsupported file type or bad MIME detection | Check `_detect_mime_type`; verify extension in URL |
| `status: failed` + embedding error | Missing/invalid `OPENAI_API_KEY` | Set key; check provider env |
| `chunk_count: 0` but `indexed` | Empty document / no extractable text | Verify source file has text (not scanned image-only PDF) |
| RAG returns no results | Wrong `workspace_ids` in chat request | Match ingest `workspace_id` |
| RAG returns no results | Similarity threshold too high | Lower `similarity_threshold` to 0.2 |
| RAG returns no results | Embeddings missing on chunks | Check `embedding` column not NULL |
| `workspace_ids missing` in tool output | Chat layer not passing context | Fix `ToolContext` in executor |
| S3 403 on HTTPS URL | Presigned PutObject URL | boto3 fallback in `fetch.py` handles `x-id=PutObject` |
| Postgres error on chunk insert | Null bytes in text | `save_chunks` strips `\x00` — ensure port includes this |
| `.doc` load fails | LibreOffice not installed | Install LibreOffice on server |

---

## Appendix A — File tree to create in new project

```
your_project/
├── models/
│   └── document_model.py
├── schemas/
│   └── document_schema.py
├── domains/
│   └── documents/
│       ├── documents_service.py
│       └── documents_routes.py
├── pipelines/
│   └── ingestion/
│       ├── indexing.py
│       ├── exceptions.py
│       ├── loaders/
│       │   ├── __init__.py          # register_all_loaders()
│       │   ├── registry.py
│       │   ├── base_loader.py
│       │   ├── fetch.py
│       │   ├── pdf_loader.py
│       │   ├── docx_loader.py
│       │   ├── doc_loader.py
│       │   ├── xlsx_loader.py
│       │   ├── xls_loader.py
│       │   ├── pptx_loader.py
│       │   ├── ppt_loader.py
│       │   ├── csv_loader.py
│       │   ├── txt_loader.py
│       │   ├── html_loader.py
│       │   ├── json_loader.py
│       │   └── libreoffice_utils.py
│       └── services/
│           ├── chunking_service.py
│           └── embedding_service.py
├── assistants/
│   └── tools/
│       ├── base_tool.py
│       ├── tool_registry.py
│       └── implementations/
│           └── rag_search.py
├── services/
│   └── chat_service.py              # or executor-only if simpler
└── alembic/versions/
    └── xxx_add_knowledge_schema.py
```

---

## Appendix B — ai-platform source reference map

| Concept | Primary file |
|---------|--------------|
| Documents table | `engine/shared/models/document_model.py` |
| Migration | `engine/alembic/versions/be362d8427dc_add_knowledge_schema_and_tables.py` |
| Ingest API | `engine/domains/workspaces/documents/documents_routes.py` |
| Document service | `engine/domains/workspaces/documents/documents_service.py` |
| Indexing task | `engine/pipelines/ingestion/indexing.py` |
| Loaders | `engine/pipelines/ingestion/loaders/` |
| Chunking | `engine/pipelines/ingestion/services/chunking_service.py` |
| Embeddings | `engine/pipelines/ingestion/services/embedding_service.py` |
| RAG tool | `engine/domains/assistants/tools/implementations/rag_search.py` |
| Chat stream | `engine/routes/v1/chat_route.py` |
| Conversations chat | `engine/domains/conversations/conversation_routes.py` |
| Assistant execution | `engine/domains/assistants/runtime/executor.py` |
| Settings | `engine/shared/config/settings.py` |

---

*Generated from ai-platform codebase. Last aligned: June 2026.*

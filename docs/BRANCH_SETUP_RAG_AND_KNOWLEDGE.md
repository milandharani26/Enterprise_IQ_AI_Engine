# Branch setup: RAG + Knowledge Ingestion

**Branch:** `milan/added-rag-tool-and-knowledge-ingestion`

This guide is for developers who check out this branch and need to run document upload, indexing, and RAG chat locally.

---

## What this branch adds

### Backend
- **Knowledge schema** (`knowledge.documents`, `knowledge.document_chunks`) with **pgvector** embeddings (1536-dim)
- **Document ingestion pipeline** — loaders (PDF, DOCX, XLSX, CSV, TXT, HTML, JSON, PPT/PPTX, legacy Office), chunking, OpenAI embeddings
- **Documents API** — `POST /api/v1/documents/upload`, list, delete, search, ingestion status
- **RAG tool** — `rag_search` searches `knowledge.document_chunks` via hybrid vector + full-text search
- **Assistant runtime** — LangChain agent with `rag_search` + `emit_ui_blocks`, wired into chat via `AssistantExecutor`
- **Celery support** (optional) — background indexing via Redis (`make dev-worker`)
- **Auth fix** — API reads `access_token` cookie (not only `Authorization` header) for document routes

### Frontend (cpanel)
- **Documents page** (`/documents`) — upload, list, delete, status polling
- **Chat page** (`/chat`) — document Q&A with assistant picker, RAG-enabled assistants, suggested prompts
- **Sidebar** — Documents nav item
- **Store hydration fix** — organization cookie loaded client-side to avoid React hydration errors

### Infrastructure
- **Postgres + pgvector** Docker image (`infra/docker/Dockerfile.postgres`)
- **Redis** service in `docker-compose.yml` (for Celery)
- **Single `.env`** at repo root (removed `engine/.env` override)

---

## Prerequisites

| Requirement | Notes |
|-------------|--------|
| Python 3.11+ | Project uses Poetry |
| Node.js 18+ | For cpanel (Next.js) |
| PostgreSQL 15+ with **pgvector** | Local or Docker |
| OpenAI API key | Chat + embeddings |
| Redis (optional) | Only if `USE_CELERY_FOR_INDEXING=true` |
| LibreOffice (optional) | Only for legacy `.doc`, `.xls`, `.ppt` files |

---

## 1. Clone and install dependencies

```bash
git checkout milan/added-rag-tool-and-knowledge-ingestion

# Python
poetry install

# Frontend
cd cpanel && npm install && cd ..
```

---

## 2. Environment variables (single `.env` at repo root)

Create or update **`.env`** in the project root. There is **no** `engine/.env` — all config loads from here.

```env
# App
ENV=local
CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000,http://localhost:8000

# Database — must match YOUR Postgres instance
DATABASE_URL=postgresql+asyncpg://postgres:YOUR_PASSWORD@localhost:5432/enterprise_engine

# Auth
JWT_SECRET=dev-secret-do-not-use-in-production
SERVICE_TOKEN_SECRET_KEY=your-service-token-secret

# OpenAI (required for chat + embeddings)
OPENAI_API_KEY=sk-your-key-here

# LLM defaults for assistants
DEFAULT_LLM_PROVIDER=openai
DEFAULT_LLM_MODEL=gpt-4.1
DEFAULT_LLM_MAX_TOKENS=2048
DEFAULT_LLM_TEMPERATURE=0.1

# Embeddings (defaults are fine)
EMBEDDING_PROVIDER=openai
EMBEDDING_MODEL=text-embedding-3-small

# Optional: Celery background indexing
# USE_CELERY_FOR_INDEXING=false
# CELERY_BROKER_URL=redis://localhost:6379/0
# CELERY_RESULT_BACKEND=redis://localhost:6379/1
```

### Important env notes

- **`OPENAI_API_KEY`** must be set or uploads will index but embeddings fail (document status = `failed`).
- **`DEFAULT_LLM_MAX_TOKENS`** should be **≥ 2048** for RAG chat. Values like `512` cause empty answers after `rag_search` runs.
- **`DATABASE_URL`** must point to the same database you use in DBeaver / pgAdmin.

---

## 3. Database setup

### Option A — Local Postgres (recommended if you already use `enterprise_engine` on port 5432)

1. Ensure database exists:
   ```bash
   createdb enterprise_engine   # if needed
   ```

2. Enable pgvector:
   ```sql
   CREATE EXTENSION IF NOT EXISTS vector;
   ```

3. Run migrations:
   ```bash
   make migrate
   ```

4. In DBeaver, refresh and check:
   - **`public`** — `users`, `organizations`, `assistant`, `conversations`, …
   - **`knowledge`** — `documents`, `document_chunks`

### Option B — Docker Postgres (pgvector pre-installed)

```bash
make db-pgvector    # recreates DB volume + runs migrations (wipes data)
# OR
make up && sleep 6 && make migrate
```

Docker DB defaults:
- Host: `localhost`
- Port: **5434** (mapped from container 5432)
- User / password: `postgres` / `postgres`
- Database: `enterprise_engine`

If using Docker DB, set in `.env`:
```env
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5434/enterprise_engine
```

---

## 4. Run the application

```bash
make dev
```

This starts:
- **API** — http://localhost:8000
- **cpanel** — http://localhost:3000

### Optional: Celery worker (background indexing)

Only needed if `USE_CELERY_FOR_INDEXING=true` in `.env`:

```bash
make up          # starts Redis + Postgres
make dev-worker  # separate terminal
```

By default, indexing uses **FastAPI BackgroundTasks** (no Celery required).

---

## 5. First-time app setup (after fresh DB / migrations)

1. **Login** — http://localhost:3000 (seed admin from migrations; check `60cba1426bc3_seed_admin_user.py` for credentials if needed).

2. **Select organization** — Settings → General → pick or create an organization.  
   Document upload and RAG are scoped by `organization_id`.

3. **Create or enable an assistant with `rag_search`**
   - Assistants page → create assistant (defaults include `rag_search`), **or**
   - Edit existing assistant → add tool `rag_search`

4. **Upload a document** — Documents page → upload PDF/DOCX/etc.  
   Wait until status = **Indexed** (polls every 3s while processing).

5. **Chat** — Chat page → select RAG-enabled assistant → ask about your document.

---

## 6. Supported upload file types

| Extensions | Formats |
|------------|---------|
| `.pdf` | PDF |
| `.docx`, `.doc` | Word |
| `.xlsx`, `.xls` | Excel |
| `.pptx`, `.ppt` | PowerPoint |
| `.csv`, `.txt`, `.md` | CSV, plain text, Markdown |
| `.html`, `.json` | HTML, JSON |

Max upload size: **50 MB** (configurable via `MAX_DOCUMENT_SIZE_MB`).

---

## 7. Key API endpoints

| Method | Path | Purpose |
|--------|------|---------|
| `POST` | `/api/v1/documents/upload` | Upload file (returns 202, indexes in background) |
| `GET` | `/api/v1/documents?organization_id=...` | List documents |
| `GET` | `/api/v1/documents/ingestion-status/{id}` | Poll indexing status |
| `POST` | `/api/v1/documents/search` | Debug semantic search (no LLM) |
| `POST` | `/api/v1/conversations/chat` | Chat with RAG assistant |
| `GET` | `/api/v1/assistants` | List assistants |

Swagger: http://localhost:8000/docs

---

## 8. How RAG chat works (short)

```
User message (chat UI)
  → POST /conversations/chat (organization_id + agent_id)
  → ConversationService → AssistantExecutor
  → LangChain agent calls rag_search
  → Embed query → search knowledge.document_chunks
  → LLM answers from retrieved chunks
```

The assistant must have **`rag_search`** in its tools list. Chat passes **`organization_id`** from the active org cookie.

---

## 9. Troubleshooting

| Symptom | Likely cause | Fix |
|---------|----------------|-----|
| DBeaver shows empty DB | Wrong host/port/db name | Match `DATABASE_URL` in `.env` |
| No `knowledge` schema | Migrations not run | `make migrate` |
| Upload → `failed`, OpenAI 401 | Missing `OPENAI_API_KEY` | Set key in root `.env`, restart `make dev` |
| Chat → "No response generated" | `DEFAULT_LLM_MAX_TOKENS` too low | Set to `2048`+, restart API |
| Documents API 401 | Cookie auth | Log in again; ensure org selected |
| Hydration error on `/documents` | Old frontend cache | Hard refresh; ensure latest cpanel code |
| `pgvector not installed` warning | Plain Postgres image | Use `make db-pgvector` or `CREATE EXTENSION vector` |
| Legacy `.doc`/`.xls` fails | No LibreOffice | Install LibreOffice or use modern formats |
| Celery tasks not running | Worker not started | `make dev-worker` + Redis up |

---

## 10. New / important files (reference)

```
engine/
  alembic/versions/knowledge_rev_add_knowledge_schema.py
  modules/documents/          # upload API + service
  modules/assistant/
    runtime/                  # executor, rag_context, simple_reactive
    tools/implementations/    # rag_search, emit_ui_blocks
  pipelines/ingestion/        # loaders, chunking, embedding, indexing
  pipelines/tasks/celery_app.py
  shared/models/document_model.py
  shared/schemas/document_schema.py

cpanel/src/
  app/(dashboard)/documents/
  app/(dashboard)/chat/       # RAG chat UI
  hooks/api/useDocuments.ts
  components/StoreHydrator.tsx

infra/docker/
  Dockerfile.postgres         # Postgres 15 + pgvector
  docker-compose.yml          # db + redis
```

---

## 11. Makefile commands (quick reference)

```bash
make dev              # API + Next.js
make migrate          # Alembic upgrade head
make db-pgvector      # Recreate Docker Postgres with pgvector + migrate
make up / make down   # Docker compose
make dev-worker       # Celery worker (optional)
make dev-cpanel-install
```

---

## 12. Checklist for a new developer

- [ ] `git checkout milan/added-rag-tool-and-knowledge-ingestion`
- [ ] `poetry install`
- [ ] `cd cpanel && npm install`
- [ ] Copy/create root `.env` with `DATABASE_URL`, `OPENAI_API_KEY`, `DEFAULT_LLM_MAX_TOKENS=2048`
- [ ] Postgres running with **pgvector** extension
- [ ] `make migrate`
- [ ] `make dev`
- [ ] Login → select organization → create/enable assistant with `rag_search`
- [ ] Upload document on `/documents` → wait for **Indexed**
- [ ] Test question on `/chat`

---

For a deeper implementation walkthrough, see also:  
`docs/DOCUMENT_INGESTION_AND_RAG_IMPLEMENTATION_GUIDE.md`

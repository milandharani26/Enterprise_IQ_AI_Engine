# Document Upload Processing - Troubleshooting & Setup Guide

**Status**: Fixed with improved error handling and reliable task scheduling

---

## ✅ What Was Fixed

Your document uploads were getting stuck in "processing" because:

1. **FastAPI BackgroundTasks were unreliable** — The task depends on request lifecycle and may not execute
2. **No timeout on document loading** — S3/HTTP fetches could hang indefinitely
3. **Missing error context** — Failures weren't tracked in the database
4. **No fallback mechanism** — When BackgroundTasks failed, no indication was provided

### Changes Made

✅ **Improved `schedule_index_document()` function**

- Added comprehensive logging at each stage
- Implemented fallback from Celery → BackgroundTasks
- Added error recovery for BackgroundTasks failures

✅ **Enhanced `run_index_document_task()` function**

- Added timeout protection for document loading (default: 300s)
- Improved error messages with operation context
- Ensured database status always updates, even on failure
- Added step-by-step progress tracking with emojis

✅ **New Configuration**

- `DOCUMENT_LOAD_TIMEOUT_SECONDS=300` (configurable)
- Better error tracking in `document.processing_error` field

---

## 📋 Quick Setup

### Option 1: Use FastAPI BackgroundTasks (Simple, Phase 1)

**Default configuration** — Works for development/small deployments:

```bash
# .env
ENABLE_ASYNC_INDEXING=true
DOCUMENT_LOAD_TIMEOUT_SECONDS=300
EMBEDDING_TIMEOUT_SECONDS=120
```

**Verify it's working:**

```bash
# Upload a document
curl -X POST http://localhost:8000/api/v1/documents/upload \
  -F "file=@sample.pdf" \
  -F "organization_id=<org-uuid>" \
  -F "title=My Document"

# Response: 202 Accepted with status=processing, task_id=null

# Check status in database
SELECT id, status, processing_error, processing_completed_at
FROM knowledge.documents
WHERE created_at > now() - interval '1 minute'
ORDER BY created_at DESC;

# After ~10-30s: status should change to 'indexed'
```

---

### Option 2: Use Celery + Redis (Production, Phase 2)

**More reliable** — Recommended for production:

```bash
# 1. Install Redis (or use Docker)
docker run -d -p 6379:6379 redis:latest

# 2. Set environment variables
export USE_CELERY_FOR_INDEXING=true
export CELERY_BROKER_URL=redis://localhost:6379/0
export CELERY_RESULT_BACKEND=redis://localhost:6379/1
export CELERY_TASK_TIME_LIMIT=600
export CELERY_TASK_SOFT_TIME_LIMIT=540

# 3. Start Celery worker (in a separate terminal)
celery -A engine.pipelines.tasks.celery_app worker \
  --loglevel=info \
  --concurrency=4 \
  --max-tasks-per-child=100
```

**Verify it's working:**

```bash
# Upload a document
curl -X POST http://localhost:8000/api/v1/documents/upload \
  -F "file=@sample.pdf" \
  -F "organization_id=<org-uuid>" \
  -F "title=My Document"

# Response: 202 Accepted with status=processing, task_id=<celery-task-id>

# Monitor task in Redis CLI
redis-cli
> KEYS *
> GET celery-task-results-<task-id>

# Or check database
SELECT id, status, processing_error, processing_completed_at
FROM knowledge.documents
WHERE created_at > now() - interval '1 minute'
ORDER BY created_at DESC;

# Status progression: processing → indexed (1-5 minutes depending on file size)
```

---

## 🔍 Diagnosing Issues

### 1. Document Stays in "processing" Forever

**Check database:**

```sql
SELECT id, title, status, processing_error, processing_started_at, processing_completed_at
FROM knowledge.documents
WHERE status = 'processing'
AND processing_started_at < now() - interval '5 minutes';
```

**If `processing_error` is NULL:**

- BackgroundTasks may not be executing (FastAPI mode)
- Check application logs for `[INDEXING]` markers

**If `processing_error` contains a message:**

- Error occurred during indexing
- See error details to identify root cause

### 2. Check Application Logs

```bash
# View live logs (Linux/Mac)
tail -f shared/logs/engine/app.json.log | grep -i indexing

# Search for specific document
grep "doc_id=<your-doc-id>" shared/logs/engine/app.json.log
```

**Look for these log messages:**

```
[INDEXING] ▶️  START: doc_id=...
[INDEXING] ⏳ Status set to 'processing'
[INDEXING] 📥 Loading from: ...
[INDEXING] ✓ Loaded X chars
[INDEXING] ✓ Created X chunks
[INDEXING] 🧠 Embedding X chunks...
[INDEXING] ✓ Embeddings completed: X vectors
[INDEXING] 💾 Saved X chunks to pgvector
[INDEXING] ✅ COMPLETE: doc_id=..., X chunks indexed, status=indexed
```

### 3. Common Failure Modes

| Status                 | Error Message                | Solution                                                                         |
| ---------------------- | ---------------------------- | -------------------------------------------------------------------------------- |
| `failed`               | "Document loading timed out" | Increase `DOCUMENT_LOAD_TIMEOUT_SECONDS` (300→600) or check S3/HTTP connectivity |
| `failed`               | "Embedding failed"           | Check `OPENAI_API_KEY` or `GROQ_API_KEY` is set; verify API balance              |
| `failed`               | "No source_url"              | Ensure document has valid `source_url` field                                     |
| `processing` (stalled) | No error message             | Enable Celery or check if BackgroundTasks is running                             |
| `processing` (stalled) | Check app logs               | Task may have crashed; see logs for `[INDEXING] ❌ FAILED`                       |

---

## 🛠️ Configuration Reference

### Document Ingestion Settings

```env
# ===== BASIC =====
ENABLE_ASYNC_INDEXING=true                        # Enable background processing
DOCUMENT_LOAD_TIMEOUT_SECONDS=300                 # Timeout for S3/HTTP fetch (seconds)

# ===== CHUNKING =====
CHUNK_SIZE_TOKENS=512                             # Tokens per chunk
CHUNK_OVERLAP_TOKENS=50                           # Overlap between chunks
MAX_CHUNK_SIZE_TOKENS=2048                        # Hard limit per chunk

# ===== EMBEDDING =====
EMBEDDING_PROVIDER=openai                         # or 'groq'
EMBEDDING_MODEL=text-embedding-3-small            # or 'text-embedding-3-large'
OPENAI_API_KEY=sk-...                             # Required if EMBEDDING_PROVIDER=openai
GROQ_API_KEY=gsk-...                              # Required if EMBEDDING_PROVIDER=groq
EMBEDDING_TIMEOUT_SECONDS=120                     # Timeout for embedding API call
EMBEDDING_MAX_RETRIES=3                           # Retries on failure

# ===== CELERY (Optional, Phase 2) =====
USE_CELERY_FOR_INDEXING=false                     # Set to true for production
CELERY_BROKER_URL=redis://localhost:6379/0        # Task queue broker
CELERY_RESULT_BACKEND=redis://localhost:6379/1    # Result storage
CELERY_TASK_TIME_LIMIT=600                        # Hard limit for task
CELERY_TASK_SOFT_TIME_LIMIT=540                   # Soft limit (raises SoftTimeLimitExceeded)
```

---

## 🧪 Test Scenarios

### Scenario 1: Small PDF (< 100 chunks)

```bash
# Expected time: 5-15 seconds
# Status: draft → processing → indexed
# Check: 10-50 chunks in knowledge.document_chunks

SELECT COUNT(*) as chunk_count FROM knowledge.document_chunks
WHERE document_id = '<doc-id>';
```

### Scenario 2: Large Document (> 1000 chunks)

```bash
# Expected time: 30-120 seconds
# May be limited by embedding API rate limits (3-5 requests/min typical)
# If stuck: check EMBEDDING_TIMEOUT_SECONDS and EMBEDDING_MAX_RETRIES

SELECT
  d.id, d.title, d.status, d.chunk_count,
  COUNT(dc.id) as actual_chunks
FROM knowledge.documents d
LEFT JOIN knowledge.document_chunks dc ON d.id = dc.document_id
WHERE d.id = '<doc-id>'
GROUP BY d.id, d.title, d.status, d.chunk_count;
```

### Scenario 3: Embedding Failure Recovery

```bash
# If embedding fails, chunks are still saved (without vectors)
# This allows partial RAG search using full-text match only

SELECT
  COUNT(CASE WHEN embedding IS NOT NULL THEN 1 END) as with_embeddings,
  COUNT(CASE WHEN embedding IS NULL THEN 1 END) as without_embeddings,
  COUNT(*) as total
FROM knowledge.document_chunks
WHERE document_id = '<doc-id>';
```

---

## 🚀 Performance Optimization

### To Speed Up Indexing

```env
# 1. Increase embedding batch size (default: 100)
EMBEDDING_BATCH_SIZE=200

# 2. Increase chunk sizes (fewer embeddings)
CHUNK_SIZE_TOKENS=1024                           # Up from 512
CHUNK_OVERLAP_TOKENS=100                         # Proportional increase

# 3. Use Celery with multiple workers
celery -A engine.pipelines.tasks.celery_app worker \
  --concurrency=8 \
  --prefetch-multiplier=2

# 4. Use embedding model cache (if available)
# Some embedding providers cache frequent queries
```

### To Reduce Memory Usage

```env
# 1. Reduce batch size
EMBEDDING_BATCH_SIZE=50

# 2. Reduce chunk sizes
CHUNK_SIZE_TOKENS=256
CHUNK_OVERLAP_TOKENS=25

# 3. Enable Celery with fewer workers
celery -A engine.pipelines.tasks.celery_app worker \
  --concurrency=2
```

---

## 📊 Monitoring & Debugging

### Query for Indexing Statistics

```sql
-- Overall stats
SELECT
  COUNT(*) as total,
  COUNT(CASE WHEN status = 'indexed' THEN 1 END) as indexed,
  COUNT(CASE WHEN status = 'processing' THEN 1 END) as processing,
  COUNT(CASE WHEN status = 'failed' THEN 1 END) as failed,
  AVG(EXTRACT(EPOCH FROM (processing_completed_at - processing_started_at))) as avg_indexing_time_sec
FROM knowledge.documents
WHERE created_at > now() - interval '1 day'
AND workspace_id = '<workspace-id>';

-- Failed documents
SELECT id, title, status, processing_error, processing_started_at
FROM knowledge.documents
WHERE status = 'failed'
AND created_at > now() - interval '1 day'
ORDER BY processing_started_at DESC;

-- Slow documents
SELECT id, title, status,
  EXTRACT(EPOCH FROM (processing_completed_at - processing_started_at)) as duration_sec
FROM knowledge.documents
WHERE status = 'indexed'
AND processing_completed_at > now() - interval '1 day'
ORDER BY duration_sec DESC
LIMIT 10;
```

---

## ✅ Health Check Endpoint

_(Recommended future enhancement)_

```python
@app.get("/api/v1/health/documents")
async def document_health():
    """Check document indexing pipeline health."""
    return {
        "status": "ok",
        "celery_enabled": settings.use_celery_for_indexing,
        "async_enabled": settings.enable_async_indexing,
        "embedding_provider": settings.embedding_provider,
        "recent_documents": {
            "total": 100,
            "indexed": 95,
            "processing": 2,
            "failed": 3,
        }
    }
```

---

## 🆘 Still Having Issues?

1. **Check logs**: `grep [INDEXING] shared/logs/engine/app.json.log`
2. **Check database**: Query `knowledge.documents` for error details
3. **Enable debug logging**: Set `LOG_LEVEL=DEBUG`
4. **Test embedding service**: Call embedding API directly with curl
5. **Test document loader**: Download from S3/HTTP manually
6. **Enable Celery**: Switch to production mode (Phase 2)

For detailed logs, add to settings:

```python
logging.getLogger("engine.pipelines").setLevel(logging.DEBUG)
logging.getLogger("engine.modules.documents").setLevel(logging.DEBUG)
```

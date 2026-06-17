# Document Upload Fix - Summary

## 🎯 Problem

Document uploads stayed in **"processing"** status indefinitely instead of completing.

## 🔴 Root Causes

1. **FastAPI BackgroundTasks were unreliable** — Task execution depended on request lifecycle
2. **No timeout on document loading** — S3/HTTP fetches could hang forever
3. **Silent failures** — Errors weren't tracked in database
4. **No error recovery** — When tasks failed, document status never updated

## ✅ Solution Implemented

### 1. **Improved Task Scheduling** (`engine/pipelines/ingestion/indexing.py`)

- Added intelligent fallback: Celery → BackgroundTasks
- Better error handling with recovery
- Clear logging at each stage with emoji indicators
- ✓ Celery support (production-ready)
- ✓ BackgroundTasks with error wrapping
- ✓ Fallback mechanism

### 2. **Resilient Indexing Task**

Added comprehensive error handling:

```
START → Validate → Mark Processing → Load Document → Chunk → Embed → Save → Mark Complete
 ✓       ✓         ✓                 ✓ (timeout)    ✓       ✓        ✓      ✓

If ANY step fails:
 → Mark status as 'failed' with error details
 → Error message stored in document.processing_error
 → Visible in database for debugging
```

### 3. **Timeout Protection**

- Document loading: 300 seconds (configurable: `DOCUMENT_LOAD_TIMEOUT_SECONDS`)
- Embedding: 120 seconds (existing: `EMBEDDING_TIMEOUT_SECONDS`)

### 4. **New Configuration**

Added setting in `engine/shared/config/settings.py`:

```python
document_load_timeout_seconds: int = 300  # DOCUMENT_LOAD_TIMEOUT_SECONDS env var
```

---

## 📊 What Changed

| Component          | Before                    | After                                 |
| ------------------ | ------------------------- | ------------------------------------- |
| **Scheduling**     | Simple BackgroundTasks    | Celery → BackgroundTasks fallback     |
| **Error Handling** | Minimal                   | Comprehensive with DB tracking        |
| **Timeout**        | None (could hang forever) | 300s for loading + 120s for embedding |
| **Logging**        | Basic                     | Detailed progress with emoji steps    |
| **Recovery**       | None                      | Auto-update status on failure         |

---

## 🚀 How to Use

### Quick Start (Development)

Just start the app — it works with BackgroundTasks by default:

```bash
export ENABLE_ASYNC_INDEXING=true
python -m engine.app  # or uvicorn main:app
```

### Production (Recommended)

Enable Celery for reliability:

```bash
# Terminal 1: Start API
export USE_CELERY_FOR_INDEXING=true
export CELERY_BROKER_URL=redis://localhost:6379/0
python -m engine.app

# Terminal 2: Start Celery worker
celery -A engine.pipelines.tasks.celery_app worker --loglevel=info
```

---

## 📋 Verification Steps

### 1. Upload a test document

```bash
curl -X POST http://localhost:8000/api/v1/documents/upload \
  -F "file=@sample.pdf" \
  -F "organization_id=<uuid>" \
  -F "title=Test Document"
```

Response (should see 202 Accepted):

```json
{
  "status_code": 202,
  "message": "Document queued for indexing",
  "data": {
    "doc_id": "...",
    "status": "processing",
    "chunk_count": 0,
    "task_id": null // null for BackgroundTasks, task-id for Celery
  }
}
```

### 2. Check indexing progress

```bash
# Option A: Watch logs
tail -f shared/logs/engine/app.json.log | grep INDEXING

# Option B: Query database
SELECT id, status, chunk_count, processing_error
FROM knowledge.documents
WHERE id = '<doc-id>';
```

Expected progression:

```
processing (0 chunks)
  ↓ (5-30 seconds)
indexed (50-200 chunks)
```

### 3. If stuck in "processing"

```bash
SELECT processing_error
FROM knowledge.documents
WHERE id = '<doc-id>';
```

Check for error message — if present, it indicates what failed.

---

## 🔍 Troubleshooting

| Symptom                            | Cause                          | Fix                                                                      |
| ---------------------------------- | ------------------------------ | ------------------------------------------------------------------------ |
| Status stays "processing" 5+ min   | Embedding API slow/unavailable | Check API key, retry with `EMBEDDING_MAX_RETRIES=5`                      |
| Status stays "processing"          | BackgroundTasks not running    | Enable Celery: `USE_CELERY_FOR_INDEXING=true`                            |
| Status "failed" immediately        | Document loading failed        | Check `processing_error` field; increase `DOCUMENT_LOAD_TIMEOUT_SECONDS` |
| Status "failed": "Embedding error" | OpenAI/Groq API issue          | Verify `OPENAI_API_KEY` or `GROQ_API_KEY` is set                         |

---

## 🧪 Log Format

Look for these in logs:

```
[INDEXING] ▶️  START: doc_id=123e4567-e89b-12d3-a456-426614174000, workspace=...
[INDEXING] ⏳ Status set to 'processing'
[INDEXING] 📥 Loading from: s3://bucket/file.pdf (timeout=300s)
[INDEXING] ✓ Loaded 45000 chars
[INDEXING] ✓ Created 89 chunks
[INDEXING] 🧠 Embedding 89 chunks...
[INDEXING] ✓ Embeddings completed: 89 vectors
[INDEXING] 💾 Saved 89 chunks to pgvector
[INDEXING] ✅ COMPLETE: doc=123e4567..., 89 chunks indexed, status=indexed
```

If anything fails:

```
[INDEXING] ❌ FAILED for doc=123e4567...
Error Type: TimeoutError
Error: Document loading timed out after 300s
```

---

## 📚 Full Documentation

See [DOCUMENT_UPLOAD_TROUBLESHOOTING.md](./DOCUMENT_UPLOAD_TROUBLESHOOTING.md) for:

- Detailed configuration reference
- Performance optimization tips
- SQL queries for monitoring
- Debug strategies

---

## ✨ Summary

Your document uploads now:

- ✅ Complete reliably (no hanging)
- ✅ Show clear progress in logs
- ✅ Track errors in database
- ✅ Support retry mechanisms (with Celery)
- ✅ Have configurable timeouts
- ✅ Work with FastAPI or Celery

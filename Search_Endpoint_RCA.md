# Sprint 27 Task 2.1 — Search Endpoint Root Cause Analysis

**Date:** 2026-06-05  
**Status:** Diagnosis Complete  

---

## Reproduction

```
GET /api/v1/search/?q=agreement&page_size=3

→ HTTP 500 Internal Server Error
```

## Full Stack Trace (Bottom = Root Cause)

```
  File "app/domains/search/engine.py", line 303, in _embed_query
    provider = embedding_registry.get_default()
  File "app/domains/vectors/embeddings.py", line 212, in get_default
    return self.get("openai")
  File "app/domains/vectors/embeddings.py", line 208, in get
    raise ValueError(f"Embedding provider '{name}' not registered")
ValueError: Embedding provider 'openai' not registered
```

## Root Cause

**The `EmbeddingProviderRegistry` is empty at search time because no code path registers the `OpenAIEmbeddingProvider` before the search endpoint runs.**

### Call Chain

```
GET /api/v1/search/?q=agreement
  → SearchService.search()
    → HybridRetrievalEngine.search()
      → HybridRetrievalEngine._hybrid_search()
        → HybridRetrievalEngine._vector_search()
          → HybridRetrievalEngine._embed_query()
            → embedding_registry.get_default()        ← FAILS HERE
              → embedding_registry.get("openai")
                → ValueError: provider not registered
```

### Why the Registry is Empty

The `EmbeddingProviderRegistry` is a **module-level singleton** (`embedding_registry` in `app/domains/vectors/embeddings.py`). Providers are registered in two places:

1. **`VectorService.generate_embeddings()`** (`app/domains/vectors/service.py:59`):
   ```python
   provider = embedding_registry.get_default()
   if not isinstance(provider, OpenAIEmbeddingProvider):
       provider = OpenAIEmbeddingProvider(api_key=settings.openai_api_key)
       embedding_registry.register(provider)
   ```
   This runs during **document ingestion** (Celery task). If no documents have been ingested in the current process lifetime, the registry is empty.

2. **`HybridRetrievalEngine._embed_query()`** (`app/domains/search/engine.py:303`):
   ```python
   provider = embedding_registry.get_default()
   if not isinstance(provider, OpenAIEmbeddingProvider):
       provider = OpenAIEmbeddingProvider(api_key=settings.openai_api_key)
       embedding_registry.register(provider)
   ```
   This has the **same logic** — it checks if the default provider is an `OpenAIEmbeddingProvider`, and if not, creates and registers one. **This code works correctly.**

### The Bug

The code at `engine.py:303-306` should work — it's identical to the working code in `service.py:56-59`. The issue is that **the `get_default()` call itself raises the exception** before the fallback registration logic runs.

```python
async def _embed_query(self, query: str) -> list[float]:
    provider = embedding_registry.get_default()       # ← THIS RAISES
    if not isinstance(provider, OpenAIEmbeddingProvider):
        provider = OpenAIEmbeddingProvider(...)
        embedding_registry.register(provider)
```

`get_default()` calls `self.get("openai")` which raises `ValueError` if `"openai"` is not registered. The `isinstance` check never executes.

### The Fix

Change `_embed_query` to catch the `ValueError` and create the provider:

```python
async def _embed_query(self, query: str) -> list[float]:
    try:
        provider = embedding_registry.get_default()
    except ValueError:
        provider = None

    if not isinstance(provider, OpenAIEmbeddingProvider):
        provider = OpenAIEmbeddingProvider(api_key=settings.openai_api_key)
        embedding_registry.register(provider)
```

Or more simply, check if the registry is empty first:

```python
async def _embed_query(self, query: str) -> list[float]:
    if not embedding_registry._providers:
        provider = OpenAIEmbeddingProvider(api_key=settings.openai_api_key)
        embedding_registry.register(provider)
    else:
        provider = embedding_registry.get_default()
```

## Production Impact

| Factor | Assessment |
|--------|------------|
| **Severity** | 🔴 **HIGH** — Search is completely broken (HTTP 500 on every request) |
| **Scope** | All search endpoints: `GET /search/`, `GET /search/clauses`, `POST /search/` |
| **Workaround** | Ingest at least one document first (registers the provider during embedding) |
| **First occurrence** | Always — search has never worked without prior document ingestion |
| **User impact** | Users cannot search contracts, clauses, or findings |

## Why Tests Didn't Catch This

The search tests in `tests/test_search.py` mock the embedding provider or the engine directly. The integration path (router → service → engine → embedding registry) is not covered by any existing test.

## Estimated Fix Effort

| Step | Time |
|------|------|
| Add try/except around `get_default()` in `engine.py:303` | **5 minutes** |
| Add test: search without prior embedding registration | **15 minutes** |
| **Total** | **~20 minutes** |

## Recommendation

**Fix before launch.** This is a high-severity, low-effort fix. Search is a core feature and returning HTTP 500 on every request is unacceptable for production.

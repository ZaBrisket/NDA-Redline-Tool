# Railway Deployment Guide

## Quick Start

1. **Connect GitHub Repository** to Railway
2. **Set Environment Variables** in Railway dashboard:
   ```
   OPENAI_API_KEY=sk-your-key
   ANTHROPIC_API_KEY=sk-ant-your-key
   ENABLE_SEMANTIC_CACHE=true
   ```
3. **Deploy** - Railway will use `nixpacks.toml` automatically

## Troubleshooting

### Issue: Application crashes with SQLite error

**Symptom:**
```
ImportError: libsqlite3.so.0: cannot open shared object file: No such file or directory
```

**Root Cause:**
The semantic cache uses `sentence-transformers` → `nltk` → `sqlite3`, which requires system SQLite libraries.

**Solutions:**

#### Solution 1: Fix nixpacks.toml (Recommended)
The project's `nixpacks.toml` already includes SQLite dependencies. If crashes persist:

1. **Trigger a fresh build:**
   - Go to Railway dashboard
   - Click "Deployments" → "Redeploy" → "Redeploy (Clear Cache)"

2. **Verify nixpacks.toml has:**
   ```toml
   [phases.setup]
   aptPkgs = ["sqlite3", "libsqlite3-dev", "libsqlite3-0"]
   ```

#### Solution 2: Disable Semantic Cache (Temporary)
If you need immediate deployment:

1. Set environment variable in Railway:
   ```
   ENABLE_SEMANTIC_CACHE=false
   ```

2. Redeploy

**Trade-off:** LLM API costs will be ~60% higher without caching.

## Health Check

After deployment, check health status:

```bash
curl https://your-app.up.railway.app/
```

**Expected response:**
```json
{
  "service": "NDA Automated Redlining",
  "version": "1.0.0",
  "status": "operational",
  "cache_enabled": true,
  "dependencies": {
    "sqlite3": {"available": true, "version": "3.x.x"},
    "numpy": {"available": true},
    "faiss": {"available": true},
    "sentence_transformers": {"available": true}
  },
  "warnings": []
}
```

**If cache is disabled:**
```json
{
  ...
  "cache_enabled": false,
  "warnings": ["Semantic cache disabled - LLM costs will be higher"]
}
```

## Logs

View startup logs in Railway dashboard to see dependency status:

```
✓ SQLite3 module available (version: 3.x.x)
✓ NumPy available (version: 1.x.x)
✓ FAISS available
✓ SentenceTransformers available
✓ OPENAI_API_KEY configured
✓ ANTHROPIC_API_KEY configured
Semantic cache: enabled (via env)
Startup complete - Ready to accept requests
```

## Performance Tuning

### Environment Variables

```bash
# LLM Settings
USE_PROMPT_CACHING=true
VALIDATION_RATE=0.15           # % of redlines to validate with Claude
CONFIDENCE_THRESHOLD=95        # Confidence threshold for GPT

# Caching
ENABLE_SEMANTIC_CACHE=true
REDIS_URL=                     # Optional: Add Redis for distributed cache

# Processing
MAX_PROCESSING_TIME=60         # Seconds
WORKER_CONCURRENCY=2           # Concurrent document processors

# Security
ENABLE_API_KEYS=false          # Set to true for production
API_KEY=your-secret-key
```

## Cost Optimization

### With Semantic Cache (Recommended)
- 60% reduction in LLM API costs
- Requires: SQLite3 system libraries
- Memory: ~200MB additional for embeddings

### Without Semantic Cache
- Higher LLM costs (no caching)
- Lower memory footprint
- Simpler deployment (no SQLite dependency)

## Common Errors

### Error: "Cache dependencies not available"
**Fix:** Enable semantic cache or set `ENABLE_SEMANTIC_CACHE=false`

### Error: "OPENAI_API_KEY not configured"
**Fix:** Add API keys to Railway environment variables

### Error: "Worker timeout"
**Fix:** Increase `MAX_PROCESSING_TIME` for large documents

## Support

- Check health endpoint: `GET /`
- View logs in Railway dashboard
- Review startup output for dependency checks
- Test upload: `POST /api/upload` with DOCX file

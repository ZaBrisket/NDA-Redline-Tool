# ✅ Deployment Ready Checklist

## Code Changes Completed

### 🔧 Updated to Use Environment Variables
- ✅ `llm_pipeline.py` now reads API keys from environment
- ✅ Enforcement level configurable via `ENFORCEMENT_LEVEL`
- ✅ All model names configurable (GPT_MODEL, SONNET_MODEL, OPUS_MODEL)
- ✅ Cache settings read from environment
- ✅ Thresholds and limits configurable

### 📁 New Files Created
- ✅ `backend/app/orchestrators/llm_pipeline.py` - 4-pass pipeline orchestrator
- ✅ `backend/app/api/v2_endpoints.py` - New v2 API endpoints
- ✅ `backend/app/core/strictness_controller.py` - Enforcement level management
- ✅ `backend/app/core/rule_engine_v2.py` - Enhanced rules engine
- ✅ `backend/app/models/schemas_v2.py` - Structured output schemas
- ✅ `backend/app/models/rules_v2.yaml` - 35+ deterministic patterns

### 📋 Documentation Added
- ✅ `ENVIRONMENT_VARIABLES_GUIDE.md` - Complete variable reference
- ✅ `DEPLOYMENT_ENV_SETUP.md` - Quick setup guide
- ✅ `IMPLEMENTATION_SUMMARY_V2.md` - Technical documentation
- ✅ `RUNBOOK_V2.md` - Testing and debugging guide

## 🚀 Railway Deployment Variables

### Minimum Required (MUST SET)
```bash
OPENAI_API_KEY=sk-proj-...
ANTHROPIC_API_KEY=sk-ant-api03-...
```

### Recommended Settings (SHOULD SET)
```bash
ENFORCEMENT_LEVEL=Balanced
ENABLE_CACHE=true
ENABLE_SEMANTIC_CACHE=true
VALIDATION_RATE=0.15
CONFIDENCE_THRESHOLD=95
USE_PROMPT_CACHING=true
MAX_CONCURRENT_DOCUMENTS=3
```

### Optional Performance Tuning
```bash
# Models (defaults work fine)
GPT_MODEL=gpt-4o
SONNET_MODEL=claude-sonnet-4-5-20250929
OPUS_MODEL=claude-opus-4-1-20250805

# Thresholds
SKIP_GPT_CONFIDENCE_THRESHOLD=98
OPUS_CONFIDENCE_THRESHOLD=85
CONSENSUS_THRESHOLD=90

# Pass Control
ENABLE_PASS_0=true
ENABLE_PASS_1=true
ENABLE_PASS_2=true
ENABLE_PASS_3=true
ENABLE_PASS_4=true

# Rate Limiting
RATE_LIMIT_ENABLED=true
RATE_LIMIT_REQUESTS_PER_MINUTE=60

# File Limits
MAX_FILE_SIZE_MB=10
MAX_BATCH_SIZE_MB=500
```

### Redis (If Using)
```bash
REDIS_URL=redis://default:password@host:port
USE_REDIS_QUEUE=true
```

## 🌐 Vercel Frontend Variables

### Required
```bash
NEXT_PUBLIC_API_URL=https://your-app.railway.app
```

### Optional
```bash
NEXT_PUBLIC_ENFORCEMENT_LEVEL=Balanced
NEXT_PUBLIC_MAX_FILE_SIZE_MB=10
```

## 📝 Deployment Steps

### 1. Railway Backend
```bash
# Set variables via dashboard or CLI
railway variables set OPENAI_API_KEY="sk-..."
railway variables set ANTHROPIC_API_KEY="sk-ant-..."
railway variables set ENFORCEMENT_LEVEL="Balanced"

# Deploy
railway up
```

### 2. Vercel Frontend
```bash
# Set backend URL
vercel env add NEXT_PUBLIC_API_URL production
# Enter: https://your-app.railway.app

# Deploy
vercel --prod
```

## 🧪 Testing Commands

### Test Environment
```bash
python validate_env.py
```

### Test Backend Health
```bash
curl https://your-app.railway.app/health/v2
```

### Test V2 Pipeline
```bash
curl -X POST https://your-app.railway.app/api/v2/test
```

### Test Enforcement Modes
```bash
curl https://your-app.railway.app/api/v2/modes
```

## 🎯 Quick Reference

### Enforcement Levels
| Level | Description | Severities |
|-------|-------------|------------|
| **Bloody** | Zero tolerance | All (critical, high, moderate, low, advisory) |
| **Balanced** | Standard | Critical, high, moderate |
| **Lenient** | Minimal | Critical only |

### API Endpoints
| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/v2/analyze` | POST | Analyze single document |
| `/api/v2/analyze/batch` | POST | Batch processing |
| `/api/v2/modes` | GET | Get enforcement modes |
| `/api/v2/statistics` | GET | Pipeline statistics |
| `/api/v2/health/v2` | GET | Health check |
| `/api/v2/test` | POST | Test pipeline |

## 🔍 Verification

### Check Variables Set
```bash
# Railway
railway variables

# Vercel
vercel env ls
```

### Monitor Logs
```bash
# Railway
railway logs

# Vercel
vercel logs
```

## ⚠️ Common Issues

| Issue | Solution |
|-------|----------|
| API keys not found | Set in platform dashboard, not .env |
| Frontend network error | Check NEXT_PUBLIC_API_URL |
| Too many/few redlines | Adjust ENFORCEMENT_LEVEL |
| Slow processing | Enable caching variables |
| Rate limits | Adjust RATE_LIMIT_REQUESTS_PER_MINUTE |

## 📊 Success Metrics

- [ ] Both API keys configured
- [ ] Health check returns "healthy"
- [ ] Test endpoint processes sample text
- [ ] Frontend connects to backend
- [ ] Document upload works
- [ ] Results display correctly

## 🎉 You're Ready!

Once all items above are checked:
1. Your NDA Reviewer is production-ready
2. 4-pass pipeline is active
3. Enforcement levels are working
4. Caching is optimized
5. Security is configured

---

**Next Steps:**
1. Add API keys to Railway
2. Set backend URL in Vercel
3. Deploy both services
4. Run test document
5. Monitor performance
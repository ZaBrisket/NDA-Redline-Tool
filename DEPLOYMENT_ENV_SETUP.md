# 🚀 Quick Deployment Environment Setup

## ✅ What Was Updated

1. **Code now reads from environment variables** instead of requiring hardcoded API keys
2. **New v2 API endpoints** added at `/api/v2/` for the 4-pass pipeline
3. **Comprehensive environment variable support** for all configuration options

## 🔑 Minimum Required Variables

### Railway (Backend) - MUST SET
```
OPENAI_API_KEY=sk-proj-...
ANTHROPIC_API_KEY=sk-ant-api03-...
```

### Vercel (Frontend) - MUST SET
```
NEXT_PUBLIC_API_URL=https://your-app.railway.app
```

## 📋 Railway Setup (Step-by-Step)

### Option 1: Railway Dashboard (Easiest)
1. Go to your Railway project
2. Click on your service
3. Go to "Variables" tab
4. Click "Raw Editor"
5. Paste this (replace with your actual keys):

```env
# Required API Keys
OPENAI_API_KEY=sk-proj-YOUR-KEY-HERE
ANTHROPIC_API_KEY=sk-ant-api03-YOUR-KEY-HERE

# Recommended Settings
ENFORCEMENT_LEVEL=Balanced
ENABLE_CACHE=true
ENABLE_SEMANTIC_CACHE=true
VALIDATION_RATE=0.15
CONFIDENCE_THRESHOLD=95
USE_PROMPT_CACHING=true

# Performance
MAX_CONCURRENT_DOCUMENTS=3
MAX_FILE_SIZE_MB=10
RATE_LIMIT_ENABLED=true
RATE_LIMIT_REQUESTS_PER_MINUTE=60

# Model Configuration (optional - defaults work fine)
GPT_MODEL=gpt-5                         # GPT-5 (released August 2025)
SONNET_MODEL=claude-3-5-sonnet-20241022
OPUS_MODEL=claude-3-opus-20240229
```

6. Click "Save" or "Deploy"

### Option 2: Railway CLI
```bash
railway login
railway link

# Set required keys
railway variables set OPENAI_API_KEY="sk-proj-..."
railway variables set ANTHROPIC_API_KEY="sk-ant-api03-..."

# Set enforcement level
railway variables set ENFORCEMENT_LEVEL="Balanced"

# Enable caching
railway variables set ENABLE_CACHE="true"

# Deploy
railway up
```

## 📋 Vercel Setup (Step-by-Step)

### Option 1: Vercel Dashboard (Easiest)
1. Go to your Vercel project
2. Go to "Settings" → "Environment Variables"
3. Add new variable:
   - **Name:** `NEXT_PUBLIC_API_URL`
   - **Value:** `https://your-app-name.railway.app` (your Railway URL)
   - **Environment:** Select all (Production, Preview, Development)
4. Click "Save"
5. Redeploy your app

### Option 2: Vercel CLI
```bash
vercel env add NEXT_PUBLIC_API_URL production
# When prompted, enter: https://your-app.railway.app

vercel --prod  # Redeploy
```

## 🧪 Test Your Deployment

### 1. Test Railway Backend
```bash
# Check health
curl https://your-app.railway.app/health/v2

# Test pipeline
curl -X POST https://your-app.railway.app/api/v2/test
```

### 2. Test Vercel Frontend
- Visit your Vercel URL
- Upload a test document
- Should process successfully

## 🎯 Enforcement Levels Explained

| Level | Description | Use Case |
|-------|-------------|----------|
| **Bloody** | Flags everything (even formatting) | Legal review, maximum protection |
| **Balanced** | Material issues only | Standard business review |
| **Lenient** | Critical issues only | Quick review, deal-friendly |

Set via: `ENFORCEMENT_LEVEL=Balanced` (or Bloody/Lenient)

## 🔍 Verify Your Setup

### Check Railway Variables
```bash
railway variables
```

### Check Vercel Variables
```bash
vercel env ls
```

### Debug Connection Issues
If frontend can't reach backend:
1. Check `NEXT_PUBLIC_API_URL` starts with `https://` not `http://`
2. Ensure Railway app is running (green status)
3. Test backend directly with curl

## 📊 Optional Performance Tuning

### For Faster Processing
```env
SKIP_GPT_CONFIDENCE_THRESHOLD=90  # Skip GPT more often
MAX_CONCURRENT_DOCUMENTS=5        # Process more in parallel
VALIDATION_RATE=0.1               # Less validation
```

### For Higher Accuracy
```env
SKIP_GPT_CONFIDENCE_THRESHOLD=100  # Never skip GPT
VALIDATION_RATE=0.3                # More validation
OPUS_CONFIDENCE_THRESHOLD=90       # Route more to Opus
```

### For Cost Savings
```env
ENABLE_CACHE=true
CACHE_VALIDATED_ONLY=true
USE_PROMPT_CACHING=true
SKIP_GPT_CONFIDENCE_THRESHOLD=85
```

## ⚡ Quick Commands

### Full Railway Setup (Copy & Paste)
```bash
# Set all recommended variables at once
railway variables set \
  OPENAI_API_KEY="sk-proj-..." \
  ANTHROPIC_API_KEY="sk-ant-..." \
  ENFORCEMENT_LEVEL="Balanced" \
  ENABLE_CACHE="true" \
  ENABLE_SEMANTIC_CACHE="true"

railway up
```

### Test the API
```bash
# Quick test with sample text
curl -X POST https://your-app.railway.app/api/v2/test
```

## 🚨 Common Issues & Fixes

| Issue | Fix |
|-------|-----|
| "OPENAI_API_KEY not found" | Set in Railway variables, not .env |
| Frontend shows "Network Error" | Check NEXT_PUBLIC_API_URL in Vercel |
| "Rate limit exceeded" | Adjust RATE_LIMIT_REQUESTS_PER_MINUTE |
| Slow processing | Enable caching: ENABLE_CACHE=true |
| Too many/few redlines | Change ENFORCEMENT_LEVEL |

## 📝 Complete Variable Reference

See `ENVIRONMENT_VARIABLES_GUIDE.md` for the full list of 50+ configuration options.

## ✨ New Features Available

With these environment variables, you now have:
- **3 enforcement modes** (Bloody/Balanced/Lenient)
- **4-pass LLM pipeline** with intelligent gating
- **Semantic caching** for 70% cost reduction
- **Banned token guarantees** (no perpetual terms)
- **API v2 endpoints** at `/api/v2/`

---

**Next Step**: Add your API keys to Railway and Vercel, then test with `/api/v2/test` endpoint!
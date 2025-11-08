# Environment Variables Configuration Guide

## 🚨 Critical Variables (Required for Both Vercel & Railway)

### API Keys (MUST SET THESE FIRST)
```bash
# OpenAI API Key - Required for GPT models
OPENAI_API_KEY=sk-...

# Anthropic API Key - Required for Claude models
ANTHROPIC_API_KEY=sk-ant-...
```

## 📦 Railway Backend Variables

### Core API Keys (Required)
```bash
OPENAI_API_KEY=sk-...                    # Your OpenAI API key
ANTHROPIC_API_KEY=sk-ant-...             # Your Anthropic API key
```

### Enforcement & Processing (Recommended)
```bash
ENFORCEMENT_LEVEL=Balanced                # Options: Bloody, Balanced, Lenient
ENABLE_CACHE=true                        # Enable semantic caching
ENABLE_SEMANTIC_CACHE=true               # Alternative cache flag
VALIDATION_RATE=0.15                     # Rate for Claude validation (0-1)
CONFIDENCE_THRESHOLD=95                  # Confidence threshold for validation
USE_PROMPT_CACHING=true                  # Enable prompt caching
```

### Pass Configuration (Optional - defaults work)
```bash
ENABLE_PASS_0=true                       # Enable deterministic rules
ENABLE_PASS_1=true                       # Enable GPT-5 recall
ENABLE_PASS_2=true                       # Enable Sonnet validation
ENABLE_PASS_3=true                       # Enable Opus adjudication
ENABLE_PASS_4=true                       # Enable consistency sweep
```

### Model Configuration (Optional - defaults work)
```bash
GPT_MODEL=gpt-5                         # Latest GPT model (GPT-5, released August 2025)
GPT_TEMPERATURE=0.1                     # GPT temperature (0.0-1.0)
GPT_MAX_TOKENS=2000                     # Max tokens for GPT

SONNET_MODEL=claude-sonnet-4-5-20250929 # Sonnet 4.5 model
SONNET_TEMPERATURE=0.2                  # Sonnet temperature
SONNET_MAX_TOKENS=1500                  # Max tokens for Sonnet

OPUS_MODEL=claude-opus-4-1-20250805     # Opus 4.1 model
OPUS_TEMPERATURE=0.1                    # Opus temperature
OPUS_MAX_TOKENS=2000                    # Max tokens for Opus
OPUS_CONFIDENCE_THRESHOLD=85            # Route to Opus if confidence < this
```

### Redis Configuration (Required if using Redis)
```bash
REDIS_URL=redis://default:password@host:port  # Full Redis URL (Railway provides this)
USE_REDIS_QUEUE=false                         # Enable Redis job queue
```

### Security & Rate Limiting (Recommended)
```bash
ENABLE_API_KEYS=false                   # Require API keys for endpoints
RATE_LIMIT_ENABLED=true                 # Enable rate limiting
RATE_LIMIT_REQUESTS_PER_MINUTE=60       # Requests per minute limit
MAX_FILE_SIZE_MB=50                     # Max file size in MB
MAX_BATCH_SIZE_MB=500                   # Max batch size in MB
KEY_ROTATION_DAYS=90                    # API key rotation period
```

### Performance & Limits (Optional)
```bash
MAX_BATCH_SIZE=100                      # Maximum batch size
MAX_CONCURRENT_DOCUMENTS=3              # Concurrent document processing
REQUEST_TIMEOUT_SECONDS=120             # API call timeout
PIPELINE_TIMEOUT_SECONDS=600            # Total pipeline timeout
```

### Server Configuration (Railway sets these)
```bash
PORT=8000                               # Server port (Railway auto-sets)
HOST=0.0.0.0                           # Server host
WORKERS=4                               # Worker processes
```

### Logging (Optional)
```bash
LOG_LEVEL=INFO                         # Options: DEBUG, INFO, WARNING, ERROR
LOG_FILE=logs/nda_reviewer.log         # Log file path
```

## 🌐 Vercel Frontend Variables

### Required for Frontend
```bash
NEXT_PUBLIC_API_URL=https://your-railway-app.railway.app  # Your Railway backend URL
```

### Optional Frontend Settings
```bash
NEXT_PUBLIC_ENFORCEMENT_LEVEL=Balanced  # Default enforcement level in UI
NEXT_PUBLIC_ENABLE_TELEMETRY=true      # Enable frontend telemetry
NEXT_PUBLIC_MAX_FILE_SIZE_MB=10        # Max file size for upload
```

## 🚀 Quick Setup Commands

### For Railway (Backend)

1. **Via Railway CLI:**
```bash
railway variables set OPENAI_API_KEY="sk-..."
railway variables set ANTHROPIC_API_KEY="sk-ant-..."
railway variables set ENFORCEMENT_LEVEL="Balanced"
railway variables set ENABLE_CACHE="true"
```

2. **Via Railway Dashboard:**
   - Go to your project → Variables tab
   - Add each variable one by one
   - Or use "Raw Editor" and paste:
```
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
ENFORCEMENT_LEVEL=Balanced
ENABLE_CACHE=true
ENABLE_SEMANTIC_CACHE=true
VALIDATION_RATE=0.15
CONFIDENCE_THRESHOLD=95
USE_PROMPT_CACHING=true
```

### For Vercel (Frontend)

1. **Via Vercel CLI:**
```bash
vercel env add NEXT_PUBLIC_API_URL
# Enter: https://your-railway-app.railway.app
```

2. **Via Vercel Dashboard:**
   - Go to Project Settings → Environment Variables
   - Add variable:
     - Name: `NEXT_PUBLIC_API_URL`
     - Value: `https://your-railway-app.railway.app`
     - Environment: Production, Preview, Development

## 📋 Complete Variable List (All Optional Except API Keys)

### Essential (Must Set)
- [ ] `OPENAI_API_KEY` - OpenAI API key
- [ ] `ANTHROPIC_API_KEY` - Anthropic API key
- [ ] `NEXT_PUBLIC_API_URL` - Backend URL (Vercel only)

### Highly Recommended
- [ ] `ENFORCEMENT_LEVEL` - Strictness level (default: Balanced)
- [ ] `ENABLE_CACHE` - Enable caching (default: true)
- [ ] `REDIS_URL` - Redis connection (if using Redis)

### Performance Tuning
- [ ] `VALIDATION_RATE` - Claude validation rate (default: 0.15)
- [ ] `CONFIDENCE_THRESHOLD` - Confidence threshold (default: 95)
- [ ] `MAX_CONCURRENT_DOCUMENTS` - Parallel processing (default: 3)
- [ ] `SKIP_GPT_CONFIDENCE_THRESHOLD` - Skip GPT if rules confident (default: 98)

### Model Configuration
- [ ] `GPT_MODEL` - GPT model name (default: gpt-5, released August 2025)
- [ ] `SONNET_MODEL` - Sonnet model (default: claude-sonnet-4-5-20250929)
- [ ] `OPUS_MODEL` - Opus model (default: claude-opus-4-1-20250805)

### Security
- [ ] `ENABLE_API_KEYS` - Require API keys (default: false)
- [ ] `RATE_LIMIT_ENABLED` - Enable rate limiting (default: true)
- [ ] `MAX_FILE_SIZE_MB` - Max upload size (default: 50)

## 🔍 Verification

### Check Railway Variables:
```bash
railway variables
```

### Check Vercel Variables:
```bash
vercel env ls
```

### Test Backend Health:
```bash
curl https://your-railway-app.railway.app/health
```

### Test Frontend Connection:
```bash
curl https://your-vercel-app.vercel.app
# Check if API calls work
```

## 🚨 Common Issues

### Issue: "OPENAI_API_KEY not found"
**Fix**: Ensure the variable is set in Railway/Vercel environment, not just .env file

### Issue: Frontend can't reach backend
**Fix**:
1. Check `NEXT_PUBLIC_API_URL` is set correctly in Vercel
2. Ensure it starts with `https://` not `http://`
3. Verify Railway app is deployed and running

### Issue: Redis connection failed
**Fix**:
1. If not using Redis, set `USE_REDIS_QUEUE=false`
2. If using Redis, ensure `REDIS_URL` is properly formatted

### Issue: Rate limiting not working
**Fix**: Set `RATE_LIMIT_ENABLED=true` and optionally adjust `RATE_LIMIT_REQUESTS_PER_MINUTE`

## 📝 Environment Priority

Variables are read in this order:
1. Direct function parameters (highest priority)
2. Environment variables (from Vercel/Railway)
3. .env file (local development only)
4. Default values in code (lowest priority)

## 🎯 Minimal Production Setup

For the absolute minimum working deployment:

**Railway (Backend):**
```
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
```

**Vercel (Frontend):**
```
NEXT_PUBLIC_API_URL=https://your-railway-app.railway.app
```

Everything else will use sensible defaults!

---

**Note**: Never commit API keys to your repository. Always use environment variables in production deployments.
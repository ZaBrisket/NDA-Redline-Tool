# Environment Files Summary - Ready for Deployment

## 📁 Files Ready for Import

All environment variable files have been updated with GPT-5 configuration and are ready to import into Railway and Vercel.

---

## 🚂 Railway Backend - RAILWAY.env

**File Location:** `RAILWAY.env`

**How to Import:**

### Option 1: Railway Dashboard (Recommended)
1. Go to your Railway project
2. Click on your service
3. Navigate to **Variables** tab
4. Click **"Raw Editor"** button
5. Copy the **entire contents** of `RAILWAY.env`
6. Paste into the Raw Editor
7. Click **"Save"** or **"Deploy"**

### Option 2: Railway CLI
```bash
railway login
railway link
# Then manually set variables or use the dashboard
```

### ⚠️ Important: Add Your API Keys
Before importing, replace these placeholders in `RAILWAY.env`:
```
OPENAI_API_KEY=sk-proj-YOUR-OPENAI-KEY-HERE
ANTHROPIC_API_KEY=sk-ant-api03-YOUR-ANTHROPIC-KEY-HERE
```

With your actual keys:
```
OPENAI_API_KEY=sk-proj-abc123...
ANTHROPIC_API_KEY=sk-ant-api03-xyz789...
```

### What's Configured in RAILWAY.env:

✅ **API Keys** (requires your keys)
- OPENAI_API_KEY
- ANTHROPIC_API_KEY

✅ **GPT-5 Configuration**
- GPT_MODEL=gpt-5
- GPT_TEMPERATURE=0.1
- GPT_MAX_TOKENS=2000

✅ **Enforcement Level**
- ENFORCEMENT_LEVEL=Balanced (Options: Bloody, Balanced, Lenient)

✅ **Caching** (70% cost savings)
- ENABLE_CACHE=true
- ENABLE_SEMANTIC_CACHE=true
- USE_PROMPT_CACHING=true

✅ **Performance**
- MAX_CONCURRENT_DOCUMENTS=3
- VALIDATION_RATE=0.15
- CONFIDENCE_THRESHOLD=95

✅ **Security**
- RATE_LIMIT_ENABLED=true
- RATE_LIMIT_REQUESTS_PER_MINUTE=60
- CORS_ORIGINS=* (change to your Vercel domain for production)

✅ **All 5 Passes Enabled**
- Pass 0: Deterministic rules
- Pass 1: GPT-5 recall
- Pass 2: Claude Sonnet validation
- Pass 3: Claude Opus adjudication
- Pass 4: Consistency sweep

---

## 🌐 Vercel Frontend - VERCEL.env

**File Location:** `VERCEL.env`

**How to Import:**

### Option 1: Vercel Dashboard (Recommended)
1. Go to your Vercel project
2. Navigate to **Settings → Environment Variables**
3. For each variable in `VERCEL.env`:
   - Click **"Add New"**
   - Enter the **Name** (e.g., `NEXT_PUBLIC_API_URL`)
   - Enter the **Value**
   - Select environments: **Production, Preview, Development**
   - Click **"Save"**
4. After adding all variables, **redeploy** your app

### Option 2: Vercel CLI
```bash
vercel env add NEXT_PUBLIC_API_URL production
# When prompted, enter: https://your-railway-app.railway.app
```

### ⚠️ Important: Update Backend URL
Before importing, replace this placeholder in `VERCEL.env`:
```
NEXT_PUBLIC_API_URL=https://your-railway-app.railway.app
```

With your actual Railway URL:
```
NEXT_PUBLIC_API_URL=https://nda-reviewer-production.railway.app
```

### What's Configured in VERCEL.env:

✅ **Required**
- NEXT_PUBLIC_API_URL (your Railway backend URL)

✅ **Optional UI Configuration**
- NEXT_PUBLIC_ENFORCEMENT_LEVEL=Balanced
- NEXT_PUBLIC_MAX_FILE_SIZE_MB=10
- NEXT_PUBLIC_ENABLE_TELEMETRY=true
- NEXT_PUBLIC_APP_NAME=NDA Reviewer

---

## 📋 Other Environment Files

### `.env` (Local Development)
**File Location:** `.env`
- Already configured with GPT-5
- Used for local development
- **DO NOT** commit this file to git

### `.env.example` (Template)
**File Location:** `.env.example`
- Already configured with GPT-5
- Template for new developers
- Safe to commit to git (contains no secrets)

---

## 🎯 Quick Import Checklist

### Railway Setup
- [ ] Open `RAILWAY.env` file
- [ ] Replace `YOUR-OPENAI-KEY-HERE` with actual OpenAI API key
- [ ] Replace `YOUR-ANTHROPIC-KEY-HERE` with actual Anthropic API key
- [ ] Go to Railway Dashboard → Variables → Raw Editor
- [ ] Copy & paste entire file contents
- [ ] Click Save/Deploy
- [ ] Wait for deployment to complete
- [ ] Copy your Railway app URL (e.g., `https://nda-reviewer-production.railway.app`)

### Vercel Setup
- [ ] Open `VERCEL.env` file
- [ ] Replace `your-railway-app.railway.app` with your actual Railway URL
- [ ] Go to Vercel Dashboard → Settings → Environment Variables
- [ ] Add each variable (5 variables total)
- [ ] Select all environments (Production, Preview, Development)
- [ ] Click Save
- [ ] Go to Deployments tab → Redeploy

---

## ✅ Verification

### Test Railway Backend
```bash
curl https://your-railway-app.railway.app/health
```

Expected response:
```json
{
  "status": "healthy",
  "models_configured": {
    "gpt": "gpt-5",
    "sonnet": "claude-sonnet-4-5-20250929",
    "opus": "claude-opus-4-1-20250805"
  }
}
```

### Test Vercel Frontend
1. Visit your Vercel URL
2. Open browser console (F12)
3. Check for API connection errors
4. Try uploading a test document

---

## 🔧 Customization Options

### Change Enforcement Level
In `RAILWAY.env`, change:
```
ENFORCEMENT_LEVEL=Balanced
```

To:
- `Bloody` - Zero tolerance (all issues flagged)
- `Lenient` - Only critical issues
- `Balanced` - Professional strictness (recommended)

### Adjust Performance
For faster processing (lower accuracy):
```
SKIP_GPT_CONFIDENCE_THRESHOLD=90
VALIDATION_RATE=0.1
```

For higher accuracy (slower):
```
SKIP_GPT_CONFIDENCE_THRESHOLD=100
VALIDATION_RATE=0.3
```

### Cost Optimization
```
ENABLE_CACHE=true
USE_PROMPT_CACHING=true
SKIP_GPT_CONFIDENCE_THRESHOLD=85
```

---

## 🚨 Security Notes

### Production Security
1. **Change CORS_ORIGINS** in Railway:
   ```
   CORS_ORIGINS=https://your-vercel-app.vercel.app
   ```

2. **Enable API Keys** (optional):
   ```
   ENABLE_API_KEYS=true
   API_KEY_REQUIRED=true
   ```

3. **Never commit** `.env` file to git

4. **Rotate API keys** periodically (set `KEY_ROTATION_DAYS=90`)

---

## 📊 What's Using GPT-5

After deployment, GPT-5 will be used for:

✅ **Pass 1: Recall Maximization**
- Initial document analysis
- Pattern detection
- Clause identification

✅ **Cost Savings**
- GPT-5 pricing: $1.25/1M input, $10/1M output
- **75% cheaper** than GPT-4o ($5/$15 per 1M)

✅ **Better Performance**
- Faster inference
- Improved accuracy
- Better reasoning

---

## 🔄 Rollback to GPT-4o (If Needed)

If you need to rollback to GPT-4o:

In Railway Dashboard → Variables:
```
GPT_MODEL=gpt-4o
```

Then redeploy. No code changes needed!

---

## 📞 Need Help?

### Common Issues

**Issue: "OPENAI_API_KEY not found"**
- Check you added it in Railway Variables
- Verify it starts with `sk-proj-` or `sk-`
- Redeploy after adding

**Issue: Frontend can't reach backend**
- Verify `NEXT_PUBLIC_API_URL` in Vercel
- Check Railway app is running (green status)
- Ensure URL starts with `https://`

**Issue: GPT-5 API errors**
- Verify your OpenAI API key has GPT-5 access
- Check API quota/billing
- Review logs in Railway Dashboard

---

## 📝 Summary

**Files Ready:**
- ✅ `RAILWAY.env` - Complete backend configuration with GPT-5
- ✅ `VERCEL.env` - Complete frontend configuration
- ✅ `.env.example` - Updated template with GPT-5
- ✅ `.env` - Local development config with GPT-5

**Total Variables:**
- Railway: ~50 variables (fully configured)
- Vercel: 5 variables (minimal required)

**Time to Deploy:** ~10 minutes
**No Code Changes Required:** Just import environment variables!

---

**Ready to deploy!** 🚀

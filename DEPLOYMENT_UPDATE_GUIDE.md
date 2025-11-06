# Deployment Update Guide - All-Claude Migration

**For:** Railway (Backend) & Vercel (Frontend)
**Migration:** All-Claude Architecture
**Date:** 2025-01-06

---

## Quick Summary

### Railway (Backend)
- ❌ **DELETE:** `OPENAI_API_KEY` (no longer used)
- ✅ **KEEP:** `ANTHROPIC_API_KEY` (required)
- 🔄 **UPDATE:** `VALIDATION_RATE` from `0.15` to `1.0`

### Vercel (Frontend)
- ✅ **NO CHANGES NEEDED** (frontend doesn't use LLM APIs)

---

## Railway (Backend) - Detailed Steps

### Step 1: Delete Obsolete Variables

Navigate to your Railway project → Variables tab

#### 1.1 Delete `OPENAI_API_KEY`

```
Variable: OPENAI_API_KEY
Action: DELETE
Reason: System now uses Claude exclusively
```

**How to delete:**
1. Go to Railway dashboard
2. Select your NDA backend project
3. Click "Variables" tab
4. Find `OPENAI_API_KEY`
5. Click the trash/delete icon
6. Confirm deletion

#### 1.2 Delete `USE_PROMPT_CACHING` (if exists)

```
Variable: USE_PROMPT_CACHING
Action: DELETE (if present)
Reason: OpenAI-specific feature
```

---

### Step 2: Verify Required Variables

#### 2.1 Verify `ANTHROPIC_API_KEY` exists and is correct

```
Variable: ANTHROPIC_API_KEY
Value: sk-ant-... (your Anthropic API key)
Status: REQUIRED
```

**Verification:**
1. In Railway Variables tab
2. Confirm `ANTHROPIC_API_KEY` is set
3. Value should start with `sk-ant-`
4. If missing, ADD it now (system won't start without it)

**⚠️ CRITICAL:** The backend will fail to start if `ANTHROPIC_API_KEY` is missing or invalid.

---

### Step 3: Update Configuration Variables

#### 3.1 Update `VALIDATION_RATE`

```
Variable: VALIDATION_RATE
Old Value: 0.15
New Value: 1.0
Reason: Now validating 100% of suggestions (not 15%)
```

**How to update:**
1. Find `VALIDATION_RATE` in Railway Variables
2. Click to edit
3. Change value from `0.15` to `1.0`
4. Save

**Alternative:** Delete this variable (system defaults to 1.0)

---

### Step 4: Optional Model Configuration

These are **OPTIONAL** - the system has good defaults.

#### 4.1 Claude Opus Model (Optional)

```
Variable: CLAUDE_OPUS_MODEL
Default: claude-3-opus-20240229
Action: Only set if you want a different model
```

#### 4.2 Claude Sonnet Model (Optional)

```
Variable: CLAUDE_SONNET_MODEL
Default: claude-sonnet-4-20250514
Action: Only set if you want a different model
```

**When to set these:**
- When Claude releases newer models
- When testing specific model versions
- For cost optimization

---

### Step 5: Verify Other Variables

Keep these unchanged:

```
CONFIDENCE_THRESHOLD=95
MAX_FILE_SIZE_MB=50
STORAGE_PATH=./storage
RETENTION_DAYS=7
LOG_LEVEL=INFO
ENVIRONMENT=production
CORS_ORIGINS=https://your-frontend.vercel.app
```

---

### Step 6: Deploy the New Code

After updating environment variables:

1. **Deploy the migration branch:**
   - In Railway, go to Settings
   - Update the branch to: `claude/migrate-all-claude-architecture-011CUsHkk2Ky6cSReTBQvwNU`
   - Or merge to main and deploy from main

2. **Watch the deployment logs:**
   ```
   Expected log messages:
   ✓ "Initialized All-Claude Orchestrator"
   ✓ "Anthropic API key validated"
   ✓ "All-Claude architecture initialized"
   ✓ "Validation: 100% of suggestions"
   ```

3. **Check for errors:**
   ```
   ❌ "ANTHROPIC_API_KEY environment variable is required"
      → Add the API key

   ❌ "OPENAI_API_KEY not set"
      → This is normal - ignore (old code remnants)
   ```

---

### Step 7: Verify Health Check

After deployment, test the health endpoint:

```bash
curl https://your-backend.railway.app/health
```

**Expected response:**
```json
{
  "status": "healthy",
  "version": "2.0.0",
  "architecture": "all-claude",
  "checks": {
    "anthropic_key_configured": true,
    "validation_rate": "100%"
  }
}
```

**If status is "degraded":**
- Check that `ANTHROPIC_API_KEY` is set correctly
- Verify the key starts with `sk-ant-`
- Check Railway logs for specific errors

---

## Vercel (Frontend) - No Changes Needed

### Why No Changes?

1. **Frontend doesn't use LLM APIs directly**
   - All LLM calls go through the backend
   - Frontend only communicates with Railway backend

2. **No OpenAI references in frontend code**
   - Verified with grep scan
   - Frontend is API-agnostic

3. **Backend API contract unchanged**
   - All endpoints return same response format
   - Frontend code doesn't need updates

### Verify Frontend Works

After backend deployment:

1. **Check API communication:**
   - Frontend should still connect to Railway backend
   - Upload/processing should work normally

2. **Environment variables to keep:**
   ```
   NEXT_PUBLIC_API_URL=https://your-backend.railway.app
   (any other frontend-specific variables)
   ```

---

## Summary Checklist

### Railway Backend

- [ ] ❌ Delete `OPENAI_API_KEY`
- [ ] ❌ Delete `USE_PROMPT_CACHING` (if exists)
- [ ] ✅ Verify `ANTHROPIC_API_KEY` is set
- [ ] 🔄 Update `VALIDATION_RATE` to `1.0`
- [ ] 📦 Deploy migration branch
- [ ] 🔍 Check deployment logs
- [ ] 🏥 Test health endpoint
- [ ] ✅ Verify status is "healthy"

### Vercel Frontend

- [ ] ✅ No changes needed
- [ ] ✅ Test that frontend still works
- [ ] ✅ Verify API communication

---

## Troubleshooting

### Issue: Backend won't start

**Error:** "ANTHROPIC_API_KEY environment variable is required"

**Solution:**
1. Go to Railway → Variables
2. Add `ANTHROPIC_API_KEY` with your Anthropic API key
3. Redeploy

---

### Issue: Health check shows "degraded"

**Possible causes:**
1. `ANTHROPIC_API_KEY` not set or invalid
2. API key is test key (starts with `sk-ant-test`)

**Solution:**
1. Verify `ANTHROPIC_API_KEY` in Railway Variables
2. Ensure it's a valid production key
3. Check Railway logs for specific error

---

### Issue: Costs are higher than expected

**Explanation:**
- All-Claude architecture costs more per document
- Claude Opus is more expensive than GPT-4o
- 100% validation (vs 15%) increases costs

**Expected cost:** ~$0.05-0.08 per document (was ~$0.01-0.02)

**Benefits:**
- Higher quality redlines
- 100% validation coverage
- Single vendor (simpler billing)

---

### Issue: Processing seems slower

**Explanation:**
- 100% validation means more LLM calls
- Each suggestion is validated with Sonnet

**Expected:** Still < 60 seconds per document

**If slower:**
- Check Railway logs for API latency
- Verify Anthropic API status
- Consider upgrading Railway plan for more resources

---

## Rollback Plan

If critical issues occur:

### Quick Rollback

1. **In Railway:**
   - Go to Deployments
   - Find previous deployment (before migration)
   - Click "Redeploy"

2. **Restore environment variables:**
   - Re-add `OPENAI_API_KEY`
   - Change `VALIDATION_RATE` back to `0.15`

3. **Verify:**
   - Check health endpoint shows version 1.0.0
   - Test document processing

### Git Rollback

```bash
# Checkout previous commit
git checkout 0b97dcd

# Force push to main (if needed)
git push origin main --force

# Railway will auto-deploy
```

---

## Support & Questions

**Documentation:**
- `MIGRATION_SUMMARY.md` - Full migration details
- `VALIDATION_REPORT.md` - Test results
- `BUGFIX_BATCH_API.md` - Batch API fix

**Monitoring:**
- Watch Railway logs for errors
- Monitor Anthropic API usage in dashboard
- Check health endpoint regularly

**Cost Tracking:**
- Anthropic dashboard: https://console.anthropic.com
- Monitor token usage and costs
- Compare vs previous OpenAI costs

---

**Last Updated:** 2025-01-06
**Migration Branch:** `claude/migrate-all-claude-architecture-011CUsHkk2Ky6cSReTBQvwNU`
**Status:** Ready for deployment

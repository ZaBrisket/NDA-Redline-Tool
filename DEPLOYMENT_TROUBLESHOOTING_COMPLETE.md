# 🚨 Complete Deployment Troubleshooting Guide
## NDA Redline Tool - Railway & Vercel Deployment

---

## 🔴 CRITICAL: Your Deployment is NOT Using Latest Code

Despite having all fixes in GitHub (commits a86cdb9, 195929d, 7b3a7d6), Railway and Vercel are deploying old code. This guide will help you fix it.

---

## 📋 Pre-Flight Checklist

### ✅ Verify Git Status First
```bash
cd "C:\Users\IT\OneDrive\Desktop\Claude Projects\NDA Reviewer\builds\nda-redline-tool\NDA-Redline-Tool"
git status
git log --oneline -5
```

**You should see:**
- `7b3a7d6 Force rebuild: Ensure production fixes are deployed`
- `195929d Fix Railway build failure: Remove unused ML dependencies`
- `a86cdb9 Critical Production Fixes - Multi-LLM Orchestration System`

### ✅ Confirm Remote Repository
```bash
git remote -v
```
**Should show:** `origin https://github.com/ZaBrisket/NDA-Redline-Tool`

---

## 🚂 RAILWAY BACKEND TROUBLESHOOTING

### 1. CHECK RAILWAY CONFIGURATION

**Go to Railway Dashboard → Your Project → Settings**

| Setting | MUST BE | Common Mistake |
|---------|---------|----------------|
| **GitHub Repo** | `ZaBrisket/NDA-Redline-Tool` | Wrong repo or fork |
| **Branch** | `main` | Deploying from old branch |
| **Root Directory** | **EMPTY** or `/` | Set to `/backend` (WRONG!) |
| **Start Command** | Auto-detected from nixpacks.toml | Manual override conflicts |
| **Build Command** | Auto-detected | Manual override breaks |

### 2. FIX WRONG REPOSITORY CONNECTION

If Railway is connected to wrong repo:

1. **Disconnect GitHub:**
   - Settings → GitHub → Disconnect

2. **Reconnect Correctly:**
   - Connect GitHub Account
   - Select `ZaBrisket/NDA-Redline-Tool`
   - Choose `main` branch
   - **LEAVE ROOT DIRECTORY EMPTY**

3. **Clear Cache & Redeploy:**
   - Settings → Danger Zone → Clear Build Cache
   - Deployments → Redeploy

### 3. CHECK BUILD LOGS

**Look for these indicators:**

✅ **GOOD Signs (New Build):**
```
Installing dependencies from requirements.txt
Collecting fastapi==0.115.6
Collecting uvicorn[standard]==0.34.0
Build completed in ~2-3 minutes
```

❌ **BAD Signs (Old Build):**
```
Downloading torch-2.x.x (700MB)
Downloading sentence-transformers
Installing faiss-cpu
Build taking 10+ minutes
```

### 4. VERIFY ENVIRONMENT VARIABLES

**Required in Railway:**
```env
OPENAI_API_KEY=sk-proj-...
ANTHROPIC_API_KEY=sk-ant-...
CORS_ORIGINS=https://your-app.vercel.app,http://localhost:3000
ENVIRONMENT=production
MAX_FILE_SIZE_MB=50
RETENTION_DAYS=7
```

### 5. RAILWAY BUILD FIXES

If build fails, try these in order:

#### Fix A: Force nixpacks.toml usage
```bash
# The nixpacks.toml file should be at repository root
# It contains: uvicorn backend.app.main:app --host 0.0.0.0 --port $PORT
```

#### Fix B: Manual Start Command (Last Resort)
If nixpacks.toml isn't working, set in Railway:
```
cd backend && pip install -r requirements.txt && uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

#### Fix C: Complete Reset
1. Delete the Railway project entirely
2. Create new project
3. Connect to `ZaBrisket/NDA-Redline-Tool`
4. Set environment variables
5. Deploy

---

## 🔷 VERCEL FRONTEND TROUBLESHOOTING

### 1. CHECK VERCEL CONFIGURATION

**Go to Vercel Dashboard → Your Project → Settings → General**

| Setting | MUST BE | Common Mistake |
|---------|---------|----------------|
| **GitHub Repo** | `ZaBrisket/NDA-Redline-Tool` | Wrong repo |
| **Branch** | `main` | Wrong branch |
| **Root Directory** | `frontend` | Set to `/frontend` with slash |
| **Framework Preset** | Next.js | Not detected |
| **Node Version** | 18.x or 20.x | Old version |

### 2. FIX VERCEL DEPLOYMENT

#### Step 1: Check Git Integration
Settings → Git → Verify:
- Repository: `ZaBrisket/NDA-Redline-Tool`
- Production Branch: `main`
- Directory: `frontend` (no leading slash!)

#### Step 2: Environment Variables
Settings → Environment Variables:
```env
NEXT_PUBLIC_API_URL=https://your-backend.up.railway.app
```

#### Step 3: Force Redeploy with Correct Commit
1. Go to Deployments tab
2. Find commit `7b3a7d6`
3. Click "..." → "Redeploy"
4. OR create new deployment from specific commit

### 3. VERCEL BUILD ERRORS

**Common Error: "Module not found"**
```bash
# Fix: Ensure root directory is exactly "frontend" (no slash)
```

**Common Error: "Build failed"**
```bash
# Fix: Check package.json is in frontend folder
# Verify with: ls frontend/package.json
```

---

## 🔧 NUCLEAR OPTION: Complete Fresh Deployment

If nothing else works, start completely fresh:

### Step 1: Prepare Local Repository
```bash
cd "C:\Users\IT\OneDrive\Desktop\Claude Projects\NDA Reviewer\builds\nda-redline-tool\NDA-Redline-Tool"

# Ensure all files are committed
git add -A
git commit -m "Deployment configuration files"
git push origin main
```

### Step 2: New Railway Project
1. Go to https://railway.app
2. New Project → Deploy from GitHub Repo
3. Select `ZaBrisket/NDA-Redline-Tool`
4. **IMPORTANT**: Leave root directory EMPTY
5. Add all environment variables
6. Deploy

### Step 3: New Vercel Project
1. Go to https://vercel.com
2. Add New → Project
3. Import `ZaBrisket/NDA-Redline-Tool`
4. **Root Directory**: `frontend`
5. Add `NEXT_PUBLIC_API_URL` with Railway URL
6. Deploy

---

## 🧪 VERIFICATION TESTS

### Test 1: Backend Health Check
```bash
curl https://your-railway-url.up.railway.app/

# Expected Response:
{
  "service": "NDA Automated Redlining",
  "version": "1.0.0",
  "status": "operational"
}
```

### Test 2: Stats Endpoint (Proves Fixes are Deployed)
```bash
curl https://your-railway-url.up.railway.app/api/stats

# If this works, the fixes are deployed!
# If 404, old code is still running
```

### Test 3: File Size Limit
Try uploading a 60MB file through the UI. Should be rejected if fixes are working.

### Test 4: Check Logs for API Validation
Railway logs should show:
```
✓ OpenAI API key validated
✓ Anthropic API key validated
```

### Test 5: Run Verification Script
```bash
python verify_deployment.py
# Enter your Railway URL
# Enter your Vercel URL
# Check all tests pass
```

---

## 📊 How to Know if Fixes Are Deployed

| Feature | Old Code | Fixed Code |
|---------|----------|------------|
| `/api/stats` endpoint | 404 Not Found | Returns statistics |
| File upload > 50MB | Accepts file | Rejects with 413 |
| Railway build time | 10+ minutes (ML packages) | 2-3 minutes |
| Memory usage | Grows indefinitely | Cleaned every hour |
| Failed jobs | Stuck in QUEUED | Marked as ERROR |
| CORS | Allows * wildcard | Specific origins only |
| API key validation | No startup check | Validates on startup |

---

## 🆘 EMERGENCY COMMANDS

### Force Git Push (if commits aren't showing)
```bash
git push --force origin main
```

### Check What Railway Sees
```bash
# In Railway logs, you should see:
# "Cloning https://github.com/ZaBrisket/NDA-Redline-Tool"
# "Checking out commit 7b3a7d6"
```

### Manual Deployment Trigger
```bash
# Railway CLI (if installed)
railway up

# Vercel CLI (if installed)
vercel --prod
```

---

## 💡 COMMON ROOT CAUSES

1. **Wrong Repository**: Railway/Vercel connected to a fork instead of main repo
2. **Wrong Branch**: Deploying from `master` instead of `main`
3. **Root Directory Issue**: Railway has `/backend` set (should be empty)
4. **Cached Old Build**: Platform using cached build from before fixes
5. **Manual Overrides**: Custom build/start commands overriding nixpacks.toml
6. **Commit Not Pushed**: Local commits not pushed to GitHub
7. **Wrong Remote**: Local git pointing to different repository

---

## 📞 SUPPORT CHECKLIST

If you need help, provide this information:

1. **Git status output**:
   ```bash
   git log --oneline -5
   git remote -v
   git status
   ```

2. **Railway configuration screenshot** showing:
   - Repository connection
   - Branch
   - Root directory
   - Latest deployment commit

3. **Vercel configuration screenshot** showing:
   - Repository connection
   - Root directory
   - Environment variables

4. **Deployment logs** from both Railway and Vercel

5. **Test results** from `python verify_deployment.py`

---

## ✅ SUCCESS CRITERIA

You'll know deployment is working when:

1. Railway build completes in 2-3 minutes (not 10+)
2. `/api/stats` endpoint returns data
3. File uploads > 50MB are rejected
4. No CORS errors in browser console
5. Documents process successfully end-to-end
6. Memory usage stays stable over time

---

## 🎯 QUICK FIX FLOWCHART

```
Is Railway showing commit 7b3a7d6?
├─ NO → Disconnect and reconnect GitHub repo to main branch
└─ YES → Is build taking > 5 minutes?
         ├─ YES → Clear cache, check requirements.txt is updated
         └─ NO → Is /api/stats working?
                  ├─ NO → Wrong root directory or nixpacks not used
                  └─ YES → Deployment successful! Check Vercel next
```

---

**Remember**: The code is FIXED. The deployment configuration is BROKEN. Focus on getting Railway and Vercel to use the code from the `main` branch of `ZaBrisket/NDA-Redline-Tool`.

---

*Last Updated: 2025-10-23*
*All fixes are in commits: a86cdb9, 195929d, 7b3a7d6*
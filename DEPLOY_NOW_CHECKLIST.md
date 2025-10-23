# 🚀 DEPLOY NOW - Quick Action Checklist

## ⚡ IMMEDIATE ACTIONS (10 minutes)

### 1️⃣ COMMIT NEW CONFIGURATION FILES (1 min)
```bash
cd "C:\Users\IT\OneDrive\Desktop\Claude Projects\NDA Reviewer\builds\nda-redline-tool\NDA-Redline-Tool"
git add railway.json vercel.json verify_deployment.py update_cors.py *.md
git commit -m "Add deployment configuration and verification tools"
git push origin main
```

### 2️⃣ FIX RAILWAY (5 mins)

Go to: https://railway.app/dashboard

**A. Check Current Settings:**
- Click your project → Settings
- **Repository**: Must be `ZaBrisket/NDA-Redline-Tool`
- **Branch**: Must be `main`
- **Root Directory**: Must be EMPTY (delete any value)

**B. If Wrong, Fix It:**
1. Settings → GitHub → Disconnect
2. Reconnect to `ZaBrisket/NDA-Redline-Tool`
3. Select `main` branch
4. Leave root directory EMPTY
5. Add environment variables:
```
OPENAI_API_KEY=sk-proj-YOUR-KEY
ANTHROPIC_API_KEY=sk-ant-YOUR-KEY
CORS_ORIGINS=https://YOUR-VERCEL-APP.vercel.app,http://localhost:3000
ENVIRONMENT=production
RETENTION_DAYS=7
MAX_FILE_SIZE_MB=50
```

**C. Force Redeploy:**
- Settings → Clear Build Cache
- Deployments → Redeploy

**D. Watch Build Logs:**
- Should take 2-3 minutes (NOT 10+)
- Should NOT download torch/ML packages
- Should show "Build successful"

### 3️⃣ FIX VERCEL (4 mins)

Go to: https://vercel.com/dashboard

**A. Check Current Settings:**
- Click your project → Settings → General
- **Repository**: Must be `ZaBrisket/NDA-Redline-Tool`
- **Root Directory**: Must be `frontend` (no slash!)

**B. If Wrong, Fix It:**
1. Settings → Git
2. Verify repo is `ZaBrisket/NDA-Redline-Tool`
3. Set Root Directory to: `frontend`
4. Add environment variable:
```
NEXT_PUBLIC_API_URL=https://YOUR-RAILWAY-APP.up.railway.app
```

**C. Force Redeploy:**
- Deployments tab
- Find latest deployment
- Click "..." → "Redeploy" → "Use different commit"
- Select commit `7b3a7d6` or latest
- Deploy

---

## ✅ VERIFY IT WORKED (2 mins)

### Quick Test #1 - Backend Health
```bash
curl https://YOUR-RAILWAY-URL.up.railway.app/
```
**Should return:** `{"service":"NDA Automated Redlining","version":"1.0.0"}`

### Quick Test #2 - Stats Endpoint (Proves fixes deployed)
```bash
curl https://YOUR-RAILWAY-URL.up.railway.app/api/stats
```
**Should return:** Statistics JSON (not 404)

### Quick Test #3 - Frontend
- Open: https://YOUR-VERCEL-URL.vercel.app
- Should see upload interface
- Try uploading a small .docx file

### Quick Test #4 - Run Verification Script
```bash
cd "C:\Users\IT\OneDrive\Desktop\Claude Projects\NDA Reviewer\builds\nda-redline-tool\NDA-Redline-Tool"
python verify_deployment.py
# Enter your Railway URL
# Enter your Vercel URL
```

---

## 🔴 IF STILL NOT WORKING

The #1 issue is Railway/Vercel using wrong repository or branch.

**Nuclear Option - Start Fresh:**
1. Delete both Railway and Vercel projects
2. Create new projects from scratch
3. Connect to `ZaBrisket/NDA-Redline-Tool`
4. Railway: Leave root directory EMPTY
5. Vercel: Set root directory to `frontend`
6. Add environment variables as shown above

---

## 📱 GET YOUR URLS

After successful deployment:

**Railway Backend URL:**
Look like: `https://nda-redline-tool-production.up.railway.app`

**Vercel Frontend URL:**
Look like: `https://nda-redline-tool.vercel.app`

**Update CORS:** Once you have both URLs:
```bash
python update_cors.py
# Enter your Vercel URL
# Enter your Railway URL
git add -A && git commit -m "Update CORS for production" && git push
```

---

## ⏱️ TIME ESTIMATE

- Git commit & push: 1 minute
- Fix Railway: 5 minutes
- Fix Vercel: 4 minutes
- Verification: 2 minutes
- **Total: ~12 minutes**

---

## 🎯 SUCCESS INDICATORS

✅ Railway build under 3 minutes (not 10+)
✅ No torch/ML package downloads
✅ `/api/stats` endpoint works
✅ Frontend loads without CORS errors
✅ Can upload and process documents

---

**REMEMBER**: The code is FIXED. You just need Railway/Vercel to deploy from the right place!

Repository: `ZaBrisket/NDA-Redline-Tool`
Branch: `main`
Latest commit: `7b3a7d6` (or newer)

---

*Start with Step 1 above. You'll have a working deployment in 10 minutes!*
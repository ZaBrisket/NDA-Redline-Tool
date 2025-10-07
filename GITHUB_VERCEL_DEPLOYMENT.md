# GitHub + Vercel Deployment Guide

Step-by-step instructions to deploy the NDA Reviewer to GitHub and Vercel.

## Prerequisites

- [ ] GitHub account (https://github.com)
- [ ] Vercel account (https://vercel.com) - sign up with GitHub
- [ ] Git installed on your computer
- [ ] OpenAI API key
- [ ] Anthropic API key

---

## Part 1: Prepare Project for GitHub

### Step 1: Open Terminal/Command Prompt

Navigate to the project directory:

```bash
cd "C:\Users\IT\OneDrive\Desktop\Claude Projects\NDA Reviewer\builds\20251005_211648"
```

### Step 2: Initialize Git Repository

```bash
git init
```

Expected output: `Initialized empty Git repository...`

### Step 3: Configure Git (First Time Only)

If you haven't configured git before:

```bash
git config --global user.name "Your Name"
git config --global user.email "your.email@example.com"
```

### Step 4: Add All Files

```bash
git add .
```

This stages all files for commit.

### Step 5: Create Initial Commit

```bash
git commit -m "Initial commit: NDA Automated Redline Tool with Review UI"
```

Expected output: Shows files committed.

---

## Part 2: Create GitHub Repository

### Step 6: Go to GitHub

1. Open browser and go to: https://github.com
2. Log in to your account
3. Click the **"+"** icon in top right
4. Select **"New repository"**

### Step 7: Configure Repository

**Repository Settings:**
- **Repository name**: `nda-reviewer` (or your preferred name)
- **Description**: "Automated NDA redlining with Edgewater checklist and review UI"
- **Visibility**:
  - ✅ **Private** (recommended for proprietary code)
  - ⬜ Public (only if you want to share publicly)
- **DO NOT** initialize with README (we already have one)
- Click **"Create repository"**

### Step 8: Push to GitHub

GitHub will show you commands. Use the "push an existing repository" section:

```bash
# Add GitHub as remote
git remote add origin https://github.com/YOUR_USERNAME/nda-reviewer.git

# Push to GitHub
git branch -M main
git push -u origin main
```

**Replace `YOUR_USERNAME`** with your actual GitHub username.

**If prompted for credentials:**
- Username: Your GitHub username
- Password: Use a **Personal Access Token** (not your password)
  - Go to: GitHub Settings → Developer settings → Personal access tokens → Tokens (classic)
  - Generate new token with `repo` scope
  - Copy and use as password

Expected output: Files uploading to GitHub.

### Step 9: Verify Upload

Go to: `https://github.com/YOUR_USERNAME/nda-reviewer`

You should see all your files!

---

## Part 3: Deploy Backend (Manual - Not on Vercel)

⚠️ **Important**: The backend (Python/FastAPI) needs to be deployed separately. Vercel is only for the frontend.

### Backend Deployment Options:

#### Option A: Railway (Recommended - Easiest)

1. Go to https://railway.app
2. Sign up with GitHub
3. Click **"New Project"** → **"Deploy from GitHub repo"**
4. Select your `nda-reviewer` repository
5. Railway auto-detects Python
6. Add environment variables:
   - `OPENAI_API_KEY`
   - `ANTHROPIC_API_KEY`
   - `USE_PROMPT_CACHING=true`
   - `VALIDATION_RATE=0.15`
7. Set start command: `cd backend && uvicorn app.main:app --host 0.0.0.0 --port $PORT`
8. Deploy!
9. Copy the generated URL (e.g., `https://nda-reviewer-production.up.railway.app`)

#### Option B: Render.com

1. Go to https://render.com
2. Sign up with GitHub
3. Click **"New +" → "Web Service"**
4. Connect your GitHub repository
5. Configure:
   - **Name**: nda-reviewer-backend
   - **Root Directory**: `backend`
   - **Runtime**: Python 3
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
6. Add environment variables (same as Railway)
7. Click **"Create Web Service"**
8. Copy the URL (e.g., `https://nda-reviewer-backend.onrender.com`)

#### Option C: Heroku

See `DEPLOYMENT.md` for Heroku instructions.

**Save your backend URL** - you'll need it for Vercel!

---

## Part 4: Deploy Frontend to Vercel

### Step 10: Go to Vercel

1. Open browser and go to: https://vercel.com
2. Click **"Sign Up"** (if new) or **"Log In"**
3. **Choose**: Sign up with GitHub
4. Authorize Vercel to access GitHub

### Step 11: Import Project

1. On Vercel dashboard, click **"Add New..." → "Project"**
2. Find your `nda-reviewer` repository in the list
3. Click **"Import"**

### Step 12: Configure Project

**Framework Preset**:
- Vercel should auto-detect **Next.js** ✅

**Root Directory**:
- Click **"Edit"**
- Set to: `frontend`
- This tells Vercel your Next.js app is in the frontend folder

**Build Settings** (usually auto-detected):
- Build Command: `npm run build`
- Output Directory: `.next`
- Install Command: `npm install`

### Step 13: Environment Variables

Click **"Environment Variables"** section.

**Add this variable:**

| Name | Value |
|------|-------|
| `NEXT_PUBLIC_API_URL` | Your backend URL from Step 9 |

Example value: `https://nda-reviewer-production.up.railway.app`

**IMPORTANT**:
- ✅ Make sure the URL has `https://`
- ✅ No trailing slash
- ✅ This is the Railway/Render URL from Part 3

### Step 14: Update Next.js Config

Before deploying, update the API proxy configuration:

**Edit `frontend/next.config.mjs`:**

```javascript
/** @type {import('next').NextConfig} */
const nextConfig = {
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: `${process.env.NEXT_PUBLIC_API_URL}/api/:path*`,
      },
    ];
  },
};

export default nextConfig;
```

**Commit and push this change:**

```bash
cd frontend
# Edit next.config.mjs as shown above
cd ..
git add frontend/next.config.mjs
git commit -m "Update API URL for production"
git push
```

### Step 15: Deploy!

Back in Vercel:
1. Click **"Deploy"**
2. Wait 2-3 minutes for build
3. Watch the build logs (optional but interesting!)

Expected output:
- ✅ Building
- ✅ Installing dependencies
- ✅ Building Next.js application
- ✅ Deployment ready

### Step 16: Get Your URL

Once deployed, Vercel gives you a URL like:

```
https://nda-reviewer-YOUR-USERNAME.vercel.app
```

Click it to open your live app! 🎉

---

## Part 5: Test Deployed Application

### Step 17: Test Upload Flow

1. Go to your Vercel URL
2. Upload a test .docx file
3. **Expected**: Processing starts
4. **Wait**: ~60 seconds
5. **Expected**: Redirected to review page
6. **Check**: Redlines displayed with checklist rules

### Step 18: Test Review UI

1. Click through redlines
2. Click ✓ Accept or ✗ Reject
3. Navigate with Previous/Next
4. **Expected**: All works smoothly

### Step 19: Test Download

1. Review all redlines
2. Click Download button
3. **Expected**: Word document downloads
4. Open in Word
5. **Check**: Track changes visible

---

## Part 6: Domain Setup (Optional)

### Step 20: Add Custom Domain

If you have your own domain (e.g., `nda.edgewater.com`):

1. In Vercel, go to your project
2. Click **"Settings" → "Domains"**
3. Add your custom domain
4. Follow DNS configuration instructions
5. Wait for DNS propagation (5-30 minutes)

---

## Troubleshooting

### Issue: Build Failed

**Check:**
- Root directory is set to `frontend`
- Node.js version (should auto-detect 18.x)
- Review build logs for specific error

**Fix:**
```bash
# Test build locally first
cd frontend
npm install
npm run build
```

### Issue: API Requests Failing

**Check:**
- `NEXT_PUBLIC_API_URL` environment variable in Vercel
- Backend is running (visit backend URL directly)
- CORS configuration in backend

**Fix backend CORS:**

Edit `backend/app/main.py`:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://nda-reviewer-YOUR-USERNAME.vercel.app",
        "http://localhost:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

Redeploy backend after changes.

### Issue: 404 on API Routes

**Check:**
- `next.config.mjs` has correct rewrite rules
- `NEXT_PUBLIC_API_URL` doesn't have trailing slash

**Fix:**
- Remove trailing slash from environment variable
- Redeploy

### Issue: Environment Variables Not Working

**After adding/changing environment variables in Vercel:**

1. Go to project in Vercel
2. Click **"Deployments"**
3. Click **"Redeploy"** on latest deployment
4. Environment changes require redeploy

### Issue: Backend Not Responding

**Check Railway/Render logs:**
- Is the service running?
- Are environment variables set?
- Is the port configured correctly?

**Railway:** Dashboard → Logs
**Render:** Dashboard → Service → Logs

---

## Updating Your App

### Make Changes Locally

```bash
# Make your changes to code
# Test locally

# Commit changes
git add .
git commit -m "Description of changes"

# Push to GitHub
git push
```

### Automatic Deployment

Vercel automatically deploys when you push to GitHub!

- **Frontend changes**: Auto-deploy in ~2 minutes
- **Backend changes**: Depends on Railway/Render settings (usually auto-deploy)

### Manual Redeploy

If needed, redeploy manually:

**Vercel:**
1. Go to project → Deployments
2. Click three dots → Redeploy

**Railway:**
1. Go to project
2. Click **"Deploy"** or wait for auto-deploy

---

## Environment Variables Summary

### Backend (Railway/Render)

```env
OPENAI_API_KEY=sk-proj-...
ANTHROPIC_API_KEY=sk-ant-...
USE_PROMPT_CACHING=true
VALIDATION_RATE=0.15
CONFIDENCE_THRESHOLD=95
CORS_ORIGINS=https://your-vercel-app.vercel.app
```

### Frontend (Vercel)

```env
NEXT_PUBLIC_API_URL=https://your-backend-url.railway.app
```

---

## Security Checklist

- [ ] Backend API keys stored in Railway/Render environment variables
- [ ] Frontend uses `NEXT_PUBLIC_API_URL` environment variable
- [ ] CORS configured with specific origins (not `*`)
- [ ] GitHub repository is private (if proprietary)
- [ ] No `.env` files committed to GitHub
- [ ] No API keys in code or frontend
- [ ] HTTPS enabled on both frontend and backend

---

## Cost Estimate

### Free Tier Limits:

**Vercel (Frontend):**
- Free tier: 100 GB bandwidth/month
- Unlimited deployments
- Custom domains included
- **Cost**: $0/month for most use cases

**Railway (Backend):**
- Free trial: $5 credit
- After trial: Pay as you go
- ~$5-10/month for light use
- **Cost**: ~$5-10/month

**Render (Alternative Backend):**
- Free tier: 750 hours/month
- Spins down after inactivity
- **Cost**: $0/month (with spindown) or $7/month (always on)

**LLM APIs:**
- OpenAI: ~$0.08 per document
- Anthropic: ~$0.03 per document
- **Cost**: Variable based on usage

**Total**: ~$5-15/month + LLM costs

---

## Architecture Diagram

```
┌─────────────────────────────────────────────┐
│   User Browser                              │
└──────────────┬──────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────┐
│   Vercel (Frontend - Next.js)               │
│   https://nda-reviewer.vercel.app           │
│   - Upload UI                               │
│   - Review interface                        │
│   - Accept/reject workflow                  │
└──────────────┬──────────────────────────────┘
               │
               │ HTTPS API calls
               ▼
┌─────────────────────────────────────────────┐
│   Railway/Render (Backend - FastAPI)       │
│   https://nda-reviewer.railway.app          │
│   - Document processing                     │
│   - Rule engine                             │
│   - LLM orchestration                       │
│   - Track changes generation                │
└──────────────┬──────────────────────────────┘
               │
               │ API calls
               ▼
┌─────────────────────────────────────────────┐
│   OpenAI + Anthropic APIs                   │
│   - GPT-5 analysis                          │
│   - Claude validation                       │
└─────────────────────────────────────────────┘
```

---

## Next Steps After Deployment

1. ✅ Test with real NDAs
2. ✅ Share URL with team
3. ✅ Monitor usage and costs
4. ✅ Set up custom domain (optional)
5. ✅ Configure monitoring/alerts
6. ✅ Add authentication if needed

---

## Support & Resources

- **Vercel Docs**: https://vercel.com/docs
- **Railway Docs**: https://docs.railway.app
- **Render Docs**: https://render.com/docs
- **Next.js Deployment**: https://nextjs.org/docs/deployment

---

## Quick Reference Commands

```bash
# Navigate to project
cd "C:\Users\IT\OneDrive\Desktop\Claude Projects\NDA Reviewer\builds\20251005_211648"

# Initialize git (first time only)
git init
git add .
git commit -m "Initial commit"

# Add GitHub remote (first time only)
git remote add origin https://github.com/YOUR_USERNAME/nda-reviewer.git
git push -u origin main

# Update code
git add .
git commit -m "Update description"
git push

# View git status
git status

# View commit history
git log --oneline
```

---

**🚀 You're Ready to Deploy!**

Follow these steps in order, and you'll have your NDA Reviewer live on the internet.

**Estimated Time**: 30-45 minutes
**Difficulty**: Beginner-Intermediate

Good luck! 🎉

# 🚀 Deployment Quick Start

**Fast track to getting your NDA Reviewer live!**

---

## 📋 Checklist

- [ ] GitHub account
- [ ] Vercel account (sign up with GitHub)
- [ ] Railway or Render account
- [ ] OpenAI API key
- [ ] Anthropic API key

---

## ⚡ 5-Minute Deploy

### 1️⃣ Push to GitHub (2 min)

```bash
cd "C:\Users\IT\OneDrive\Desktop\Claude Projects\NDA Reviewer\builds\20251005_211648"

git init
git add .
git commit -m "Initial commit: NDA Reviewer"

# Create repo on GitHub.com (name it "nda-reviewer")
# Then:
git remote add origin https://github.com/YOUR_USERNAME/nda-reviewer.git
git push -u origin main
```

### 2️⃣ Deploy Backend on Railway (2 min)

1. Go to https://railway.app
2. **"New Project"** → **"Deploy from GitHub"**
3. Select `nda-reviewer` repo
4. Add environment variables:
   - `OPENAI_API_KEY` = your key
   - `ANTHROPIC_API_KEY` = your key
5. Set command: `cd backend && uvicorn app.main:app --host 0.0.0.0 --port $PORT`
6. **Deploy**
7. **Copy the URL** (e.g., `https://xxx.up.railway.app`)

### 3️⃣ Deploy Frontend on Vercel (1 min)

1. Go to https://vercel.com
2. **"Add New"** → **"Project"**
3. Import `nda-reviewer` from GitHub
4. Set **Root Directory** to: `frontend`
5. Add environment variable:
   - `NEXT_PUBLIC_API_URL` = Railway URL from step 2
6. **Deploy**
7. **Visit your URL!** (e.g., `https://nda-reviewer-xxx.vercel.app`)

---

## ✅ Test It

1. Go to your Vercel URL
2. Upload a .docx NDA
3. Review redlines with checklist rules
4. Download the final document

**Done!** 🎉

---

## 🔧 If Something Breaks

### Backend not responding?
- Check Railway logs
- Verify environment variables are set
- Make sure port is `$PORT`

### Frontend can't reach backend?
- Check `NEXT_PUBLIC_API_URL` in Vercel
- Add frontend URL to backend CORS:
  ```python
  allow_origins=["https://your-vercel-url.vercel.app"]
  ```

### Need to update?
```bash
git add .
git commit -m "Update"
git push
```
Vercel auto-deploys! Railway too!

---

## 📊 Architecture

```
User
  ↓
Vercel (Frontend)
  ↓
Railway (Backend)
  ↓
OpenAI + Anthropic
```

---

## 💰 Cost

- Vercel: **Free**
- Railway: **~$5-10/month**
- APIs: **~$0.08-0.11 per document**

---

## 📚 Full Instructions

See `GITHUB_VERCEL_DEPLOYMENT.md` for complete step-by-step guide.

---

**Questions?** Check the troubleshooting section in the full deployment guide!

# 🚀 Quick Start - With Your API Keys

Since your API keys are already saved, this guide will get you running even faster!

---

## ⚡ Super Fast Setup (2 minutes)

### Step 1: Navigate to Project

```bash
cd "C:\Users\IT\OneDrive\Desktop\Claude Projects\NDA Reviewer\builds\20251005_211648"
```

### Step 2: Auto-Setup Environment

```bash
python setup_env.py
```

This script will:
- ✅ Read your Anthropic key from: `C:\Users\IT\OneDrive\Desktop\Claude Projects\API Keys\NDA Reviewer - Anthropic.txt`
- ✅ Read your OpenAI key from: `C:\Users\IT\OneDrive\Desktop\Claude Projects\API Keys\NDA Reviewer - OpenAI.txt`
- ✅ Create `backend/.env` with all settings
- ✅ Verify key formats

**Expected output:**
```
============================================================
NDA Reviewer - Environment Setup
============================================================

📖 Reading API keys from files...
✅ Anthropic API key loaded (108 characters)
✅ OpenAI API key loaded (164 characters)

✅ Created: backend\.env

🔍 Verifying API key formats...
✅ API key formats look correct!

============================================================
✅ Setup Complete!
============================================================
```

### Step 3: Install Backend Dependencies

```bash
cd backend
pip install -r requirements.txt
```

### Step 4: Start Backend

```bash
cd ..
python start_server.py
```

**Backend running on**: http://localhost:8000

### Step 5: Install Frontend Dependencies (New Terminal)

Open a **second terminal**:

```bash
cd "C:\Users\IT\OneDrive\Desktop\Claude Projects\NDA Reviewer\builds\20251005_211648\frontend"
npm install
```

### Step 6: Start Frontend

```bash
npm run dev
```

**Frontend running on**: http://localhost:3000

### Step 7: Test It! 🎉

Open browser: http://localhost:3000

1. Upload an NDA (.docx)
2. Wait ~60 seconds
3. Review redlines with checklist rules
4. Accept/reject each one
5. Download final document

---

## 📋 Your API Keys Location

The script reads from these files:

- **Anthropic**: `C:\Users\IT\OneDrive\Desktop\Claude Projects\API Keys\NDA Reviewer - Anthropic.txt`
- **OpenAI**: `C:\Users\IT\OneDrive\Desktop\Claude Projects\API Keys\NDA Reviewer - OpenAI.txt`

**Format in each file**: Just the API key, nothing else
```
sk-ant-api03-xxxxxxxxxxxx...
```

---

## 🔧 If Setup Script Fails

### Manual Setup (Backup Plan)

```bash
# Copy template
cd backend
cp .env.template .env

# Edit .env manually
notepad .env
```

**Then paste your keys:**
- Open: `C:\Users\IT\OneDrive\Desktop\Claude Projects\API Keys\NDA Reviewer - Anthropic.txt`
- Copy the key
- Paste into `.env` as: `ANTHROPIC_API_KEY=sk-ant-...`
- Repeat for OpenAI key

---

## 🌐 For Deployment (Railway/Vercel)

When deploying, you'll enter these same API keys in the web dashboards:

### Railway (Backend)
1. Dashboard → Environment Variables
2. Add `ANTHROPIC_API_KEY` = (paste your Anthropic key)
3. Add `OPENAI_API_KEY` = (paste your OpenAI key)

### Vercel (Frontend)
1. Dashboard → Environment Variables
2. Add `NEXT_PUBLIC_API_URL` = (your Railway URL)

**Your local `.env` is NOT uploaded to GitHub** (excluded by `.gitignore`)

---

## ✅ Verification Checklist

After running `setup_env.py`, verify:

- [ ] File exists: `backend/.env`
- [ ] Contains: `ANTHROPIC_API_KEY=sk-ant-...`
- [ ] Contains: `OPENAI_API_KEY=sk-...` or `sk-proj-...`
- [ ] Contains: `USE_PROMPT_CACHING=true`
- [ ] No errors when running script

---

## 🎯 Complete Flow

```
1. Run setup_env.py
   ↓
2. Install backend dependencies
   ↓
3. Start backend (python start_server.py)
   ↓
4. Install frontend dependencies (npm install)
   ↓
5. Start frontend (npm run dev)
   ↓
6. Open http://localhost:3000
   ↓
7. Upload NDA and test!
```

**Total time: ~5 minutes** (most of it is installing dependencies)

---

## 🚨 Troubleshooting

### "File not found" error

**Check your API key files exist:**
```bash
dir "C:\Users\IT\OneDrive\Desktop\Claude Projects\API Keys\NDA Reviewer - Anthropic.txt"
dir "C:\Users\IT\OneDrive\Desktop\Claude Projects\API Keys\NDA Reviewer - OpenAI.txt"
```

If missing, create them and paste your keys.

### "API key invalid" when running

**Check the key format:**
- Anthropic keys start with: `sk-ant-`
- OpenAI keys start with: `sk-` or `sk-proj-`
- No extra spaces or quotes
- Just the raw key

### Backend won't start

**Check .env was created:**
```bash
dir backend\.env
```

**View the file:**
```bash
type backend\.env
```

Should show your API keys (first 20 chars visible).

---

## 📞 Support

- **Setup script issues**: Check file paths are exactly correct
- **API key issues**: Verify keys work on OpenAI/Anthropic websites
- **Deployment**: See `GITHUB_VERCEL_DEPLOYMENT.md`

---

## 🎉 Next Steps

Once running locally:

1. **Test with real NDAs** - Upload a few different formats
2. **Review accuracy** - Compare to manual redlines
3. **Deploy to production** - Follow `GITHUB_VERCEL_DEPLOYMENT.md`
4. **Share with team** - Send them the Vercel URL

---

**🚀 You're ready! Run `python setup_env.py` to start!**

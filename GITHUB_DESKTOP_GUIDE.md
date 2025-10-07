# 🖥️ GitHub Desktop - Step-by-Step Guide

The easiest way to add your NDA Reviewer to GitHub using the visual interface.

---

## 📋 Prerequisites

- [ ] Download GitHub Desktop: https://desktop.github.com
- [ ] GitHub account (free): https://github.com

---

## 🚀 Step-by-Step Instructions

### Step 1: Install GitHub Desktop

1. Go to: https://desktop.github.com
2. Click **"Download for Windows"**
3. Run the installer
4. Wait for installation to complete

---

### Step 2: Sign In to GitHub

1. Open **GitHub Desktop**
2. Click **"Sign in to GitHub.com"**
3. Enter your GitHub username and password
4. Click **"Authorize desktop"** (if prompted)
5. Click **"Finish"**

✅ You should now see the GitHub Desktop main screen

---

### Step 3: Add Your Project

1. In GitHub Desktop, click **"File"** → **"Add local repository"**

   **Or** click the **"Add"** dropdown → **"Add existing repository"**

2. Click **"Choose..."** to browse for your folder

3. Navigate to:
   ```
   C:\Users\IT\OneDrive\Desktop\Claude Projects\NDA Reviewer\builds\20251005_211648
   ```

4. Click **"Select Folder"**

5. You'll see a message: **"This directory does not appear to be a Git repository"**

6. Click **"create a repository"** link

---

### Step 4: Create Repository

1. In the "Create a repository" dialog:

   **Name**: `nda-reviewer` (or your preferred name)

   **Description**: `Automated NDA redlining with Edgewater checklist and review UI`

   **Git Ignore**: Leave as "None" (we already have .gitignore)

   **License**: None (or choose if needed)

   ✅ **Keep "Initialize this repository with a README" UNCHECKED** (we have one)

2. Click **"Create Repository"**

✅ Your project is now a Git repository!

---

### Step 5: Review Changes

You should now see GitHub Desktop showing:

**Left panel**:
- List of all your files (backend, frontend, docs, etc.)
- All files should have a **green +** (new files)

**Right panel**:
- Shows the contents of selected files

**Bottom left**:
- "Summary" field
- "Description" field

---

### Step 6: Make First Commit

1. In the **"Summary"** field (bottom left), type:
   ```
   Initial commit: NDA Reviewer with Review UI
   ```

2. In the **"Description"** field (optional), you can add:
   ```
   - Backend: FastAPI with GPT-5 + Claude
   - Frontend: Next.js review interface
   - 20+ automated redline rules
   - Complete documentation
   ```

3. Click the big blue **"Commit to main"** button

✅ All your files are now committed!

---

### Step 7: Publish to GitHub

1. At the top, click **"Publish repository"**

2. In the dialog that appears:

   **Name**: `nda-reviewer` (should be pre-filled)

   **Description**: (should be pre-filled)

   **Keep this code private**: ✅ **CHECK THIS BOX** (recommended)

   **Organization**: None (or select if you have one)

3. Click **"Publish Repository"**

4. Wait 10-30 seconds while it uploads...

✅ **Done! Your code is on GitHub!**

---

### Step 8: Verify on GitHub.com

1. In GitHub Desktop, click **"Repository"** → **"View on GitHub"**

   **Or** go to: `https://github.com/YOUR_USERNAME/nda-reviewer`

2. You should see all your files listed!

3. Check that you see:
   - ✅ `backend/` folder
   - ✅ `frontend/` folder
   - ✅ `README.md`
   - ✅ All documentation files
   - ❌ **No `.env` file** (good - it's excluded by .gitignore)

---

## 🎯 What Just Happened

```
Your Computer
     ↓
GitHub Desktop (Local Repository)
     ↓
GitHub.com (Remote Repository)
```

Your code is now:
1. ✅ Backed up on GitHub
2. ✅ Version controlled
3. ✅ Ready for Vercel deployment

---

## 📝 Making Future Changes

### When You Update Code

1. Make your changes to files (edit code, add features, etc.)

2. Open **GitHub Desktop**

3. You'll see changed files in the left panel

4. Type a summary of your changes:
   ```
   Fix bug in redline processing
   ```

5. Click **"Commit to main"**

6. Click **"Push origin"** (top right)

✅ Your changes are now on GitHub!

---

## 🎨 Visual Guide

### GitHub Desktop Main Screen

```
┌─────────────────────────────────────────────────┐
│ File  Edit  View  Repository  Branch  Help     │
├─────────────────────────────────────────────────┤
│ Current Repository: nda-reviewer           [▼]  │
│ Current Branch: main                       [▼]  │
├──────────────────┬──────────────────────────────┤
│ Changes (95)     │ backend/app/main.py         │
│                  │ ┌──────────────────────────┐ │
│ ☑ backend/       │ │ from fastapi import...   │ │
│ ☑ frontend/      │ │ from fastapi.middle...   │ │
│ ☑ README.md      │ │                          │ │
│ ☑ .gitignore     │ │ app = FastAPI(          │ │
│                  │ │     title="NDA Aut...   │ │
│                  │ └──────────────────────────┘ │
├──────────────────┴──────────────────────────────┤
│ Summary (required)                              │
│ ┌─────────────────────────────────────────────┐ │
│ │ Initial commit: NDA Reviewer               │ │
│ └─────────────────────────────────────────────┘ │
│                                                 │
│ Description                                     │
│ ┌─────────────────────────────────────────────┐ │
│ │ Complete NDA review system                 │ │
│ └─────────────────────────────────────────────┘ │
│                                                 │
│        [Commit to main]                         │
└─────────────────────────────────────────────────┘
```

---

## ⚡ Quick Reference

| Action | Steps |
|--------|-------|
| **Add repository** | File → Add local repository → Choose folder → Create repository |
| **Commit changes** | Type summary → Click "Commit to main" |
| **Upload to GitHub** | Click "Publish repository" |
| **Push updates** | Click "Push origin" (after committing) |
| **View on GitHub** | Repository → View on GitHub |
| **Pull changes** | Click "Fetch origin" then "Pull origin" |

---

## 🔧 Troubleshooting

### "This directory does not appear to be a Git repository"

**Solution**: Click the "create a repository" link in the message

### "Authentication failed"

**Solution**:
1. File → Options → Accounts
2. Sign out and sign back in
3. Try again

### ".env file showing in changes"

**Problem**: You don't want this in GitHub!

**Solution**:
1. Right-click the `.env` file
2. Select "Ignore file"
3. Confirm

### "Push rejected"

**Solution**:
1. Click "Fetch origin"
2. Click "Pull origin"
3. Click "Push origin" again

### Can't find your project folder

**Solution**:
1. Copy this path: `C:\Users\IT\OneDrive\Desktop\Claude Projects\NDA Reviewer\builds\20251005_211648`
2. In the folder browser, paste into the address bar
3. Press Enter

---

## 🎯 Next Steps After GitHub Upload

### Option 1: Deploy to Vercel (Frontend)

Now that your code is on GitHub, you can deploy:

1. Go to https://vercel.com
2. Sign in with GitHub
3. Click "Add New Project"
4. Select `nda-reviewer`
5. Set root directory to `frontend`
6. Add environment variable: `NEXT_PUBLIC_API_URL`
7. Deploy!

**See full guide**: `GITHUB_VERCEL_DEPLOYMENT.md`

### Option 2: Deploy to Railway (Backend)

1. Go to https://railway.app
2. Sign in with GitHub
3. "New Project" → "Deploy from GitHub repo"
4. Select `nda-reviewer`
5. Add environment variables (API keys)
6. Deploy!

**See full guide**: `GITHUB_VERCEL_DEPLOYMENT.md`

---

## 💡 Pro Tips

### Tip 1: Use Descriptive Commit Messages
✅ Good: "Fix redline positioning bug"
❌ Bad: "Update files"

### Tip 2: Commit Often
- Don't wait until everything is perfect
- Small, frequent commits are better
- Easier to track what changed

### Tip 3: Check .gitignore Works
Before first commit, verify:
- ❌ No `.env` file visible
- ❌ No `node_modules/` folder
- ❌ No `__pycache__/` folders

### Tip 4: Sync Regularly
- Click "Fetch origin" daily
- Keeps your local copy updated
- Prevents conflicts

---

## 🆘 Need Help?

### GitHub Desktop Help
- Help menu → GitHub Desktop Help
- https://docs.github.com/en/desktop

### Can't Sign In?
- Make sure you have a GitHub account: https://github.com/signup
- Check your internet connection
- Try signing in through the browser first

### Repository Not Showing?
- Make sure you clicked "Publish repository"
- Check Repository → View on GitHub

---

## 📚 Additional Resources

- **GitHub Desktop Docs**: https://docs.github.com/en/desktop
- **GitHub Guides**: https://guides.github.com
- **Video Tutorial**: Search YouTube for "GitHub Desktop tutorial"

---

## ✅ Success Checklist

After following this guide, you should have:

- [✓] GitHub Desktop installed
- [✓] Signed in to GitHub account
- [✓] Repository created locally
- [✓] First commit made
- [✓] Published to GitHub.com
- [✓] Verified files on GitHub.com
- [✓] `.env` file NOT on GitHub
- [✓] Ready to deploy to Vercel/Railway

---

**🎉 Congratulations! Your code is now on GitHub!**

**Next**: Deploy to production using `GITHUB_VERCEL_DEPLOYMENT.md`

---

## 🎬 Visual Walkthrough

### Screen 1: Add Repository
```
┌────────────────────────────────────┐
│  Add Local Repository              │
├────────────────────────────────────┤
│  Local path:                       │
│  ┌──────────────────────────────┐  │
│  │ C:\Users\IT\OneDrive\...   📁 │  │
│  └──────────────────────────────┘  │
│                                    │
│           [Add Repository]         │
└────────────────────────────────────┘
```

### Screen 2: Create Repository
```
┌────────────────────────────────────┐
│  Create a Repository               │
├────────────────────────────────────┤
│  Name:                             │
│  ┌──────────────────────────────┐  │
│  │ nda-reviewer                 │  │
│  └──────────────────────────────┘  │
│                                    │
│  Description:                      │
│  ┌──────────────────────────────┐  │
│  │ Automated NDA redlining...   │  │
│  └──────────────────────────────┘  │
│                                    │
│  ☐ Initialize with README         │
│                                    │
│           [Create Repository]      │
└────────────────────────────────────┘
```

### Screen 3: Publish
```
┌────────────────────────────────────┐
│  Publish Repository                │
├────────────────────────────────────┤
│  Name: nda-reviewer                │
│  Description: Automated NDA...     │
│                                    │
│  ☑ Keep this code private          │
│                                    │
│  Organization: None            [▼] │
│                                    │
│           [Publish Repository]     │
└────────────────────────────────────┘
```

---

**Need help?** Check the troubleshooting section above or see the full deployment guide!

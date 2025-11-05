# Vercel Deployment Setup

## Quick Fix for Build Error

The Vercel build is failing because it needs to be configured to use the `frontend` subdirectory.

### Option 1: Configure via Vercel Dashboard (Recommended)

1. Go to your Vercel project settings
2. Navigate to **Settings** → **General**
3. Scroll down to **Build & Development Settings**
4. Set **Root Directory** to: `frontend`
5. **Framework Preset**: Next.js (should auto-detect)
6. Leave **Build Command**, **Output Directory**, and **Install Command** as default
7. Click **Save**
8. Redeploy

### Option 2: Vercel CLI

If you have Vercel CLI installed:

```bash
vercel --prod --cwd frontend
```

Or link the project with the frontend directory:

```bash
cd frontend
vercel link
vercel --prod
```

### Verification

After setting the Root Directory to `frontend`, Vercel will:
- ✅ Run `npm install` in the `frontend` directory automatically
- ✅ Run `npm run build` in the `frontend` directory
- ✅ Deploy the `.next` directory correctly

### Current Configuration

The `vercel.json` file has been simplified to work with the Root Directory setting:

```json
{
  "buildCommand": "npm run build",
  "outputDirectory": ".next",
  "installCommand": "npm install",
  "devCommand": "npm run dev"
}
```

This assumes Vercel is already running from the `frontend` directory (via Root Directory setting).

---

## Troubleshooting

If you still see errors:

1. **Check the Root Directory**: Make sure it's set to `frontend` in Vercel settings
2. **Verify package.json**: Ensure `frontend/package.json` has the correct scripts
3. **Check dependencies**: All npm packages should be installed (they are in the PR)
4. **Environment variables**: Add `NEXT_PUBLIC_API_URL` in Vercel settings if needed

---

## Environment Variables

Set these in Vercel Project Settings → Environment Variables:

- `NEXT_PUBLIC_API_URL` - Your backend API URL (e.g., Railway deployment URL)

Example: `https://your-backend.railway.app`

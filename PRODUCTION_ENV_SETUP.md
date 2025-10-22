# Production Environment Setup - CRITICAL FIX

## Current Production Issue
The upload feature is failing because the frontend at `https://edgetoolspro.com` is trying to call the wrong API URL.

## IMMEDIATE FIX REQUIRED

### 1. Vercel Environment Variables (Frontend)
Go to Vercel Dashboard → Project Settings → Environment Variables

**DELETE any existing `NEXT_PUBLIC_API_URL` and ADD:**
```
NEXT_PUBLIC_API_URL = https://nda-redline-tool-production.up.railway.app
```

**IMPORTANT**:
- This URL must point to your Railway backend, NOT the Vercel frontend
- The current incorrect value `https://nda-redline-tool.vercel.app/` is causing the failure
- Make sure to select: Production, Preview, Development

### 2. Railway Environment Variables (Backend)
Go to Railway Dashboard → Variables tab

**ENSURE these are set:**
```
# API Keys (ALREADY SET - DO NOT MODIFY)
OPENAI_API_KEY = [ALREADY SET - DO NOT MODIFY]
ANTHROPIC_API_KEY = [ALREADY SET - DO NOT MODIFY]

# CORS Configuration (CRITICAL)
CORS_ORIGINS = https://edgetoolspro.com,https://www.edgetoolspro.com,https://nda-redline-tool.vercel.app,http://localhost:3000

# Other important settings
ENFORCEMENT_LEVEL = Balanced
ENABLE_CACHE = true
ENABLE_SEMANTIC_CACHE = true
USE_PROMPT_CACHING = true
MAX_FILE_SIZE_MB = 10
RATE_LIMIT_ENABLED = true
RATE_LIMIT_REQUESTS_PER_MINUTE = 60
```

### 3. Verify Railway Backend URL
1. Go to Railway Dashboard
2. Click on your project (ID: f0f0b42b-1a0e-412f-b626-44b21297f36a)
3. Go to Networking → Public Networking
4. Your URL is: `https://nda-redline-tool-production.up.railway.app` (Port 8080)
5. This EXACT URL must be used in Vercel's `NEXT_PUBLIC_API_URL`

## Testing After Configuration

### Step 1: Redeploy Both Services
**Vercel:**
1. After updating environment variables
2. Go to Deployments tab
3. Click "..." on latest deployment → Redeploy

**Railway:**
1. After updating environment variables
2. Railway automatically redeploys

### Step 2: Test Upload
1. Open `https://edgetoolspro.com`
2. Open browser DevTools → Network tab
3. Try uploading a .docx file
4. Check that the API call goes to Railway backend (not Vercel)

### Step 3: Verify CORS
In browser console, you should NOT see CORS errors. If you do:
1. Check Railway logs for the actual CORS_ORIGINS being used
2. Ensure the Railway backend has redeployed with new settings

## Common Issues & Solutions

### Issue: "Failed to upload file. Please try again."
**Cause**: Frontend calling wrong backend URL
**Solution**: Update `NEXT_PUBLIC_API_URL` in Vercel to Railway backend URL

### Issue: CORS errors in browser console
**Cause**: Backend not allowing the new domain
**Solution**: Update `CORS_ORIGINS` in Railway to include `https://edgetoolspro.com`

### Issue: 404 Not Found on /api/upload
**Cause**: API call going to Vercel frontend instead of Railway backend
**Solution**: Fix `NEXT_PUBLIC_API_URL` - it must NOT end with a slash

### Issue: Network timeout
**Cause**: Railway backend might be sleeping (free tier)
**Solution**: Wake it up by visiting the Railway URL directly first

## Verification Checklist
- [ ] `NEXT_PUBLIC_API_URL` in Vercel points to Railway backend
- [ ] `CORS_ORIGINS` in Railway includes `https://edgetoolspro.com`
- [ ] Both services have been redeployed
- [ ] Upload API call goes to Railway (check Network tab)
- [ ] No CORS errors in browser console
- [ ] File upload completes successfully
- [ ] Progress updates stream via SSE
- [ ] Download works after processing

## Support URLs
- Production Site: https://edgetoolspro.com
- Railway Dashboard: https://railway.app/project/f0f0b42b-1a0e-412f-b626-44b21297f36a
- Vercel Dashboard: https://vercel.com/dashboard
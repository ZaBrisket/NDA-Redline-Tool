# Upload Fix Summary & Deployment Instructions

## Critical Issue Resolved
**Problem**: Upload feature completely broken on production site `https://edgetoolspro.com`
**Root Cause**: Frontend was calling itself instead of the Railway backend due to incorrect `NEXT_PUBLIC_API_URL`

## Changes Made (Commit: ffd5df0)

### 1. Fixed Environment Configuration Files
- **VERCEL.env**: Changed `NEXT_PUBLIC_API_URL` from `https://nda-redline-tool.vercel.app/` to `https://nda-redline-tool-production.up.railway.app`
- **RAILWAY.env**: Updated `CORS_ORIGINS` to include new domain `https://edgetoolspro.com`
- **backend/.env**: Updated local development CORS settings

### 2. Fixed Backend CORS Handling
- Modified `backend/app/main.py` to properly parse `CORS_ORIGINS` environment variable
- Now supports comma-separated list of allowed origins
- Added logging for CORS configuration

### 3. Resolved Build Warnings
- Updated `frontend/package.json` with overrides for deprecated packages
- Changed eslint from v8 to v9
- Added overrides for inflight, rimraf, and glob packages

### 4. Created Documentation
- `PRODUCTION_ENV_SETUP.md`: Step-by-step fix instructions
- `CRITICAL_FIX_COMMIT.md`: Deployment guide
- `test_production_fix.py`: Automated testing script

## IMMEDIATE ACTION REQUIRED

### Step 1: Update Vercel Environment Variables (CRITICAL)
1. Go to: https://vercel.com/dashboard
2. Select your project
3. Navigate to: Settings → Environment Variables
4. Find `NEXT_PUBLIC_API_URL`
5. **DELETE the old value and ADD:**
   ```
   NEXT_PUBLIC_API_URL = https://nda-redline-tool-production.up.railway.app
   ```
   **IMPORTANT**: Do NOT include a trailing slash!
6. Select all environments: Production, Preview, Development
7. Click Save

### Step 2: Redeploy Vercel
1. Go to Deployments tab
2. Click "..." on the latest deployment
3. Select "Redeploy"
4. Choose "Use existing Build Cache" → Redeploy

### Step 3: Update Railway Environment Variables
1. Go to: https://railway.app/project/f0f0b42b-1a0e-412f-b626-44b21297f36a
2. Click on Variables tab
3. Find or add `CORS_ORIGINS`
4. Set value to:
   ```
   https://edgetoolspro.com,https://www.edgetoolspro.com,https://nda-redline-tool.vercel.app,http://localhost:3000
   ```
5. Railway will automatically redeploy

### Step 4: Verify Deployments
- Vercel deployment: ~2-3 minutes
- Railway deployment: ~2-3 minutes
- Both must complete before testing

## Testing the Fix

### Browser Test (Recommended)
1. Open https://edgetoolspro.com
2. Press F12 to open Developer Tools
3. Go to Network tab
4. Clear the network log
5. Upload a .docx file
6. **Verify**:
   - API call goes to `nda-redline-tool-production.up.railway.app/api/upload`
   - Response status is 200 OK
   - No CORS errors in console
   - Upload completes successfully

### Command Line Test
```bash
# Test backend health
curl https://nda-redline-tool-production.up.railway.app/

# Test CORS
curl -I -X OPTIONS https://nda-redline-tool-production.up.railway.app/api/upload \
  -H "Origin: https://edgetoolspro.com" \
  -H "Access-Control-Request-Method: POST"
```

### Python Test Script
```bash
cd NDA-Redline-Tool
python test_production_fix.py
```

## Verification Checklist
- [ ] GitHub commit pushed successfully
- [ ] Vercel `NEXT_PUBLIC_API_URL` updated to Railway backend URL
- [ ] Railway `CORS_ORIGINS` includes edgetoolspro.com
- [ ] Vercel redeployed with new environment variables
- [ ] Railway redeployed (automatic after variable change)
- [ ] Upload works on https://edgetoolspro.com
- [ ] No CORS errors in browser console
- [ ] API calls go to Railway backend (check Network tab)
- [ ] File processing completes successfully
- [ ] Download works after processing

## Troubleshooting

### Issue: Still seeing "Failed to upload"
1. Check Vercel environment variables - ensure NO trailing slash
2. Verify Railway URL is correct (check Railway dashboard for exact URL)
3. Clear browser cache and retry

### Issue: CORS errors in console
1. Check Railway logs for CORS configuration
2. Ensure Railway has redeployed
3. Verify `CORS_ORIGINS` includes your domain

### Issue: 404 on /api/upload
1. API URL is wrong - it's calling Vercel instead of Railway
2. Fix `NEXT_PUBLIC_API_URL` in Vercel

### Issue: Network timeout
1. Railway backend might be sleeping (free tier)
2. Visit Railway URL directly to wake it up

## Environment Variables Summary

### Vercel (Frontend) - Required
```
NEXT_PUBLIC_API_URL = https://nda-redline-tool-production.up.railway.app
```

### Railway (Backend) - Required
```
OPENAI_API_KEY = [ALREADY SET - DO NOT MODIFY]
ANTHROPIC_API_KEY = [ALREADY SET - DO NOT MODIFY]
CORS_ORIGINS = https://edgetoolspro.com,https://www.edgetoolspro.com,https://nda-redline-tool.vercel.app,http://localhost:3000
```

## Success Metrics
Once properly configured:
- Upload should complete in < 5 seconds for small files
- Processing should start immediately
- SSE progress updates should stream in real-time
- No errors in browser console
- Download should work for processed documents

## Next Steps
1. Monitor Railway logs for any errors
2. Test with various file sizes
3. Consider setting up error monitoring
4. Update documentation with correct Railway URL

## Support
- Production Site: https://edgetoolspro.com
- Old Site: https://nda-redline-tool.vercel.app
- Railway Dashboard: https://railway.app/project/f0f0b42b-1a0e-412f-b626-44b21297f36a
- Vercel Dashboard: https://vercel.com/dashboard
- GitHub Repo: https://github.com/ZaBrisket/NDA-Redline-Tool
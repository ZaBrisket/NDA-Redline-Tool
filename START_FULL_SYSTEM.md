# Quick Start Guide - Complete System

This guide will get both the backend and frontend running for the complete NDA review experience.

## Prerequisites

- Python 3.10+
- Node.js 18+
- OpenAI API key
- Anthropic API key

## Step 1: Start Backend

### Terminal 1 - Backend

```bash
# Navigate to project
cd "C:\Users\IT\OneDrive\Desktop\Claude Projects\NDA Reviewer\builds\20251005_211648"

# Install Python dependencies
cd backend
pip install -r requirements.txt

# Configure environment
cp .env.template .env
# Edit .env and add your API keys:
#   OPENAI_API_KEY=sk-...
#   ANTHROPIC_API_KEY=sk-ant-...

# Start backend server
cd ..
python start_server.py
```

Backend will be running on **http://localhost:8000**

## Step 2: Start Frontend

### Terminal 2 - Frontend

```bash
# Navigate to frontend directory
cd "C:\Users\IT\OneDrive\Desktop\Claude Projects\NDA Reviewer\builds\20251005_211648\frontend"

# Install dependencies (first time only)
npm install

# Start development server
npm run dev
```

Frontend will be running on **http://localhost:3000**

## Step 3: Use the System

1. **Open browser**: Navigate to http://localhost:3000

2. **Upload NDA**:
   - Drag and drop a .docx file
   - Or click "Select File"

3. **Wait for processing** (~45-60 seconds):
   - Rules applied
   - LLM analysis
   - Track changes generated

4. **Review redlines**:
   - See document with all proposed changes on left
   - View checklist rule explanation on right
   - Click ✓ to accept or ✗ to reject each redline

5. **Download**:
   - Once all redlines reviewed, click Download
   - Get Word document with only accepted changes

## Architecture

```
┌─────────────────────────────────────────────────┐
│                                                 │
│  Browser (http://localhost:3000)                │
│  - Upload interface                             │
│  - Review UI with checklist rules               │
│  - Accept/reject redlines                       │
│                                                 │
└──────────────────┬──────────────────────────────┘
                   │
                   │ HTTP + SSE
                   ▼
┌─────────────────────────────────────────────────┐
│                                                 │
│  FastAPI Backend (http://localhost:8000)        │
│  - Document processing                          │
│  - Rule engine (20+ patterns)                   │
│  - LLM orchestration (GPT-5 + Claude)           │
│  - Track changes generation                     │
│                                                 │
└─────────────────────────────────────────────────┘
```

## User Experience Flow

```
1. UPLOAD
   User: Drop NDA.docx
   ↓
   Backend: Save file → Create job → Return job_id

2. PROCESSING (Real-time updates via SSE)
   Backend: Parse DOCX → Apply rules → LLM analysis → Generate track changes
   Frontend: Shows loading with status updates

3. REVIEW
   Frontend: Display document with redlines
   User: For each redline...
     - Read original text (strikethrough)
     - Read proposed text (highlighted)
     - Read checklist rule explanation
     - Click ✓ Accept or ✗ Reject
   Frontend: Auto-save decision to backend

4. EXPORT
   User: Click Download (enabled when all reviewed)
   Backend: Generate DOCX with only accepted changes
   Frontend: Download file
```

## Sample Redline Review Screen

```
┌────────────────────────────────────┬────────────────────────────┐
│ Document with Redlines             │ Checklist Rule Details     │
├────────────────────────────────────┼────────────────────────────┤
│ REDLINE #1                         │ Confidentiality Term Limit │
│ ┌──────────────────────────────┐   │                            │
│ │ Original:                    │   │ EDGEWATER REQUIREMENT      │
│ │ perpetual confidentiality    │   │ 18-24 months maximum       │
│ │ (strikethrough + red)        │   │                            │
│ │                              │   │ WHAT THIS MEANS            │
│ │ Proposed:                    │   │ Edgewater never accepts... │
│ │ eighteen (18) months         │   │                            │
│ │ (highlighted + green)        │   │ WHY THIS MATTERS           │
│ └──────────────────────────────┘   │ Perpetual terms create...  │
│                                    │                            │
│ REDLINE #2                         │ [Accept ✓] [Reject ✗]     │
│ ┌──────────────────────────────┐   │                            │
│ │ ...                          │   │ 1 of 95 redlines           │
│ └──────────────────────────────┘   │ [← Previous] [Next →]      │
└────────────────────────────────────┴────────────────────────────┘
```

## Checklist Rules Displayed

For each redline, the UI shows:

1. **Rule Title**: e.g., "Confidentiality Term Limit"
2. **Severity**: Critical/High/Moderate/Low (color-coded)
3. **Requirement**: What Edgewater requires
4. **Description**: What the rule means
5. **Why it Matters**: Business justification
6. **Standard Language**: Template text (expandable)
7. **Confidence Score**: 0-100% from AI
8. **Source**: Rule-based or LLM

## Example Checklist Rules

### Critical Rules
- **Confidentiality Term Limit**: 18-24 months max
- **Document Retention**: Legal/regulatory/archival carveout
- **Non-Solicit Carveouts**: 4 standard exceptions
- **Competition Safe Harbor**: Normal business operations allowed

### Moderate Rules
- **Governing Law**: Change to Delaware
- **Affiliate Removal**: Limit to named parties
- **Legal Modifiers**: "best efforts" → "commercially reasonable"
- **Injunctive Relief**: Require court determination

## Testing the System

### Test with Sample NDA

1. Create a simple NDA with these clauses:
```
"The undersigned agrees to maintain perpetual confidentiality..."
"This Agreement shall be governed by the laws of California..."
"Recipient shall not hire any employees of the Company..."
```

2. Upload and wait for processing

3. Expect redlines for:
   - Term limit (perpetual → 18 months)
   - Governing law (California → Delaware)
   - Non-solicit (add 4 exceptions)

### Verify Track Changes in Word

1. Download the reviewed document
2. Open in Microsoft Word
3. Go to Review tab → Track Changes
4. Should see:
   - Deletions in strikethrough
   - Insertions underlined
   - Author: "ndaOK"

## Troubleshooting

### Backend Issues

**"ModuleNotFoundError"**
```bash
cd backend
pip install -r requirements.txt
```

**"API keys not configured"**
```bash
# Edit backend/.env
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
```

**"Port 8000 already in use"**
```bash
# Find process using port
netstat -ano | findstr :8000
# Kill process or change port in start_server.py
```

### Frontend Issues

**"Cannot connect to backend"**
- Check backend is running on http://localhost:8000
- Check frontend/next.config.mjs proxy configuration

**"npm install fails"**
```bash
# Clear cache and reinstall
rm -rf node_modules package-lock.json
npm install
```

**"Port 3000 already in use"**
```bash
# Run on different port
npm run dev -- -p 3001
```

### Review UI Issues

**"Redlines not displaying"**
- Check browser console for errors
- Verify job status is "complete"
- Refresh the page

**"Download button disabled"**
- Review all pending redlines (check header count)
- Make accept/reject decision for each

**"No checklist rule information"**
- Backend should include `checklist_rule` in redline data
- Check API response in Network tab

## Performance Expectations

- **Upload**: < 1 second
- **Processing**: 45-60 seconds
- **Review UI**: Instant navigation between redlines
- **Download**: < 5 seconds

## Next Steps

Once the system is running:

1. **Test with training data**:
   ```bash
   python test_training_corpus.py
   ```

2. **Review accuracy**: Compare generated redlines to manual redlines

3. **Customize rules**: Edit `backend/app/models/rules.yaml`

4. **Add custom checklist items**: Update `backend/app/models/checklist_rules.py`

5. **Deploy to production**: See DEPLOYMENT.md

## Support

- **Backend API docs**: http://localhost:8000/docs
- **Backend README**: backend/README.md (if exists)
- **Frontend README**: frontend/README.md
- **Project summary**: PROJECT_SUMMARY.md

---

**System Ready**: Both services should now be running!
- Frontend: http://localhost:3000
- Backend: http://localhost:8000
- API Docs: http://localhost:8000/docs

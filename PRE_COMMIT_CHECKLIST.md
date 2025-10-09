# ✅ Pre-Commit Checklist for GitHub Deployment

**IMPORTANT**: Complete this checklist before pushing to GitHub!

## 🔴 Critical Security Checks

- [ ] **NO API Keys in Code**
  ```bash
  # Run this check:
  grep -r "sk-" --exclude-dir=.git --exclude="*.md" .
  grep -r "OPENAI_API_KEY" --exclude=".env*" --exclude-dir=.git .
  grep -r "ANTHROPIC_API_KEY" --exclude=".env*" --exclude-dir=.git .
  ```

- [ ] **.env Files Excluded**
  ```bash
  # Verify .env is not staged:
  git ls-files | grep -E "\.env"
  # Should return nothing
  ```

- [ ] **No Sensitive Documents**
  ```bash
  # Check for test documents:
  git ls-files | grep -E "\.(docx|pdf|doc)$"
  # Only sample/test docs should appear
  ```

## 🟡 Code Quality Checks

- [ ] **Tests Pass**
  ```bash
  python test_simple.py
  # All 4 tests should pass
  ```

- [ ] **Server Starts Successfully**
  ```bash
  cd backend && python -m uvicorn app.main:app --port 8000
  # Should start without errors
  ```

- [ ] **No Debug Code**
  ```bash
  # Check for debug prints:
  grep -r "print(" backend/app --exclude-dir=__pycache__ | grep -v "#"
  ```

## 🟢 Repository Hygiene

- [ ] **Clean Working Directory**
  ```bash
  git status
  # Only intended files should be staged
  ```

- [ ] **.gitignore Updated**
  - Includes Redis data patterns
  - Includes cache file patterns
  - Includes log file patterns
  - Includes test document patterns

- [ ] **Dependencies Updated**
  ```bash
  # Verify requirements.txt has all packages:
  cat backend/requirements.txt | grep -E "faiss|redis|prometheus|slowapi"
  ```

## 📝 Documentation Checks

- [ ] **README.md Updated**
  - New features documented
  - Performance metrics included
  - Installation steps current

- [ ] **Environment Template**
  ```bash
  # Verify .env.template exists:
  ls backend/.env.template
  ```

- [ ] **Deployment Guides Present**
  - PRODUCTION_ENHANCEMENTS_SUMMARY.md
  - IMPLEMENTATION_COMPLETE.md
  - GITHUB_CLEANUP_AND_DEPLOY.md

## 🔍 Final Verification Commands

Run these commands in order:

```bash
# 1. Check what you're committing
git diff --staged --name-only

# 2. Verify no secrets in staged files
git diff --staged | grep -E "(secret|SECRET|key|KEY|password|PASSWORD)" | grep -v "api_key_manager"

# 3. Check file sizes (nothing huge)
git diff --staged --stat

# 4. Verify critical files are included
git diff --staged --name-only | grep -E "(semantic_cache|redis_job_queue|batch\.py|telemetry|security)"
```

## 🚦 Ready to Deploy?

If all checks pass:

1. **Run the deployment script**:
   ```bash
   # Windows:
   deploy_to_github.bat

   # Linux/Mac:
   bash deploy_to_github.sh
   ```

2. **Or manually**:
   ```bash
   git add .
   git commit -m "feat: Production enhancements with 3x performance"
   git push origin main
   ```

## ⚠️ If You Find Issues

### API Keys in committed files:
```bash
# Remove from staging:
git reset HEAD <file>
# Remove sensitive data from file
# Re-add file:
git add <file>
```

### Wrong files staged:
```bash
# Unstage everything:
git reset HEAD
# Add files selectively:
git add backend/
git add frontend/
git add *.md
git add docker-compose.yml
```

### Need to abort:
```bash
# Reset everything:
git reset --hard HEAD
# Start over with deployment script
```

## 📊 Success Metrics

After successful deployment, verify on GitHub:

- [ ] No .env files visible
- [ ] No API keys in code
- [ ] All enhancement files present
- [ ] Clean commit message
- [ ] No error in Actions (if configured)

## 🎉 Post-Deployment

After pushing to GitHub:

1. **Check GitHub repository**
   - Verify files are correctly uploaded
   - Check no sensitive data is exposed

2. **Create a Release**
   ```bash
   git tag -a v2.0.0 -m "Production enhancements release"
   git push --tags
   ```

3. **Update GitHub Settings**
   - Add repository description
   - Add topics: `nda`, `document-processing`, `ai`, `fastapi`, `nextjs`
   - Configure GitHub Pages if needed

---

**Remember**: It's better to be cautious. Double-check everything before pushing!
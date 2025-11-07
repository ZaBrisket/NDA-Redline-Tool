#!/bin/bash

# OpenAI Cleanup Script
# Removes all OpenAI/GPT references from the codebase

echo "==================================="
echo "OpenAI/GPT Complete Removal Script"
echo "==================================="
echo ""

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Create backup
echo -e "${YELLOW}Creating backup...${NC}"
BACKUP_FILE="backup_before_cleanup_$(date +%Y%m%d_%H%M%S).tar.gz"
tar -czf "$BACKUP_FILE" backend/ 2>/dev/null
if [ $? -eq 0 ]; then
    echo -e "${GREEN}Backup created: $BACKUP_FILE${NC}"
else
    echo -e "${RED}Warning: Backup creation failed${NC}"
fi

# Find and report OpenAI imports
echo -e "\n${YELLOW}Scanning for OpenAI imports...${NC}"
OPENAI_FILES=$(grep -r "from openai\|import openai\|OpenAI" backend/app --include="*.py" -l 2>/dev/null || true)

if [ -z "$OPENAI_FILES" ]; then
    echo -e "${GREEN}No OpenAI imports found in backend/app${NC}"
else
    echo -e "${RED}Found OpenAI imports in:${NC}"
    echo "$OPENAI_FILES"

    # Remove OpenAI imports
    for file in $OPENAI_FILES; do
        echo "Cleaning $file..."
        sed -i.bak '/^from openai/d' "$file"
        sed -i.bak '/^import openai/d' "$file"
        sed -i.bak '/OpenAI(/d' "$file"
        rm -f "${file}.bak"
    done
fi

# Find and report GPT references
echo -e "\n${YELLOW}Scanning for GPT references...${NC}"
GPT_FILES=$(grep -r "gpt-4\|gpt-5\|GPT-4\|GPT-5\|gpt4\|gpt5" backend/app --include="*.py" -l 2>/dev/null || true)

if [ -z "$GPT_FILES" ]; then
    echo -e "${GREEN}No GPT references found in backend/app${NC}"
else
    echo -e "${RED}Found GPT references in:${NC}"
    echo "$GPT_FILES"

    # Replace GPT references
    for file in $GPT_FILES; do
        echo "Updating $file..."
        sed -i.bak 's/gpt-4[^ "'\'')]*/claude-3-opus-20240229/g' "$file"
        sed -i.bak 's/gpt-5[^ "'\'')]*/claude-3-opus-20240229/g' "$file"
        sed -i.bak 's/GPT-4/Claude Opus/g' "$file"
        sed -i.bak 's/GPT-5/Claude Opus/g' "$file"
        rm -f "${file}.bak"
    done
fi

# Clean environment files (only remove active OPENAI_API_KEY, not comments)
echo -e "\n${YELLOW}Cleaning environment files...${NC}"
for env_file in backend/.env backend/.env.local; do
    if [ -f "$env_file" ]; then
        echo "Cleaning $env_file..."
        # Only remove uncommented OPENAI_API_KEY lines
        sed -i.bak '/^OPENAI_API_KEY/d' "$env_file"
        sed -i.bak '/^USE_OPENAI/d' "$env_file"
        rm -f "${env_file}.bak"
    fi
done

# Note: .env.example is not cleaned as it may have migration notes

# Remove OpenAI from requirements (if not already done)
echo -e "\n${YELLOW}Checking requirements.txt...${NC}"
if [ -f "backend/requirements.txt" ]; then
    if grep -q "^openai" backend/requirements.txt; then
        echo "Removing OpenAI from requirements.txt..."
        sed -i.bak '/^openai/d' backend/requirements.txt
        rm -f backend/requirements.txt.bak
        echo -e "${GREEN}Removed OpenAI from requirements${NC}"
    else
        echo -e "${GREEN}OpenAI already removed from requirements${NC}"
    fi
fi

# Final verification
echo -e "\n${YELLOW}Running final verification...${NC}"
REMAINING_OPENAI=$(grep -r "from openai\|import openai" backend/app --include="*.py" 2>/dev/null | wc -l)
REMAINING_GPT=$(grep -r "gpt-[45]\|GPT-[45]" backend/app --include="*.py" 2>/dev/null | wc -l)

echo ""
echo "====== VERIFICATION RESULTS ======"
echo "OpenAI import lines found: $REMAINING_OPENAI"
echo "GPT-4/5 references found: $REMAINING_GPT"
echo ""

if [ "$REMAINING_OPENAI" -eq 0 ] && [ "$REMAINING_GPT" -eq 0 ]; then
    echo -e "${GREEN}✅ CLEANUP SUCCESSFUL!${NC}"
    echo -e "${GREEN}All OpenAI and GPT references have been removed from backend/app.${NC}"
    echo ""
    echo "Next steps:"
    echo "1. Review the changes"
    echo "2. Run tests: cd backend && pytest tests/test_anthropic_migration.py"
    echo "3. Verify the application starts: uvicorn app.main:app"
else
    echo -e "${YELLOW}⚠️  WARNING: Some references may remain${NC}"
    echo "Please review the following files manually:"
    if [ "$REMAINING_OPENAI" -gt 0 ]; then
        grep -r "from openai\|import openai" backend/app --include="*.py" -l 2>/dev/null
    fi
    if [ "$REMAINING_GPT" -gt 0 ]; then
        grep -r "gpt-[45]\|GPT-[45]" backend/app --include="*.py" -l 2>/dev/null
    fi
fi

echo ""
echo -e "${GREEN}Cleanup complete!${NC}"
echo "Backup saved to: $BACKUP_FILE"

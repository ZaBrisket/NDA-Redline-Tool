#!/bin/bash
# Test runner script for NDA Redline Tool backend
# Usage: ./run_tests.sh [options]

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
COVERAGE_THRESHOLD=70
PYTHONPATH="$(pwd):$PYTHONPATH"
export PYTHONPATH

# Print header
echo -e "${BLUE}============================================${NC}"
echo -e "${BLUE}   NDA Redline Tool - Test Suite Runner   ${NC}"
echo -e "${BLUE}============================================${NC}"
echo ""

# Check if pytest is installed
if ! command -v pytest &> /dev/null; then
    echo -e "${RED}ERROR: pytest is not installed${NC}"
    echo "Install with: pip install pytest pytest-asyncio pytest-cov httpx"
    exit 1
fi

# Create .env if it doesn't exist
if [ ! -f .env ]; then
    echo -e "${YELLOW}Creating .env from .env.example...${NC}"
    cp .env.example .env
    echo "OPENAI_API_KEY=sk-test-fake-key" >> .env
    echo "ANTHROPIC_API_KEY=sk-ant-test-fake-key" >> .env
    echo "ENVIRONMENT=test" >> .env
fi

# Parse command line arguments
MODE="all"
VERBOSE="-v"
COVERAGE=true

while [[ $# -gt 0 ]]; do
    case $1 in
        --fast)
            MODE="fast"
            shift
            ;;
        --unit)
            MODE="unit"
            shift
            ;;
        --integration)
            MODE="integration"
            shift
            ;;
        --smoke)
            MODE="smoke"
            shift
            ;;
        --no-coverage)
            COVERAGE=false
            shift
            ;;
        --quiet)
            VERBOSE=""
            shift
            ;;
        --help)
            echo "Usage: $0 [options]"
            echo ""
            echo "Options:"
            echo "  --fast          Run only fast unit tests"
            echo "  --unit          Run all unit tests"
            echo "  --integration   Run integration tests"
            echo "  --smoke         Run smoke tests only"
            echo "  --no-coverage   Skip coverage reporting"
            echo "  --quiet         Minimize output"
            echo "  --help          Show this help message"
            echo ""
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Run tests based on mode
echo -e "${GREEN}Running tests in '$MODE' mode...${NC}"
echo ""

case $MODE in
    fast)
        echo -e "${BLUE}Running fast unit tests...${NC}"
        pytest tests/unit $VERBOSE -m "fast" --tb=short
        ;;
    unit)
        echo -e "${BLUE}Running all unit tests...${NC}"
        if [ "$COVERAGE" = true ]; then
            pytest tests/unit $VERBOSE --cov=backend/app --cov-report=term-missing --cov-report=html --tb=short
        else
            pytest tests/unit $VERBOSE --tb=short
        fi
        ;;
    integration)
        echo -e "${BLUE}Running integration tests...${NC}"
        if [ "$COVERAGE" = true ]; then
            pytest tests/integration $VERBOSE --cov=backend/app --cov-report=term-missing --cov-report=html --tb=short
        else
            pytest tests/integration $VERBOSE --tb=short
        fi
        ;;
    smoke)
        echo -e "${BLUE}Running smoke tests...${NC}"
        pytest tests/ $VERBOSE -m "smoke" --tb=short
        ;;
    all)
        echo -e "${BLUE}Running all tests...${NC}"
        if [ "$COVERAGE" = true ]; then
            pytest tests/ $VERBOSE --cov=backend/app --cov-report=term-missing --cov-report=html --cov-report=xml --cov-fail-under=$COVERAGE_THRESHOLD --tb=short
        else
            pytest tests/ $VERBOSE --tb=short
        fi
        ;;
esac

# Check exit code
TEST_EXIT_CODE=$?

echo ""
if [ $TEST_EXIT_CODE -eq 0 ]; then
    echo -e "${GREEN}============================================${NC}"
    echo -e "${GREEN}   ✓ All tests passed!${NC}"
    echo -e "${GREEN}============================================${NC}"

    if [ "$COVERAGE" = true ] && [ "$MODE" != "smoke" ] && [ "$MODE" != "fast" ]; then
        echo ""
        echo -e "${BLUE}Coverage report generated in: htmlcov/index.html${NC}"
    fi
else
    echo -e "${RED}============================================${NC}"
    echo -e "${RED}   ✗ Some tests failed${NC}"
    echo -e "${RED}============================================${NC}"
fi

echo ""
exit $TEST_EXIT_CODE

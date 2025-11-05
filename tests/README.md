# NDA Redline Tool - Test Suite Documentation

## Overview

Comprehensive test suite for the NDA Redline Tool backend, featuring unit tests, integration tests, and CI/CD automation for Railway deployment.

**Test Coverage Target:** ≥70%

---

## 📁 Test Structure

```
tests/
├── conftest.py                 # Shared fixtures and pytest configuration
├── unit/                       # Unit tests for individual components
│   ├── test_rule_engine.py     # Rule engine pattern matching tests
│   └── test_file_validator.py  # File validation and security tests
├── integration/                # Integration tests for API endpoints
│   └── test_api_endpoints.py   # Full API request/response tests
└── fixtures/                   # Test data and mock objects
```

---

## 🚀 Quick Start

### Prerequisites

```bash
# Install test dependencies
pip install pytest pytest-asyncio pytest-cov httpx

# Or install all project dependencies
pip install -r requirements.txt
```

### Running Tests

**Option 1: Using the test runner script (recommended)**

```bash
# Run all tests with coverage
./run_tests.sh

# Run only fast unit tests
./run_tests.sh --fast

# Run unit tests
./run_tests.sh --unit

# Run integration tests
./run_tests.sh --integration

# Run smoke tests
./run_tests.sh --smoke

# Run without coverage (faster)
./run_tests.sh --no-coverage
```

**Option 2: Using pytest directly**

```bash
# Run all tests
pytest tests/

# Run with coverage
pytest tests/ --cov=backend/app --cov-report=html --cov-report=term-missing

# Run specific test file
pytest tests/unit/test_rule_engine.py -v

# Run specific test class
pytest tests/unit/test_rule_engine.py::TestRuleEngine -v

# Run specific test
pytest tests/unit/test_rule_engine.py::TestRuleEngine::test_pattern_compilation -v

# Run tests by marker
pytest tests/ -m "fast" -v      # Only fast tests
pytest tests/ -m "unit" -v      # Only unit tests
pytest tests/ -m "integration" -v  # Only integration tests
pytest tests/ -m "smoke" -v     # Only smoke tests
```

---

## 🏷️ Test Markers

Tests are organized using pytest markers:

| Marker | Description | Usage |
|--------|-------------|-------|
| `@pytest.mark.unit` | Unit tests for individual functions | `pytest -m unit` |
| `@pytest.mark.integration` | Integration tests for full workflows | `pytest -m integration` |
| `@pytest.mark.fast` | Quick tests (<1s each) | `pytest -m fast` |
| `@pytest.mark.slow` | Slower tests (>5s each) | `pytest -m slow` |
| `@pytest.mark.smoke` | Critical functionality smoke tests | `pytest -m smoke` |
| `@pytest.mark.requires_api_keys` | Tests needing real API keys | `pytest -m "not requires_api_keys"` |
| `@pytest.mark.requires_redis` | Tests needing Redis connection | `pytest -m "not requires_redis"` |

**Example: Run only fast unit tests**
```bash
pytest tests/ -m "unit and fast" -v
```

**Example: Skip tests requiring external services**
```bash
pytest tests/ -m "not requires_api_keys and not requires_redis" -v
```

---

## 🧪 Test Types

### Unit Tests

Test individual components in isolation with mocked dependencies.

**Coverage:**
- Rule engine pattern matching
- File validation logic
- Security middleware
- Confidence scoring
- Text parsing utilities

**Example:**
```python
@pytest.mark.unit
@pytest.mark.fast
def test_pattern_compilation(sample_rules):
    """Test that regex patterns compile without errors"""
    for rule in sample_rules:
        pattern = rule['pattern']
        compiled = re.compile(pattern)
        assert compiled is not None
```

### Integration Tests

Test API endpoints with full request/response cycles.

**Coverage:**
- Health check endpoints
- Document upload
- Job status tracking
- Decision submission
- Document download
- Error handling

**Example:**
```python
@pytest.mark.integration
def test_upload_valid_docx(test_client, sample_docx_file):
    """Test uploading a valid DOCX file"""
    with open(sample_docx_file, 'rb') as f:
        files = {'file': ('test.docx', f, 'application/vnd.openxmlformats-officedocument.wordprocessingml.document')}
        response = test_client.post("/api/upload", files=files)
    assert response.status_code == 200
```

### Smoke Tests

Quick tests of critical functionality to ensure basic operations work.

**Example:**
```python
@pytest.mark.smoke
def test_health_check(test_client):
    """Test that server is responding"""
    response = test_client.get("/")
    assert response.status_code == 200
```

---

## 🔧 Fixtures

Common fixtures are defined in `conftest.py`:

### Test Clients
```python
test_client          # Synchronous FastAPI TestClient
async_test_client    # Asynchronous HTTPX client
```

### Mock LLM Clients
```python
mock_openai_client      # Mocked OpenAI GPT-5 client
mock_anthropic_client   # Mocked Anthropic Claude client
mock_llm_orchestrator   # Full LLM orchestrator mock
```

### Test Data
```python
sample_nda_text      # Sample NDA text string
sample_docx_file     # Temporary .docx file
sample_violation     # Sample violation object
sample_redlines      # List of sample redlines
sample_rules         # Sample validation rules
```

### Utilities
```python
temp_storage         # Temporary storage directory structure
test_env            # Test environment variables
mock_job_queue      # Mocked job queue
assert_logs         # Helper for checking log messages
```

---

## 📊 Coverage Reports

### Generating Coverage Reports

```bash
# Generate HTML, XML, and terminal coverage reports
pytest tests/ --cov=backend/app --cov-report=html --cov-report=xml --cov-report=term-missing

# View HTML report
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
start htmlcov/index.html  # Windows
```

### Coverage Configuration

Coverage settings are in `pytest.ini`:

```ini
[coverage:run]
source = backend/app
omit =
    */tests/*
    */test_*.py
    */__pycache__/*

[coverage:report]
precision = 2
show_missing = True
fail_under = 70
```

### Checking Coverage Threshold

```bash
# Fail if coverage is below 70%
pytest tests/ --cov=backend/app --cov-fail-under=70
```

---

## 🔄 CI/CD Integration

### GitHub Actions

Tests run automatically on:
- Push to `main`, `develop`, or `claude/**` branches
- Pull requests to `main` or `develop`
- Changes to backend code, tests, or requirements

**Workflow:** `.github/workflows/backend-tests.yml`

**Jobs:**
1. **test** - Run full test suite with coverage (Python 3.10 & 3.11)
2. **smoke-test** - Quick smoke tests for critical functionality
3. **lint** - Code quality checks (Black, isort, flake8)
4. **security** - Security scanning (Bandit, Safety)

### Railway Deployment

**Test Configuration:** `railway.test.json`

```json
{
  "deploy": {
    "startCommand": "pytest tests/ -v --tb=short"
  }
}
```

To run tests on Railway before deployment:

```bash
railway run pytest tests/ -v
```

---

## 🛠️ Writing New Tests

### Test Template

```python
import pytest
from unittest.mock import Mock, patch

@pytest.mark.unit
@pytest.mark.fast
class TestYourComponent:
    """Test suite for YourComponent"""

    def test_your_functionality(self, test_client):
        """Test description"""
        # Arrange
        expected_result = "value"

        # Act
        result = your_function()

        # Assert
        assert result == expected_result
```

### Best Practices

1. **Use descriptive test names**
   - ✅ `test_upload_rejects_oversized_files`
   - ❌ `test_upload_3`

2. **Follow Arrange-Act-Assert pattern**
   ```python
   # Arrange - Set up test data
   # Act - Execute the code being tested
   # Assert - Verify the results
   ```

3. **Use appropriate markers**
   ```python
   @pytest.mark.unit  # or integration
   @pytest.mark.fast  # if test runs quickly
   ```

4. **Mock external dependencies**
   ```python
   @patch('backend.app.core.llm_orchestrator.OpenAI')
   def test_with_mock(mock_openai):
       # Test code
   ```

5. **Use fixtures for common setup**
   ```python
   def test_something(test_client, sample_docx_file):
       # test_client and sample_docx_file are provided by fixtures
   ```

6. **Test both success and failure cases**
   ```python
   def test_valid_input_succeeds(self):
       # Test happy path

   def test_invalid_input_raises_error(self):
       # Test error handling
   ```

---

## 📝 Configuration Files

### pytest.ini

Main pytest configuration:
- Test discovery patterns
- Coverage settings
- Output options
- Marker definitions

### conftest.py

Shared fixtures and configuration:
- FastAPI test clients
- Mock LLM clients
- Test data generators
- Helper functions

---

## 🚨 Troubleshooting

### Tests failing with "No module named 'backend'"

**Solution:** Ensure you're running from project root:
```bash
cd /path/to/NDA-Redline-Tool
pytest tests/
```

### Missing API key errors

**Solution:** Create `.env` with test keys:
```bash
cp .env.example .env
echo "OPENAI_API_KEY=sk-test-fake-key" >> .env
echo "ANTHROPIC_API_KEY=sk-ant-test-fake-key" >> .env
```

### Import errors in tests

**Solution:** Install all test dependencies:
```bash
pip install pytest pytest-asyncio pytest-cov httpx
```

### Coverage not generated

**Solution:** Ensure pytest-cov is installed:
```bash
pip install pytest-cov
```

### Tests hang or timeout

**Solution:** Use `--timeout` flag:
```bash
pytest tests/ --timeout=60
```

---

## 📈 Test Metrics

### Current Status

- **Total Tests:** 50+ tests
- **Coverage Target:** ≥70%
- **Test Categories:**
  - Unit tests: ~30 tests
  - Integration tests: ~20 tests
  - Smoke tests: ~5 tests

### Performance Targets

- Fast tests: <1 second each
- Unit test suite: <10 seconds total
- Integration test suite: <30 seconds total
- Full test suite: <1 minute total

---

## 🔗 Related Documentation

- [Main README](../README.md)
- [Deployment Guide](../DEPLOYMENT.md)
- [Contributing Guide](../CONTRIBUTING.md)
- [API Documentation](../API_DOCS.md)

---

## 📧 Support

For questions about testing:
1. Check this documentation
2. Review example tests in `tests/unit/` and `tests/integration/`
3. Open an issue on GitHub

---

**Last Updated:** 2025-11-05
**Test Suite Version:** 1.0.0

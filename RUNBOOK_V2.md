# NDA Reviewer v2 - Quick Start Runbook

## 🚀 Quick Start

### 1. Setup Environment

```bash
# Install dependencies
pip install pydantic anthropic openai pyyaml

# Configure API keys
cp .env.example .env
# Edit .env and add your OPENAI_API_KEY and ANTHROPIC_API_KEY
```

### 2. Test Rules Engine (No API needed)

```bash
# Test deterministic rules only
python -c "
from backend.app.core.rule_engine_v2 import RuleEngineV2
from backend.app.core.strictness_controller import EnforcementLevel

# Test with sample text
text = 'The obligations shall survive in perpetuity and continue indefinitely.'

# Test each enforcement level
for level in [EnforcementLevel.BLOODY, EnforcementLevel.BALANCED, EnforcementLevel.LENIENT]:
    engine = RuleEngineV2(enforcement_level=level)
    violations = engine.apply_rules(text)
    print(f'{level.value}: Found {len(violations)} violations')
"
```

### 3. Run Enforcement Mode Tests

```bash
# Run full test suite (uses mock mode if no API keys)
python test_enforcement_modes.py

# Expected output:
# ============================================================
# NDA REVIEWER - ENFORCEMENT MODE TEST SUITE
# ============================================================
# Testing Bloody Mode...
# Testing Balanced Mode...
# Testing Lenient Mode...
```

### 4. Test Individual Components

#### Test Strictness Controller
```python
from backend.app.core.strictness_controller import StrictnessController, EnforcementLevel

# Test filtering
controller = StrictnessController(EnforcementLevel.BALANCED)

# Should flag: True (moderate is included in Balanced)
print(controller.should_flag('moderate'))

# Should flag: False (advisory only in Bloody)
print(controller.should_flag('advisory'))
```

#### Test Rules Loading
```python
from backend.app.core.rule_engine_v2 import RuleEngineV2

engine = RuleEngineV2()
stats = engine.get_statistics()
print(f"Loaded {stats['active_rules']} active rules")
print(f"Total rules available: {stats['total_rules']}")
```

## 📊 Validation Checklist

### Rule Coverage
- [ ] Test perpetual terms (critical) - all modes flag
- [ ] Test 3-year terms (moderate) - Bloody/Balanced flag
- [ ] Test best efforts (low) - only Bloody flags
- [ ] Test indemnification (critical) - all modes flag
- [ ] Test formatting issues (advisory) - only Bloody flags

### Pass Execution
- [ ] Pass 0 runs for all modes
- [ ] Pass 1 skipped when rule confidence high
- [ ] Pass 2 validates all violations
- [ ] Pass 3 routes critical disagreements
- [ ] Pass 4 skipped in Lenient mode

### Expected Results by Mode

| Test Case | Bloody | Balanced | Lenient |
|-----------|--------|----------|---------|
| Perpetual term | ✓ Flag | ✓ Flag | ✓ Flag |
| 3-year term | ✓ Flag | ✓ Flag | ✗ Ignore |
| Best efforts | ✓ Flag | ✗ Ignore | ✗ Ignore |
| Indemnification | ✓ Flag | ✓ Flag | ✓ Flag |
| No carveout | ✓ Flag | ✓ Flag | ✗ Ignore |
| CAPS formatting | ✓ Flag | ✗ Ignore | ✗ Ignore |

## 🔍 Debugging

### Check Rule Loading
```bash
python -c "
import yaml
with open('backend/app/models/rules_v2.yaml') as f:
    rules = yaml.safe_load(f)
    print(f'Total rules: {len(rules[\"rules\"])}')

    # Count by severity
    severities = {}
    for rule in rules['rules']:
        sev = rule.get('severity', 'unknown')
        severities[sev] = severities.get(sev, 0) + 1

    for sev, count in severities.items():
        print(f'{sev}: {count} rules')
"
```

### Test Pattern Matching
```python
import re

# Test a specific pattern
pattern = r'\b(perpetual|indefinite|unlimited|no\s+expir)\b'
test_texts = [
    "obligations continue in perpetuity",
    "shall survive indefinitely",
    "for a period of two years",
    "no expiration date"
]

compiled = re.compile(pattern, re.IGNORECASE)
for text in test_texts:
    if compiled.search(text):
        print(f"✓ Matched: {text}")
    else:
        print(f"✗ No match: {text}")
```

## 🎯 Success Criteria

### Minimum Viable Testing
1. ✓ Rules load without errors
2. ✓ Each enforcement level returns different violation counts
3. ✓ Critical violations flagged in all modes
4. ✓ Advisory violations only in Bloody mode
5. ✓ Test suite runs without crashes

### Full Validation
1. F1 Score ≥0.98 on test corpus
2. Zero banned token escapes
3. Consensus score ≥90% on validated items
4. Processing time <20s per document
5. Cache hit rate ≥70% after 10 similar docs

## 🚨 Common Issues

### Issue: "No module named 'backend'"
**Fix**: Run from project root directory

### Issue: "API key not found"
**Fix**: Set environment variables or update .env file

### Issue: "Rules file not found"
**Fix**: Ensure rules_v2.yaml exists at `backend/app/models/rules_v2.yaml`

### Issue: Test failing for specific severity
**Fix**: Check enforcement level filtering in rules_v2.yaml

## 📈 Performance Testing

```bash
# Time rule processing
python -c "
import time
from backend.app.core.rule_engine_v2 import RuleEngineV2

text = open('sample_nda.txt').read() if os.path.exists('sample_nda.txt') else 'Sample text' * 1000

engine = RuleEngineV2()
start = time.time()
violations = engine.apply_rules(text)
elapsed = time.time() - start

print(f'Processed in {elapsed:.2f}s')
print(f'Found {len(violations)} violations')
print(f'Rate: {len(text)/elapsed:.0f} chars/sec')
"
```

## 🎉 Ready for Production?

If all tests pass:
1. ✅ Rules engine processes text correctly
2. ✅ Enforcement levels filter appropriately
3. ✅ Test suite shows expected results
4. ✅ Performance meets requirements

Then you're ready to:
- Integrate with API endpoints
- Connect frontend
- Deploy to production
- Start processing real NDAs!

---

**Support**: Check IMPLEMENTATION_SUMMARY_V2.md for detailed documentation
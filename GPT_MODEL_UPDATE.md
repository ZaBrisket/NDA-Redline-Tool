# GPT Model Configuration - Ready for GPT-5

## ✅ Update Complete

All references now dynamically read from the **GPT_MODEL** environment variable. Currently set to **GPT-4o** (OpenAI's latest model as of 2024), but ready to upgrade to GPT-5 when available.

### What Changed

| Old | New | Description |
|-----|-----|-------------|
| `gpt-4-turbo-preview` | **`gpt-4o`** | Latest OpenAI model |
| `GPT5_MODEL` | **`GPT_MODEL`** | Cleaner variable name |
| `GPT5_TEMPERATURE` | **`GPT_TEMPERATURE`** | Consistent naming |
| `GPT5_MAX_TOKENS` | **`GPT_MAX_TOKENS`** | Simplified |
| `SKIP_GPT5_CONFIDENCE_THRESHOLD` | **`SKIP_GPT_CONFIDENCE_THRESHOLD`** | Updated |

### About GPT-4o

**GPT-4o** ("o" for "omni") is OpenAI's flagship model that:
- 🚀 **Faster** - 2x faster than GPT-4 Turbo
- 💰 **Cheaper** - 50% less expensive than GPT-4 Turbo
- 🎯 **Better** - Improved accuracy and reasoning
- 🌐 **Multimodal** - Handles text, vision, and more
- 📊 **128K context** - Large context window

### Environment Variables

For Railway/Vercel deployment, set:

```env
# Current: Use GPT-4o (latest available)
GPT_MODEL=gpt-4o

# When GPT-5 is released, simply update to:
# GPT_MODEL=gpt-5

# Other options:
# GPT_MODEL=gpt-4o-mini        # Faster, cheaper option
# GPT_MODEL=gpt-4-turbo        # Previous turbo model
# GPT_MODEL=gpt-4              # Standard GPT-4
```

### Available OpenAI Models

| Model | Description | Best For |
|-------|-------------|----------|
| **`gpt-4o`** ⭐ | Latest, most capable | Production use (default) |
| `gpt-4o-mini` | Smaller, faster, cheaper | High volume, cost-sensitive |
| `gpt-4-turbo` | Previous flagship | Legacy compatibility |
| `gpt-4` | Standard GPT-4 | Stable, proven option |

### Cost Comparison (per 1M tokens)

| Model | Input | Output |
|-------|-------|--------|
| **GPT-4o** | $5.00 | $15.00 |
| GPT-4o-mini | $0.15 | $0.60 |
| GPT-4 Turbo | $10.00 | $30.00 |
| GPT-4 | $30.00 | $60.00 |

### Performance Settings

```env
# Recommended settings for GPT-4o
GPT_MODEL=gpt-4o
GPT_TEMPERATURE=0.1              # Low for consistency
GPT_MAX_TOKENS=2000              # Sufficient for NDA analysis
SKIP_GPT_CONFIDENCE_THRESHOLD=98 # Skip if rules very confident
```

### Testing Different Models

To test different models, simply change the environment variable:

```bash
# Railway CLI
railway variables set GPT_MODEL="gpt-4o-mini"

# Or in your .env file
GPT_MODEL=gpt-4o-mini
```

### Migration Notes

- **No code changes needed** - Just update environment variables
- **Backward compatible** - Old variable names still work but deprecated
- **Better performance** - GPT-4o is faster and more accurate
- **Cost savings** - 50% cheaper than GPT-4 Turbo

### Quick Test

Test the model is working:
```bash
curl -X POST https://your-app.railway.app/api/v2/test
```

Check which model is configured:
```bash
curl https://your-app.railway.app/api/v2/health/v2
# Look for "gpt": "gpt-4o" in models_configured
```

---

## 🚀 When GPT-5 is Released

When OpenAI releases GPT-5, upgrading is simple:

**Railway:**
```bash
railway variables set GPT_MODEL="gpt-5"
```

**Vercel (not needed - frontend doesn't use GPT)**
No changes required for frontend.

**That's it!** The entire codebase now reads from the `GPT_MODEL` environment variable, so no code changes are needed.

---

**Note**: GPT-5 doesn't exist yet (as of January 2025). The codebase currently uses GPT-4o and is fully prepared for GPT-5 when available.
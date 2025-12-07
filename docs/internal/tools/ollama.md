# Ollama Cloud Integration

## Overview
Ollama Cloud provides access to powerful open-source language models via a simple API. We use it as an alternative to OpenAI for LLM-powered features in the Scout and Builder agents.

## Setup

### 1. Get API Key
1. Visit [ollama.com/settings/keys](https://ollama.com/settings/keys)
2. Generate a new API key
3. Add it to your `.env` file:
```bash
OLLAMA_API_KEY=your-key-here
```

### 2. Configuration
The `LLMClient` (`src/core/llm.py`) automatically detects Ollama when `OLLAMA_API_KEY` is present.

You can also explicitly set the provider:
```bash
LLM_PROVIDER=ollama  # or "openai" to force OpenAI
LLM_MODEL=gpt-oss:120b  # Default Ollama model
```

## Available Models
Ollama Cloud supports various models. Check the latest list at:
```bash
curl https://ollama.com/api/tags
```

Common models:
- `gpt-oss:120b` - Large open-source GPT model
- `llama3.1:70b` - Meta's Llama 3.1
- `qwen2.5:72b` - Alibaba's Qwen model

## Usage

### Automatic Detection
The `LLMClient` automatically uses Ollama when the API key is present:

```python
from src.core.llm import LLMClient

client = LLMClient()  # Auto-detects Ollama
response = client.chat_completion([
    {"role": "user", "content": "Hello!"}
])
```

### Explicit Configuration
```python
client = LLMClient(
    api_key="your-ollama-key",
    base_url="https://ollama.com",
    model="gpt-oss:120b"
)
```

## Authentication
Ollama Cloud uses Bearer token authentication:
```python
from ollama import Client

client = Client(
    host="https://ollama.com",
    headers={'Authorization': 'Bearer YOUR_API_KEY'}
)
```

Our `LLMClient` handles this automatically.

## JSON Mode
Ollama doesn't have native JSON mode like OpenAI. Our implementation appends a prompt instruction when `json_mode=True`:

```python
response = client.chat_completion(
    messages=[...],
    json_mode=True  # Adds "Please respond with valid JSON only."
)
```

## Cost & Rate Limits
- Check your usage at [ollama.com/settings](https://ollama.com/settings)
- Rate limits vary by plan
- Open-source models are generally cheaper than proprietary alternatives

## Switching Between Providers
To switch between Ollama and OpenAI:

**Use Ollama:**
```bash
# .env
OLLAMA_API_KEY=your-key
# LLM_PROVIDER=auto (default, will use Ollama)
```

**Use OpenAI:**
```bash
# .env
LLM_API_KEY=sk-your-openai-key
LLM_PROVIDER=openai  # Force OpenAI even if OLLAMA_API_KEY exists
```

## Troubleshooting

### "No API key found for provider 'ollama'"
- Ensure `OLLAMA_API_KEY` is set in `.env`
- Verify `.env` is being loaded (check `src/main.py`)

### "ollama library not installed"
```bash
pip install ollama
```

### Model not found
- Check available models: `curl https://ollama.com/api/tags`
- Update `LLM_MODEL` in `.env`

## Performance Notes
- Ollama Cloud models may have different response times than OpenAI
- For production, consider testing both providers and choosing based on:
  - Cost
  - Latency
  - Output quality
  - Rate limits

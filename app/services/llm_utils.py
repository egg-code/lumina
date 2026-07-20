import os
import re
import json
import logging
import httpx
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")

# MODELS = [
#     "openrouter/free",              # auto-router, picks an available free model
#     "deepseek/deepseek-v3:free",
#     "qwen/qwen3-coder:free",
#     "meta-llama/llama-3.3-70b-instruct:free",

#     "nousresearch/hermes-3-llama-3.1-405b:free",
#     "google/gemma-4-31b-it:free",
#     "nvidia/nemotron-3-ultra-550b-a55b:free",
#     "openai/gpt-4o-mini:free"

    
# ]

MODELS = [
    "llama-3.3-70b-versatile",
    "llama-3.1-8b-instant",
    "mixtral-8x7b-32768",
    "gemma2-9b-it",
]

async def _groq_post(model: str, system: str, prompt: str, timeout: float = 60.0, max_tokens: int = 2000) -> str:
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": prompt}
        ],
        "response_format": {"type": "json_object"},
        "max_tokens": max_tokens
    }
    async with httpx.AsyncClient(timeout=httpx.Timeout(connect=5.0, read=timeout, write=5.0, pool=5.0)) as client:
        response = await client.post(url, headers=headers, json=payload, timeout=timeout)
        response.raise_for_status()
        data = response.json()
        content = data["choices"][0]["message"]["content"]

        content = content.strip()
        if content.startswith("```json"):
            content = content[7:-3].strip()
        elif content.startswith("```"):
            content = content[3:-3].strip()

        return content

def _safe_json_parse(text: str) -> dict:
    """Strip markdown fences; attempt JSON parse; fall back to regex block extraction."""
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r'^```(?:json)?\s*', '', text)
        text = re.sub(r'\s*```$', '', text)
        text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass
        raise

async def call_llm(prompt: str, system: str, timeout: float = 60.0, max_tokens: int = 2000) -> dict:
    if not GROQ_API_KEY:
        raise ValueError("GROQ_API_KEY not set")

    for model in MODELS:
        try:
            logger.info(f"Calling Groq API with model {model}...")
            response_text = await _groq_post(model, system, prompt, timeout=timeout, max_tokens=max_tokens)
            return _safe_json_parse(response_text)
        except httpx.ReadTimeout:
            logger.warning(f"[LLM] {model} timed out after {timeout}s. Trying next.")
        except httpx.HTTPStatusError as e:
            logger.warning(f"[LLM] {model} returned HTTP {e.response.status_code}. Trying next.")
        except (json.JSONDecodeError, ValueError) as e:
            logger.warning(f"[LLM] {model} returned unparseable JSON: {e}. Trying next.")
        except Exception as e:
            logger.warning(f"[LLM] {model} failed ({type(e).__name__}): {e}. Trying next.")
    raise RuntimeError("All LLM models failed")

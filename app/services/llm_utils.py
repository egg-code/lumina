import os
import json
import logging
import httpx
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")

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
    "openai/gpt-4o-mini",            # put the reliable paid one first
    "deepseek/deepseek-v3:free"     # one free fallback is enough

    #  "openrouter/free",              # auto-router, picks an available free model
    #  "deepseek/deepseek-v3:free",
    #  "qwen/qwen3-coder:free",
    #  "meta-llama/llama-3.3-70b-instruct:free",
    #  "nousresearch/hermes-3-llama-3.1-405b:free",
    #  "openai/gpt-4o-mini",           # cheap paid fallback, not free — remove if you don't want any spend
]

async def _openrouter_post(model: str, system: str, prompt: str, timeout: float = 60.0) -> str:
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "http://localhost:8000",
        "X-Title": "Lumina Career Navigator"
    }
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": prompt}
        ],
        "response_format": {"type": "json_object"}
    }
    
    async with httpx.AsyncClient() as client:
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

async def call_llm(prompt: str, system: str, timeout: float = 60.0) -> dict:
    if not OPENROUTER_API_KEY:
        raise ValueError("OPENROUTER_API_KEY not set")
        
    for model in MODELS:
        try:
            logger.info(f"Calling OpenRouter with model {model}...")
            response_text = await _openrouter_post(model, system, prompt, timeout=timeout)
            return json.loads(response_text)
        except Exception as e:
            logger.warning(f"Model {model} failed: {e}. Trying next.")
    raise RuntimeError("All LLM models failed")

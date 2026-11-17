# llm_service.py
# Reusable service for communicating with the Groq API.
# Each report makes ONE call (the written brief), about 2,000 to 3,000 tokens.
# Groq's free tier allows 8,000 tokens a minute per model, so the models below are
# tried in turn: each has its own allowance, and a rate-limited model is skipped at once.
# Configures strict timeouts and raises exceptions on failure to allow rule fallbacks.

import os
import logging
import httpx
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("quantum_agent.llm_service")

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
# The 120b model follows the JSON format and the evidence-only rules reliably;
# the 20b model often fails JSON validation on this prompt, so it is only a fallback.
DEFAULT_MODEL = "openai/gpt-oss-120b"
FALLBACK_MODELS = ["openai/gpt-oss-120b", "qwen/qwen3.8-27b", "openai/gpt-oss-20b"]
# Ceiling on the answer, so one report can never use up a whole minute's allowance.
MAX_OUTPUT_TOKENS = int(os.getenv("GROQ_MAX_OUTPUT_TOKENS", "1600"))

import re

def clean_json_text(text: str) -> str:
    """Strips markdown code blocks and extracts JSON object from LLM response."""
    if not text:
        return text
    text = text.strip()
    # Strip markdown backticks
    text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s*```$", "", text)
    # Match outermost curly braces to extract raw JSON
    match = re.search(r"(\{.*\})", text, re.DOTALL)
    if match:
        return match.group(1)
    return text

def query_groq(prompt: str, system_prompt: str = None, response_json: bool = True) -> str:
    """
    Directly queries the Groq API via HTTP POST.
    Sanitizes API keys, enforces 25.0s timeout, supports model fallbacks,
    and propagates exceptions so the caller can fall back to local rule-based engines.
    """
    raw_key = os.getenv("GROQ_API_KEY", "")
    api_key = raw_key.strip().strip("'\"")
    if not api_key:
        raise ValueError("GROQ_API_KEY is not defined in environment variables.")

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    primary_model = os.getenv("GROQ_MODEL", DEFAULT_MODEL).strip().strip("'\"")
    # Candidate models to try in sequence if one hits rate limits or errors
    candidate_models = [primary_model]
    for fallback_m in FALLBACK_MODELS:
        if fallback_m not in candidate_models:
            candidate_models.append(fallback_m)

    last_err = None

    for model_name in candidate_models:
        payload = {
            "model": model_name,
            "messages": messages,
            "temperature": 0.1,
            "max_completion_tokens": MAX_OUTPUT_TOKENS,
        }
        if model_name.startswith("openai/gpt-oss"):
            # The scores are already calculated; the model only writes, so little hidden reasoning is needed.
            payload["reasoning_effort"] = "low"
        if response_json:
            payload["response_format"] = {"type": "json_object"}

        try:
            with httpx.Client() as client:
                response = client.post(
                    GROQ_URL, 
                    json=payload, 
                    headers=headers, 
                    timeout=25.0
                )
                response.raise_for_status()
                
                resp_data = response.json()
                choices = resp_data.get("choices", [])
                if not choices:
                    raise ValueError("Groq returned response without choices.")
                    
                content = choices[0]["message"]["content"]
                if response_json:
                    content = clean_json_text(content)
                logger.info(f"Groq query succeeded using model: {model_name}")
                return content
        except Exception as e:
            last_err = e
            err_body = getattr(e, "response", None)
            err_detail = err_body.text if err_body is not None else ""
            logger.warning(f"Groq model {model_name} attempt failed: {str(e)} | Details: {err_detail[:200]}")

    raise last_err


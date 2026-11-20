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
# Order matters: qwen is last because its free tier allows only 1,000 output tokens a minute (about one brief).
FALLBACK_MODELS = ["openai/gpt-oss-120b", "openai/gpt-oss-20b", "qwen/qwen3.8-27b"]
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

def query_groq_with_meta(prompt: str, system_prompt: str = None, response_json: bool = True,
                         request_id: str = "-") -> dict:
    """
    Queries Groq, trying each model in turn until one answers.

    Returns {"content", "model", "usage": {"prompt_tokens", "completion_tokens", "total_tokens"},
    "attempts": [{"model", "status"}]}. Each model is tried once with a 25-second timeout;
    any HTTP error (429 rate limit, 400 including Groq's json_validate_failed, 5xx),
    timeout or network error moves to the next model. If every model fails, the last
    error is raised so the caller can use its rule-written fallback.
    """
    raw_key = os.getenv("GROQ_API_KEY", "")
    api_key = raw_key.strip().strip("'\"")
    if not api_key:
        raise ValueError("GROQ_API_KEY is not defined in environment variables.")

    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    primary_model = os.getenv("GROQ_MODEL", DEFAULT_MODEL).strip().strip("'\"")
    candidate_models = [primary_model]
    for fallback_m in FALLBACK_MODELS:
        if fallback_m not in candidate_models:
            candidate_models.append(fallback_m)

    attempts = []
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
                response = client.post(GROQ_URL, json=payload, headers=headers, timeout=25.0)
                response.raise_for_status()
                resp_data = response.json()
            choices = resp_data.get("choices", [])
            if not choices:
                raise ValueError("Groq returned response without choices.")
            content = choices[0]["message"]["content"]
            if response_json:
                content = clean_json_text(content)
            raw_usage = resp_data.get("usage") or {}
            usage = {k: int(raw_usage.get(k) or 0) for k in ("prompt_tokens", "completion_tokens", "total_tokens")}
            attempts.append({"model": model_name, "status": response.status_code})
            logger.info(f"[{request_id}] Groq ok model={model_name} prompt_tokens={usage['prompt_tokens']} "
                        f"completion_tokens={usage['completion_tokens']} total_tokens={usage['total_tokens']}")
            return {"content": content, "model": model_name, "usage": usage, "attempts": attempts}
        except Exception as e:
            last_err = e
            err_body = getattr(e, "response", None)
            status = err_body.status_code if err_body is not None else type(e).__name__
            err_detail = err_body.text if err_body is not None else ""
            attempts.append({"model": model_name, "status": status})
            logger.warning(f"[{request_id}] Groq model {model_name} failed ({status}): {str(e)[:120]} | {err_detail[:200]}")

    raise last_err


def query_groq(prompt: str, system_prompt: str = None, response_json: bool = True) -> str:
    """The model's text only. Kept for callers that do not need the model name or usage."""
    return query_groq_with_meta(prompt, system_prompt, response_json)["content"]

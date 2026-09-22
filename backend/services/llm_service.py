# llm_service.py
# Reusable service for communicating with the Groq API.
# Utilizes llama-3.3-70b-versatile as the reasoning backbone.
# Configures strict timeouts and raises exceptions on failure to allow rule fallbacks.

import os
import logging
import httpx
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("quantum_agent.llm_service")

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
DEFAULT_MODEL = "openai/gpt-oss-20b"

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
    Handles strict 10.0s timeout and propagates exceptions so the caller 
    can fall back to local rule-based engines.
    """
    api_key = os.getenv("GROQ_API_KEY")
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

    payload = {
        "model": os.getenv("GROQ_MODEL", DEFAULT_MODEL),
        "messages": messages,
        "temperature": 0.1
    }

    if response_json:
        payload["response_format"] = {"type": "json_object"}

    # Enforce strict 10-second timeout with retries and exponential backoff
    max_retries = 2
    backoff = 1.0
    last_err = None

    for attempt in range(max_retries + 1):
        try:
            with httpx.Client() as client:
                response = client.post(
                    GROQ_URL, 
                    json=payload, 
                    headers=headers, 
                    timeout=10.0
                )
                response.raise_for_status()
                
                resp_data = response.json()
                choices = resp_data.get("choices", [])
                if not choices:
                    raise ValueError("Groq returned response without choices.")
                    
                content = choices[0]["message"]["content"]
                if response_json:
                    content = clean_json_text(content)
                return content
        except Exception as e:
            last_err = e
            logger.warning(f"Groq API connection attempt {attempt + 1} failed: {str(e)}")
            if attempt < max_retries:
                import time
                time.sleep(backoff * (attempt + 1))

    raise last_err


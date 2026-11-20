# llm_service.py
# Async Groq client with a fallback chain, per-model retry, rate-limit awareness
# and one overall deadline.
#
# Chain: GROQ_MODEL (default gpt-oss-120b) -> gpt-oss-20b -> qwen3.8-27b.
# For each model, in order:
#   - Skip it if it is cooling down after a 429, or if Groq's last
#     x-ratelimit-remaining-tokens says it cannot fit this request before its
#     window resets. Once the cooldown or reset time passes it is used again
#     (automatic recovery).
#   - Call it. On 429 or 5xx, wait (Retry-After if given, capped at 3 s) and
#     retry once; then move on. Timeouts, network errors and other 4xx move on
#     at once.
# Every attempt is bounded by the remaining overall deadline. If no model
# answers, AllModelsFailed is raised and the caller uses its rule-written brief.
#
# Every call's model, status, tokens (from Groq's `usage`) and latency is logged
# with the request_id and prompt_version, and added to usage_service.

import asyncio
import logging
import os
import re
import threading
import time
from dataclasses import asdict, dataclass, field

import httpx
from dotenv import load_dotenv

from services import usage_service

load_dotenv()

logger = logging.getLogger("quantum_agent.llm_service")

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
DEFAULT_MODEL = "openai/gpt-oss-120b"
# Order matters: qwen is last because its free tier allows only 1,000 output tokens a minute (about one brief).
FALLBACK_MODELS = ["openai/gpt-oss-120b", "openai/gpt-oss-20b", "qwen/qwen3.8-27b"]
# Ceiling on the answer, so one report can never use up a whole minute's allowance.
MAX_OUTPUT_TOKENS = int(os.getenv("GROQ_MAX_OUTPUT_TOKENS", "1600"))
PER_CALL_TIMEOUT = float(os.getenv("GROQ_CALL_TIMEOUT_SECONDS", "25"))
MAX_RETRY_WAIT = 3.0
MIN_TIME_FOR_CALL = 1.0  # do not start a call with less than this left on the deadline

# Tests replace these: the HTTP transport (httpx.MockTransport) and the retry sleep.
_transport = None
_sleep = asyncio.sleep


class AllModelsFailed(Exception):
    def __init__(self, message: str, calls: list, deadline_exceeded: bool = False):
        super().__init__(message)
        self.calls = calls
        self.deadline_exceeded = deadline_exceeded


@dataclass
class CallRecord:
    model: str
    step: int            # position in the chain, 0 = primary
    attempt: int         # 0 = first try, 1 = retry
    status: object       # HTTP status, or "timeout" / "network" / "skipped" / "deadline" / "bad_response"
    latency_ms: float = 0.0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    error: str = ""


@dataclass
class LLMResult:
    content: str
    model: str
    fallback_step: int
    usage: dict
    latency_ms: float
    calls: list = field(default_factory=list)

    @property
    def fallback_used(self) -> bool:
        return self.fallback_step > 0


def clean_json_text(text: str) -> str:
    """Strips markdown code fences and extracts the outermost JSON object."""
    if not text:
        return text
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s*```$", "", text)
    match = re.search(r"(\{.*\})", text, re.DOTALL)
    return match.group(1) if match else text


def _parse_duration(value):
    """Groq reset headers look like "7.66s", "1m26.4s" or "250ms"; Retry-After is seconds."""
    if value is None:
        return None
    value = str(value).strip()
    try:
        return float(value)
    except ValueError:
        pass
    total, found = 0.0, False
    for amount, unit in re.findall(r"([\d.]+)\s*(ms|h|m|s)", value):
        found = True
        total += float(amount) * {"ms": 0.001, "s": 1, "m": 60, "h": 3600}[unit]
    return total if found else None


class RateLimitTracker:
    """What Groq last told us about each model's per-minute token window."""

    def __init__(self):
        self._lock = threading.Lock()
        self._state = {}  # model -> {"remaining": int|None, "reset_at": float, "cooldown_until": float}

    def _get(self, model):
        return self._state.setdefault(model, {"remaining": None, "reset_at": 0.0, "cooldown_until": 0.0})

    def update(self, model: str, headers):
        remaining = headers.get("x-ratelimit-remaining-tokens")
        if remaining is None:
            return
        reset = _parse_duration(headers.get("x-ratelimit-reset-tokens"))
        with self._lock:
            state = self._get(model)
            try:
                state["remaining"] = int(float(remaining))
            except ValueError:
                return
            state["reset_at"] = time.monotonic() + (reset if reset is not None else 60.0)

    def cool_down(self, model: str, seconds: float):
        with self._lock:
            state = self._get(model)
            state["cooldown_until"] = max(state["cooldown_until"], time.monotonic() + max(1.0, seconds))

    def skip_reason(self, model: str, tokens_needed: int):
        now = time.monotonic()
        with self._lock:
            state = self._state.get(model)
            if not state:
                return None
            if now < state["cooldown_until"]:
                return f"cooling down for {state['cooldown_until'] - now:.1f}s after a rate limit"
            if state["remaining"] is not None and now < state["reset_at"] and state["remaining"] < tokens_needed:
                return (f"near its token limit ({state['remaining']} left, about {tokens_needed} needed; "
                        f"resets in {state['reset_at'] - now:.1f}s)")
        return None

    def snapshot(self) -> dict:
        now = time.monotonic()
        with self._lock:
            return {m: {"remaining_tokens": s["remaining"],
                        "window_resets_in_s": round(max(0.0, s["reset_at"] - now), 1),
                        "cooldown_s": round(max(0.0, s["cooldown_until"] - now), 1)}
                    for m, s in self._state.items()}

    def reset(self):
        with self._lock:
            self._state.clear()


rate_limits = RateLimitTracker()


def model_chain() -> list:
    primary = os.getenv("GROQ_MODEL", DEFAULT_MODEL).strip().strip("'\"") or DEFAULT_MODEL
    chain = [primary]
    for model in FALLBACK_MODELS:
        if model not in chain:
            chain.append(model)
    return chain


def _api_key() -> str:
    key = os.getenv("GROQ_API_KEY", "").strip().strip("'\"")
    if not key:
        raise ValueError("GROQ_API_KEY is not set")
    return key


def _log_call(record: CallRecord):
    usage_service.record_llm_call(record.model, record.status, record.prompt_tokens, record.completion_tokens,
                                  record.latency_ms, skipped=record.status == "skipped")
    level = logging.INFO if record.status in (200, "skipped") else logging.WARNING
    fields = {k: v for k, v in asdict(record).items() if k != "step"}
    logger.log(level, "llm_call", extra={"event": {"type": "llm_call", "fallback_step": record.step, **fields}})


async def generate(prompt: str, *, deadline_at: float, response_json: bool = True) -> LLMResult:
    """Calls the chain until one model answers. deadline_at is an event-loop time (loop.time())."""
    loop = asyncio.get_running_loop()
    headers = {"Authorization": f"Bearer {_api_key()}", "Content-Type": "application/json"}
    tokens_needed = len(prompt) // 4 + MAX_OUTPUT_TOKENS
    calls = []

    async with httpx.AsyncClient(transport=_transport) as client:
        for step, model in enumerate(model_chain()):
            reason = rate_limits.skip_reason(model, tokens_needed)
            if reason:
                record = CallRecord(model, step, 0, "skipped", error=reason)
                calls.append(record)
                _log_call(record)
                continue

            payload = {"model": model, "messages": [{"role": "user", "content": prompt}],
                       "temperature": 0.1, "max_completion_tokens": MAX_OUTPUT_TOKENS}
            if model.startswith("openai/gpt-oss"):
                # The scores are already calculated; the model only writes, so little hidden reasoning is needed.
                payload["reasoning_effort"] = "low"
            if response_json:
                payload["response_format"] = {"type": "json_object"}

            for attempt in range(2):
                remaining = deadline_at - loop.time()
                if remaining < MIN_TIME_FOR_CALL:
                    record = CallRecord(model, step, attempt, "deadline", error="overall LLM deadline reached")
                    calls.append(record)
                    _log_call(record)
                    raise AllModelsFailed("overall LLM deadline reached", calls, deadline_exceeded=True)

                started = time.perf_counter()
                try:
                    response = await client.post(GROQ_URL, json=payload, headers=headers,
                                                 timeout=min(PER_CALL_TIMEOUT, remaining))
                except (httpx.TimeoutException, httpx.TransportError) as err:
                    kind = "timeout" if isinstance(err, httpx.TimeoutException) else "network"
                    record = CallRecord(model, step, attempt, kind,
                                        round((time.perf_counter() - started) * 1000, 1), error=str(err)[:200])
                    calls.append(record)
                    _log_call(record)
                    break

                latency = round((time.perf_counter() - started) * 1000, 1)
                rate_limits.update(model, response.headers)
                status = response.status_code

                if status == 200:
                    try:
                        data = response.json()
                        content = data["choices"][0]["message"]["content"]
                    except (ValueError, KeyError, IndexError, TypeError) as err:
                        record = CallRecord(model, step, attempt, "bad_response", latency, error=str(err)[:200])
                        calls.append(record)
                        _log_call(record)
                        break
                    usage = data.get("usage") or {}
                    record = CallRecord(model, step, attempt, 200, latency,
                                        int(usage.get("prompt_tokens") or 0), int(usage.get("completion_tokens") or 0),
                                        int(usage.get("total_tokens") or 0))
                    calls.append(record)
                    _log_call(record)
                    return LLMResult(
                        content=clean_json_text(content) if response_json else content,
                        model=model, fallback_step=step, latency_ms=latency, calls=calls,
                        usage={"prompt_tokens": record.prompt_tokens, "completion_tokens": record.completion_tokens,
                               "total_tokens": record.total_tokens})

                record = CallRecord(model, step, attempt, status, latency, error=response.text[:200])
                calls.append(record)
                _log_call(record)

                retry_after = _parse_duration(response.headers.get("retry-after"))
                if status == 429:
                    rate_limits.cool_down(model, retry_after or _parse_duration(
                        response.headers.get("x-ratelimit-reset-tokens")) or 10.0)
                retryable = status == 429 or status >= 500
                if not retryable or attempt == 1:
                    break
                wait = min(MAX_RETRY_WAIT, retry_after if retry_after is not None else 1.0)
                if deadline_at - loop.time() - wait < MIN_TIME_FOR_CALL:
                    break
                await _sleep(wait)

    raise AllModelsFailed("no model answered", calls)

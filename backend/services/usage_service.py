# usage_service.py
# In-memory daily aggregates of LLM usage, brief outcomes and cache behaviour,
# served at GET /api/admin/usage. Keyed by UTC date; the last KEEP_DAYS days
# are kept. Lost on restart and not shared between server instances.

import threading
from collections import defaultdict
from datetime import datetime, timezone

KEEP_DAYS = 7

_lock = threading.Lock()
_days = {}


def _today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _new_day() -> dict:
    return {
        "reports": {"requests": 0, "generated": 0, "cache_hits": 0, "coalesced": 0, "conflicted": 0, "errors": 0},
        "briefs": defaultdict(int),
        "llm": defaultdict(lambda: {"calls": 0, "ok": 0, "rate_limited": 0, "server_errors": 0, "other_errors": 0,
                                    "skipped": 0, "prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0,
                                    "latency_ms_total": 0.0}),
        "fallback": {"briefs_with_fallback_model": 0, "rule_briefs": 0, "deadline_exceeded": 0},
        "cache": defaultdict(lambda: {"hits": 0, "misses": 0, "coalesced": 0}),
    }


def _day() -> dict:
    today = _today()
    if today not in _days:
        _days[today] = _new_day()
        for old in sorted(_days)[:-KEEP_DAYS]:
            del _days[old]
    return _days[today]


def record_llm_call(model: str, status, prompt_tokens: int = 0, completion_tokens: int = 0,
                    latency_ms: float = 0.0, skipped: bool = False):
    with _lock:
        m = _day()["llm"][model]
        if skipped:
            m["skipped"] += 1
            return
        m["calls"] += 1
        if status == 200:
            m["ok"] += 1
        elif status == 429:
            m["rate_limited"] += 1
        elif isinstance(status, int) and status >= 500:
            m["server_errors"] += 1
        else:
            m["other_errors"] += 1
        m["prompt_tokens"] += int(prompt_tokens or 0)
        m["completion_tokens"] += int(completion_tokens or 0)
        m["total_tokens"] += int(prompt_tokens or 0) + int(completion_tokens or 0)
        m["latency_ms_total"] += float(latency_ms or 0)


def record_brief(outcome: str, fallback_used: bool, deadline_exceeded: bool = False):
    with _lock:
        day = _day()
        day["briefs"][outcome] += 1
        if fallback_used:
            day["fallback"]["briefs_with_fallback_model"] += 1
        if outcome == "rule":
            day["fallback"]["rule_briefs"] += 1
        if deadline_exceeded:
            day["fallback"]["deadline_exceeded"] += 1


def record_cache(tier: str, event: str):
    """event: "hits", "misses" or "coalesced"."""
    with _lock:
        _day()["cache"][tier][event] += 1


def record_report(event: str):
    """event: requests, generated, cache_hits, coalesced, conflicted or errors."""
    with _lock:
        _day()["reports"][event] += 1


def snapshot() -> dict:
    with _lock:
        out = {}
        for date in sorted(_days, reverse=True):
            day = _days[date]
            llm = {}
            for model, m in day["llm"].items():
                calls = m["calls"]
                llm[model] = {**m, "avg_latency_ms": round(m["latency_ms_total"] / calls, 1) if calls else None}
            cache = {}
            for tier, c in day["cache"].items():
                looked_up = c["hits"] + c["misses"] + c["coalesced"]
                cache[tier] = {**c, "hit_rate": round((c["hits"] + c["coalesced"]) / looked_up, 3) if looked_up else None}
            out[date] = {
                "reports": dict(day["reports"]),
                "briefs": dict(day["briefs"]),
                "fallback": dict(day["fallback"]),
                "llm": llm,
                "llm_totals": {
                    "calls": sum(m["calls"] for m in day["llm"].values()),
                    "total_tokens": sum(m["total_tokens"] for m in day["llm"].values()),
                },
                "cache": cache,
            }
    return {"timezone": "UTC", "days": out}


def reset():
    with _lock:
        _days.clear()

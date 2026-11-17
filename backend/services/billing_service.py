# billing_service.py
# Plans, entitlements and usage metering.
#
# This is the foundation layer: plans are defined here, paid access is granted with
# signed access keys (issued by scripts/issue_access_key.py), and daily usage is
# counted in memory. Accounts, a database and a payment webhook replace the key
# issuing and the in-memory counters later without changing the callers.

import copy
import hashlib
import hmac
import os
import threading
import time
from datetime import datetime, timezone

# Section ids match the locked sections in frontend/src/components/ResearchReport.jsx.
PREMIUM_SECTIONS = ["base_rates", "debate", "risks", "watch"]

PLANS = {
    "free": {
        "id": "free",
        "name": "Free",
        "price_inr": 0,
        "price_usd": 0,
        "daily_reports": int(os.getenv("FREE_DAILY_REPORTS", "3")),
        "locked_sections": PREMIUM_SECTIONS,
        "pdf_export": False,
        "features": [
            "3 research reports a day",
            "Overall view and 8-pillar scorecard",
            "Price, financials and news evidence",
            "US and Indian stocks",
        ],
    },
    "plus": {
        "id": "plus",
        "name": "Plus",
        "price_inr": 149,
        "price_usd": 1.99,
        "daily_reports": 15,
        "locked_sections": ["risks", "watch"],
        "pdf_export": False,
        "features": [
            "15 research reports a day",
            "Everything in Free",
            "Historical base rates for the current trend",
            "Bull case and bear case",
        ],
    },
    "pro": {
        "id": "pro",
        "name": "Pro",
        "price_inr": 499,
        "price_usd": 5.99,
        "daily_reports": 60,
        "locked_sections": [],
        "pdf_export": True,
        "features": [
            "60 research reports a day",
            "Everything in Plus",
            "Risk register",
            "What would change the view, with key dates",
            "PDF export",
        ],
    },
}

# Fields of final_decision that belong to each premium section.
_SECTION_FIELDS = {
    "debate": ["bull_case", "bear_case"],
    "risks": ["risk_register"],
    "watch": ["catalyst_calendar", "watchlist_factors"],
}
# Fields of the insight block that belong to each premium section.
_INSIGHT_FIELDS = {
    "base_rates": ["base_rates"],
    "watch": ["watch", "calendar"],
}

_usage_lock = threading.Lock()
_usage = {}  # {(client_id, "YYYY-MM-DD"): set of symbols analysed that day}


def _secret() -> bytes:
    return os.getenv("ACCESS_KEY_SECRET", "").strip().encode("utf-8")


def _sign(payload: str) -> str:
    return hmac.new(_secret(), payload.encode("utf-8"), hashlib.sha256).hexdigest()[:32]


def issue_access_key(plan: str, days: int) -> str:
    """Create a signed access key such as 'qk_pro_1767225600_<signature>'."""
    if plan not in PLANS or plan == "free":
        raise ValueError(f"Unknown paid plan: {plan}")
    if not _secret():
        raise ValueError("ACCESS_KEY_SECRET is not set")
    expires = int(time.time()) + days * 86400
    payload = f"{plan}_{expires}"
    return f"qk_{payload}_{_sign(payload)}"


def verify_access_key(key: str):
    """Returns (plan_id, expires_unix) for a valid, unexpired key, else None."""
    if not key or not _secret():
        return None
    parts = key.strip().split("_")
    if len(parts) != 4 or parts[0] != "qk":
        return None
    _, plan, expires_str, signature = parts
    if plan not in PLANS or not expires_str.isdigit():
        return None
    if not hmac.compare_digest(signature, _sign(f"{plan}_{expires_str}")):
        return None
    if int(expires_str) < time.time():
        return None
    return plan, int(expires_str)


def client_ip(request) -> str:
    """The caller's address. Behind Render/Vercel the real one is in X-Forwarded-For."""
    forwarded = request.headers.get("x-forwarded-for", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def resolve_access(request) -> dict:
    """Works out who is calling and which plan they are on."""
    key = request.headers.get("x-quantum-key", "")
    verified = verify_access_key(key)
    if verified:
        plan_id, expires = verified
        client_id = "key:" + hashlib.sha256(key.encode("utf-8")).hexdigest()[:16]
        return {"plan": PLANS[plan_id], "client_id": client_id, "expires": expires, "key_rejected": False}
    return {
        "plan": PLANS["free"],
        "client_id": "ip:" + client_ip(request),
        "expires": None,
        "key_rejected": bool(key),
    }


def _today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _symbols_today(client_id: str) -> set:
    today = _today()
    # Drop counters from earlier days so the dict does not grow forever.
    for stale in [k for k in _usage if k[1] != today]:
        del _usage[stale]
    return _usage.setdefault((client_id, today), set())


def usage_snapshot(access: dict) -> dict:
    with _usage_lock:
        used = len(_symbols_today(access["client_id"]))
    limit = access["plan"]["daily_reports"]
    return {"used": used, "limit": limit, "remaining": max(0, limit - used)}


def can_analyze(access: dict, symbol: str) -> bool:
    """True if this caller may run a report on symbol today.
    Re-opening a symbol already analysed today never costs a second report."""
    with _usage_lock:
        seen = _symbols_today(access["client_id"])
        return symbol in seen or len(seen) < access["plan"]["daily_reports"]


def record_analysis(access: dict, symbol: str) -> None:
    """Counts a delivered report. Called only after the report was produced."""
    with _usage_lock:
        _symbols_today(access["client_id"]).add(symbol)


def access_summary(access: dict) -> dict:
    plan = access["plan"]
    return {
        "plan": plan["id"],
        "plan_name": plan["name"],
        "locked_sections": list(plan["locked_sections"]),
        "pdf_export": plan["pdf_export"],
        "expires": access["expires"],
        "key_rejected": access["key_rejected"],
        "usage": usage_snapshot(access),
    }


def apply_entitlements(report: dict, access: dict) -> dict:
    """Returns a copy of the report with premium content removed for plans that
    do not include it. Locking happens here on the server; the browser never
    receives content the plan does not cover."""
    gated = copy.deepcopy(report)
    decision = gated.get("final_decision", {})
    for section in access["plan"]["locked_sections"]:
        for field in _SECTION_FIELDS.get(section, []):
            decision[field] = []
        for field in _INSIGHT_FIELDS.get(section, []):
            if isinstance(gated.get("insight"), dict):
                gated["insight"][field] = None
    gated["access"] = access_summary(access)
    return gated


def public_plans() -> list:
    return [
        {k: plan[k] for k in ("id", "name", "price_inr", "price_usd", "daily_reports", "pdf_export", "features")}
        for plan in PLANS.values()
    ]

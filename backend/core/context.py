# context.py
# Per-request context and tracing.
#
# request_id, prompt_version and the active Trace live in contextvars, so every
# coroutine started with asyncio.gather and every asyncio.to_thread worker sees
# the values of the request that started it, without passing them around.
#
# A Trace is a list of spans (name, start/end in ms from the request start,
# status, error, attributes). Finished traces go into a ring buffer of the last
# TRACE_BUFFER_SIZE requests, served at GET /api/admin/traces.

import contextlib
import logging
import threading
import time
import uuid
from collections import deque
from contextvars import ContextVar

logger = logging.getLogger("quantum_agent.trace")

request_id_var: ContextVar[str] = ContextVar("request_id", default="-")
prompt_version_var: ContextVar[str] = ContextVar("prompt_version", default="-")
trace_var: ContextVar["Trace | None"] = ContextVar("trace", default=None)

TRACE_BUFFER_SIZE = 200


def new_request_id() -> str:
    return uuid.uuid4().hex[:12]


class Trace:
    """Spans recorded during one request. Safe to add to from several tasks and threads."""

    def __init__(self, request_id: str, symbol: str = "", prompt_version: str = "-"):
        self.request_id = request_id
        self.symbol = symbol
        self.prompt_version = prompt_version
        self.started_at = time.time()
        self._t0 = time.perf_counter()
        self._lock = threading.Lock()
        self.spans = []
        self.attrs = {}

    def now_ms(self) -> float:
        return round((time.perf_counter() - self._t0) * 1000, 1)

    def add(self, name: str, start_ms: float, end_ms: float, status: str = "ok", error: str = None, **attrs):
        span = {"name": name, "start_ms": start_ms, "end_ms": end_ms,
                "duration_ms": round(end_ms - start_ms, 1), "status": status, "error": error}
        if attrs:
            span["attrs"] = attrs
        with self._lock:
            self.spans.append(span)
        logger.info("span", extra={"event": {"type": "span", "symbol": self.symbol, **span}})
        return span

    @contextlib.contextmanager
    def span(self, name: str, **attrs):
        """Times a block. The yielded dict can receive attributes; an exception marks it as an error."""
        start = self.now_ms()
        extra = dict(attrs)
        try:
            yield extra
        except Exception as err:
            self.add(name, start, self.now_ms(), status="error", error=f"{type(err).__name__}: {str(err)[:200]}", **extra)
            raise
        else:
            status = extra.pop("status", "ok")
            self.add(name, start, self.now_ms(), status=status, **extra)

    def to_dict(self) -> dict:
        with self._lock:
            spans = sorted(self.spans, key=lambda s: s["start_ms"])
        return {"request_id": self.request_id, "symbol": self.symbol, "prompt_version": self.prompt_version,
                "started_at": round(self.started_at, 3), "total_ms": self.now_ms(), "spans": spans, **self.attrs}


class TraceStore:
    """Ring buffer of the most recent finished traces."""

    def __init__(self, size: int = TRACE_BUFFER_SIZE):
        self._items = deque(maxlen=size)
        self._lock = threading.Lock()

    def add(self, trace: dict):
        with self._lock:
            self._items.append(trace)

    def recent(self, limit: int = 50) -> list:
        with self._lock:
            items = list(self._items)
        return list(reversed(items))[: max(0, limit)]

    def clear(self):
        with self._lock:
            self._items.clear()


traces = TraceStore()


def current_trace():
    return trace_var.get()


@contextlib.contextmanager
def span(name: str, **attrs):
    """A span on the current request's trace; a no-op outside a request."""
    trace = trace_var.get()
    if trace is None:
        yield dict(attrs)
        return
    with trace.span(name, **attrs) as extra:
        yield extra

# logging_setup.py
# One log line per event, as JSON, with the request_id and prompt_version of the
# request that produced it (read from contextvars). Structured fields are passed
# with extra={"event": {...}} and merged into the line.
#
# LOG_FORMAT=text switches to plain text for local reading. LOG_FILE adds a
# rotating file next to stdout.

import json
import logging
import os
import sys
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler

from core.context import prompt_version_var, request_id_var


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        line = {
            "ts": datetime.fromtimestamp(record.created, timezone.utc).isoformat(timespec="milliseconds"),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
            "request_id": request_id_var.get(),
            "prompt_version": prompt_version_var.get(),
        }
        event = getattr(record, "event", None)
        if isinstance(event, dict):
            line.update(event)
        if record.exc_info:
            line["exc"] = self.formatException(record.exc_info)
        return json.dumps(line, default=str, ensure_ascii=False)


class TextFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        base = (f"{datetime.fromtimestamp(record.created).strftime('%H:%M:%S')} {record.levelname} "
                f"[{request_id_var.get()}] {record.name}: {record.getMessage()}")
        event = getattr(record, "event", None)
        if isinstance(event, dict):
            base += " " + " ".join(f"{k}={v}" for k, v in event.items())
        return base


_configured = False


def configure_logging():
    global _configured
    if _configured:
        return
    _configured = True
    formatter = TextFormatter() if os.getenv("LOG_FORMAT", "json").lower() == "text" else JsonFormatter()
    handlers = [logging.StreamHandler(sys.stdout)]
    log_file = os.getenv("LOG_FILE", "quantum_system.log").strip()
    if log_file:
        try:
            handlers.append(RotatingFileHandler(log_file, maxBytes=10 * 1024 * 1024, backupCount=5, encoding="utf-8"))
        except OSError:
            pass
    root = logging.getLogger()
    root.handlers = []
    for handler in handlers:
        handler.setFormatter(formatter)
        root.addHandler(handler)
    root.setLevel(logging.INFO)
    # yfinance and httpx are chatty at INFO.
    for noisy in ("httpx", "httpcore", "yfinance", "peewee", "urllib3"):
        logging.getLogger(noisy).setLevel(logging.WARNING)

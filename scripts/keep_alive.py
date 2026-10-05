#!/usr/bin/env python3
"""
keep_alive.py — Keep Render / Cloud Web Services Alive 24/7

Render and other free-tier hosts put instances to sleep after 15 minutes of inactivity.
This script pings your backend's /health endpoint every 10 minutes to ensure it stays active.

Usage:
    python scripts/keep_alive.py [BACKEND_URL] [INTERVAL_MINUTES]

Example:
    python scripts/keep_alive.py https://quantum-agent-api.onrender.com 10
"""

import sys
import time
import urllib.request
import urllib.error
import datetime

DEFAULT_URL = "https://quantum-financial-agent.onrender.com"
DEFAULT_INTERVAL_MINUTES = 10


def ping(url: str):
    health_url = url.rstrip("/")
    if not health_url.endswith("/health"):
        health_url += "/health"

    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] Pinging {health_url} ...", end=" ", flush=True)

    try:
        req = urllib.request.Request(
            health_url,
            headers={"User-Agent": "QuantumAgent-KeepAlive/1.0"}
        )
        with urllib.request.urlopen(req, timeout=45) as resp:
            status = resp.status
            body = resp.read().decode("utf-8", errors="ignore")
            print(f"✅ Status {status} OK (Server is Awake)")
            return True
    except urllib.error.HTTPError as e:
        print(f"⚠️ HTTP Error {e.code}: {e.reason}")
        return False
    except urllib.error.URLError as e:
        print(f"❌ Connection Error: {e.reason} (Server may be cold-starting)")
        return False
    except Exception as e:
        print(f"❌ Unexpected Error: {e}")
        return False


def main():
    target_url = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_URL
    interval_min = float(sys.argv[2]) if len(sys.argv) > 2 else DEFAULT_INTERVAL_MINUTES
    interval_sec = int(interval_min * 60)

    print("=" * 60)
    print("🚀 QUANTUM AGENT — KEEP-ALIVE DAEMON")
    print("=" * 60)
    print(f"Target URL:        {target_url}")
    print(f"Ping Interval:     Every {interval_min} minutes ({interval_sec}s)")
    print("Press Ctrl+C at any time to stop.")
    print("=" * 60)

    # Initial ping
    ping(target_url)

    while True:
        try:
            time.sleep(interval_sec)
            ping(target_url)
        except KeyboardInterrupt:
            print("\n🛑 Keep-alive daemon stopped by user.")
            break


if __name__ == "__main__":
    main()

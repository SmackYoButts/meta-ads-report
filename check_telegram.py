"""
Checks Telegram for a /report command sent in the last 15 minutes.
Acknowledges the update after finding it so it won't trigger again.
Exits 0 (TRIGGER) if found, exits 1 otherwise.
"""
import json
import os
import sys
import urllib.request
from datetime import datetime, timezone, timedelta

TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
WINDOW_SECONDS = 900  # 15 min — covers GitHub Actions scheduling delays
API = f"https://api.telegram.org/bot{TOKEN}"


def api_call(method: str, params: str = "") -> dict:
    url = f"{API}/{method}?{params}"
    with urllib.request.urlopen(url, timeout=10) as r:
        return json.load(r)


def acknowledge(update_id: int) -> None:
    """Tell Telegram we processed this update so it won't reappear."""
    api_call("getUpdates", f"offset={update_id + 1}&limit=1&timeout=0")


def main() -> None:
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(seconds=WINDOW_SECONDS)

    updates = api_call("getUpdates", "limit=20&timeout=0")["result"]

    for update in updates:
        msg = update.get("message", {})
        text = (msg.get("text") or "").lower()
        ts = msg.get("date", 0)
        sent_at = datetime.fromtimestamp(ts, tz=timezone.utc)

        if "/report" in text and sent_at >= cutoff:
            print(f"TRIGGER — /report received at {sent_at.isoformat()}")
            acknowledge(update["update_id"])
            sys.exit(0)

    print("No /report command in the last 15 minutes.")
    sys.exit(1)


if __name__ == "__main__":
    main()

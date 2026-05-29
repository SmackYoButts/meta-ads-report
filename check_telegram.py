"""
Checks the last 4 minutes of Telegram messages for a /report command.
Exits with code 0 and prints TRIGGER if found, exits 1 otherwise.
Run by GitHub Actions every 5 minutes.
"""
import json
import os
import sys
import urllib.request
from datetime import datetime, timezone, timedelta

TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
WINDOW_SECONDS = 240  # 4-minute window — no overlap with 5-min schedule


def get_updates() -> list:
    url = f"https://api.telegram.org/bot{TOKEN}/getUpdates?limit=20&timeout=0"
    with urllib.request.urlopen(url, timeout=10) as r:
        return json.load(r)["result"]


def main() -> None:
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(seconds=WINDOW_SECONDS)

    updates = get_updates()
    for update in updates:
        msg = update.get("message", {})
        text = (msg.get("text") or "").lower()
        ts = msg.get("date", 0)
        sent_at = datetime.fromtimestamp(ts, tz=timezone.utc)

        if "/report" in text and sent_at >= cutoff:
            print(f"TRIGGER — /report received at {sent_at.isoformat()}")
            sys.exit(0)

    print("No /report command in last 4 minutes.")
    sys.exit(1)


if __name__ == "__main__":
    main()

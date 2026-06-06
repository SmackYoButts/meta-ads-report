#!/usr/bin/env python3
"""
Meta Ads Daily Report
Usage:
    python report.py       # start scheduler (runs daily at 00:01 Israel time)
    python report.py --now # run immediately
"""

import argparse
import logging
import os
import sys
from datetime import datetime
from dotenv import load_dotenv

import meta_ads
import sheets
import telegram_bot
import scheduler

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("report.log"),
    ],
)
logger = logging.getLogger(__name__)


def _require_env(key: str) -> str:
    value = os.getenv(key)
    if not value:
        logger.error("Missing required environment variable: %s", key)
        sys.exit(1)
    return value


def run_report() -> None:
    logger.info("Starting Meta Ads report run...")

    access_token     = _require_env("META_ACCESS_TOKEN")
    ad_account_id    = _require_env("META_AD_ACCOUNT_ID")
    bot_token        = _require_env("TELEGRAM_BOT_TOKEN")
    chat_id          = _require_env("TELEGRAM_CHAT_ID")
    sheet_url        = _require_env("GOOGLE_SHEET_URL")
    credentials_path = _require_env("GOOGLE_CREDENTIALS_JSON_PATH")

    is_thursday = datetime.today().weekday() == 3  # 0=Mon … 6=Sun

    # ── Pull daily data (yesterday vs day before) ──────────────────────────
    try:
        logger.info("Pulling daily Meta Ads data...")
        campaigns, totals, prev_camps, prev_totals = meta_ads.pull_daily_report(
            access_token, ad_account_id
        )
    except Exception as e:
        logger.error("Failed to pull Meta Ads data: %s", e)
        return

    # ── Pull weekly data on Thursdays ──────────────────────────────────────
    weekly_totals = prev_weekly_totals = None
    weekly_camps = []
    if is_thursday:
        try:
            logger.info("Thursday — pulling weekly comparison data...")
            weekly_camps, weekly_totals, _, prev_weekly_totals = meta_ads.pull_weekly_report(
                access_token, ad_account_id
            )
        except Exception as e:
            logger.warning("Could not pull weekly data: %s", e)

    # ── Write to Google Sheets ─────────────────────────────────────────────
    try:
        logger.info("Writing to Google Sheets...")
        sheets.append_campaign_rows(sheet_url, credentials_path, campaigns)
    except Exception as e:
        logger.error("Failed to write to Google Sheets: %s", e)

    # ── Send Telegram report ───────────────────────────────────────────────
    try:
        logger.info("Sending Telegram report...")
        message = telegram_bot.build_daily_message(
            campaigns=campaigns,
            totals=totals,
            prev_campaigns=prev_camps,
            prev_totals=prev_totals,
            sheet_url=sheet_url,
            is_thursday=is_thursday,
            weekly_totals=weekly_totals,
            prev_weekly_totals=prev_weekly_totals,
        )
        telegram_bot.send_report(bot_token, chat_id, message)
    except Exception as e:
        logger.error("Failed to send Telegram message: %s", e)

    logger.info("Report run complete.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Meta Ads Daily Report")
    parser.add_argument("--now", action="store_true", help="Run immediately")
    args = parser.parse_args()

    if args.now:
        run_report()
    else:
        logger.info("Starting scheduler.")
        scheduler.start(run_report)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Meta Ads Weekly Report
Usage:
    python report.py          # start scheduler (runs every Thursday at 09:00)
    python report.py --now    # run report immediately
"""

import argparse
import logging
import os
import sys
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

    access_token = _require_env("META_ACCESS_TOKEN")
    ad_account_id = _require_env("META_AD_ACCOUNT_ID")
    bot_token = _require_env("TELEGRAM_BOT_TOKEN")
    chat_id = _require_env("TELEGRAM_CHAT_ID")
    sheet_url = _require_env("GOOGLE_SHEET_URL")
    credentials_path = _require_env("GOOGLE_CREDENTIALS_JSON_PATH")

    try:
        logger.info("Pulling Meta Ads data...")
        campaigns, totals = meta_ads.pull_campaign_insights(access_token, ad_account_id)
    except Exception as e:
        logger.error("Failed to pull Meta Ads data: %s", e)
        return

    try:
        logger.info("Writing to Google Sheets...")
        sheets.append_campaign_rows(sheet_url, credentials_path, campaigns)
    except Exception as e:
        logger.error("Failed to write to Google Sheets: %s", e)

    try:
        logger.info("Sending Telegram report...")
        telegram_bot.send_report(bot_token, chat_id, campaigns, totals, sheet_url)
    except Exception as e:
        logger.error("Failed to send Telegram message: %s", e)

    logger.info("Report run complete.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Meta Ads Weekly Report")
    parser.add_argument(
        "--now",
        action="store_true",
        help="Run the report immediately instead of starting the scheduler",
    )
    args = parser.parse_args()

    if args.now:
        run_report()
    else:
        logger.info("Starting scheduler. Use --now to run immediately.")
        scheduler.start(run_report)


if __name__ == "__main__":
    main()

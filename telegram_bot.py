import logging
import asyncio
from telegram import Bot
from telegram.error import TelegramError

logger = logging.getLogger(__name__)


def _format_number(n: int | float) -> str:
    return f"{n:,.0f}"


def build_message(totals: dict, sheet_url: str) -> str:
    date_range = f"{totals['date_since']} – {totals['date_until']}"
    spend = f"₪{totals['total_spend']:,.2f}"
    impressions = _format_number(totals["total_impressions"])
    clicks = _format_number(totals["total_clicks"])
    leads = _format_number(totals["total_leads"])
    ctr = f"{totals['ctr']:.2f}%"

    return (
        f"📊 *Weekly Ads Report — {date_range}*\n"
        f"\n"
        f"💰 Total Spend: {spend}\n"
        f"👁 Impressions: {impressions}\n"
        f"🖱 Clicks: {clicks}\n"
        f"📈 CTR: {ctr}\n"
        f"🎯 Leads: {leads}\n"
        f"\n"
        f"📋 [View full report]({sheet_url})"
    )


async def _send(bot_token: str, chat_id: str, text: str) -> None:
    async with Bot(token=bot_token) as bot:
        await bot.send_message(
            chat_id=chat_id,
            text=text,
            parse_mode="Markdown",
            disable_web_page_preview=True,
        )


def send_report(bot_token: str, chat_id: str, totals: dict, sheet_url: str) -> None:
    message = build_message(totals, sheet_url)
    try:
        asyncio.run(_send(bot_token, chat_id, message))
        logger.info("Telegram report sent to chat %s.", chat_id)
    except TelegramError as e:
        logger.error("Telegram send error: %s", e)
        raise

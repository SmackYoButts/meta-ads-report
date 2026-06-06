import logging
import asyncio
from telegram import Bot
from telegram.error import TelegramError

logger = logging.getLogger(__name__)


def build_message(campaigns: list[dict], totals: dict, sheet_url: str) -> str:
    date = totals["date_since"]  # single day
    spend = f"₪{totals['total_spend']:,.2f}"
    impressions = f"{totals['total_impressions']:,}"
    clicks = f"{totals['total_clicks']:,}"
    leads = f"{totals['total_leads']:,}"
    ctr = f"{totals['ctr']:.2f}%"

    lines = [
        f"📊 *Daily Ads Report — {date}*",
        "",
        f"💰 Total Spend: {spend}",
        f"👁 Impressions: {impressions}",
        f"🖱 Clicks: {clicks}",
        f"📈 CTR: {ctr}",
        f"🎯 Leads: {leads}",
        "",
        "━━━━━━━━━━━━━━━━━━━━",
        "*Campaign Breakdown:*",
        "",
    ]

    for c in sorted(campaigns, key=lambda x: x["spend"], reverse=True):
        lines.append(f"📌 *{c['campaign_name']}*")
        lines.append(f"   💰 ₪{c['spend']:,.2f}  |  🎯 {c['leads']} leads  |  📈 {c['ctr']:.2f}%")
        lines.append("")

    lines.append(f"📋 [View full report]({sheet_url})")
    return "\n".join(lines)


async def _send(bot_token: str, chat_id: str, text: str) -> None:
    async with Bot(token=bot_token) as bot:
        await bot.send_message(
            chat_id=chat_id,
            text=text,
            parse_mode="Markdown",
            disable_web_page_preview=True,
        )


def send_report(bot_token: str, chat_id: str, campaigns: list[dict], totals: dict, sheet_url: str) -> None:
    message = build_message(campaigns, totals, sheet_url)
    try:
        asyncio.run(_send(bot_token, chat_id, message))
        logger.info("Telegram report sent to chat %s.", chat_id)
    except TelegramError as e:
        logger.error("Telegram send error: %s", e)
        raise

import logging
import asyncio
from telegram import Bot
from telegram.error import TelegramError

logger = logging.getLogger(__name__)


# ── helpers ──────────────────────────────────────────────────────────────────

def _pct(current, previous) -> str:
    """Return a coloured % change string, e.g. '↑12.3%' or '↓5.1%'."""
    if previous is None or current is None:
        return ""
    if previous == 0:
        return " (new)" if current else ""
    change = (current - previous) / abs(previous) * 100
    arrow = "↑" if change >= 0 else "↓"
    return f" ({arrow}{abs(change):.1f}%)"


def _cpl_str(cpl) -> str:
    return f"₪{cpl:,.2f}" if cpl is not None else "N/A"


def _campaign_lookup(campaigns: list[dict]) -> dict:
    return {c["campaign_name"]: c for c in campaigns}


# ── message builders ─────────────────────────────────────────────────────────

def _summary_block(totals: dict, prev_totals: dict | None, label: str) -> list[str]:
    p = prev_totals or {}
    lines = [
        f"*{label}*",
        f"💰 Spend: ₪{totals['total_spend']:,.2f}{_pct(totals['total_spend'], p.get('total_spend'))}",
        f"👁 Impressions: {totals['total_impressions']:,}{_pct(totals['total_impressions'], p.get('total_impressions'))}",
        f"🖱 Clicks: {totals['total_clicks']:,}{_pct(totals['total_clicks'], p.get('total_clicks'))}",
        f"📈 CTR: {totals['ctr']:.2f}%{_pct(totals['ctr'], p.get('ctr'))}",
        f"🎯 Leads: {totals['total_leads']:,}{_pct(totals['total_leads'], p.get('total_leads'))}",
        f"💵 CPL: {_cpl_str(totals['cpl'])}{_pct(totals['cpl'], p.get('cpl'))}",
    ]
    return lines


def build_daily_message(
    campaigns: list[dict],
    totals: dict,
    prev_campaigns: list[dict],
    prev_totals: dict,
    sheet_url: str,
    is_thursday: bool = False,
    weekly_totals: dict | None = None,
    prev_weekly_totals: dict | None = None,
) -> str:
    date = totals["date_since"]
    prev_lookup = _campaign_lookup(prev_campaigns)

    lines = [f"📊 *Daily Ads Report — {date}*", ""]
    lines += _summary_block(totals, prev_totals, "📋 Summary (vs yesterday)")
    lines += ["", "━━━━━━━━━━━━━━━━━━━━", "*Campaign Breakdown:*", ""]

    for c in sorted(campaigns, key=lambda x: x["spend"], reverse=True):
        prev = prev_lookup.get(c["campaign_name"], {})
        lines.append(f"📌 *{c['campaign_name']}*")
        lines.append(
            f"   💰 ₪{c['spend']:,.2f}{_pct(c['spend'], prev.get('spend'))}  |  "
            f"🎯 {c['leads']}{_pct(c['leads'], prev.get('leads'))}  |  "
            f"📈 {c['ctr']:.2f}%{_pct(c['ctr'], prev.get('ctr'))}  |  "
            f"💵 {_cpl_str(c['cpl'])}{_pct(c['cpl'], prev.get('cpl'))}"
        )
        lines.append("")

    # Thursday: add weekly summary block
    if is_thursday and weekly_totals:
        w_since = weekly_totals["date_since"]
        w_until = weekly_totals["date_until"]
        lines += [
            "━━━━━━━━━━━━━━━━━━━━",
            f"📅 *Weekly Summary ({w_since} → {w_until})*",
            "",
        ]
        lines += _summary_block(weekly_totals, prev_weekly_totals, "📊 This week (vs last week)")
        lines.append("")

    lines.append(f"📋 [View full report]({sheet_url})")
    return "\n".join(lines)


# ── send ─────────────────────────────────────────────────────────────────────

async def _send(bot_token: str, chat_id: str, text: str) -> None:
    async with Bot(token=bot_token) as bot:
        await bot.send_message(
            chat_id=chat_id,
            text=text,
            parse_mode="Markdown",
            disable_web_page_preview=True,
        )


def send_report(bot_token: str, chat_id: str, message: str) -> None:
    try:
        asyncio.run(_send(bot_token, chat_id, message))
        logger.info("Telegram report sent to chat %s.", chat_id)
    except TelegramError as e:
        logger.error("Telegram send error: %s", e)
        raise

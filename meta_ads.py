import logging
from datetime import datetime, timedelta
from facebook_business.api import FacebookAdsApi
from facebook_business.adobjects.adaccount import AdAccount
from facebook_business.exceptions import FacebookRequestError

logger = logging.getLogger(__name__)

FIELDS = [
    "campaign_name", "spend", "impressions", "clicks",
    "ctr", "cpm", "cpc", "reach", "actions",
]


def init_meta_api(access_token: str, ad_account_id: str) -> AdAccount:
    FacebookAdsApi.init(access_token=access_token)
    account_id = ad_account_id if ad_account_id.startswith("act_") else f"act_{ad_account_id}"
    return AdAccount(account_id)


def _cpl(spend: float, leads: int) -> float | None:
    return round(spend / leads, 2) if leads else None


def _parse_rows(rows, date_range: dict) -> tuple[list[dict], dict]:
    campaigns = []
    for row in rows:
        actions = {a["action_type"]: int(float(a["value"])) for a in row.get("actions", [])}
        leads = actions.get("lead", 0)
        spend = float(row.get("spend", 0))
        campaigns.append({
            "campaign_name": row.get("campaign_name", "Unknown"),
            "spend":       spend,
            "impressions": int(row.get("impressions", 0)),
            "clicks":      int(row.get("clicks", 0)),
            "ctr":         float(row.get("ctr", 0)),
            "cpm":         float(row.get("cpm", 0)),
            "cpc":         float(row.get("cpc", 0)),
            "reach":       int(row.get("reach", 0)),
            "leads":       leads,
            "cpl":         _cpl(spend, leads),
        })
    return campaigns, _aggregate(campaigns, date_range)


def _aggregate(campaigns: list[dict], date_range: dict) -> dict:
    spend      = sum(c["spend"] for c in campaigns)
    impressions = sum(c["impressions"] for c in campaigns)
    clicks     = sum(c["clicks"] for c in campaigns)
    leads      = sum(c["leads"] for c in campaigns)
    ctr        = (clicks / impressions * 100) if impressions else 0
    return {
        "date_since":        date_range["since"],
        "date_until":        date_range["until"],
        "total_spend":       spend,
        "total_impressions": impressions,
        "total_clicks":      clicks,
        "total_leads":       leads,
        "ctr":               round(ctr, 2),
        "cpl":               _cpl(spend, leads),
    }


def _fetch(account: AdAccount, since: str, until: str) -> tuple[list[dict], dict]:
    date_range = {"since": since, "until": until}
    try:
        rows = account.get_insights(
            fields=FIELDS,
            params={"time_range": date_range, "level": "campaign", "limit": 500},
        )
    except FacebookRequestError as e:
        logger.error("Meta API error: %s", e)
        raise
    campaigns, totals = _parse_rows(rows, date_range)
    logger.info("Pulled %d campaigns for %s → %s", len(campaigns), since, until)
    return campaigns, totals


def pull_daily_report(access_token: str, ad_account_id: str):
    """Returns (campaigns, totals, prev_campaigns, prev_totals).
    current = yesterday, previous = day before yesterday."""
    account = init_meta_api(access_token, ad_account_id)
    today = datetime.today()
    yesterday   = (today - timedelta(days=1)).strftime("%Y-%m-%d")
    day_before  = (today - timedelta(days=2)).strftime("%Y-%m-%d")
    campaigns, totals         = _fetch(account, yesterday, yesterday)
    prev_camps, prev_totals   = _fetch(account, day_before, day_before)
    return campaigns, totals, prev_camps, prev_totals


def pull_weekly_report(access_token: str, ad_account_id: str):
    """Returns (campaigns, totals, prev_campaigns, prev_totals).
    current = last 7 days (Fri→Thu), previous = 7 days before that."""
    account = init_meta_api(access_token, ad_account_id)
    today = datetime.today()
    days_since_thu = (today.weekday() - 3) % 7
    thu = today - timedelta(days=days_since_thu)
    fri = thu - timedelta(days=6)
    prev_thu = fri - timedelta(days=1)
    prev_fri = prev_thu - timedelta(days=6)

    camps, totals           = _fetch(account, fri.strftime("%Y-%m-%d"), thu.strftime("%Y-%m-%d"))
    prev_camps, prev_totals = _fetch(account, prev_fri.strftime("%Y-%m-%d"), prev_thu.strftime("%Y-%m-%d"))
    return camps, totals, prev_camps, prev_totals

import logging
from datetime import datetime, timedelta
from facebook_business.api import FacebookAdsApi
from facebook_business.adobjects.adaccount import AdAccount
from facebook_business.exceptions import FacebookRequestError

logger = logging.getLogger(__name__)


def init_meta_api(access_token: str, ad_account_id: str) -> AdAccount:
    FacebookAdsApi.init(access_token=access_token)
    account_id = ad_account_id if ad_account_id.startswith("act_") else f"act_{ad_account_id}"
    return AdAccount(account_id)


def get_date_range() -> dict:
    today = datetime.today()
    # Most recent Thursday (weekday=3); if today is Thursday, use today
    days_since_thursday = (today.weekday() - 3) % 7
    last_thursday = today - timedelta(days=days_since_thursday)
    last_friday = last_thursday - timedelta(days=6)
    return {
        "since": last_friday.strftime("%Y-%m-%d"),
        "until": last_thursday.strftime("%Y-%m-%d"),
    }


def pull_campaign_insights(access_token: str, ad_account_id: str) -> tuple[list[dict], dict]:
    account = init_meta_api(access_token, ad_account_id)
    date_range = get_date_range()

    fields = [
        "campaign_name",
        "spend",
        "impressions",
        "clicks",
        "ctr",
        "cpm",
        "cpc",
        "reach",
        "actions",
    ]

    params = {
        "time_range": date_range,
        "level": "campaign",
        "limit": 500,
    }

    try:
        insights = account.get_insights(fields=fields, params=params)
    except FacebookRequestError as e:
        logger.error("Meta API error: %s", e)
        raise

    campaigns = []
    for row in insights:
        actions = {a["action_type"]: int(float(a["value"])) for a in row.get("actions", [])}
        leads = actions.get("lead", 0)

        campaigns.append({
            "campaign_name": row.get("campaign_name", "Unknown"),
            "spend": float(row.get("spend", 0)),
            "impressions": int(row.get("impressions", 0)),
            "clicks": int(row.get("clicks", 0)),
            "ctr": float(row.get("ctr", 0)),
            "cpm": float(row.get("cpm", 0)),
            "cpc": float(row.get("cpc", 0)),
            "reach": int(row.get("reach", 0)),
            "leads": leads,
        })

    totals = _aggregate_totals(campaigns, date_range)
    logger.info("Pulled %d campaigns for %s → %s", len(campaigns), date_range["since"], date_range["until"])
    return campaigns, totals


def _aggregate_totals(campaigns: list[dict], date_range: dict) -> dict:
    total_spend = sum(c["spend"] for c in campaigns)
    total_impressions = sum(c["impressions"] for c in campaigns)
    total_clicks = sum(c["clicks"] for c in campaigns)
    total_leads = sum(c["leads"] for c in campaigns)
    ctr = (total_clicks / total_impressions * 100) if total_impressions else 0

    return {
        "date_since": date_range["since"],
        "date_until": date_range["until"],
        "total_spend": total_spend,
        "total_impressions": total_impressions,
        "total_clicks": total_clicks,
        "total_leads": total_leads,
        "ctr": round(ctr, 2),
    }

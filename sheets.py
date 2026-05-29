import logging
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials

logger = logging.getLogger(__name__)

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.readonly",
]

HEADER_ROW = [
    "Report Date",
    "Campaign Name",
    "Spend (₪)",
    "Impressions",
    "Clicks",
    "CTR (%)",
    "CPM (₪)",
    "CPC (₪)",
    "Leads",
    "Reach",
]


def _open_sheet(sheet_url: str, credentials_path: str) -> gspread.Worksheet:
    creds = Credentials.from_service_account_file(credentials_path, scopes=SCOPES)
    client = gspread.authorize(creds)
    spreadsheet = client.open_by_url(sheet_url)
    return spreadsheet.sheet1


def ensure_header(worksheet: gspread.Worksheet) -> None:
    first_row = worksheet.row_values(1)
    if first_row != HEADER_ROW:
        worksheet.insert_row(HEADER_ROW, index=1)
        logger.info("Header row written to sheet.")


def append_campaign_rows(sheet_url: str, credentials_path: str, campaigns: list[dict], report_date: str | None = None) -> None:
    if report_date is None:
        report_date = datetime.today().strftime("%Y-%m-%d")

    try:
        worksheet = _open_sheet(sheet_url, credentials_path)
        ensure_header(worksheet)

        rows = []
        for c in campaigns:
            rows.append([
                report_date,
                c["campaign_name"],
                round(c["spend"], 2),
                c["impressions"],
                c["clicks"],
                round(c["ctr"], 4),
                round(c["cpm"], 2),
                round(c["cpc"], 2),
                c["leads"],
                c["reach"],
            ])

        if rows:
            worksheet.append_rows(rows, value_input_option="USER_ENTERED")
            logger.info("Appended %d campaign rows to Google Sheet.", len(rows))
        else:
            logger.warning("No campaign data to write.")

    except gspread.exceptions.APIError as e:
        logger.error("Google Sheets API error: %s", e)
        raise
    except FileNotFoundError:
        logger.error("Google credentials file not found: %s", credentials_path)
        raise

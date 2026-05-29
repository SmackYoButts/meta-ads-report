# Meta Ads Weekly Report Automation

Pulls Meta Ads campaign data every Thursday, writes it to Google Sheets, and sends a summary to Telegram.

---

## What It Does

- Every Thursday at 09:00, the script automatically:
  1. Fetches last 7 days of campaign metrics from your Meta Ads account
  2. Appends the data to a Google Sheet
  3. Sends a summary message to a Telegram chat

You can also trigger it manually at any time with `python report.py --now`.

---

## File Overview

```
meta_ads_report/
├── report.py          ← main entry point
├── meta_ads.py        ← Meta Ads API logic
├── sheets.py          ← Google Sheets logic
├── telegram_bot.py    ← Telegram logic
├── scheduler.py       ← weekly scheduling
├── requirements.txt   ← Python dependencies
├── .env.example       ← template for your credentials
└── README.md          ← this file
```

---

## Setup Instructions

### Step 1 — Install Python

You need Python 3.11 or newer. Check if you have it:

```bash
python3 --version
```

If not, download it from [python.org](https://www.python.org/downloads/).

---

### Step 2 — Install dependencies

Open a terminal in the project folder and run:

```bash
pip install -r requirements.txt
```

---

### Step 3 — Create your `.env` file

Copy the example file:

```bash
cp .env.example .env
```

Then open `.env` in any text editor and fill in each value. The sections below explain exactly how to get each one.

---

## Getting Your Credentials

### A) Meta Ads API — Access Token & Ad Account ID

**What you need:** `META_ACCESS_TOKEN` and `META_AD_ACCOUNT_ID`

1. Go to [developers.facebook.com](https://developers.facebook.com/) and log in with your Facebook account.
2. Click **My Apps** (top right) → **Create App**.
3. Choose **Other** as the use case, then **Business** as the type. Give it a name and click **Create**.
4. In your new app's dashboard, click **Add Product** and add **Marketing API**.
5. Go to **Tools → Graph API Explorer** from the top menu.
6. In the Explorer, click **Generate Access Token**. Select your app from the dropdown.
7. Under **Permissions**, add these:
   - `ads_read`
   - `ads_management`
   - `read_insights`
8. Click **Generate Access Token** and copy the token shown. Paste it as `META_ACCESS_TOKEN`.

> ⚠️ The token from the Explorer expires in ~60 days. For a long-lived token, ask your Meta Business Manager admin to generate a System User token from **Business Settings → System Users**.

**Finding your Ad Account ID:**

1. Go to [business.facebook.com/adsmanager](https://business.facebook.com/adsmanager).
2. Look at the URL — it will contain something like `act_123456789`.
3. Copy the number (with or without `act_` prefix) as `META_AD_ACCOUNT_ID`.

---

### B) Google Sheets — Service Account Credentials

**What you need:** `GOOGLE_SHEET_URL` and `GOOGLE_CREDENTIALS_JSON_PATH`

#### 1. Create a Google Cloud project and enable APIs

1. Go to [console.cloud.google.com](https://console.cloud.google.com/).
2. Click the project dropdown (top left) → **New Project**. Name it anything (e.g. `ads-report`).
3. In the search bar, search for **Google Sheets API** and click **Enable**.
4. Search for **Google Drive API** and click **Enable** as well.

#### 2. Create a Service Account

1. In the left menu, go to **IAM & Admin → Service Accounts**.
2. Click **Create Service Account**. Name it something like `ads-report-bot`.
3. Click **Done** (skip the optional role and user steps).

#### 3. Download the credentials JSON

1. Click on the service account you just created.
2. Go to the **Keys** tab → **Add Key → Create new key**.
3. Choose **JSON** and click **Create**. A file downloads automatically.
4. Move that file into the project folder and name it `credentials.json`.
5. Set `GOOGLE_CREDENTIALS_JSON_PATH=credentials.json` in your `.env`.

#### 4. Share your Google Sheet with the service account

1. Open your Google Sheet (or create a new one).
2. Copy the URL from your browser. Paste it as `GOOGLE_SHEET_URL` in your `.env`.
3. Click **Share** (top right of the sheet).
4. Open your `credentials.json` file and find the `"client_email"` field — it looks like `ads-report-bot@your-project.iam.gserviceaccount.com`.
5. Paste that email into the Share dialog and give it **Editor** access. Click **Send**.

> The script will automatically create a header row on first run.

---

### C) Telegram Bot

**What you need:** `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID`

#### 1. Create a bot with BotFather

1. Open Telegram and search for **@BotFather**.
2. Send the message `/newbot`.
3. Follow the prompts — give your bot a name (e.g. `Ads Report`) and a username (must end in `bot`, e.g. `my_ads_report_bot`).
4. BotFather will reply with a token like `123456789:ABCDEFabcdef`. Copy it as `TELEGRAM_BOT_TOKEN`.

#### 2. Get your Chat ID

**For a personal chat (just you):**
1. Open a chat with your new bot and send it any message (e.g. `/start`).
2. Visit this URL in your browser (replace `YOUR_TOKEN`):
   ```
   https://api.telegram.org/botYOUR_TOKEN/getUpdates
   ```
3. Look for `"chat": {"id": 123456789}` in the response. That number is your `TELEGRAM_CHAT_ID`.

**For a group chat:**
1. Add your bot to the group.
2. Send any message in the group.
3. Visit the same `getUpdates` URL above.
4. The group chat ID will be a negative number like `-1001234567890`. Use that as `TELEGRAM_CHAT_ID`.

---

## Running the Script

### Run once immediately (for testing)

```bash
python report.py --now
```

### Start the weekly scheduler

```bash
python report.py
```

The script will keep running and automatically send the report every Thursday at 09:00. Keep this terminal open, or run it as a background service (see below).

---

## Running as a Background Service (Optional)

If you want the script to run automatically even when the terminal is closed:

**On Mac/Linux using `nohup`:**

```bash
nohup python report.py > report.log 2>&1 &
```

**On a server using `systemd`** (Linux):

Create `/etc/systemd/system/ads-report.service`:

```ini
[Unit]
Description=Meta Ads Weekly Report
After=network.target

[Service]
WorkingDirectory=/path/to/meta_ads_report
ExecStart=/usr/bin/python3 report.py
Restart=always

[Install]
WantedBy=multi-user.target
```

Then run:

```bash
sudo systemctl enable ads-report
sudo systemctl start ads-report
```

---

## Troubleshooting

| Problem | Likely cause | Fix |
|---|---|---|
| `Missing required environment variable` | `.env` not filled in | Open `.env` and check all values are set |
| Meta API 190 error (invalid token) | Token expired | Generate a new access token |
| `Spreadsheet not found` | Sheet not shared with service account | Re-share the sheet with the `client_email` from `credentials.json` |
| Telegram `Unauthorized` | Wrong bot token | Double-check `TELEGRAM_BOT_TOKEN` in `.env` |
| Telegram `Chat not found` | Wrong chat ID | Redo the getUpdates step to find the correct ID |
| No data in sheet | No campaigns ran last 7 days | Check your Meta Ads account has active campaigns |

All errors are logged to `report.log` in the project folder.

---

## Metrics Explained

| Metric | Description |
|---|---|
| **Spend** | Total amount spent in USD |
| **Impressions** | Number of times your ads were shown |
| **Clicks** | Number of clicks on your ads |
| **CTR** | Click-through rate (clicks ÷ impressions × 100) |
| **CPM** | Cost per 1,000 impressions |
| **CPC** | Cost per click |
| **ROAS** | Return on ad spend (revenue ÷ spend). Only available if purchase tracking is set up. |
| **Reach** | Number of unique people who saw your ads |

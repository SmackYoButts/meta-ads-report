#!/usr/bin/env python3
"""
One-time Google setup script.
Run this once: python setup_google.py

It will:
  1. Open your browser for a Google sign-in (click Allow)
  2. Create a GCP project named 'ads-report'
  3. Enable Google Sheets + Drive APIs
  4. Create a service account and download credentials.json
  5. Share your Google Sheet with the service account
"""

import json
import os
import sys
import time
import webbrowser
from pathlib import Path

from dotenv import load_dotenv
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

load_dotenv()

SHEET_URL = os.getenv("GOOGLE_SHEET_URL", "")
CREDENTIALS_OUT = os.getenv("GOOGLE_CREDENTIALS_JSON_PATH", "credentials.json")

PROJECT_ID = "ads-report-auto"
PROJECT_NAME = "Ads Report"
SA_NAME = "ads-report-bot"
SA_DISPLAY = "Ads Report Bot"

SCOPES = [
    "https://www.googleapis.com/auth/cloud-platform",
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/spreadsheets",
]

# Public OAuth client from Google Cloud SDK — safe to use for personal scripts
CLIENT_CONFIG = {
    "installed": {
        "client_id": "32555940559.apps.googleusercontent.com",
        "client_secret": "ZmssLNjJy2998hD4CTg2ejr2",
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "redirect_uris": ["urn:ietf:wg:oauth:2.0:oob", "http://localhost"],
    }
}


def step(msg: str) -> None:
    print(f"\n{'='*60}\n{msg}\n{'='*60}")


def authenticate() -> Credentials:
    step("Step 1 — Sign in to Google")
    print("Your browser will open. Sign in and click Allow.")
    flow = InstalledAppFlow.from_client_config(CLIENT_CONFIG, scopes=SCOPES)
    creds = flow.run_local_server(port=0, open_browser=True)
    print("✅ Signed in successfully.")
    return creds


def get_or_create_project(creds: Credentials) -> str:
    step("Step 2 — Creating GCP project")
    rm = build("cloudresourcemanager", "v1", credentials=creds)

    # Check if project already exists
    try:
        rm.projects().get(projectId=PROJECT_ID).execute()
        print(f"✅ Project '{PROJECT_ID}' already exists.")
        return PROJECT_ID
    except HttpError:
        pass

    op = rm.projects().create(body={
        "projectId": PROJECT_ID,
        "name": PROJECT_NAME,
    }).execute()

    # Wait for project creation
    for _ in range(30):
        time.sleep(3)
        result = rm.operations().get(name=op["name"]).execute()
        if result.get("done"):
            break

    print(f"✅ Project '{PROJECT_ID}' created.")
    return PROJECT_ID


def enable_apis(creds: Credentials, project_id: str) -> None:
    step("Step 3 — Enabling Google Sheets + Drive APIs")
    su = build("serviceusage", "v1", credentials=creds)
    apis = [
        "sheets.googleapis.com",
        "drive.googleapis.com",
        "iam.googleapis.com",
    ]
    for api in apis:
        try:
            su.services().enable(
                name=f"projects/{project_id}/services/{api}"
            ).execute()
            print(f"  ✅ Enabled {api}")
        except HttpError as e:
            if "already enabled" in str(e).lower() or e.resp.status == 400:
                print(f"  ✅ {api} already enabled")
            else:
                print(f"  ⚠️  Could not enable {api}: {e}")
    time.sleep(5)  # let APIs propagate


def create_service_account(creds: Credentials, project_id: str) -> str:
    step("Step 4 — Creating service account")
    iam = build("iam", "v1", credentials=creds)
    sa_email = f"{SA_NAME}@{project_id}.iam.gserviceaccount.com"

    # Check if already exists
    try:
        iam.projects().serviceAccounts().get(
            name=f"projects/{project_id}/serviceAccounts/{sa_email}"
        ).execute()
        print(f"✅ Service account '{sa_email}' already exists.")
        return sa_email
    except HttpError:
        pass

    iam.projects().serviceAccounts().create(
        name=f"projects/{project_id}",
        body={
            "accountId": SA_NAME,
            "serviceAccount": {"displayName": SA_DISPLAY},
        },
    ).execute()
    print(f"✅ Service account created: {sa_email}")
    return sa_email


def download_key(creds: Credentials, project_id: str, sa_email: str) -> None:
    step("Step 5 — Downloading service account key")
    iam = build("iam", "v1", credentials=creds)
    key = iam.projects().serviceAccounts().keys().create(
        name=f"projects/{project_id}/serviceAccounts/{sa_email}",
        body={"privateKeyType": "TYPE_GOOGLE_CREDENTIALS_FILE"},
    ).execute()

    key_data = json.loads(
        __import__("base64").b64decode(key["privateKeyData"]).decode()
    )
    with open(CREDENTIALS_OUT, "w") as f:
        json.dump(key_data, f, indent=2)

    print(f"✅ credentials.json saved to: {Path(CREDENTIALS_OUT).resolve()}")


def share_sheet(creds: Credentials, sa_email: str) -> None:
    if not SHEET_URL:
        print("⚠️  GOOGLE_SHEET_URL not set in .env — skipping sheet share.")
        return

    step("Step 6 — Sharing Google Sheet with service account")

    # Extract sheet ID from URL
    try:
        sheet_id = SHEET_URL.split("/d/")[1].split("/")[0]
    except IndexError:
        print("⚠️  Could not parse sheet ID from GOOGLE_SHEET_URL.")
        return

    drive = build("drive", "v3", credentials=creds)
    drive.permissions().create(
        fileId=sheet_id,
        body={"type": "user", "role": "writer", "emailAddress": sa_email},
        sendNotificationEmail=False,
    ).execute()
    print(f"✅ Sheet shared with {sa_email}")


def main() -> None:
    print("\n🚀 Meta Ads Report — Google Setup\n")

    try:
        creds = authenticate()
        project_id = get_or_create_project(creds)
        enable_apis(creds, project_id)
        sa_email = create_service_account(creds, project_id)
        download_key(creds, project_id, sa_email)
        share_sheet(creds, sa_email)
    except KeyboardInterrupt:
        print("\nCancelled.")
        sys.exit(1)
    except HttpError as e:
        print(f"\n❌ Google API error: {e}")
        print("Make sure you signed in with an account that has Google Cloud access.")
        sys.exit(1)

    print("\n" + "="*60)
    print("✅ Setup complete! You can now run: python report.py --now")
    print("="*60 + "\n")


if __name__ == "__main__":
    main()

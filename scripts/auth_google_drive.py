#!/usr/bin/env python3
"""
Google Drive Authentication Script

Generates token.json using OAuth2 credentials.
"""

import os
import sys
from pathlib import Path

from google_auth_oauthlib.flow import InstalledAppFlow

# Allow localhost HTTP redirect
os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.shared.config.settings import get_settings

SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]


def main():
    try:
        print("=" * 80)
        print("Google Drive OAuth Setup")
        print("=" * 80)

        settings = get_settings()

        client_id = os.getenv("CLIENT_ID") or getattr(settings, "client_id", None)

        client_secret = os.getenv("CLIENT_SECRET") or getattr(
            settings, "client_secret", None
        )

        if not client_id:
            raise Exception("CLIENT_ID not found")

        if not client_secret:
            raise Exception("CLIENT_SECRET not found")

        print(f"Current Directory : {os.getcwd()}")
        print(f"Client ID Found   : {'YES' if client_id else 'NO'}")
        print(f"Client Secret     : {'YES' if client_secret else 'NO'}")

        client_config = {
            "installed": {
                "client_id": client_id,
                "project_id": "enterpriseiq-ai",
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
                "client_secret": client_secret,
                "redirect_uris": ["http://localhost:5000/", "http://127.0.0.1:5000/"],
            }
        }

        print("\nStarting OAuth flow...")

        flow = InstalledAppFlow.from_client_config(client_config, SCOPES)

        print("Waiting for Google authorization...")

        print("BEFORE OAuth")

        creds = flow.run_local_server(
            host="localhost",
            port=5000,
            open_browser=True,
            success_message=("Authentication successful. You may close this window."),
        )

        print("AFTER OAuth")

        print("\nOAuth completed successfully!")

        if not creds:
            raise Exception("Credentials object is empty")

        print(f"Access Token Exists  : {bool(creds.token)}")
        print(f"Refresh Token Exists : {bool(creds.refresh_token)}")

        token_path = Path(__file__).resolve().parent / "token.json"

        print(f"\nWriting token file:")
        print(token_path)

        with open(token_path, "w") as token:
            token.write(creds.to_json())

        if not token_path.exists():
            raise Exception("token.json was not created")

        print("\n" + "=" * 80)
        print("SUCCESS")
        print("=" * 80)
        print(f"token.json generated at:\n{token_path}")

        print("\nToken Content Preview:")
        print("-" * 40)

        with open(token_path, "r") as f:
            data = f.read()

        print(data[:300])
        print("...")

    except Exception as e:
        print("\n" + "=" * 80)
        print("ERROR")
        print("=" * 80)
        print(str(e))
        raise


if __name__ == "__main__":
    main()

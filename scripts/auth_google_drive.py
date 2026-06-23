#!/usr/bin/env python3
"""
Google Drive Authentication Script.
Run this script locally to generate the `token.json` file.
It requires the CLIENT_ID and CLIENT_SECRET from your .env file.
"""

import os
import sys
import json
from google_auth_oauthlib.flow import InstalledAppFlow

# Fix for CSRF State Mismatch errors over localhost HTTP
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.shared.config.settings import get_settings

SCOPES = ['https://www.googleapis.com/auth/drive.readonly']


def main():
    settings = get_settings()
    client_id = os.getenv("CLIENT_ID") or getattr(settings, "client_id", None)
    client_secret = os.getenv("CLIENT_SECRET") or getattr(settings, "client_secret", None)

    if not client_id or not client_secret:
        print("Error: CLIENT_ID or CLIENT_SECRET not found in .env")
        sys.exit(1)

    # We need to construct a client_secret.json dictionary on the fly for InstalledAppFlow
    client_config = {
        "installed": {
            "client_id": client_id,
            "project_id": "enterpriseiq-ai",
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
            "client_secret": client_secret,
            "redirect_uris": ["http://localhost:5000/"]
        }
    }

    print("Initiating Google Drive authentication flow...")
    flow = InstalledAppFlow.from_client_config(client_config, SCOPES)
    creds = flow.run_local_server(port=5000, prompt='consent')

    # Save the credentials for the next run
    with open('token.json', 'w') as token:
        token.write(creds.to_json())

    print("\n✅ Success! token.json has been generated in the current directory.")
    print("The backend can now use GoogleDriveClient to access your Drive.")

if __name__ == '__main__':
    main()

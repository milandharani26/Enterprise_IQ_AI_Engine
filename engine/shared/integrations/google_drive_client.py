"""Google Drive API Client for retrieving and downloading files."""

import io
import os
import json
import logging
from typing import List, Dict, Any, Optional

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

from engine.shared.config.settings import get_settings

logger = logging.getLogger(__name__)

SCOPES = ['https://www.googleapis.com/auth/drive.readonly']


class GoogleDriveClient:
    """Wrapper for the Google Drive API v3."""

    def __init__(self, token_path: str = "token.json"):
        self.settings = get_settings()
        self.token_path = token_path
        self.creds = None
        self.service = None
        self._authenticate()

    def _authenticate(self):
        """Load tokens from local token.json or initiate flow if missing."""
        if os.path.exists(self.token_path):
            try:
                self.creds = Credentials.from_authorized_user_file(self.token_path, SCOPES)
            except Exception as e:
                logger.warning(f"Failed to load token.json: {e}")

        # If there are no (valid) credentials available, let the user log in.
        # However, typically the server won't be able to run InstalledAppFlow interactively.
        # That's why the local auth script should be run first.
        if not self.creds or not self.creds.valid:
            if self.creds and self.creds.expired and self.creds.refresh_token:
                try:
                    self.creds.refresh(Request())
                    with open(self.token_path, 'w') as token:
                        token.write(self.creds.to_json())
                except Exception as e:
                    logger.error(f"Failed to refresh Google token: {e}")
                    raise Exception("Google token expired and could not be refreshed. Please re-authenticate.")
            else:
                raise Exception(
                    "No valid Google credentials found. Please run scripts/auth_google_drive.py first "
                    "to generate the token.json file."
                )

        self.service = build('drive', 'v3', credentials=self.creds)

    def list_files(self, query: str = None, page_size: int = 50) -> List[Dict[str, Any]]:
        """
        List files matching the query.
        Example query: "mimeType='application/pdf'" or "'root' in parents"
        """
        try:
            # We request relevant fields including id, name, webViewLink, owners, etc.
            fields = "nextPageToken, files(id, name, mimeType, webViewLink, webContentLink, size, owners, modifiedTime, parents)"
            
            # If no query provided, exclude folders by default
            if query is None:
                query = "mimeType != 'application/vnd.google-apps.folder'"

            results = self.service.files().list(
                q=query,
                pageSize=page_size,
                fields=fields,
                spaces='drive'
            ).execute()
            
            files = results.get('files', [])
            return files
        except Exception as e:
            logger.error(f"Failed to list Google Drive files: {e}")
            raise

    def download_file(self, file_id: str, mime_type: str) -> bytes:
        """
        Download a file's contents from Google Drive.
        Google Docs/Sheets/Slides need to be exported, other files are downloaded directly.
        """
        try:
            if mime_type.startswith('application/vnd.google-apps.'):
                # It's a Google Workspace document, we must export it
                export_mime_type = "application/pdf" # Default fallback
                if "document" in mime_type:
                    export_mime_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                elif "spreadsheet" in mime_type:
                    export_mime_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                elif "presentation" in mime_type:
                    export_mime_type = "application/vnd.openxmlformats-officedocument.presentationml.presentation"

                request = self.service.files().export_media(fileId=file_id, mimeType=export_mime_type)
            else:
                # It's a binary file (PDF, image, etc.)
                request = self.service.files().get_media(fileId=file_id)

            fh = io.BytesIO()
            downloader = MediaIoBaseDownload(fh, request)
            done = False
            while done is False:
                status, done = downloader.next_chunk()
            
            return fh.getvalue()
        except Exception as e:
            logger.error(f"Failed to download Google Drive file {file_id}: {e}")
            raise

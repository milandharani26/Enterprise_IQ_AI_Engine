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

    def __init__(self, token_path: str = "token.json", auth_data: dict = None):
        self.settings = get_settings()
        self.token_path = token_path
        self.auth_data = auth_data
        self.creds = None
        self.service = None
        self._authenticate()

    def _authenticate(self):
        """Load tokens from auth_data dict or local token.json."""
        if self.auth_data:
            try:
                # If the DB stored the exact token.json content
                if 'json_content' in self.auth_data:
                    info = self.auth_data['json_content']
                    stored_scopes = info.get('scopes') or SCOPES
                    self.creds = Credentials.from_authorized_user_info(info, stored_scopes)
                else:
                    self.creds = Credentials.from_authorized_user_info(self.auth_data, SCOPES)
            except Exception as e:
                logger.warning(f"Failed to load credentials from auth_data: {e}")
        elif os.path.exists(self.token_path):
            try:
                self.creds = Credentials.from_authorized_user_file(self.token_path, SCOPES)
            except Exception as e:
                logger.warning(f"Failed to load token.json: {e}")

        # If there are no (valid) credentials available
        if not self.creds or not self.creds.valid:
            if self.creds and self.creds.expired and self.creds.refresh_token:
                try:
                    self.creds.refresh(Request())
                    # We won't try to write back to token_path if we used auth_data
                    if not self.auth_data:
                        with open(self.token_path, 'w') as token:
                            token.write(self.creds.to_json())
                except Exception as e:
                    logger.error(f"Failed to refresh Google token: {e}")
                    raise Exception("Google token expired and could not be refreshed. Please re-authenticate.")
            else:
                raise Exception(
                    "No valid Google credentials found. Please provide valid auth_data or token.json."
                )

        self.service = build('drive', 'v3', credentials=self.creds)

    def list_files(self, query: str = None, page_size: int = 50, fetch_all: bool = False) -> List[Dict[str, Any]]:
        """
        List files matching the query.
        Example query: "mimeType='application/pdf'" or "'root' in parents"
        """
        try:
            # We request relevant fields including id, name, webViewLink, owners, etc.
            fields = "nextPageToken, files(id, name, mimeType, webViewLink, webContentLink, size, owners, modifiedTime, parents)"
            
            # If no query provided, exclude unsupported Google Apps types by default
            if query is None:
                query = (
                    "trashed = false and "
                    "mimeType != 'application/vnd.google-apps.folder' and "
                    "mimeType != 'application/vnd.google-apps.shortcut' and "
                    "mimeType != 'application/vnd.google-apps.form' and "
                    "mimeType != 'application/vnd.google-apps.site' and "
                    "mimeType != 'application/vnd.google-apps.map'"
                )

            all_files = []
            page_token = None
            
            while True:
                results = self.service.files().list(
                    q=query,
                    pageSize=page_size,
                    fields=fields,
                    spaces='drive',
                    pageToken=page_token,
                    supportsAllDrives=True,
                    includeItemsFromAllDrives=True
                ).execute()
                
                files = results.get('files', [])
                all_files.extend(files)
                
                page_token = results.get('nextPageToken')
                if not fetch_all or not page_token:
                    break
                    
            return all_files
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
                request = self.service.files().get_media(fileId=file_id, acknowledgeAbuse=True)

            fh = io.BytesIO()
            downloader = MediaIoBaseDownload(fh, request)
            done = False
            while done is False:
                status, done = downloader.next_chunk()
            
            return fh.getvalue()
        except Exception as e:
            logger.error(f"Failed to download Google Drive file {file_id}: {e}")
            raise

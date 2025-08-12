"""GDrive API client"""

import io
import logging

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from googleapiclient.errors import HttpError

logger = logging.getLogger(__name__)


class GDrive:
    def __init__(self, secrets_file_path: str = "service_secrets.json") -> None:
        self.scope = ["https://www.googleapis.com/auth/drive"]
        self.credentials = service_account.Credentials.from_service_account_file(
            filename=secrets_file_path, scopes=self.scope
        )
        self.service = build("drive", "v3", credentials=self.credentials)

    def find_file(self, folder_id: str, filename: str = "") -> list[dict]:
        """Find files matching a name in a Google Drive folder"""
        try:
            # Build query
            query_parts = []
            if folder_id:
                query_parts.append(f"'{folder_id}' in parents")
            query_parts.append("trashed=false")
            if filename:
                query_parts.append(f"name='{filename}'")

            query = " and ".join(query_parts)

            results = (
                self.service.files()
                .list(
                    q=query,
                    pageSize=1000,
                    fields="nextPageToken, files(id, name, mimeType, size, modifiedTime, parents)",
                )
                .execute()
            )

            return results.get("files", [])
        except HttpError as error:
            logger.error(f"An error occurred while listing files: {error}")
            return []

    def download_file(self, file_id: str, file_name: str) -> io.BytesIO:
        """Download a file from Google Drive"""
        try:
            request = self.service.files().get_media(fileId=file_id)
            file_content = io.BytesIO()
            downloader = MediaIoBaseDownload(file_content, request)

            done = False
            while done is False:
                status, done = downloader.next_chunk()

            file_content.seek(0)
            return file_content
        except HttpError as error:
            logger.error(f"An error occurred while downloading {file_name}: {error}")
            return None

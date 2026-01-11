"""GDrive API client"""

import io
import logging
from typing import TYPE_CHECKING, Any

from google.oauth2 import service_account
from googleapiclient.discovery import build  # type: ignore[import-untyped]
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseDownload

from exceptions import GDriveError

if TYPE_CHECKING:
    from googleapiclient._apis.drive.v3.resources import (  # type: ignore[import-not-found]
        DriveResource,
    )
    from googleapiclient._apis.drive.v3.schemas import (  # type: ignore[import-not-found]
        File,
    )

logger = logging.getLogger(__name__)


class GDrive:
    def __init__(self, secrets_file_path: str = "service_secrets.json") -> None:
        """Initialise GDrive client"""
        credentials: Any = service_account.Credentials.from_service_account_file(  # type: ignore[misc]
            filename=secrets_file_path,
            scopes=["https://www.googleapis.com/auth/drive.readonly"],
        )
        self.service: DriveResource = build("drive", "v3", credentials=credentials)

    def find_file(self, folder_id: str, filename: str = "") -> list[File]:
        """Find files matching a name in a Google Drive folder"""
        query = f"'{folder_id}' in parents and trashed=false"
        if filename:
            query += f" and name='{filename}'"

        try:
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
            raise GDriveError(
                f"Failed to list files in folder {folder_id}: {error}"
            ) from error

    def download_file(self, file_id: str) -> io.BytesIO:
        """Download a file from Google Drive"""
        try:
            request = self.service.files().get_media(fileId=file_id)
            file_content = io.BytesIO()
            downloader = MediaIoBaseDownload(file_content, request)

            done = False
            while done is False:
                _, done = downloader.next_chunk()  # type: ignore[misc]

            file_content.seek(0)
            return file_content
        except HttpError as error:
            raise GDriveError(f"Failed to download file {file_id}: {error}") from error

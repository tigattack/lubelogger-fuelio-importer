"""GDrive API client"""

import enum
import logging

from pydrive2.auth import GoogleAuth
from pydrive2.drive import GoogleDrive
from pydrive2.files import GoogleDriveFile

logger = logging.getLogger(__name__)


class GDrive:
    def __init__(self) -> None:
        self.auth = self.drive_service_auth()
        self.drive = GoogleDrive(self.auth)

    def drive_service_auth(self) -> GoogleAuth:
        """
        Performs non-interactive authentication with
        Google Drive API using service account credentials
        """
        auth_settings = {
            "client_config_backend": "service",
            "service_config": {"client_json_file_path": "service_secrets.json"},
        }
        gauth = GoogleAuth(settings=auth_settings)
        gauth.ServiceAuth()
        return gauth

    def find_file(self, folder_id: str, filename: str = "") -> list[GoogleDriveFile]:
        """Find files matching a name in a Google Drive folder"""
        query = {
            "q": (
                f"'{folder_id}' in parents and trashed=false"
                + " and title='"
                + filename
                + "'"
                if filename
                else ""
            )
        }
        return self.drive.ListFile(query).GetList()

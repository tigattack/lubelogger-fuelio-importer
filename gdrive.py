"""GDrive API client"""

import enum
import logging
import sys
import warnings

from pydrive2.auth import AuthenticationError, GoogleAuth
from pydrive2.drive import GoogleDrive
from pydrive2.files import GoogleDriveFile

logger = logging.getLogger(__name__)


class AuthType(enum.Enum):
    SERVICE = "service"
    CLIENT = "client"


class GDrive:
    def __init__(self, auth_type: AuthType) -> None:
        assert auth_type in AuthType, "Invalid auth_type"

        if auth_type == AuthType.SERVICE:
            self.auth = self.drive_service_auth()
        elif auth_type == AuthType.CLIENT:
            self.auth = self.drive_client_auth()

        self.drive = GoogleDrive(self.auth)

    def drive_service_auth(self) -> GoogleAuth:
        """
        Performs non-interactive authentication with
        Google Drive API using service account credentials
        """
        auth_settings = {
            "client_config_backend": "service",
            "service_config": {
                "client_json_file_path": "service_secrets.json"
            }
        }
        gauth = GoogleAuth(settings=auth_settings)
        gauth.ServiceAuth()
        return gauth

    def drive_client_auth(self) -> GoogleAuth:
        """
        Performs interactive authentication with
        Google Drive API using client credentials
        """
        gauth = GoogleAuth()

        warnings.filterwarnings("ignore")

        gauth.LoadCredentialsFile("cached_creds.txt")
        if gauth.credentials is None:
            try:
                gauth.LocalWebserverAuth()
            except AuthenticationError:
                print("Authentication failed")
                sys.exit(1)
        elif gauth.access_token_expired:
            gauth.Refresh()
        else:
            gauth.Authorize()
        gauth.SaveCredentialsFile("mycreds.txt")

        return gauth

    def find_file(self, folder_id: str, filename: str = "") -> list[GoogleDriveFile]:
        """Find files matching a name in a Google Drive folder"""
        query = {
            'q': f"'{folder_id}' in parents and trashed=false" + 
                 " and title='" + filename + "'" if filename else ''
        }
        return self.drive.ListFile(query).GetList()

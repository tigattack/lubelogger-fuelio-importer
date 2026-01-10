import logging

import requests
from requests.auth import HTTPBasicAuth

from models import LubeloggerFillup, LubeloggerVehicleInfo

logger = logging.getLogger(__name__)


class Lubelogger:
    """Lubelogger API client"""

    def __init__(self, url: str, username: str, password: str):
        self.url = url
        self.username = username
        self.password = password
        self.session = requests.Session()
        self.session.auth = HTTPBasicAuth(self.username, self.password)
        self.session.headers.update({"culture-invariant": "true"})
        self.timeout = 10

    def get_fillups(self, vehicle_id: int) -> list[LubeloggerFillup]:
        """Get all fuel fillup logs from Lubelogger"""
        params = {"vehicleId": vehicle_id}
        response = None
        try:
            response = self.session.get(
                f"{self.url}/api/vehicle/gasrecords",
                params=params,
                timeout=self.timeout,
            )
            response.raise_for_status()
        except requests.exceptions.ReadTimeout:
            logger.error("Lubelogger API timed out while fetching fillups")
            return []
        except requests.exceptions.HTTPError as exc:
            logger.error(
                "HTTP error fetching fillups: %s (status: %s)",
                exc,
                response.status_code if response else "unknown",
            )
            return []
        except requests.exceptions.RequestException as exc:
            logger.error("Request error fetching fillups: %s", exc)
            return []

        return [LubeloggerFillup.from_api_response(f) for f in response.json()]

    def add_fillup(
        self, vehicle_id: int, fillup: LubeloggerFillup
    ) -> requests.Response | None:
        """Add a fuel fillup log to Lubelogger"""
        params = {"vehicleId": vehicle_id}
        response = None
        try:
            response = self.session.post(
                f"{self.url}/api/vehicle/gasrecords/add",
                data=fillup.to_api_dict(),
                params=params,
                timeout=self.timeout,
            )
            response.raise_for_status()
            return response
        except requests.exceptions.ReadTimeout:
            logger.error("Lubelogger API timed out while adding fillup")
            return None
        except requests.exceptions.HTTPError as exc:
            logger.error(
                "HTTP error adding fillup: %s (status: %s)",
                exc,
                response.status_code if response else "unknown",
            )
            return None
        except requests.exceptions.RequestException as exc:
            logger.error("Request error adding fillup: %s", exc)
            return None

    def get_vehicle_info(self, vehicle_id: int) -> LubeloggerVehicleInfo | None:
        """Get vehicle info from Lubelogger"""
        params = {"vehicleId": vehicle_id}
        response = None
        try:
            response = self.session.get(
                f"{self.url}/api/vehicle/info",
                params=params,
                timeout=self.timeout,
            )
            response.raise_for_status()
            data = response.json()
            # API returns a list with a single element containing vehicleData
            if data and len(data) > 0 and "vehicleData" in data[0]:
                return LubeloggerVehicleInfo.from_api_response(data[0]["vehicleData"])
            return None
        except requests.exceptions.ReadTimeout:
            logger.error("Lubelogger API timed out while fetching vehicle info")
            return None
        except requests.exceptions.HTTPError as exc:
            logger.error(
                "HTTP error fetching vehicle info: %s (status: %s)",
                exc,
                response.status_code if response else "unknown",
            )
            return None
        except requests.exceptions.RequestException as exc:
            logger.error("Request error fetching vehicle info: %s", exc)
            return None

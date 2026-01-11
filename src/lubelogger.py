"""Lubelogger API client"""

import logging

import requests
from requests.auth import HTTPBasicAuth

from exceptions import LubeloggerAPIError
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
        except requests.exceptions.ReadTimeout as exc:
            raise LubeloggerAPIError(
                f"API timed out while fetching fillups for vehicle {vehicle_id}"
            ) from exc
        except requests.exceptions.HTTPError as exc:
            status = response.status_code if response else "unknown"
            raise LubeloggerAPIError(
                f"HTTP {status} error fetching fillups for vehicle {vehicle_id}: {exc}"
            ) from exc
        except requests.exceptions.RequestException as exc:
            raise LubeloggerAPIError(
                f"Request failed while fetching fillups for vehicle {vehicle_id}: {exc}"
            ) from exc

        return [LubeloggerFillup.from_api_response(f) for f in response.json()]

    def add_fillup(
        self, vehicle_id: int, fillup: LubeloggerFillup
    ) -> requests.Response:
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
        except requests.exceptions.ReadTimeout as exc:
            raise LubeloggerAPIError(
                f"API timed out while adding fillup to vehicle {vehicle_id}"
            ) from exc
        except requests.exceptions.HTTPError as exc:
            status = response.status_code if response else "unknown"
            raise LubeloggerAPIError(
                f"HTTP {status} error adding fillup to vehicle {vehicle_id}: {exc}"
            ) from exc
        except requests.exceptions.RequestException as exc:
            raise LubeloggerAPIError(
                f"Request failed while adding fillup to vehicle {vehicle_id}: {exc}"
            ) from exc

    def get_vehicle_info(self, vehicle_id: int) -> LubeloggerVehicleInfo:
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
            raise LubeloggerAPIError(
                f"Vehicle {vehicle_id} not found or invalid response format"
            )
        except requests.exceptions.ReadTimeout as exc:
            raise LubeloggerAPIError(
                f"API timed out while fetching info for vehicle {vehicle_id}"
            ) from exc
        except requests.exceptions.HTTPError as exc:
            status = response.status_code if response else "unknown"
            raise LubeloggerAPIError(
                f"HTTP {status} error fetching info for vehicle {vehicle_id}: {exc}"
            ) from exc
        except requests.exceptions.RequestException as exc:
            raise LubeloggerAPIError(
                f"Request failed while fetching info for vehicle {vehicle_id}: {exc}"
            ) from exc

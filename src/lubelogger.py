"""LubeLogger API client"""

import logging

import requests
from requests.auth import HTTPBasicAuth

from exceptions import LubeLoggerAPIError
from models import (
    LubeLoggerAddFuelRecordResponse,
    LubeLoggerFuelRecord,
    LubeLoggerVehicleInfo,
)

logger = logging.getLogger(__name__)


class LubeLogger:
    """LubeLogger API client"""

    def __init__(self, url: str, username: str, password: str):
        self.url = url
        self.username = username
        self.password = password
        self.session = requests.Session()
        self.session.auth = HTTPBasicAuth(self.username, self.password)
        self.session.headers.update({"culture-invariant": "true"})
        self.timeout = 10

    def get_fuel_records(self, vehicle_id: int) -> list[LubeLoggerFuelRecord]:
        """Get all fuel record logs from LubeLogger"""
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
            raise LubeLoggerAPIError(
                f"API timed out while fetching fuel records for vehicle {vehicle_id}"
            ) from exc
        except requests.exceptions.HTTPError as exc:
            status = response.status_code if response else "unknown"
            raise LubeLoggerAPIError(
                f"HTTP {status} error fetching fuel records for vehicle {vehicle_id}: {exc}"
            ) from exc
        except requests.exceptions.RequestException as exc:
            raise LubeLoggerAPIError(
                f"Request failed while fetching fuel records for vehicle {vehicle_id}: {exc}"
            ) from exc

        return [LubeLoggerFuelRecord.from_api_response(f) for f in response.json()]

    def add_fuel_record(
        self, vehicle_id: int, fuel_record: LubeLoggerFuelRecord
    ) -> LubeLoggerAddFuelRecordResponse:
        """Add a fuel record log to LubeLogger"""
        params = {"vehicleId": vehicle_id}
        response = None
        try:
            response = self.session.post(
                f"{self.url}/api/vehicle/gasrecords/add",
                data=fuel_record.to_api_dict(),
                params=params,
                timeout=self.timeout,
            )
            response.raise_for_status()
            return LubeLoggerAddFuelRecordResponse.from_api_response(response.json())
        except requests.exceptions.ReadTimeout as exc:
            raise LubeLoggerAPIError(
                f"API timed out while adding fuel record to vehicle {vehicle_id}"
            ) from exc
        except requests.exceptions.HTTPError as exc:
            status = response.status_code if response else "unknown"
            raise LubeLoggerAPIError(
                f"HTTP {status} error adding fuel record to vehicle {vehicle_id}: {exc}"
            ) from exc
        except requests.exceptions.RequestException as exc:
            raise LubeLoggerAPIError(
                f"Request failed while adding fuel record to vehicle {vehicle_id}: {exc}"
            ) from exc

    def get_vehicle_info(self, vehicle_id: int) -> LubeLoggerVehicleInfo:
        """Get vehicle info from LubeLogger"""
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
                return LubeLoggerVehicleInfo.from_api_response(data[0]["vehicleData"])
            raise LubeLoggerAPIError(
                f"Vehicle {vehicle_id} not found or invalid response format"
            )
        except requests.exceptions.ReadTimeout as exc:
            raise LubeLoggerAPIError(
                f"API timed out while fetching info for vehicle {vehicle_id}"
            ) from exc
        except requests.exceptions.HTTPError as exc:
            status = response.status_code if response else "unknown"
            raise LubeLoggerAPIError(
                f"HTTP {status} error fetching info for vehicle {vehicle_id}: {exc}"
            ) from exc
        except requests.exceptions.RequestException as exc:
            raise LubeLoggerAPIError(
                f"Request failed while fetching info for vehicle {vehicle_id}: {exc}"
            ) from exc

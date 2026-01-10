import logging
from dataclasses import asdict, dataclass

import requests
from requests.auth import HTTPBasicAuth

logger = logging.getLogger(__name__)

def to_camel_case(snake_str):
    """Convert snake_case string to camelCase"""
    camel_string = "".join(x.capitalize() for x in snake_str.lower().split("_"))
    return snake_str[0].lower() + camel_string[1:]


@dataclass
class LubeloggerFillup:
    """Lubelogger fuel fillup object"""

    date: str
    odometer: int
    fuel_consumed: float
    cost: float
    is_fill_to_full: bool
    missed_fuel_up: bool
    notes: str = ""

    def to_dict(self) -> dict:
        """Return fillup as dict"""
        return asdict(self)

    def to_api_dict(self) -> dict:
        """Return fillup as dict for Lubelogger API (camelCase keys)"""
        return {to_camel_case(k): v for k, v in asdict(self).items()}

    @classmethod
    def from_api_response(cls, data: dict) -> "LubeloggerFillup":
        """Create a LubeloggerFillup from Lubelogger API response data"""
        return cls(
            date=data["date"],
            odometer=int(data["odometer"]),
            fuel_consumed=data["fuelConsumed"],
            cost=data["cost"],
            is_fill_to_full=data["isFillToFull"],
            missed_fuel_up=data["missedFuelUp"],
            notes=data["notes"] if data["notes"] else "",
        )


class Lubelogger:
    """Lubelogger API client"""

    def __init__(self, url: str, username: str, password: str):
        self.url = url
        self.username = username
        self.password = password
        self.session = requests.Session()
        self.session.auth = HTTPBasicAuth(self.username, self.password)
        self.session.headers.update({"culture-invariant": "true"})

    def get_fillups(self, vehicle_id: int) -> list[LubeloggerFillup]:
        """Get all fuel fillup logs from Lubelogger"""
        params = {"vehicleId": vehicle_id}
        try:
            response = self.session.get(
                f"{self.url}/api/vehicle/gasrecords",
                params=params,
                timeout=10,
            )
        except requests.exceptions.ReadTimeout:
            logger.error("Lubelogger API timed out")
            return []

        try:
            response.raise_for_status()
        except requests.exceptions.HTTPError as exc:
            logger.error(exc)
            return []

        return [LubeloggerFillup.from_api_response(f) for f in response.json()]

    def add_fillup(self, vehicle_id: int, fillup: LubeloggerFillup):
        """Add a fuel fillup log to Lubelogger"""
        params = {"vehicleId": vehicle_id}
        try:
            response = self.session.post(
                f"{self.url}/api/vehicle/gasrecords/add",
                fillup.to_api_dict(),
                params=params,
                timeout=10,
            )
            response.raise_for_status()
            return response
        except requests.exceptions.HTTPError as exc:
            logger.error(exc)
        except requests.exceptions.ReadTimeout:
            logger.error("Lubelogger API timed out")

    def get_vehicle_info(self, vehicle_id: int) -> dict | None:
        """Get vehicle info from Lubelogger"""
        params = {"vehicleId": vehicle_id}
        try:
            response = self.session.get(
                f"{self.url}/api/vehicle/info",
                params=params,
                timeout=10,
            )
            response.raise_for_status()
            data = response.json()
            # API returns a list with a single element containing vehicleData
            if data and len(data) > 0 and "vehicleData" in data[0]:
                return data[0]["vehicleData"]
            return None
        except requests.exceptions.ReadTimeout:
            logger.error("Lubelogger API timed out while fetching vehicle info")
            return None
        except requests.exceptions.HTTPError as exc:
            logger.error(exc)
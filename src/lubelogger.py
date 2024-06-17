import logging
from dataclasses import asdict, dataclass

import requests
from requests.auth import HTTPBasicAuth

logger = logging.getLogger(__name__)


def to_lower_camel_case(snake_str):
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
        return dict(asdict(self).items())

    def to_lubelogger_api_format(self) -> dict:
        """Return fillup as dict for use in Lubelogger API"""
        return {to_lower_camel_case(k): v for k, v in asdict(self).items()}


class Lubelogger:
    """Lubelogger API client"""

    def __init__(self, url: str, username: str, password: str):
        self.url = url
        self.username = username
        self.password = password
        self.session = requests.Session()
        self.session.auth = HTTPBasicAuth(self.username, self.password)

    def _create_fillup(self, fillup) -> LubeloggerFillup:
        return LubeloggerFillup(
            fillup["date"],
            int(fillup["odometer"]),
            fillup["fuelConsumed"],
            fillup["cost"],
            fillup["isFillToFull"] == "True",
            fillup["missedFuelUp"] == "True",
            fillup["notes"] if fillup["notes"] else "",
        )

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

        fillups = []
        for fillup in response.json():
            fillups.append(self._create_fillup(fillup))

        return fillups

    def add_fillup(self, vehicle_id: int, fillup: LubeloggerFillup):
        """Add a fuel fillup log to Lubelogger"""
        params = {"vehicleId": vehicle_id}
        try:
            response = self.session.post(
                f"{self.url}/api/vehicle/gasrecords/add",
                fillup.to_lubelogger_api_format(),
                params=params,
                timeout=10,
            )
        except requests.exceptions.ReadTimeout:
            logger.error("Lubelogger API timed out")

        try:
            response.raise_for_status()
        except requests.exceptions.HTTPError as exc:
            logger.error(exc)

        return response

    def get_vehicle_info(self, vehicle_id: int) -> dict:
        """Get vehicle info from Lubelogger"""
        try:
            response = self.session.get(
                f"{self.url}/api/vehicles",
                timeout=10,
            )
        except requests.exceptions.ReadTimeout:
            logger.error("Lubelogger API timed out")
            return {}

        try:
            response.raise_for_status()
        except requests.exceptions.HTTPError as exc:
            logger.error(exc)
            return {}

        try:
            return [v for v in response.json() if v["id"] == vehicle_id][0]
        except IndexError as exc:
            raise ValueError(f"No vehicle found with ID {vehicle_id}") from exc

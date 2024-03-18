import logging
from dataclasses import asdict, dataclass

import requests
from requests.auth import HTTPBasicAuth

logger = logging.getLogger(__name__)





@dataclass(frozen=True)
class LubeloggerFillup:
    """Lubelogger fuel fillup object"""

    date: str
    odometer: int
    fuel_consumed: float
    cost: float
    is_fill_to_full: bool
    missed_fuel_up: bool
    notes: str = ""

    @property
    def as_dict(self) -> dict:
        """Return fillup as dict"""
        return asdict(self)

    def __eq__(self, __value: object) -> bool:
        if type(__value) != LubeloggerFillup:
            raise ValueError(f"'==' not supported between instances of {type(self)} and {type(__value)}")
        return __value.date == self.date and self.odometer == self.odometer

    def __iter__(self):
        return iter(self.as_dict.items())

    def __getitem__(self, key):
        return self.as_dict[key]

class Lubelogger:
    """Lubelogger API client"""

    def __init__(self, url: str, username: str, password: str):
        self.url = url
        self.username = username
        self.password = password
        self.session = requests.Session()
        self.session.auth = HTTPBasicAuth(self.username, self.password)

    @staticmethod
    def _to_lower_camel_case(snake_str):
        camel_string = "".join(x.capitalize() for x in snake_str.lower().split("_"))
        return snake_str[0].lower() + camel_string[1:]

    def _to_api_format(self, lube_logger_fillup: LubeloggerFillup) -> dict:
        """Return fillup as dict for use in Lubelogger API"""
        return {self._to_lower_camel_case(k): v for k, v in lube_logger_fillup}

    def _create_fillup(self, fillup) -> LubeloggerFillup:
        return LubeloggerFillup(
            fillup["date"],
            int(fillup["odometer"]),
            fillup["fuelConsumed"],
            fillup["cost"],
            fillup["isFillToFull"] == "True",
            fillup["missedFuelUp"] == "True",
            fillup["notes"] if fillup["notes"] else ""
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
            fillups.append(self._create_fillup(fillup=fillup))

        return fillups

    def add_fillup(self, vehicle_id: int, fillup: LubeloggerFillup):
        """Add a fuel fillup log to Lubelogger"""
        params = {"vehicleId": vehicle_id}
        try:
            response = self.session.post(
                f"{self.url}/api/vehicle/gasrecords/add",
                self._to_api_format(fillup),
                params=params,
                timeout=10,
            )
        except requests.exceptions.ReadTimeout:
            logger.error(msg="Lubelogger API timed out")

        try:
            response.raise_for_status()
        except requests.exceptions.HTTPError as exc:
            logger.error(exc)

        return response

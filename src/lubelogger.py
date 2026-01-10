import logging
from dataclasses import asdict, dataclass, field

import requests
from requests.auth import HTTPBasicAuth

logger = logging.getLogger(__name__)

# Keys to drop when sending fillup data to the API or comparing fillups
FILLUP_IGNORE_KEYS = [
    "id",
    "fuel_economy",
    "extra_fields",
    "files",
]


# Source - https://stackoverflow.com/a/19053800
# Posted by jbaiter, modified by community. See post 'Timeline' for change history
# Retrieved 2024-03-15, License - CC BY-SA 4.0
# Further modified by tigattack
def to_camel_case(snake_str):
    """Convert snake_case string to camelCase"""
    camel_string = "".join(x.capitalize() for x in snake_str.lower().split("_"))
    return snake_str[0].lower() + camel_string[1:]


def from_camel_case(camel_str):
    """Convert camelCase string to snake_case"""
    result = []
    for i, char in enumerate(camel_str):
        if char.isupper() and i > 0:
            result.append("_")
        result.append(char.lower())
    return "".join(result)


@dataclass
class LubeloggerFillup:
    """Lubelogger fuel fillup object"""

    date: str
    odometer: int
    fuel_consumed: float
    cost: float
    is_fill_to_full: bool
    missed_fuel_up: bool
    id: int | None = None
    fuel_economy: float = 0
    notes: str = ""
    tags: str = ""
    extra_fields: list = field(default_factory=list)
    files: list = field(default_factory=list)

    def to_dict(self) -> dict:
        """Return fillup as dict"""
        return asdict(self)

    def to_api_dict(self) -> dict:
        """Return fillup as dict for Lubelogger API (camelCase keys)"""
        data = asdict(self)
        for key in FILLUP_IGNORE_KEYS:
            data.pop(key, None)
        return {to_camel_case(k): v for k, v in data.items()}

    @classmethod
    def from_api_response(cls, data: dict) -> "LubeloggerFillup":
        """Create a LubeloggerFillup from Lubelogger API response data"""
        snake_case_data = {from_camel_case(k): v for k, v in data.items()}
        return cls(**snake_case_data)


@dataclass
class LubeloggerVehicleInfo:
    """Lubelogger vehicle info object"""

    id: int
    year: int
    make: str
    model: str
    license_plate: str
    image_location: str = ""
    map_location: str = ""
    purchase_date: str = ""
    sold_date: str = ""
    purchase_price: float = 0.0
    sold_price: float = 0.0
    is_electric: bool = False
    is_diesel: bool = False
    use_hours: bool = False
    odometer_optional: bool = False
    extra_fields: list = field(default_factory=list)
    tags: list = field(default_factory=list)
    has_odometer_adjustment: bool = False
    odometer_multiplier: int = 1
    odometer_difference: int = 0
    dashboard_metrics: list = field(default_factory=list)
    vehicle_identifier: str = "LicensePlate"

    def to_dict(self) -> dict:
        """Return vehicle info as dict"""
        return asdict(self)

    @classmethod
    def from_api_response(cls, data: dict) -> "LubeloggerVehicleInfo":
        """Create a LubeloggerVehicleInfo from Lubelogger API response data"""
        snake_case_data = {from_camel_case(k): v for k, v in data.items()}
        return cls(**snake_case_data)


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

    def get_vehicle_info(self, vehicle_id: int) -> LubeloggerVehicleInfo | None:
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
                return LubeloggerVehicleInfo.from_api_response(data[0]["vehicleData"])
            return None
        except requests.exceptions.ReadTimeout:
            logger.error("Lubelogger API timed out while fetching vehicle info")
            return None
        except requests.exceptions.HTTPError as exc:
            logger.error(exc)
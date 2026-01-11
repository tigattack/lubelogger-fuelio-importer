"""Data models"""

from dataclasses import asdict, dataclass, field

from util import from_camel_case, to_camel_case

# Keys to drop when sending fillup data to the API or comparing fillups
FILLUP_IGNORE_KEYS = [
    "id",
    "fuel_economy",
    "extra_fields",
    "files",
]

DEFAULT_VECHICLE_IDENTIFIER = "LicensePlate"


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
    vehicle_identifier: str = DEFAULT_VECHICLE_IDENTIFIER

    def to_dict(self) -> dict:
        """Return vehicle info as dict"""
        return asdict(self)

    @classmethod
    def from_api_response(cls, data: dict) -> "LubeloggerVehicleInfo":
        """Create a LubeloggerVehicleInfo from Lubelogger API response data"""
        snake_case_data = {from_camel_case(k): v for k, v in data.items()}
        return cls(**snake_case_data)

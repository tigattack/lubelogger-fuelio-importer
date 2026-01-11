"""Data models"""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from util import from_camel_case, to_camel_case

# Keys to exclude when sending fillup data to the API or comparing fillups
FILLUP_EXCLUDE_KEYS = {"id", "fuel_economy", "extra_fields", "files"}

DEFAULT_VECHICLE_IDENTIFIER = "LicensePlate"


class LubeloggerFillup(BaseModel):
    """Lubelogger fuel fillup object"""

    model_config = ConfigDict(populate_by_name=True)

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
    extra_fields: list[Any] = Field(default_factory=list)
    files: list[Any] = Field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Return fillup as dict"""
        return self.model_dump()

    def to_api_dict(self) -> dict[str, Any]:
        """Return fillup as dict for Lubelogger API (camelCase keys)"""
        data = self.model_dump(exclude=FILLUP_EXCLUDE_KEYS)
        return {to_camel_case(k): v for k, v in data.items()}

    @classmethod
    def from_api_response(cls, data: dict[str, Any]) -> "LubeloggerFillup":
        """Create a LubeloggerFillup from Lubelogger API response data"""
        snake_case_data = {from_camel_case(k): v for k, v in data.items()}
        return cls(**snake_case_data)


class LubeloggerVehicleInfo(BaseModel):
    """Lubelogger vehicle info object"""

    model_config = ConfigDict(populate_by_name=True)

    id: int
    year: int
    make: str
    model: str
    license_plate: str
    image_location: str = ""
    map_location: str = ""
    purchase_date: str = ""
    sold_date: str | None = None
    purchase_price: float = 0.0
    sold_price: float = 0.0
    is_electric: bool = False
    is_diesel: bool = False
    use_hours: bool = False
    odometer_optional: bool = False
    extra_fields: list[Any] = Field(default_factory=list)
    tags: list[Any] = Field(default_factory=list)
    has_odometer_adjustment: bool = False
    odometer_multiplier: int = 1
    odometer_difference: int = 0
    dashboard_metrics: list[Any] = Field(default_factory=list)
    vehicle_identifier: str = DEFAULT_VECHICLE_IDENTIFIER

    def to_dict(self) -> dict[str, Any]:
        """Return vehicle info as dict"""
        return self.model_dump()

    @classmethod
    def from_api_response(cls, data: dict[str, Any]) -> "LubeloggerVehicleInfo":
        """Create a LubeloggerVehicleInfo from Lubelogger API response data"""
        snake_case_data = {from_camel_case(k): v for k, v in data.items()}
        return cls(**snake_case_data)

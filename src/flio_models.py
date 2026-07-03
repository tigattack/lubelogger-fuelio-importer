"""Fuelio data models"""

from dataclasses import dataclass
from datetime import datetime

from fuelio import FuelioColumns


@dataclass
class FuelioFuelRecord:
    """Represents a Fuelio fuel record"""

    datetime: datetime
    odometer: float
    fuel_consumed: float
    cost: float
    is_full: bool
    missed: bool
    latitude: str
    longitude: str
    station: str
    notes: str
    fuel_type: int

    @classmethod
    def from_csv_row(cls, row: dict[str, str]) -> "FuelioFuelRecord":
        """Create FuelioFuelRecord from CSV row"""

        # Field extraction helpers
        def get_str(key: str) -> str:
            """Get string, default to empty (optional fields)"""
            return row.get(key, "")

        def get_float(key: str, required: bool = True) -> float:
            """Get float value, optionally required"""
            value = row.get(key, "")
            if not value:
                if required:
                    raise ValueError(f"Required field '{key}' is missing or empty")
                return 0.0
            return float(value)

        def get_int(key: str) -> int:
            """Get int, default to 0"""
            value = row.get(key, "")
            return int(value) if value else 0

        def get_bool(key: str) -> bool:
            """Get bool from int field"""
            return get_int(key) == 1

        # Parse datetime defensively
        datetime_str = row.get(FuelioColumns.DATETIME, "")
        if not datetime_str:
            raise ValueError("Required field 'Data' (datetime) is missing or empty")

        try:
            record_datetime = datetime.strptime(datetime_str, "%Y-%m-%d %H:%M")
        except ValueError as e:
            raise ValueError(f"Invalid datetime format '{datetime_str}': {e}") from e

        return cls(
            datetime=record_datetime,
            odometer=get_float(FuelioColumns.ODOMETER),
            fuel_consumed=get_float(FuelioColumns.FUEL_CONSUMED),
            cost=get_float(FuelioColumns.COST, required=False),
            is_full=get_bool(FuelioColumns.IS_FULL),
            missed=get_bool(FuelioColumns.MISSED),
            latitude=get_str(FuelioColumns.LATITUDE),
            longitude=get_str(FuelioColumns.LONGITUDE),
            station=get_str(FuelioColumns.STATION).strip(),
            notes=get_str(FuelioColumns.NOTES),
            fuel_type=get_int(FuelioColumns.FUEL_TYPE)
            if row.get(FuelioColumns.FUEL_TYPE)
            else -1,
        )

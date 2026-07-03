"""Fuelio data models"""

from dataclasses import dataclass
from datetime import datetime


# Fuelio CSV column name mappings
class FuelioFuelColumns:
    """Column names in Fuelio CSV Log (fuel) section"""

    DATETIME = "Data"
    ODOMETER = "Odo (mi)"
    FUEL_CONSUMED = "Fuel (litres)"
    IS_FULL = "Full"
    COST = "Price (optional)"
    LATITUDE = "latitude (optional)"
    LONGITUDE = "longitude (optional)"
    STATION = "City (optional)"
    NOTES = "Notes (optional)"
    MISSED = "Missed"
    FUEL_TYPE = "FuelType"

    # Required columns that must be present
    REQUIRED = {DATETIME, ODOMETER, FUEL_CONSUMED, IS_FULL}


class FuelioVehicleColumns:
    """Column names in Fuelio CSV Vehicle section"""

    NAME = "Name"
    DESCRIPTION = "Description"
    DIST_UNIT = "DistUnit"
    FUEL_UNIT = "FuelUnit"
    CONSUMPTION_UNIT = "ConsumptionUnit"
    IMPORT_CSV_DATE_FORMAT = "ImportCSVDateFormat"
    VIN = "VIN"
    INSURANCE = "Insurance"
    PLATE = "Plate"
    MAKE = "Make"
    MODEL = "Model"
    YEAR = "Year"
    TANK_COUNT = "TankCount"
    TANK1_TYPE = "Tank1Type"
    TANK2_TYPE = "Tank2Type"
    ACTIVE = "Active"
    TANK1_CAPACITY = "Tank1Capacity"
    TANK2_CAPACITY = "Tank2Capacity"
    FUEL_UNIT_TANK2 = "FuelUnitTank2"
    FUEL_CONSUMPTION_TANK2 = "FuelConsumptionTank2"
    GUID = "guid"
    LAST_UPDATED = "lastupdated"


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
        datetime_str = row.get(FuelioFuelColumns.DATETIME, "")
        if not datetime_str:
            raise ValueError("Required field 'Data' (datetime) is missing or empty")

        try:
            record_datetime = datetime.strptime(datetime_str, "%Y-%m-%d %H:%M")
        except ValueError as e:
            raise ValueError(f"Invalid datetime format '{datetime_str}': {e}") from e

        return cls(
            datetime=record_datetime,
            odometer=get_float(FuelioFuelColumns.ODOMETER),
            fuel_consumed=get_float(FuelioFuelColumns.FUEL_CONSUMED),
            cost=get_float(FuelioFuelColumns.COST, required=False),
            is_full=get_bool(FuelioFuelColumns.IS_FULL),
            missed=get_bool(FuelioFuelColumns.MISSED),
            latitude=get_str(FuelioFuelColumns.LATITUDE),
            longitude=get_str(FuelioFuelColumns.LONGITUDE),
            station=get_str(FuelioFuelColumns.STATION).strip(),
            notes=get_str(FuelioFuelColumns.NOTES),
            fuel_type=get_int(FuelioFuelColumns.FUEL_TYPE)
            if row.get(FuelioFuelColumns.FUEL_TYPE)
            else -1,
        )


@dataclass
class FuelioVehicleInfo:
    """Represents Fuelio vehicle data from the CSV Vehicle section"""

    name: str
    description: str
    dist_unit: int
    fuel_unit: int
    consumption_unit: int
    import_csv_date_format: str
    vin: str
    insurance: str
    plate: str
    make: str
    model: str
    year: int
    tank_count: int
    tank1_type: int
    tank2_type: int
    active: bool
    tank1_capacity: float
    tank2_capacity: float
    fuel_unit_tank2: int
    fuel_consumption_tank2: int
    # Fuelio internal vehicle GUID (not the same as the CSV filename vehicle ID)
    guid: str
    last_updated: int
    # Fuelio vehicle ID from CSV filename (not from CSV contents)
    id: int

    @classmethod
    def from_csv_row(cls, row: dict[str, str], vehicle_id: int) -> "FuelioVehicleInfo":
        """Create FuelioVehicleInfo from a row in the Vehicle section"""

        def get_str(key: str, required: bool = False) -> str:
            value = row.get(key, "")
            if required and not value:
                raise ValueError(f"Required field '{key}' is missing or empty")
            return value

        def get_int(key: str, required: bool = True, default: int = 0) -> int:
            value = row.get(key, "")
            if not value:
                if required:
                    raise ValueError(f"Required field '{key}' is missing or empty")
                return default
            return int(value)

        def get_float(key: str, required: bool = True, default: float = 0.0) -> float:
            value = row.get(key, "")
            if not value:
                if required:
                    raise ValueError(f"Required field '{key}' is missing or empty")
                return default
            return float(value)

        return cls(
            name=get_str(FuelioVehicleColumns.NAME, required=True),
            description=get_str(FuelioVehicleColumns.DESCRIPTION),
            dist_unit=get_int(FuelioVehicleColumns.DIST_UNIT),
            fuel_unit=get_int(FuelioVehicleColumns.FUEL_UNIT),
            consumption_unit=get_int(FuelioVehicleColumns.CONSUMPTION_UNIT),
            import_csv_date_format=get_str(FuelioVehicleColumns.IMPORT_CSV_DATE_FORMAT),
            vin=get_str(FuelioVehicleColumns.VIN),
            insurance=get_str(FuelioVehicleColumns.INSURANCE),
            plate=get_str(FuelioVehicleColumns.PLATE, required=True),
            make=get_str(FuelioVehicleColumns.MAKE, required=True),
            model=get_str(FuelioVehicleColumns.MODEL, required=True),
            year=get_int(FuelioVehicleColumns.YEAR),
            tank_count=get_int(FuelioVehicleColumns.TANK_COUNT),
            tank1_type=get_int(FuelioVehicleColumns.TANK1_TYPE),
            tank2_type=get_int(FuelioVehicleColumns.TANK2_TYPE, required=False),
            active=get_int(FuelioVehicleColumns.ACTIVE) == 1,
            tank1_capacity=get_float(FuelioVehicleColumns.TANK1_CAPACITY),
            tank2_capacity=get_float(
                FuelioVehicleColumns.TANK2_CAPACITY, required=False
            ),
            fuel_unit_tank2=get_int(
                FuelioVehicleColumns.FUEL_UNIT_TANK2, required=False
            ),
            fuel_consumption_tank2=get_int(
                FuelioVehicleColumns.FUEL_CONSUMPTION_TANK2, required=False
            ),
            guid=get_str(FuelioVehicleColumns.GUID),
            last_updated=get_int(FuelioVehicleColumns.LAST_UPDATED, required=False),
            id=vehicle_id,
        )

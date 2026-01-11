"""Fuelio backup data processing and CSV parsing"""

import csv
import logging
import tempfile
import zipfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

from exceptions import FuelioDataError, GDriveError
from gdrive import GDrive

if TYPE_CHECKING:
    from googleapiclient._apis.drive.v3.schemas import (  # type: ignore[import-not-found]
        File,
    )

# Fuelio backups implement a fundamentally broken CSV structure. This makes parsing them very frustrating.
# See my rant in the README for details.


# CSV field indices for Fuelio fuel record data
# Based on Fuelio export format: Data, Odo, Fuel, Full, Price, mpg, lat, lon, City, Notes, Missed, TankNumber, FuelType, etc.
class FuelioFields:
    """Field indices for Fuelio CSV export"""

    ODOMETER = 0
    FUEL_CONSUMED = 1
    IS_FULL = 2
    COST = 3
    MPG = 4  # Not used
    LATITUDE = 5
    LONGITUDE = 6
    STATION = 7
    NOTES = 8
    MISSED = 9
    TANK_NUMBER = 10  # Not used
    FUEL_TYPE = 11


# Fuelio fuel type ID to name mapping
FUEL_TYPES = {
    -1: "Unknown",
    0: "Unset",
    110: "Petrol Regular",
    112: "Petrol Super",
    113: "Petrol Ultimate",
    114: "Petrol Racing",
    119: "Petrol E10",
    201: "Diesel Regular",
    202: "Diesel Plus",
    209: "Biodiesel B20",
    211: "Biodiesel",
    217: "Diesel Adblue",
    218: "Biodiesel B10",
    219: "Biodiesel B30",
    305: "E85",
    401: "LPG",
    501: "CNG",
    502: "CBG",
    503: "Biogas",
    601: "240V",
    602: "DC 500 Fast Charge",
}


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
    def from_csv_row(cls, row: dict[str, Any]) -> "FuelioFuelRecord":
        """Create FuelioFuelRecord from CSV row"""
        # The datetime is in the ## Vehicle column
        fuel_record_datetime = datetime.strptime(row["## Vehicle"], "%Y-%m-%d %H:%M")

        # All other fields are in unnamed columns accessed via None key
        # Type checker doesn't understand csv.DictReader's None key pattern
        fields = row[None]  # type: ignore[index]

        return cls(
            datetime=fuel_record_datetime,
            odometer=float(fields[FuelioFields.ODOMETER]),
            fuel_consumed=float(fields[FuelioFields.FUEL_CONSUMED]),
            cost=float(fields[FuelioFields.COST]),
            is_full=int(fields[FuelioFields.IS_FULL]) == 1,
            missed=int(fields[FuelioFields.MISSED]) == 1,
            latitude=fields[FuelioFields.LATITUDE],
            longitude=fields[FuelioFields.LONGITUDE],
            station=fields[FuelioFields.STATION].strip(),
            notes=fields[FuelioFields.NOTES],
            fuel_type=int(fields[FuelioFields.FUEL_TYPE]),
        )


class FuelioClient:
    """Client for processing Fuelio backup data"""

    def __init__(self, credentials_file: str):
        """Initialise Fuelio client"""
        self.drive = GDrive(credentials_file)
        self.logger = logging.getLogger(__name__)

    def get_fuel_type_name(self, fuel_type_id: int) -> str:
        """Get fuel type name from ID"""
        return FUEL_TYPES.get(fuel_type_id, FUEL_TYPES[-1])

    def fetch_fuel_records(
        self, folder_id: str, vehicle_id: int
    ) -> list[FuelioFuelRecord]:
        """Fetch Fuelio fuel record data for given vehicle ID"""
        csv_filename = f"vehicle-{vehicle_id}-sync.csv"
        zip_filename = f"{csv_filename}.zip"

        # Find backup file
        try:
            backups = self.drive.find_file(folder_id, zip_filename)
        except GDriveError as e:
            raise FuelioDataError(
                f"Failed to search for backup file {zip_filename}: {e}"
            ) from e

        if not backups:
            raise FuelioDataError(
                f"No backup found for vehicle {vehicle_id} (looking for {zip_filename})"
            )

        backup = backups[0]
        backup_name = backup.get("name", "unknown")
        backup_id = backup.get("id", "unknown")
        self.logger.debug(
            "Found backup: %s (ID: %s, modified: %s)",
            backup_name,
            backup_id,
            backup.get("modifiedTime", "unknown"),
        )

        # Download and extract
        csv_data = self._extract_csv_from_backup(backup, csv_filename)

        # Parse CSV
        fuel_records = self._parse_csv(csv_data)

        self.logger.info("Loaded %d fuel records from Fuelio backup", len(fuel_records))
        return fuel_records

    def _extract_csv_from_backup(
        self, backup: File, csv_filename: str
    ) -> list[dict[str, Any]]:
        """Extract CSV data from ZIP backup"""
        backup_name = backup.get("name", "unknown")
        backup_id = backup.get("id", "unknown")

        with tempfile.TemporaryDirectory() as tempdir:
            # Download ZIP file
            try:
                zip_content = self.drive.download_file(backup_id)
            except GDriveError as e:
                raise FuelioDataError(
                    f"Failed to download backup file {backup_name} (ID: {backup_id}): {e}"
                ) from e

            # Extract ZIP
            extract_path = Path(tempdir) / "fuelio"
            extract_path.mkdir(parents=True, exist_ok=True)

            try:
                with zipfile.ZipFile(zip_content, "r") as zip_ref:
                    zip_ref.extractall(extract_path)
            except zipfile.BadZipFile as e:
                raise FuelioDataError(f"Invalid ZIP file: {backup_name}") from e

            # Read CSV
            csv_path = extract_path / csv_filename
            if not csv_path.exists():
                raise FuelioDataError(f"CSV file not found in backup: {csv_filename}")

            # Read all data into memory before tempdir is cleaned up
            with open(csv_path, "r", encoding="utf-8") as csv_file:
                reader = csv.DictReader(csv_file)
                return list(reader)

    def _parse_csv(self, csv_data: list[dict[str, Any]]) -> list[FuelioFuelRecord]:
        """Parse Fuelio CSV data and extract fuel records

        Fuelio CSV contains multiple sections (## Vehicle, ## Log, ## CostCategories, etc.).
        Fuel records are in the ## Log section.
        """
        fuel_records: list[FuelioFuelRecord] = []
        in_log_section = False

        for row in csv_data:
            first_col = row.get("## Vehicle", "")

            # Track which section we're in
            if first_col == "## Log":
                in_log_section = True
                continue
            elif first_col.startswith("##"):
                in_log_section = False
                continue

            # Skip rows outside the Log section
            if not in_log_section:
                continue

            # Skip header row (contains "Data" in first column)
            if first_col == "Data":
                continue

            # Try to parse fuel record
            try:
                fuel_records.append(FuelioFuelRecord.from_csv_row(row))
            except (ValueError, KeyError, TypeError) as e:
                self.logger.debug(
                    "Skipping row with invalid data: %s (error: %s)",
                    first_col,
                    e,
                )
                continue

        return fuel_records

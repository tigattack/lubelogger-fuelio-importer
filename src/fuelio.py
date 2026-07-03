"""Fuelio backup data processing and CSV parsing"""

import csv
import io
import logging
import zipfile
from typing import TYPE_CHECKING

from exceptions import FuelioDataError, GDriveError
from flio_models import FuelioFuelColumns, FuelioFuelRecord
from gdrive import GDrive

if TYPE_CHECKING:
    from googleapiclient._apis.drive.v3.schemas import (  # type: ignore[import-not-found]
        File,
    )

# Fuelio backups implement a fundamentally broken CSV structure. This makes parsing them very frustrating.
# See my rant in the README for details.


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

        # Sort by modified time to get the latest backup
        backups.sort(key=lambda b: b.get("modifiedTime", ""), reverse=True)
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
        csv_content = self._extract_csv_from_backup(backup, csv_filename)
        csv_fuel_log = self._get_fuelio_csv_section(csv_content, "Log")

        # Parse CSV
        fuel_records = self._parse_csv_fuel_log(csv_fuel_log)

        self.logger.info("Loaded %d fuel records from Fuelio backup", len(fuel_records))
        return fuel_records

    def _extract_csv_from_backup(self, backup: File, csv_filename: str) -> str:
        """Extract file content from ZIP backup"""
        backup_name = backup.get("name", "unknown")
        backup_id = backup.get("id", "unknown")

        # Download ZIP file
        try:
            zip_content = self.drive.download_file(backup_id)
        except GDriveError as e:
            raise FuelioDataError(
                f"Failed to download backup file {backup_name} (ID: {backup_id}): {e}"
            ) from e

        # Read CSV directly from ZIP
        try:
            with zipfile.ZipFile(zip_content, "r") as zip_ref:
                if csv_filename not in zip_ref.namelist():
                    raise FuelioDataError(
                        f"CSV file not found in backup: {csv_filename}"
                    )

                return zip_ref.read(csv_filename).decode("utf-8")
        except zipfile.BadZipFile as e:
            raise FuelioDataError(f"Invalid ZIP file: {backup_name}") from e

    def _get_fuelio_csv_section(self, csv_text: str, section_name: str) -> str:
        """Extract the specified section from Fuelio CSV text"""
        lines = csv_text.splitlines(keepends=True)

        # Find section boundaries (strip whitespace and quotes for matching)
        try:
            section_start = next(
                i
                for i, line in enumerate(lines)
                if line.lstrip().strip('"').startswith(f"## {section_name}")
            )
        except StopIteration:
            raise FuelioDataError(f"No {section_name} section found in Fuelio CSV data")

        # Find next section or end of file
        section_end = len(lines)
        for i in range(section_start + 1, len(lines)):
            if lines[i].lstrip().strip('"').startswith("##"):
                section_end = i
                break

        # Return section (skip the marker line itself, keep header + data)
        return "".join(lines[section_start + 1 : section_end])

    def _parse_csv_fuel_log(self, log_section_text: str) -> list[FuelioFuelRecord]:
        """Parse Fuelio 'Log' section CSV data and extract fuel records"""
        reader = csv.DictReader(io.StringIO(log_section_text))

        if not reader.fieldnames:
            raise FuelioDataError("CSV Log section has no header row")

        # Validate that required columns are present
        missing_cols = FuelioFuelColumns.REQUIRED - set(reader.fieldnames)
        if missing_cols:
            raise FuelioDataError(
                f"Missing required columns in CSV: {', '.join(sorted(missing_cols))}. "
                f"Found columns: {', '.join(reader.fieldnames)}"
            )

        fuel_records: list[FuelioFuelRecord] = []
        for row in reader:
            try:
                fuel_records.append(FuelioFuelRecord.from_csv_row(row))
            except (ValueError, KeyError, TypeError) as e:
                self.logger.debug(
                    "Skipping row with invalid data: %s (error: %s)",
                    row.get(FuelioFuelColumns.DATETIME, "unknown"),
                    e,
                )

        return fuel_records

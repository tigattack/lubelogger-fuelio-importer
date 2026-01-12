"""Business logic for syncing Fuelio data to LubeLogger"""

import logging
import sys
from pprint import pformat
from textwrap import dedent
from typing import Any

from pygments import highlight  # type: ignore[import-untyped]
from pygments.formatters import Terminal256Formatter
from pygments.lexers import PythonLexer  # type: ignore[import-untyped]

from fuelio import FuelioClient, FuelioFuelRecord
from lubelogger import LubeLogger
from exceptions import FuelioDataError, LubeLoggerAPIError
from models import FUEL_RECORD_EXCLUDE_KEYS, LubeLoggerFuelRecord


def pprint_colour(obj: Any) -> None:
    """Pretty-print object with syntax highlighting if terminal supports it"""
    if sys.stdout.isatty():
        print(highlight(pformat(obj), PythonLexer(), Terminal256Formatter()), end="")  # type: ignore[arg-type]
    else:
        print(pformat(obj))


class SyncService:
    """Service for synchronising Fuelio data to LubeLogger"""

    def __init__(
        self,
        fuelio_client: FuelioClient,
        lubelogger_client: LubeLogger,
        dry_run: bool = False,
    ):
        """Initialise sync service"""
        self.fuelio = fuelio_client
        self.lubelogger = lubelogger_client
        self.dry_run = dry_run
        self.logger = logging.getLogger(__name__)

    def convert_to_lubelogger(
        self, fuel_record: FuelioFuelRecord
    ) -> LubeLoggerFuelRecord:
        """Convert Fuelio fuel record to LubeLogger format"""
        # Build notes with structured information from Fuelio record
        fuel_type_name = self.fuelio.get_fuel_type_name(fuel_record.fuel_type)

        fuel_record_notes = dedent(
            f"""
            * Fuel station: {fuel_record.station}
            * Location: [{fuel_record.latitude},{fuel_record.longitude}](https://www.google.com/maps/place/{fuel_record.latitude},{fuel_record.longitude})
            * Time: {fuel_record.datetime.strftime("%H:%M")}
            * Fuel type: {fuel_type_name}"""
        ).strip()

        if fuel_record.notes:
            fuel_record_notes += f"\n\n###### Fuelio notes:\n\n{fuel_record.notes}"

        return LubeLoggerFuelRecord(
            date=fuel_record.datetime.strftime("%Y-%m-%d"),
            odometer=int(fuel_record.odometer),
            fuel_consumed=fuel_record.fuel_consumed,
            cost=fuel_record.cost,
            is_fill_to_full=fuel_record.is_full,
            missed_fuel_up=fuel_record.missed,
            notes=fuel_record_notes,
        )

    @staticmethod
    def fuel_record_to_comparable_dict(
        fuel_record: LubeLoggerFuelRecord,
    ) -> dict[str, Any]:
        """Convert fuel record to dict excluding ignored keys for comparison"""
        return {
            k: v
            for k, v in fuel_record.to_dict().items()
            if k not in FUEL_RECORD_EXCLUDE_KEYS
        }

    def find_duplicate(
        self, new_fill: LubeLoggerFuelRecord, existing_fills: list[LubeLoggerFuelRecord]
    ) -> dict[str, Any] | None:
        """Find duplicate fuel record by date and odometer"""
        return next(
            (
                fill.to_dict()
                for fill in existing_fills
                if fill.date == new_fill.date and fill.odometer == new_fill.odometer
            ),
            None,
        )

    def log_duplicate_differences(
        self, new_fill: LubeLoggerFuelRecord, existing_fill: dict[str, Any]
    ) -> None:
        """Log differences between new and existing fuel record"""
        self.logger.warning(
            "Found existing fuel record on %s with different attributes. "
            "This is likely a duplicate and the relevant attributes will need to be manually patched.",
            new_fill.date,
        )

        # Print full objects if debug logging enabled
        if self.logger.level <= logging.DEBUG:
            self.logger.debug("Existing fill:")
            pprint_colour(existing_fill)
            self.logger.debug("Incoming fill:")
            pprint_colour(new_fill.to_dict())

        # Log each differing field (excluding ignored keys)
        for key, new_value in new_fill.to_dict().items():
            if (
                key not in FUEL_RECORD_EXCLUDE_KEYS
                and key in existing_fill
                and new_value != existing_fill[key]
            ):
                self.logger.warning(
                    'The current value of attribute "%s":\n%s',
                    key,
                    repr(existing_fill[key]),
                )
                self.logger.warning(
                    'The incoming value of attribute "%s":\n%s', key, repr(new_value)
                )

    def sync_vehicle(
        self, fuelio_vehicle_id: int, lubelogger_vehicle_id: int, drive_folder_id: str
    ) -> None:
        """Sync fuel records for a single vehicle"""
        self.logger.info(
            "SYNCING LUBELOGGER VEHICLE %d ← FUELIO VEHICLE %d",
            lubelogger_vehicle_id,
            fuelio_vehicle_id,
        )

        # Fetch LubeLogger vehicle info
        self.logger.debug("Fetching LubeLogger vehicle data")
        try:
            vehicle_info = self.lubelogger.get_vehicle_info(lubelogger_vehicle_id)
        except LubeLoggerAPIError as e:
            self.logger.error(
                "Failed to fetch info for LubeLogger vehicle with ID %d: %s",
                lubelogger_vehicle_id,
                e,
            )
            return

        vehicle_title = " ".join(
            [
                str(vehicle_info.year),
                vehicle_info.make,
                vehicle_info.model,
                f"({vehicle_info.license_plate})",
            ]
        )
        self.logger.info("Found LubeLogger vehicle: %s", vehicle_title)

        # Fetch Fuelio data
        self.logger.debug("Fetching Fuelio backup data")
        try:
            fuelio_fills = self.fuelio.fetch_fuel_records(
                drive_folder_id, fuelio_vehicle_id
            )
        except FuelioDataError as e:
            self.logger.error("Failed to fetch Fuelio data: %s", e)
            return

        if not fuelio_fills:
            self.logger.warning("No fuel records found in Fuelio backup!")
            return

        # Fetch LubeLogger fuel records
        self.logger.debug("Fetching LubeLogger fuel records")
        try:
            lubelogger_fills = self.lubelogger.get_fuel_records(lubelogger_vehicle_id)
        except LubeLoggerAPIError as e:
            self.logger.error(
                "Failed to fetch fuel records for LubeLogger vehicle with ID %d: %s",
                lubelogger_vehicle_id,
                e,
            )
            return

        self.logger.info(
            "Found %d fuel records in LubeLogger",
            len(lubelogger_fills),
        )

        # Process fuel records
        added_fuel_records = self._process_fuel_records(
            fuelio_fills, lubelogger_fills, lubelogger_vehicle_id
        )

        # Recalculate odometer records if any fuel records were added
        if len(added_fuel_records) > 0 and not self.dry_run:
            self._recalculate_odometer_records(lubelogger_vehicle_id)

    def _process_fuel_records(
        self,
        fuelio_fills: list[FuelioFuelRecord],
        lubelogger_fills: list[LubeLoggerFuelRecord],
        vehicle_id: int,
    ) -> list[LubeLoggerFuelRecord]:
        """Process and sync fuel records

        Returns:
            list[LubeLoggerFuelRecord]: List of added fuel records
        """
        added_fuel_records: list[LubeLoggerFuelRecord] = []

        # Process in reverse order (oldest first)
        for fuelio_fill in reversed(fuelio_fills):
            # Convert to LubeLogger format
            new_fill = self.convert_to_lubelogger(fuelio_fill)

            # Check if already exists with matching attributes
            new_fill_comparable = self.fuel_record_to_comparable_dict(new_fill)
            if any(
                self.fuel_record_to_comparable_dict(existing) == new_fill_comparable
                for existing in lubelogger_fills
            ):
                # Already exists, skip
                continue

            # Check for duplicate with different attributes
            duplicate = self.find_duplicate(new_fill, lubelogger_fills)
            if duplicate:
                self.log_duplicate_differences(new_fill, duplicate)
                continue

            # Add new fuel record
            if not self.dry_run:
                self.logger.info("Adding fuel record from %s", new_fill.date)
                try:
                    self.lubelogger.add_fuel_record(vehicle_id, new_fill)
                    added_fuel_records.append(new_fill)
                except LubeLoggerAPIError as e:
                    self.logger.error(
                        "Failed to add fuel record from %s: %s", new_fill.date, e
                    )
            else:
                self.logger.info(
                    "Dry run: Would add fuel record from %s", new_fill.date
                )
                added_fuel_records.append(new_fill)

        if not added_fuel_records:
            self.logger.info("Nothing to add, LubeLogger fuel logs are up to date!")
        else:
            action = "Would add" if self.dry_run else "Added"
            self.logger.info("%s %d fuel record(s)", action, len(added_fuel_records))

        return added_fuel_records

    def _recalculate_odometer_records(self, vehicle_id: int) -> None:
        """Recalculate odometer records if negative distances are detected"""
        try:
            # Fetch odometer records to check for negative distances
            self.logger.debug("Checking for negative odometer distances")
            odometer_records = self.lubelogger.get_odometer_records(vehicle_id)

            # Check if any records have negative distances
            has_negative = any(
                (record.odometer - record.initial_odometer) < 0
                for record in odometer_records
            )

            if has_negative:
                self.logger.info(
                    "Negative odometer distances detected, recalculating records",
                )
                response = self.lubelogger.recalculate_odometer_records(vehicle_id)
                self.logger.info("Recalculation complete: %s", response.message)
            else:
                self.logger.debug(
                    "No negative distances detected, skipping recalculation"
                )
        except LubeLoggerAPIError as e:
            # Don't fail the entire sync - odometer records can be manually fixed
            self.logger.error(
                "Failed to recalculate odometer records for vehicle %d: %s",
                vehicle_id,
                e,
            )

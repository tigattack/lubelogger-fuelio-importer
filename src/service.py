"""Business logic for syncing Fuelio data to Lubelogger"""

import logging
import sys
from pprint import pformat
from textwrap import dedent
from typing import Any

from pygments import highlight
from pygments.formatters import Terminal256Formatter
from pygments.lexers import PythonLexer

from fuelio import FuelioClient, FuelioFillup
from lubelogger import Lubelogger
from exceptions import LubeloggerAPIError
from models import FILLUP_IGNORE_KEYS, LubeloggerFillup


def pprint_colour(obj: Any) -> None:
    """Pretty-print object with syntax highlighting if terminal supports it"""
    if sys.stdout.isatty():
        print(highlight(pformat(obj), PythonLexer(), Terminal256Formatter()), end="")
    else:
        print(pformat(obj))


class SyncService:
    """Service for synchronising Fuelio data to Lubelogger"""

    def __init__(
        self,
        fuelio_client: FuelioClient,
        lubelogger_client: Lubelogger,
        dry_run: bool = False,
    ):
        """Initialise sync service"""
        self.fuelio = fuelio_client
        self.lubelogger = lubelogger_client
        self.dry_run = dry_run
        self.logger = logging.getLogger(__name__)

    def convert_to_lubelogger(self, fillup: FuelioFillup) -> LubeloggerFillup:
        """Convert Fuelio fillup to Lubelogger format"""
        # Build notes with structured information
        fuel_type_name = self.fuelio.get_fuel_type_name(fillup.fuel_type)

        fillup_notes = dedent(
            f"""
            * Fuel station: {fillup.station}
            * Location: [{fillup.latitude},{fillup.longitude}](https://www.google.com/maps/place/{fillup.latitude},{fillup.longitude})
            * Time: {fillup.datetime.strftime("%H:%M")}
            * Fuel type: {fuel_type_name}"""
        ).strip()

        if fillup.notes:
            fillup_notes += f"\n\n###### Fuelio notes:\n\n{fillup.notes}"

        return LubeloggerFillup(
            date=fillup.datetime.strftime("%Y-%m-%d"),
            odometer=int(fillup.odometer),
            fuel_consumed=fillup.fuel_consumed,
            cost=fillup.cost,
            is_fill_to_full=fillup.is_full,
            missed_fuel_up=fillup.missed,
            notes=fillup_notes,
        )

    @staticmethod
    def fillup_to_comparable_dict(fillup: LubeloggerFillup) -> dict:
        """Convert fillup to dict excluding ignored keys for comparison"""
        return {
            k: v for k, v in fillup.to_dict().items() if k not in FILLUP_IGNORE_KEYS
        }

    def find_duplicate(
        self, new_fill: LubeloggerFillup, existing_fills: list[LubeloggerFillup]
    ) -> dict | None:
        """Find duplicate fillup by date and odometer"""
        return next(
            (
                fill.to_dict()
                for fill in existing_fills
                if fill.date == new_fill.date and fill.odometer == new_fill.odometer
            ),
            None,
        )

    def log_duplicate_differences(
        self, new_fill: LubeloggerFillup, existing_fill: dict
    ) -> None:
        """Log differences between new and existing fillup"""
        self.logger.warning(
            "Found existing fillup on %s with different attributes. "
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
                key not in FILLUP_IGNORE_KEYS
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
        """Sync fillups for a single vehicle"""
        self.logger.info(
            "SYNCING LUBELOGGER VEHICLE %d ← FUELIO VEHICLE %d",
            lubelogger_vehicle_id,
            fuelio_vehicle_id,
        )

        # Fetch Lubelogger vehicle info
        self.logger.debug("Fetching Lubelogger vehicle data")
        try:
            vehicle_info = self.lubelogger.get_vehicle_info(lubelogger_vehicle_id)
        except LubeloggerAPIError as e:
            self.logger.error(
                "Failed to fetch info for Lubelogger vehicle with ID %d: %s",
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
        self.logger.info("Found Lubelogger vehicle: %s", vehicle_title)

        # Fetch Fuelio data
        self.logger.debug("Fetching Fuelio backup data")
        try:
            fuelio_fills = self.fuelio.fetch_fillups(drive_folder_id, fuelio_vehicle_id)
        except (FileNotFoundError, RuntimeError) as e:
            self.logger.error("Failed to fetch Fuelio data: %s", e)
            return

        if not fuelio_fills:
            self.logger.warning("No fuel fillups found in Fuelio backup!")
            return

        # Fetch Lubelogger fillups
        self.logger.debug("Fetching Lubelogger fillups")
        try:
            lubelogger_fills = self.lubelogger.get_fillups(lubelogger_vehicle_id)
        except LubeloggerAPIError as e:
            self.logger.error(
                "Failed to fetch fillups for Lubelogger vehicle with ID %d: %s",
                lubelogger_vehicle_id,
                e,
            )
            return

        self.logger.info(
            "Found %d fillups in Lubelogger",
            len(lubelogger_fills),
        )

        # Process fillups
        self._process_fillups(fuelio_fills, lubelogger_fills, lubelogger_vehicle_id)

    def _process_fillups(
        self,
        fuelio_fills: list[FuelioFillup],
        lubelogger_fills: list[LubeloggerFillup],
        vehicle_id: int,
    ) -> None:
        """Process and sync fillups"""
        added_count = 0

        # Process in reverse order (oldest first)
        for fuelio_fill in reversed(fuelio_fills):
            # Convert to Lubelogger format
            new_fill = self.convert_to_lubelogger(fuelio_fill)

            # Check if already exists with matching attributes
            new_fill_comparable = self.fillup_to_comparable_dict(new_fill)
            if any(
                self.fillup_to_comparable_dict(existing) == new_fill_comparable
                for existing in lubelogger_fills
            ):
                # Already exists, skip
                continue

            # Check for duplicate with different attributes
            duplicate = self.find_duplicate(new_fill, lubelogger_fills)
            if duplicate:
                self.log_duplicate_differences(new_fill, duplicate)
                continue

            # Add new fillup
            if not self.dry_run:
                self.logger.info("Adding fuel fillup from %s", new_fill.date)
                try:
                    self.lubelogger.add_fillup(vehicle_id, new_fill)
                    added_count += 1
                except LubeloggerAPIError as e:
                    self.logger.error(
                        "Failed to add fillup from %s: %s", new_fill.date, e
                    )
            else:
                self.logger.info(
                    "Dry run: Would add fuel fillup from %s", new_fill.date
                )
                added_count += 1

        if added_count == 0:
            self.logger.info("Nothing to add, Lubelogger fuel logs are up to date!")
        else:
            action = "Would add" if self.dry_run else "Added"
            self.logger.info("%s %d fillup(s)", action, added_count)

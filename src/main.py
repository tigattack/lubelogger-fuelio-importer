"""Script to import Fuelio fillups into Lubelogger"""

import argparse
import csv
import logging
import os
import sys
import tempfile
import zipfile
from datetime import datetime
from pprint import pformat
from textwrap import dedent
from typing import Any

import yaml
from pydrive2.files import GoogleDriveFile
from pygments import highlight
from pygments.formatters import Terminal256Formatter
from pygments.lexers import PythonLexer

import gdrive
from lubelogger import Lubelogger, LubeloggerFillup


def pprint_colour(obj: Any) -> None:
    """Pretty-print, in colour if possible"""
    if sys.stdout.isatty():
        print(highlight(pformat(obj), PythonLexer(), Terminal256Formatter()), end="")
    else:
        print(pformat(obj))


def load_config(directory: str) -> dict:
    """Loads config from YAML file"""
    config_path = os.path.join(directory, "config.yml")
    with open(config_path, "r", encoding="utf-8") as config_file:
        return yaml.safe_load(config_file)


def fuelio_csv_from_backup(backup: GoogleDriveFile, filename: str) -> csv.DictReader:
    """Returns Fuelio data from Google Drive backup"""
    with tempfile.TemporaryDirectory() as tempdir:
        backup_path = os.path.join(tempdir, "fuelio.zip")
        extract_path = os.path.join(tempdir, "fuelio")

        backup.GetContentFile(backup_path, mimetype="application/zip")
        with zipfile.ZipFile(backup_path, "r") as zip_ref:
            zip_ref.extractall(extract_path)

        return csv.DictReader(
            open(os.path.join(extract_path, filename), "r", encoding="utf-8")
        )


def filter_fuelio_fillups(fuelio_data: csv.DictReader) -> list[dict]:
    """Filters Fuelio CSV export to only include fuel fillups"""
    fillups = []
    for fillup in fuelio_data:
        try:
            datetime.strptime(fillup.get("## Vehicle"), "%Y-%m-%d %H:%M")
            fillups.append(fillup)
        except ValueError:
            pass

    return fillups


def lubelogger_converter(fillup) -> LubeloggerFillup:
    """Converts a Fuelio fillup to Lubelogger fillup"""
    fillup_datetime = datetime.strptime(fillup["## Vehicle"], "%Y-%m-%d %H:%M")
    fillup_notes = dedent(
        f"""
            Fuel station: {fillup[None][7].strip()}

            Location: [{fillup[None][5]},{fillup[None][6]}](https://www.google.com/maps/place/{fillup[None][5]},{fillup[None][6]})

            Time: {fillup_datetime.strftime('%H:%M')}"""
    ).strip()

    if fillup[None][8]:
        fillup_notes += f"\n\n###### Fuelio notes:\n\n{fillup[None][8]}"

    return LubeloggerFillup(
        date            = fillup_datetime.strftime('%d/%m/%Y'),
        odometer        = int(float(fillup[None][0])),
        fuel_consumed   = fillup[None][1],
        cost            = fillup[None][3],
        is_fill_to_full = int(fillup[None][2]) == 1,
        missed_fuel_up  = int(fillup[None][9]) == 1,
        notes           = fillup_notes
    )


def fetch_fuelio_data(folder_id: str, vehicle_id: str, auth_type: str) -> list[dict]:
    """Fetches Fuelio backup data for given vehicle ID"""
    fuelio_csv_filename = f"vehicle-{vehicle_id}-sync.csv"

    assert auth_type in gdrive.AuthType, "Invalid auth_type"
    drive = gdrive.GDrive(auth_type=gdrive.AuthType[str(auth_type).upper()])

    backup = drive.find_file(folder_id, fuelio_csv_filename + ".zip")[0]

    assert len(backup) > 0, f"No backup found for {vehicle_id}"

    fuelio_data = fuelio_csv_from_backup(backup, fuelio_csv_filename)
    fuelio_fills = filter_fuelio_fillups(fuelio_data)

    return fuelio_fills


def find_duplicate_fillups(
    new_fill: LubeloggerFillup, lubelog_fills: list[LubeloggerFillup]
):
    """Finds duplicate fillups"""
    return next(
        (
            fill_log.to_dict()
            for fill_log in lubelog_fills
            if fill_log.date == new_fill.date and fill_log.odometer == new_fill.odometer
        ),
        None,
    )


def process_fillups(
    fuelio_fills: list[dict],
    lubelogger: Lubelogger,
    lubelog_fills: list[LubeloggerFillup],
    lubelogger_vehicle_id: str,
    dry_run: bool,
):
    """Processes fillups"""
    logger = logging.getLogger(__name__)

    # Loop through the fuelio fills list in reverse order (oldest first)
    is_lubelogger_missing_logs = False
    for f_fill in fuelio_fills[::-1]:
        # Convert fuelio fillup to lubelogger schema
        new_ll_fill = lubelogger_converter(f_fill)

        # Check if the converted fillup already
        # exists in lubelogger and fully matches
        # the incoming Fuelio fillup. If so, skip.
        if not any(ll_fill == new_ll_fill for ll_fill in lubelog_fills):
            is_lubelogger_missing_logs = True

            # Check if a fillup already exists for given date
            # and mileage but with other differing attributes
            dupe_ll_fill = find_duplicate_fillups(new_ll_fill, lubelog_fills)
            if dupe_ll_fill:
                logger.warning(
                    "Found existing fillup on %s with different attributes. " +
                    "This is likely a duplicate and the relevant attributes will need to be manually patched.",
                    new_ll_fill.date,
                )

                # Print full existing & incoming fill objects if log level is DEBUG (10) or lower
                if logger.level <= logging.DEBUG:
                    logger.debug("Existing fill:")
                    pprint_colour(dupe_ll_fill)
                    logger.debug("Incoming fill:")
                    pprint_colour(new_ll_fill.to_dict())

                # Log each key/value pair that does not match
                for k, v in new_ll_fill.to_dict().items():
                    if k in dupe_ll_fill and v != dupe_ll_fill[k]:
                        logger.warning('The current value of attribute "%s":\n%s', k, dupe_ll_fill[k])
                        logger.warning('The incoming value of attribute "%s":\n%s', k, v)

                # Skip this fillup
                continue

            # Add fillup
            if not dry_run:
                logger.info("Adding fuel fillup from %s", new_ll_fill.date)
                lubelogger.add_fillup(lubelogger_vehicle_id, new_ll_fill)
            else:
                logger.info("Dry run: Would add fuel fillup from %s", new_ll_fill.date)

    if not is_lubelogger_missing_logs:
        logger.info("Nothing to add, Lubelogger fuel logs are up to date!")


def main(args):
    logger = logging.getLogger(__name__)
    logsh = logging.StreamHandler()
    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    logsh.setFormatter(formatter)
    logger.addHandler(logsh)

    config = load_config(args.config_dir)

    log_level_name = args.log_level if len(args.log_level) > 0 else config.get("log_level", "INFO")
    logger.setLevel(logging.getLevelName(log_level_name.upper()))

    lubelogger = Lubelogger(
        config["lubelogger_url"],
        config["lubelogger_username"],
        config["lubelogger_password"],
    )

    for vehicle in config["sync_vehicles"]:
        logger.info(
            "RUNNING FOR LUBELOGGER VEHICLE ID %d, FUELIO VEHICLE ID %d",
            vehicle["fuelio_id"],
            vehicle["lubelogger_id"])

        logger.debug("Fetching Lubelogger vehicle data")
        lubelog_vehicle_info = lubelogger.get_vehicle_info(vehicle["lubelogger_id"])

        lubelog_vehicle_title = ' '.join([
                        str(lubelog_vehicle_info["year"]),
                        lubelog_vehicle_info["make"],
                        lubelog_vehicle_info["model"],
                        f"({lubelog_vehicle_info["licensePlate"]})"
                    ])

        logger.info("Found Lubelogger vehicle: %s", lubelog_vehicle_title)

        logger.debug("Fetching Fuelio backup data")
        fuelio_fills = fetch_fuelio_data(
            folder_id=config["drive_folder_id"],
            vehicle_id=vehicle["fuelio_id"],
            auth_type=config["auth_type"])

        if len(fuelio_fills) == 0:
            logger.error("No fuel fillups found in Fuelio backup!")
            return

        logger.debug("Fetching Lubelogger fillups")
        lubelog_fills = lubelogger.get_fillups(vehicle["lubelogger_id"])

        logger.info(
            "Found %d fillups in Fuelio backup and %d in Lubelogger",
            len(list(fuelio_fills)),
            len(lubelog_fills))

        process_fillups(fuelio_fills, lubelogger, lubelog_fills, vehicle["lubelogger_id"], args.dry_run)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Import Fuelio fillups into Lubelogger"
    )
    parser.add_argument(
        "config_dir",
        type=str,
        help="Config directory",
        default=os.environ.get('CONFIG_DIR', './config')
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Perform a dry run without making any changes",
    )
    parser.add_argument(
        "--log-level",
        default="",
        choices=["debug", "info", "warning", "error", "critical"],
        help="Log level to use",
    )
    args = parser.parse_args()
    main(args)

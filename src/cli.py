"""CLI entrypoint, arg parsing, and logging setup."""

import argparse
import logging
import os
import sys

from config import load_config
from exceptions import ConfigError
from fuelio import FuelioClient
from lubelogger import LubeLogger
from service import SyncService


def setup_logging(log_level: str) -> None:
    """Configure logging for the application"""
    logger = logging.getLogger()
    logger.setLevel(getattr(logging, log_level.upper()))

    # Remove existing handlers to avoid duplicates
    logger.handlers.clear()

    # Console handler with formatting
    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)


def parse_args() -> argparse.Namespace:
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description="Import Fuelio fuel records into LubeLogger"
    )
    parser.add_argument(
        "config_dir",
        type=str,
        help="Config directory",
        default=os.environ.get("CONFIG_DIR", "./config"),
        nargs="?",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Perform a dry run without making any changes",
    )
    parser.add_argument(
        "--clobber",
        action="store_true",
        help="Override LubeLogger fuel records with Fuelio data when conflicts are found (based on matching date and mileage)",
    )
    parser.add_argument(
        "--list-fuelio-vehicles",
        action="store_true",
        help="List Fuelio vehicles and exit",
    )
    parser.add_argument(
        "--list-lubelogger-vehicles",
        action="store_true",
        help="List LubeLogger vehicles and exit",
    )
    parser.add_argument(
        "--log-level",
        default="",
        choices=["debug", "info", "warning", "error", "critical"],
        help="Log level to use (overrides config file)",
    )

    return parser.parse_args()


def launch():
    """CLI entrypoint"""
    args = parse_args()

    # Load configuration
    try:
        config = load_config(args.config_dir)
    except ConfigError as e:
        print(f"Configuration error: {e}", file=sys.stderr)
        sys.exit(1)

    # Setup logging
    log_level = args.log_level if args.log_level else config.log_level
    setup_logging(log_level)

    logger = logging.getLogger(__name__)

    # Initialise clients
    fuelio_client = FuelioClient(config.credentials_file_path)
    lubelogger_client = LubeLogger(
        config.lubelogger_url,
        config.lubelogger_username,
        config.lubelogger_password,
    )

    if args.list_fuelio_vehicles:
        vehicles = fuelio_client.fetch_vehicles(config.drive_folder_id)
        for vehicle in vehicles:
            print(f"Fuelio Vehicle: {vehicle.name}, ID: {vehicle.id}")
        sys.exit(0)

    if args.list_lubelogger_vehicles:
        vehicles = lubelogger_client.get_vehicles()
        for vehicle in vehicles:
            print(
                f"LubeLogger Vehicle: {vehicle.make} {vehicle.model}, ID: {vehicle.id}"
            )
        sys.exit(0)

    else:
        logger.info("Starting Fuelio to LubeLogger sync")

        # Initialise sync service
        sync_service = SyncService(
            fuelio_client, lubelogger_client, args.dry_run, args.clobber
        )

        # Sync each configured vehicle
        for vehicle in config.sync_vehicles:
            try:
                sync_service.sync_vehicle(
                    fuelio_vehicle_id=vehicle.fuelio_id,
                    lubelogger_vehicle_id=vehicle.lubelogger_id,
                    drive_folder_id=config.drive_folder_id,
                )
            except Exception as e:
                logger.error(
                    "Failed to sync vehicle (Fuelio ID: %d, LubeLogger ID: %d): %s",
                    vehicle.fuelio_id,
                    vehicle.lubelogger_id,
                    e,
                    exc_info=True,
                )
                continue

        logger.info("Sync complete")


if __name__ == "__main__":
    launch()

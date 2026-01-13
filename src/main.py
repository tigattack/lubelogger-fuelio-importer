"""Script to import Fuelio fuel records into LubeLogger"""

import logging
import sys

from cli import parse_args, setup_logging
from config import load_config
from exceptions import ConfigError
from fuelio import FuelioClient
from lubelogger import LubeLogger
from service import SyncService


def main():
    """Main entry point for Fuelio to LubeLogger sync"""
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
    logger.info("Starting Fuelio to LubeLogger sync")

    # Initialise clients
    fuelio_client = FuelioClient(config.credentials_file_path)
    lubelogger_client = LubeLogger(
        config.lubelogger_url,
        config.lubelogger_username,
        config.lubelogger_password,
    )

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
    main()

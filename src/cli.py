"""CLI argument parsing and logging setup"""

import argparse
import logging
import os
import sys


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
        description="Import Fuelio fuel records into Lubelogger"
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
        "--log-level",
        default="",
        choices=["debug", "info", "warning", "error", "critical"],
        help="Log level to use (overrides config file)",
    )

    return parser.parse_args()

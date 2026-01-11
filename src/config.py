"""Configuration management"""

import logging
from pathlib import Path

import yaml
from pydantic import BaseModel, Field, ValidationError, field_validator

from exceptions import ConfigError


class VehicleConfig(BaseModel):
    """Configuration for a single vehicle sync"""

    fuelio_id: int
    lubelogger_id: int


class Config(BaseModel):
    """Application configuration with pydantic validation"""

    lubelogger_url: str = Field(..., description="LubeLogger instance URL")
    lubelogger_username: str = Field(..., description="LubeLogger username")
    lubelogger_password: str = Field(..., description="LubeLogger password")
    drive_folder_id: str = Field(..., description="Google Drive folder ID")
    credentials_file_path: str = Field(
        ..., description="Path to Google credentials file"
    )
    sync_vehicles: list[VehicleConfig] = Field(
        ..., description="List of vehicles to sync"
    )
    log_level: str = Field(default="INFO", description="Logging level")

    @field_validator("log_level")
    @classmethod
    def normalise_log_level(cls, v: str) -> str:
        """Normalise log level to uppercase"""
        normalised = v.upper()
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if normalised not in valid_levels:
            raise ValueError(f"Invalid log level: {v}. Must be one of {valid_levels}")
        return normalised


def load_config(config_dir: str) -> Config:
    """Load configuration from YAML file"""
    logger = logging.getLogger(__name__)
    config_path = Path(config_dir) / "config.yml"

    if not config_path.exists():
        raise ConfigError(
            f"config.yml could not be found in {config_dir}. "
            "Specify a different config directory using CLI arguments "
            "or the CONFIG_DIR environment variable."
        )

    logger.debug("Loading config from %s", config_path)

    with open(config_path, "r", encoding="utf-8") as config_file:
        data = yaml.safe_load(config_file)

    if not data:
        raise ConfigError(f"Config file is empty: {config_path}")

    try:
        return Config(**data)
    except ValidationError as e:
        raise ConfigError(f"Invalid configuration: {e}") from e

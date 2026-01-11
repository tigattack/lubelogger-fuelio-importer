"""Tests for configuration module"""

import os
import sys
import tempfile
import unittest
from pathlib import Path

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from pydantic import ValidationError

from config import Config, VehicleConfig, load_config
from exceptions import ConfigError


class TestVehicleConfig(unittest.TestCase):
    """Tests for VehicleConfig dataclass"""

    def test_create_vehicle_config(self):
        """Test creating a VehicleConfig"""
        vehicle = VehicleConfig(fuelio_id=1, lubelogger_id=2)
        self.assertEqual(vehicle.fuelio_id, 1)
        self.assertEqual(vehicle.lubelogger_id, 2)


class TestConfig(unittest.TestCase):
    """Tests for Config dataclass"""

    def test_from_dict_valid(self):
        """Test creating Config from valid dict"""
        data = {
            "lubelogger_url": "http://localhost:8080",
            "lubelogger_username": "admin",
            "lubelogger_password": "password",
            "drive_folder_id": "folder123",
            "credentials_file_path": "/path/to/creds.json",
            "sync_vehicles": [
                {"fuelio_id": 1, "lubelogger_id": 2},
                {"fuelio_id": 3, "lubelogger_id": 4},
            ],
            "log_level": "debug",
        }

        config = Config(**data)

        self.assertEqual(config.lubelogger_url, "http://localhost:8080")
        self.assertEqual(config.lubelogger_username, "admin")
        self.assertEqual(config.lubelogger_password, "password")
        self.assertEqual(config.drive_folder_id, "folder123")
        self.assertEqual(config.credentials_file_path, "/path/to/creds.json")
        self.assertEqual(config.log_level, "DEBUG")
        self.assertEqual(len(config.sync_vehicles), 2)
        self.assertEqual(config.sync_vehicles[0].fuelio_id, 1)
        self.assertEqual(config.sync_vehicles[0].lubelogger_id, 2)

    def test_from_dict_default_log_level(self):
        """Test Config uses default log level if not specified"""
        data = {
            "lubelogger_url": "http://localhost:8080",
            "lubelogger_username": "admin",
            "lubelogger_password": "password",
            "drive_folder_id": "folder123",
            "credentials_file_path": "/path/to/creds.json",
            "sync_vehicles": [{"fuelio_id": 1, "lubelogger_id": 2}],
        }

        config = Config(**data)
        self.assertEqual(config.log_level, "INFO")

    def test_from_dict_missing_required_field(self):
        """Test Config raises ValidationError when required field is missing"""
        data = {
            "lubelogger_url": "http://localhost:8080",
            "lubelogger_username": "admin",
            # Missing password
            "drive_folder_id": "folder123",
            "credentials_file_path": "/path/to/creds.json",
            "sync_vehicles": [],
        }

        with self.assertRaises(ValidationError):
            Config(**data)

    def test_invalid_log_level(self):
        """Test Config raises ValidationError for invalid log level"""
        data = {
            "lubelogger_url": "http://localhost:8080",
            "lubelogger_username": "admin",
            "lubelogger_password": "password",
            "drive_folder_id": "folder123",
            "credentials_file_path": "/path/to/creds.json",
            "sync_vehicles": [{"fuelio_id": 1, "lubelogger_id": 2}],
            "log_level": "INVALID",
        }

        with self.assertRaisesRegex(ValidationError, "Invalid log level"):
            Config(**data)


class TestLoadConfig(unittest.TestCase):
    """Tests for load_config function"""

    def test_load_config_success(self):
        """Test loading valid config file"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.yml"
            config_path.write_text(
                """
lubelogger_url: http://localhost:8080
lubelogger_username: admin
lubelogger_password: secret
drive_folder_id: abc123
credentials_file_path: /creds.json
log_level: debug
sync_vehicles:
  - fuelio_id: 1
    lubelogger_id: 2
  - fuelio_id: 3
    lubelogger_id: 4
"""
            )

            config = load_config(tmpdir)

            self.assertEqual(config.lubelogger_url, "http://localhost:8080")
            self.assertEqual(config.log_level, "DEBUG")
            self.assertEqual(len(config.sync_vehicles), 2)

    def test_load_config_file_not_found(self):
        """Test load_config raises ConfigError when file doesn't exist"""
        with self.assertRaisesRegex(ConfigError, r"config\.yml could not be found"):
            load_config("/nonexistent/path")

    def test_load_config_empty_file(self):
        """Test load_config raises ConfigError for empty config"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.yml"
            config_path.write_text("")

            with self.assertRaisesRegex(ConfigError, r"Config file is empty"):
                load_config(tmpdir)

    def test_load_config_invalid_yaml(self):
        """Test load_config handles invalid YAML"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.yml"
            config_path.write_text("{\ninvalid")

            with self.assertRaises(Exception):  # yaml.YAMLError or similar
                load_config(tmpdir)


if __name__ == "__main__":
    unittest.main()

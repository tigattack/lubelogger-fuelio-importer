"""Tests for CLI module"""

import logging
import os
import sys
import unittest
from unittest.mock import Mock, patch

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from cli import launch, parse_args, setup_logging
from config import Config, VehicleConfig
from service import SyncResult


class TestSetupLogging(unittest.TestCase):
    """Tests for setup_logging function"""

    def tearDown(self):
        """Clean up logging handlers after each test"""
        logger = logging.getLogger()
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)

    def test_setup_logging_sets_level(self):
        """Test that setup_logging sets the correct level"""
        setup_logging("debug")
        logger = logging.getLogger()
        self.assertEqual(logger.level, logging.DEBUG)

    def test_setup_logging_adds_handler(self):
        """Test that setup_logging adds a handler"""
        setup_logging("info")
        logger = logging.getLogger()
        self.assertGreater(len(logger.handlers), 0)


class TestParseArgs(unittest.TestCase):
    """Tests for parse_args function"""

    def test_parse_args_with_config_dir(self):
        """Test parsing config directory argument"""
        with patch("sys.argv", ["cli.py", "/path/to/config"]):
            args = parse_args()
            self.assertEqual(args.config_dir, "/path/to/config")

    def test_parse_args_flags(self):
        """Test parsing command line flags"""
        with patch("sys.argv", ["cli.py", "--dry-run", "--clobber"]):
            args = parse_args()
            self.assertTrue(args.dry_run)
            self.assertTrue(args.clobber)


class TestLaunch(unittest.TestCase):
    """Tests for launch function"""

    def setUp(self):
        """Set up test fixtures"""
        self.mock_config = Mock(spec=Config)
        self.mock_config.log_level = "INFO"
        self.mock_config.credentials_file_path = "/path/to/creds.json"
        self.mock_config.lubelogger_url = "http://localhost:8080"
        self.mock_config.lubelogger_username = "admin"
        self.mock_config.lubelogger_password = "password"
        self.mock_config.drive_folder_id = "folder123"
        self.mock_config.sync_vehicles = [
            VehicleConfig(fuelio_id=1, lubelogger_id=2),
        ]

    def tearDown(self):
        """Clean up logging handlers after each test"""
        logger = logging.getLogger()
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)

    @patch("cli.SyncService")
    @patch("cli.LubeLogger")
    @patch("cli.FuelioClient")
    @patch("cli.load_config")
    @patch("sys.argv", ["cli.py"])
    def test_launch_syncs_vehicle(
        self,
        mock_load_config: Mock,
        mock_fuelio: Mock,
        mock_lubelogger: Mock,
        mock_sync_service: Mock,
    ) -> None:
        """Test launch syncs configured vehicles"""
        mock_load_config.return_value = self.mock_config
        mock_sync_instance = Mock()
        mock_sync_instance.sync_vehicle.return_value = SyncResult(
            fuelio_vehicle_id=1,
            lubelogger_vehicle_id=2,
            vehicle_title="1997 BMW Z3 (R137LDE)",
            added=1,
        )
        mock_sync_service.return_value = mock_sync_instance

        launch()

        mock_sync_instance.sync_vehicle.assert_called_once()


if __name__ == "__main__":
    unittest.main()

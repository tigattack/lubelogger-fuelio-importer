"""Tests for sync service"""

import os
import sys
import unittest
from datetime import datetime
from unittest.mock import Mock

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from fuelio import FuelioFuelRecord
from models import LubeLoggerFuelRecord
from service import SyncService


class TestSyncService(unittest.TestCase):
    """Tests for SyncService class"""

    def setUp(self):
        """Set up test fixtures"""
        self.mock_fuelio = Mock()
        self.mock_lubelogger = Mock()
        self.service = SyncService(
            self.mock_fuelio, self.mock_lubelogger, dry_run=False
        )

    def test_init(self):
        """Test SyncService initialisation"""
        self.assertEqual(self.service.fuelio, self.mock_fuelio)
        self.assertEqual(self.service.lubelogger, self.mock_lubelogger)
        self.assertFalse(self.service.dry_run)

    def test_convert_to_lubelogger(self):
        """Test converting Fuelio fuel record to LubeLogger format"""
        self.mock_fuelio.get_fuel_type_name.return_value = "Petrol Regular"

        fuelio_fill = FuelioFuelRecord(
            datetime=datetime(2024, 1, 15, 14, 30),
            odometer=12345.6,
            fuel_consumed=45.5,
            cost=75.50,
            is_full=True,
            missed=False,
            latitude="51.5074",
            longitude="-0.1278",
            station="Shell Station",
            notes="Test notes",
            fuel_type=110,
        )

        result = self.service.convert_to_lubelogger(fuelio_fill)

        self.assertIsInstance(result, LubeLoggerFuelRecord)
        self.assertEqual(result.date, "2024-01-15")
        self.assertEqual(result.odometer, 12345)
        self.assertEqual(result.fuel_consumed, 45.5)
        self.assertEqual(result.cost, 75.50)
        self.assertTrue(result.is_fill_to_full)
        self.assertFalse(result.missed_fuel_up)
        self.assertIn("Shell Station", result.notes)
        self.assertIn("Petrol Regular", result.notes)
        self.assertIn("Test notes", result.notes)

    def test_fuel_record_to_comparable_dict(self):
        """Test converting fuel record to comparable dict"""
        fuel_record = LubeLoggerFuelRecord(
            date="2024-01-15",
            odometer=12345,
            fuel_consumed=45.5,
            cost=75.50,
            is_fill_to_full=True,
            missed_fuel_up=False,
            notes="Test",
        )

        result = SyncService.fuel_record_to_comparable_dict(fuel_record)

        # Should exclude FUEL_RECORD_EXCLUDE_KEYS
        self.assertIsInstance(result, dict)
        self.assertIn("date", result)
        self.assertIn("odometer", result)

    def test_find_duplicate_found(self):
        """Test finding duplicate fuel record"""
        new_fill = LubeLoggerFuelRecord(
            date="2024-01-15",
            odometer=12345,
            fuel_consumed=45.5,
            cost=75.50,
            is_fill_to_full=True,
            missed_fuel_up=False,
        )

        existing_fills = [
            LubeLoggerFuelRecord(
                date="2024-01-15",
                odometer=12345,
                fuel_consumed=45.0,  # Different amount
                cost=75.00,
                is_fill_to_full=True,
                missed_fuel_up=False,
            )
        ]

        result = self.service.find_duplicate(new_fill, existing_fills)

        self.assertIsNotNone(result)
        self.assertEqual(result["date"], "2024-01-15")
        self.assertEqual(result["odometer"], 12345)

    def test_find_duplicate_not_found(self):
        """Test finding duplicate when none exists"""
        new_fill = LubeLoggerFuelRecord(
            date="2024-01-15",
            odometer=12345,
            fuel_consumed=45.5,
            cost=75.50,
            is_fill_to_full=True,
            missed_fuel_up=False,
        )

        existing_fills = [
            LubeLoggerFuelRecord(
                date="2024-01-16",  # Different date
                odometer=12400,  # Different odometer
                fuel_consumed=45.0,
                cost=75.00,
                is_fill_to_full=True,
                missed_fuel_up=False,
            )
        ]

        result = self.service.find_duplicate(new_fill, existing_fills)

        self.assertIsNone(result)

    def test_sync_vehicle_success(self):
        """Test successful vehicle sync"""
        # Mock vehicle info
        mock_vehicle = Mock()
        mock_vehicle.year = 2020
        mock_vehicle.make = "Toyota"
        mock_vehicle.model = "Camry"
        mock_vehicle.license_plate = "ABC123"
        self.mock_lubelogger.get_vehicle_info.return_value = mock_vehicle

        # Mock Fuelio data
        fuelio_fill = FuelioFuelRecord(
            datetime=datetime(2024, 1, 15, 14, 30),
            odometer=12345.0,
            fuel_consumed=45.5,
            cost=75.50,
            is_full=True,
            missed=False,
            latitude="51.5",
            longitude="-0.1",
            station="Shell",
            notes="",
            fuel_type=110,
        )
        self.mock_fuelio.fetch_fuel_records.return_value = [fuelio_fill]
        self.mock_fuelio.get_fuel_type_name.return_value = "Petrol Regular"

        # Mock LubeLogger fuel records (empty)
        self.mock_lubelogger.get_fuel_records.return_value = []

        # Run sync
        self.service.sync_vehicle(
            fuelio_vehicle_id=1, lubelogger_vehicle_id=2, drive_folder_id="folder123"
        )

        # Verify calls
        self.mock_lubelogger.get_vehicle_info.assert_called_once_with(2)
        self.mock_fuelio.fetch_fuel_records.assert_called_once_with("folder123", 1)
        self.mock_lubelogger.get_fuel_records.assert_called_once_with(2)
        self.mock_lubelogger.add_fuel_record.assert_called_once()

    def test_sync_vehicle_dry_run(self):
        """Test vehicle sync in dry run mode"""
        service = SyncService(self.mock_fuelio, self.mock_lubelogger, dry_run=True)

        # Mock data
        mock_vehicle = Mock()
        mock_vehicle.year = 2020
        mock_vehicle.make = "Toyota"
        mock_vehicle.model = "Camry"
        mock_vehicle.license_plate = "ABC123"
        self.mock_lubelogger.get_vehicle_info.return_value = mock_vehicle

        fuelio_fill = FuelioFuelRecord(
            datetime=datetime(2024, 1, 15, 14, 30),
            odometer=12345.0,
            fuel_consumed=45.5,
            cost=75.50,
            is_full=True,
            missed=False,
            latitude="51.5",
            longitude="-0.1",
            station="Shell",
            notes="",
            fuel_type=110,
        )
        self.mock_fuelio.fetch_fuel_records.return_value = [fuelio_fill]
        self.mock_fuelio.get_fuel_type_name.return_value = "Petrol Regular"
        self.mock_lubelogger.get_fuel_records.return_value = []

        # Run sync
        service.sync_vehicle(
            fuelio_vehicle_id=1, lubelogger_vehicle_id=2, drive_folder_id="folder123"
        )

        # Verify add_fuel_record was NOT called in dry run
        self.mock_lubelogger.add_fuel_record.assert_not_called()


if __name__ == "__main__":
    unittest.main()

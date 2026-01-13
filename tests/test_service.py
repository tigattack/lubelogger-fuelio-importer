"""Tests for sync service"""

import os
import sys
import unittest
from datetime import datetime
from unittest.mock import Mock

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from fuelio import FuelioFuelRecord
from models import (
    LubeLoggerAddFuelRecordResponse,
    LubeLoggerFuelRecord,
    LubeLoggerOdometerRecord,
    LubeLoggerOdoRecalculateResponse,
)
from service import SyncService


class TestSyncService(unittest.TestCase):
    """Tests for SyncService class"""

    def setUp(self):
        """Set up test fixtures"""
        self.mock_fuelio = Mock()
        self.mock_lubelogger = Mock()
        self.service = SyncService(
            self.mock_fuelio, self.mock_lubelogger, dry_run=False, clobber=False
        )

    def test_init(self):
        """Test SyncService initialisation"""
        self.assertEqual(self.service.fuelio, self.mock_fuelio)
        self.assertEqual(self.service.lubelogger, self.mock_lubelogger)
        self.assertFalse(self.service.dry_run)
        self.assertFalse(self.service.clobber)

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

    def test_find_conflict_found(self):
        """Test finding conflicting fuel record"""
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

        result = self.service.find_conflict(new_fill, existing_fills)

        self.assertIsNotNone(result)
        self.assertIsInstance(result, LubeLoggerFuelRecord)
        self.assertEqual(result.date, "2024-01-15")
        self.assertEqual(result.odometer, 12345)

    def test_find_conflict_not_found(self):
        """Test finding conflict when none exists"""
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

        result = self.service.find_conflict(new_fill, existing_fills)

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

        # Mock add_fuel_record response
        mock_response = LubeLoggerAddFuelRecordResponse(
            success=True,
            message="Gas Record Added",
            additional_data={"recordId": 100},
        )
        self.mock_lubelogger.add_fuel_record.return_value = mock_response

        # Mock odometer records with negative distance
        mock_odo = LubeLoggerOdometerRecord(
            id=1,
            date="2024-01-15",
            initial_odometer=15000,  # Higher than odometer - negative distance!
            odometer=12345,
            notes="",
            tags="",
        )
        self.mock_lubelogger.get_odometer_records.return_value = [mock_odo]

        # Mock recalculate response
        mock_recalc = LubeLoggerOdoRecalculateResponse(
            success=True, message="Odometer Records Adjusted(1)"
        )
        self.mock_lubelogger.recalculate_odometer_records.return_value = mock_recalc

        # Run sync
        self.service.sync_vehicle(
            fuelio_vehicle_id=1, lubelogger_vehicle_id=2, drive_folder_id="folder123"
        )

        # Verify calls
        self.mock_lubelogger.get_vehicle_info.assert_called_once_with(2)
        self.mock_fuelio.fetch_fuel_records.assert_called_once_with("folder123", 1)
        self.mock_lubelogger.get_fuel_records.assert_called_once_with(2)
        self.mock_lubelogger.add_fuel_record.assert_called_once()
        # Verify recalculate was called after adding fuel record
        self.mock_lubelogger.get_odometer_records.assert_called_once_with(2)
        self.mock_lubelogger.recalculate_odometer_records.assert_called_once_with(2)

    def test_sync_vehicle_dry_run(self):
        """Test vehicle sync in dry run mode"""
        service = SyncService(
            self.mock_fuelio, self.mock_lubelogger, dry_run=True, clobber=False
        )

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
        # Verify recalculate was NOT called in dry run
        self.mock_lubelogger.recalculate_odometer_records.assert_not_called()

    def test_recalculate_with_negative_distances(self):
        """Test that recalculate is called when negative distances are detected"""
        # Mock odometer records with negative distance
        mock_odo = LubeLoggerOdometerRecord(
            id=1,
            date="2024-01-15",
            initial_odometer=15000,  # Higher than odometer - negative!
            odometer=12345,
            notes="",
            tags="",
        )
        self.mock_lubelogger.get_odometer_records.return_value = [mock_odo]

        # Mock recalculate response
        mock_recalc = LubeLoggerOdoRecalculateResponse(
            success=True, message="Odometer Records Adjusted(1)"
        )
        self.mock_lubelogger.recalculate_odometer_records.return_value = mock_recalc

        # Call the method
        self.service._recalculate_odometer_records(vehicle_id=1)

        # Verify recalculate was called
        self.mock_lubelogger.recalculate_odometer_records.assert_called_once_with(1)

    def test_no_recalculate_without_negative_distances(self):
        """Test that recalculate is NOT called when all distances are positive"""
        # Mock odometer records with positive distances
        mock_odo1 = LubeLoggerOdometerRecord(
            id=1,
            date="2024-01-15",
            initial_odometer=12000,
            odometer=12345,
            notes="",
            tags="",
        )
        mock_odo2 = LubeLoggerOdometerRecord(
            id=2,
            date="2024-01-16",
            initial_odometer=12345,
            odometer=12450,
            notes="",
            tags="",
        )
        self.mock_lubelogger.get_odometer_records.return_value = [mock_odo1, mock_odo2]

        # Call the method
        self.service._recalculate_odometer_records(vehicle_id=1)

        # Verify recalculate was NOT called (no negative distances)
        self.mock_lubelogger.recalculate_odometer_records.assert_not_called()

    def test_recalculate_not_called_when_no_fuel_records_added(self):
        """Test that recalculate is not called when no fuel records were added"""
        # Mock vehicle info
        mock_vehicle = Mock()
        mock_vehicle.year = 2020
        mock_vehicle.make = "Toyota"
        mock_vehicle.model = "Camry"
        mock_vehicle.license_plate = "ABC123"
        self.mock_lubelogger.get_vehicle_info.return_value = mock_vehicle

        # Mock Fuelio data - but it already exists in LubeLogger
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

        # Mock LubeLogger - fuel record already exists
        existing_fill = LubeLoggerFuelRecord(
            date="2024-01-15",
            odometer=12345,
            fuel_consumed=45.5,
            cost=75.50,
            is_fill_to_full=True,
            missed_fuel_up=False,
            notes="* Fuel station: Shell\n* Location: [51.5,-0.1](https://www.google.com/maps/place/51.5,-0.1)\n* Time: 14:30\n* Fuel type: Petrol Regular",
        )
        self.mock_lubelogger.get_fuel_records.return_value = [existing_fill]

        # Run sync
        self.service.sync_vehicle(
            fuelio_vehicle_id=1, lubelogger_vehicle_id=2, drive_folder_id="folder123"
        )

        # Verify recalculate was NOT called (no fuel records added)
        self.mock_lubelogger.get_odometer_records.assert_not_called()
        self.mock_lubelogger.recalculate_odometer_records.assert_not_called()

    def test_clobber_enabled(self):
        """Test that conflicts are overridden when clobber is True"""
        service = SyncService(
            self.mock_fuelio, self.mock_lubelogger, dry_run=False, clobber=True
        )

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
            notes="New notes",
            fuel_type=110,
        )
        self.mock_fuelio.fetch_fuel_records.return_value = [fuelio_fill]
        self.mock_fuelio.get_fuel_type_name.return_value = "Petrol Regular"

        # Mock existing LubeLogger fuel record with same date/odometer but different data (conflict)
        existing_fill = LubeLoggerFuelRecord(
            id=100,
            date="2024-01-15",
            odometer=12345,
            fuel_consumed=40.0,  # Different amount
            cost=70.00,  # Different cost
            is_fill_to_full=False,  # Different flag
            missed_fuel_up=False,
            notes="Old notes",
        )
        self.mock_lubelogger.get_fuel_records.return_value = [existing_fill]

        # Mock odometer records (no negative distances)
        self.mock_lubelogger.get_odometer_records.return_value = []

        # Run sync
        service.sync_vehicle(
            fuelio_vehicle_id=1, lubelogger_vehicle_id=2, drive_folder_id="folder123"
        )

        # Verify update was called, not add
        self.mock_lubelogger.update_fuel_record.assert_called_once()
        self.mock_lubelogger.add_fuel_record.assert_not_called()

        # Verify the updated record has the ID from the existing record
        updated_record = self.mock_lubelogger.update_fuel_record.call_args[0][0]
        self.assertEqual(updated_record.id, 100)
        self.assertEqual(updated_record.fuel_consumed, 45.5)
        self.assertEqual(updated_record.cost, 75.50)
        self.assertTrue(updated_record.is_fill_to_full)

    def test_clobber_disabled(self):
        """Test that conflicts are NOT overridden when clobber is False"""
        # Service with clobber disabled (default)
        service = SyncService(
            self.mock_fuelio, self.mock_lubelogger, dry_run=False, clobber=False
        )

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
            notes="New notes",
            fuel_type=110,
        )
        self.mock_fuelio.fetch_fuel_records.return_value = [fuelio_fill]
        self.mock_fuelio.get_fuel_type_name.return_value = "Petrol Regular"

        # Mock existing LubeLogger fuel record with same date/odometer (conflict)
        existing_fill = LubeLoggerFuelRecord(
            id=100,
            date="2024-01-15",
            odometer=12345,
            fuel_consumed=40.0,  # Different amount
            cost=70.00,  # Different cost
            is_fill_to_full=False,
            missed_fuel_up=False,
            notes="Old notes",
        )
        self.mock_lubelogger.get_fuel_records.return_value = [existing_fill]

        # Run sync
        service.sync_vehicle(
            fuelio_vehicle_id=1, lubelogger_vehicle_id=2, drive_folder_id="folder123"
        )

        # Verify neither update nor add was called (conflict was logged but not overridden)
        self.mock_lubelogger.update_fuel_record.assert_not_called()
        self.mock_lubelogger.add_fuel_record.assert_not_called()
        # Verify odometer recalc was not called since nothing was modified
        self.mock_lubelogger.get_odometer_records.assert_not_called()

    def test_clobber_dry_run(self):
        """Test that clobber works correctly in dry run mode"""
        service = SyncService(
            self.mock_fuelio, self.mock_lubelogger, dry_run=True, clobber=True
        )

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
            notes="New notes",
            fuel_type=110,
        )
        self.mock_fuelio.fetch_fuel_records.return_value = [fuelio_fill]
        self.mock_fuelio.get_fuel_type_name.return_value = "Petrol Regular"

        # Mock existing LubeLogger fuel record
        existing_fill = LubeLoggerFuelRecord(
            id=100,
            date="2024-01-15",
            odometer=12345,
            fuel_consumed=40.0,
            cost=70.00,
            is_fill_to_full=False,
            missed_fuel_up=False,
            notes="Old notes",
        )
        self.mock_lubelogger.get_fuel_records.return_value = [existing_fill]

        # Run sync
        service.sync_vehicle(
            fuelio_vehicle_id=1, lubelogger_vehicle_id=2, drive_folder_id="folder123"
        )

        # Verify update was NOT called in dry run
        self.mock_lubelogger.update_fuel_record.assert_not_called()
        self.mock_lubelogger.add_fuel_record.assert_not_called()


if __name__ == "__main__":
    unittest.main()

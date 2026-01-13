"""Tests for data models"""

import unittest

import sys
import os

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from models import (
    FUEL_RECORD_EXCLUDE_KEYS,
    LubeLoggerFuelRecord,
    LubeLoggerVehicleInfo,
)


class TestLubeLoggerFuelRecord(unittest.TestCase):
    """Test LubeLoggerFuelRecord dataclass"""

    def setUp(self):
        """Set up test data"""
        self.fuel_record_data = {
            "date": "2024-01-15",
            "odometer": 150000,
            "fuel_consumed": 45.5,
            "cost": 75.25,
            "is_fill_to_full": True,
            "missed_fuel_up": False,
            "notes": "Test fuel record",
            "tags": "highway",
        }

        self.api_response_data = {
            "date": "2024-01-15",
            "odometer": 150000,
            "fuelConsumed": 45.5,
            "cost": 75.25,
            "isFillToFull": True,
            "missedFuelUp": False,
            "id": 123,
            "fuelEconomy": 6.5,
            "notes": "Test fuel record",
            "tags": "highway",
            "extraFields": [],
            "files": [],
        }

    def test_fuel_record_creation(self):
        """Test creating a fuel record from scratch"""
        fuel_record = LubeLoggerFuelRecord(**self.fuel_record_data)
        self.assertEqual(fuel_record.date, "2024-01-15")
        self.assertEqual(fuel_record.odometer, 150000)
        self.assertEqual(fuel_record.fuel_consumed, 45.5)
        self.assertEqual(fuel_record.cost, 75.25)
        self.assertTrue(fuel_record.is_fill_to_full)
        self.assertFalse(fuel_record.missed_fuel_up)
        self.assertEqual(fuel_record.notes, "Test fuel record")

    def test_fuel_record_to_dict(self):
        """Test converting fuel record to dictionary"""
        fuel_record = LubeLoggerFuelRecord(**self.fuel_record_data)
        result = fuel_record.to_dict()

        self.assertIsInstance(result, dict)
        self.assertEqual(result["date"], "2024-01-15")
        self.assertEqual(result["odometer"], 150000)
        self.assertEqual(result["fuel_consumed"], 45.5)

    def test_fuel_record_to_api_dict(self):
        """Test converting fuel record to API format (camelCase, ignored keys removed)"""
        fuel_record = LubeLoggerFuelRecord(**self.fuel_record_data)
        api_dict = fuel_record.to_api_dict()

        # Check camelCase conversion
        self.assertIn("fuelConsumed", api_dict)
        self.assertIn("isFillToFull", api_dict)
        self.assertIn("missedFuelUp", api_dict)

        # Check values
        self.assertEqual(api_dict["fuelConsumed"], 45.5)
        self.assertEqual(api_dict["isFillToFull"], True)
        self.assertEqual(api_dict["missedFuelUp"], False)

        # Check ignored keys are removed
        for key in FUEL_RECORD_EXCLUDE_KEYS:
            camel_key = key
            # Convert to camelCase for checking
            if "_" in key:
                parts = key.split("_")
                camel_key = parts[0] + "".join(p.capitalize() for p in parts[1:])
            self.assertNotIn(camel_key, api_dict)
            self.assertNotIn(key, api_dict)

    def test_fuel_record_from_api_response(self):
        """Test creating fuel record from API response"""
        fuel_record = LubeLoggerFuelRecord.from_api_response(self.api_response_data)

        self.assertEqual(fuel_record.date, "2024-01-15")
        self.assertEqual(fuel_record.odometer, 150000)
        self.assertEqual(fuel_record.fuel_consumed, 45.5)
        self.assertEqual(fuel_record.cost, 75.25)
        self.assertTrue(fuel_record.is_fill_to_full)
        self.assertFalse(fuel_record.missed_fuel_up)
        self.assertEqual(fuel_record.id, 123)
        self.assertEqual(fuel_record.fuel_economy, 6.5)
        self.assertEqual(fuel_record.notes, "Test fuel record")
        self.assertEqual(fuel_record.tags, "highway")

    def test_fuel_record_round_trip_conversion(self):
        """Test that API response -> fuel record -> API dict preserves data (excluding ignored keys)"""
        fuel_record = LubeLoggerFuelRecord.from_api_response(self.api_response_data)
        api_dict = fuel_record.to_api_dict()

        # Check that non-ignored fields are preserved
        self.assertEqual(api_dict["date"], self.api_response_data["date"])
        self.assertEqual(api_dict["odometer"], self.api_response_data["odometer"])
        self.assertEqual(
            api_dict["fuelConsumed"], self.api_response_data["fuelConsumed"]
        )
        self.assertEqual(api_dict["cost"], self.api_response_data["cost"])
        self.assertEqual(
            api_dict["isFillToFull"], self.api_response_data["isFillToFull"]
        )
        self.assertEqual(
            api_dict["missedFuelUp"], self.api_response_data["missedFuelUp"]
        )

    def test_fuel_record_default_values(self):
        """Test that default values are set correctly"""
        minimal_fuel_record = LubeLoggerFuelRecord(
            date="2024-01-15",
            odometer=150000,
            fuel_consumed=45.5,
            cost=75.25,
            is_fill_to_full=True,
            missed_fuel_up=False,
        )

        self.assertIsNone(minimal_fuel_record.id)
        self.assertEqual(minimal_fuel_record.fuel_economy, 0)
        self.assertEqual(minimal_fuel_record.notes, "")
        self.assertEqual(minimal_fuel_record.tags, "")
        self.assertEqual(minimal_fuel_record.extra_fields, [])
        self.assertEqual(minimal_fuel_record.files, [])


class TestLubeLoggerVehicleInfo(unittest.TestCase):
    """Test LubeLoggerVehicleInfo dataclass"""

    def setUp(self):
        """Set up test data"""
        self.vehicle_data = {
            "id": 1,
            "year": 2018,
            "make": "Toyota",
            "model": "Camry",
            "license_plate": "ABC123",
        }

        self.api_response_data = {
            "id": 1,
            "imageLocation": "/images/car.jpg",
            "mapLocation": "",
            "year": 2018,
            "make": "Toyota",
            "model": "Camry",
            "licensePlate": "ABC123",
            "purchaseDate": "2018-05-10",
            "soldDate": "",
            "purchasePrice": 25000.0,
            "soldPrice": 0.0,
            "isElectric": False,
            "isDiesel": False,
            "useHours": False,
            "odometerOptional": False,
            "extraFields": [],
            "tags": [],
            "hasOdometerAdjustment": False,
            "odometerMultiplier": 1,
            "odometerDifference": 0,
            "dashboardMetrics": [1, 2],
            "vehicleIdentifier": "LicensePlate",
        }

    def test_vehicle_creation(self):
        """Test creating a vehicle from scratch"""
        vehicle = LubeLoggerVehicleInfo(**self.vehicle_data)
        self.assertEqual(vehicle.id, 1)
        self.assertEqual(vehicle.year, 2018)
        self.assertEqual(vehicle.make, "Toyota")
        self.assertEqual(vehicle.model, "Camry")
        self.assertEqual(vehicle.license_plate, "ABC123")

    def test_vehicle_to_dict(self):
        """Test converting vehicle to dictionary"""
        vehicle = LubeLoggerVehicleInfo(**self.vehicle_data)
        result = vehicle.to_dict()

        self.assertIsInstance(result, dict)
        self.assertEqual(result["id"], 1)
        self.assertEqual(result["year"], 2018)
        self.assertEqual(result["make"], "Toyota")
        self.assertEqual(result["model"], "Camry")
        self.assertEqual(result["license_plate"], "ABC123")

    def test_vehicle_from_api_response(self):
        """Test creating vehicle from API response"""
        vehicle = LubeLoggerVehicleInfo.from_api_response(self.api_response_data)

        self.assertEqual(vehicle.id, 1)
        self.assertEqual(vehicle.year, 2018)
        self.assertEqual(vehicle.make, "Toyota")
        self.assertEqual(vehicle.model, "Camry")
        self.assertEqual(vehicle.license_plate, "ABC123")
        self.assertEqual(vehicle.image_location, "/images/car.jpg")
        self.assertEqual(vehicle.purchase_date, "2018-05-10")
        self.assertEqual(vehicle.purchase_price, 25000.0)
        self.assertFalse(vehicle.is_electric)
        self.assertFalse(vehicle.is_diesel)
        self.assertEqual(vehicle.odometer_multiplier, 1)
        self.assertEqual(vehicle.dashboard_metrics, [1, 2])

    def test_vehicle_round_trip_conversion(self):
        """Test that API response -> vehicle -> dict preserves data"""
        vehicle = LubeLoggerVehicleInfo.from_api_response(self.api_response_data)
        result_dict = vehicle.to_dict()

        # Check that fields are preserved (in snake_case)
        self.assertEqual(result_dict["id"], self.api_response_data["id"])
        self.assertEqual(result_dict["year"], self.api_response_data["year"])
        self.assertEqual(result_dict["make"], self.api_response_data["make"])
        self.assertEqual(result_dict["model"], self.api_response_data["model"])
        self.assertEqual(
            result_dict["license_plate"], self.api_response_data["licensePlate"]
        )
        self.assertEqual(
            result_dict["image_location"], self.api_response_data["imageLocation"]
        )
        self.assertEqual(
            result_dict["purchase_date"], self.api_response_data["purchaseDate"]
        )
        self.assertEqual(
            result_dict["is_electric"], self.api_response_data["isElectric"]
        )
        self.assertEqual(
            result_dict["odometer_multiplier"],
            self.api_response_data["odometerMultiplier"],
        )

    def test_vehicle_default_values(self):
        """Test that default values are set correctly"""
        minimal_vehicle = LubeLoggerVehicleInfo(
            id=1,
            year=2018,
            make="Toyota",
            model="Camry",
            license_plate="ABC123",
        )

        self.assertEqual(minimal_vehicle.image_location, "")
        self.assertEqual(minimal_vehicle.map_location, "")
        self.assertIsNone(minimal_vehicle.purchase_date)
        self.assertIsNone(minimal_vehicle.sold_date)
        self.assertEqual(minimal_vehicle.purchase_price, 0.0)
        self.assertEqual(minimal_vehicle.sold_price, 0.0)
        self.assertFalse(minimal_vehicle.is_electric)
        self.assertFalse(minimal_vehicle.is_diesel)
        self.assertFalse(minimal_vehicle.use_hours)
        self.assertFalse(minimal_vehicle.odometer_optional)
        self.assertEqual(minimal_vehicle.extra_fields, [])
        self.assertEqual(minimal_vehicle.tags, [])
        self.assertFalse(minimal_vehicle.has_odometer_adjustment)
        self.assertEqual(minimal_vehicle.odometer_multiplier, 1)
        self.assertEqual(minimal_vehicle.odometer_difference, 0)
        self.assertEqual(minimal_vehicle.dashboard_metrics, [])
        self.assertEqual(minimal_vehicle.vehicle_identifier, "LicensePlate")


if __name__ == "__main__":
    unittest.main()

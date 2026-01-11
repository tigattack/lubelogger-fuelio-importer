"""Tests for Fuelio client"""

import os
import sys
import unittest
from datetime import datetime
from unittest.mock import Mock, patch

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from exceptions import FuelioDataError
from fuelio import FuelioClient, FuelioFields, FuelioFuelRecord


class TestFuelioFields(unittest.TestCase):
    """Tests for FuelioFields constants"""

    def test_field_indices(self):
        """Test that field indices are defined"""
        self.assertEqual(FuelioFields.ODOMETER, 0)
        self.assertEqual(FuelioFields.FUEL_CONSUMED, 1)
        self.assertEqual(FuelioFields.IS_FULL, 2)
        self.assertEqual(FuelioFields.COST, 3)
        self.assertEqual(FuelioFields.LATITUDE, 5)
        self.assertEqual(FuelioFields.LONGITUDE, 6)
        self.assertEqual(FuelioFields.STATION, 7)
        self.assertEqual(FuelioFields.NOTES, 8)
        self.assertEqual(FuelioFields.MISSED, 9)
        self.assertEqual(FuelioFields.FUEL_TYPE, 11)


class TestFuelioFuelRecord(unittest.TestCase):
    """Tests for FuelioFuelRecord dataclass"""

    def test_from_csv_row(self):
        """Test creating FuelioFuelRecord from CSV row"""
        # Based on actual Fuelio CSV structure from fuelio_backup_sample.csv
        row = {
            "## Vehicle": "2024-03-10 16:01",
            None: [
                "212477.0",  # 0: Odo (mi)
                "46.301",  # 1: Fuel (litres)
                "1",  # 2: Full
                "67.09",  # 3: Price
                "21.8",  # 4: mpg (optional)
                "51.16514",  # 5: latitude (optional)
                "-2.99017",  # 6: longitude (optional)
                "Somerset - Sun all Service Station",  # 7: City (optional)
                "Test notes",  # 8: Notes (optional)
                "0",  # 9: Missed
                "1",  # 10: TankNumber
                "-1",  # 11: FuelType
                "1.449",  # 12: VolumePrice
                "496456",  # 13: StationID (optional)
                "0.0",  # 14: ExcludeDistance
                "218",  # 15: UniqueId
                "0.0",  # 16: TankCalc
            ],
        }

        fuel_record = FuelioFuelRecord.from_csv_row(row)  # type: ignore

        self.assertEqual(fuel_record.datetime, datetime(2024, 3, 10, 16, 1))
        self.assertEqual(fuel_record.odometer, 212477.0)
        self.assertEqual(fuel_record.fuel_consumed, 46.301)
        self.assertEqual(fuel_record.cost, 67.09)
        self.assertTrue(fuel_record.is_full)
        self.assertFalse(fuel_record.missed)
        self.assertEqual(fuel_record.latitude, "51.16514")
        self.assertEqual(fuel_record.longitude, "-2.99017")
        self.assertEqual(fuel_record.station, "Somerset - Sun all Service Station")
        self.assertEqual(fuel_record.notes, "Test notes")
        self.assertEqual(fuel_record.fuel_type, -1)


class TestFuelioClient(unittest.TestCase):
    """Tests for FuelioClient"""

    def test_init(self):
        """Test FuelioClient initialisation"""
        with patch("fuelio.GDrive"):
            client = FuelioClient("/path/to/creds.json")
            self.assertIsNotNone(client)

    def test_get_fuel_type_name_known(self):
        """Test getting fuel type name for known type"""
        with patch("fuelio.GDrive"):
            client = FuelioClient("/path/to/creds.json")
            self.assertEqual(client.get_fuel_type_name(110), "Petrol Regular")
            self.assertEqual(client.get_fuel_type_name(201), "Diesel Regular")
            self.assertEqual(client.get_fuel_type_name(305), "E85")

    def test_get_fuel_type_name_unknown(self):
        """Test getting fuel type name for unknown type"""
        with patch("fuelio.GDrive"):
            client = FuelioClient("/path/to/creds.json")
            self.assertEqual(client.get_fuel_type_name(9999), "Unknown")

    def test_fetch_fuel_records_no_backup(self):
        """Test fetch_fuel_records raises error when no backup found"""
        with patch("fuelio.GDrive") as mock_gdrive:
            mock_drive_instance = Mock()
            mock_drive_instance.find_file.return_value = []
            mock_gdrive.return_value = mock_drive_instance

            client = FuelioClient("/path/to/creds.json")

            with self.assertRaisesRegex(FuelioDataError, "No backup found"):
                client.fetch_fuel_records("folder123", 1)

    def test_parse_csv(self):
        """Test parsing CSV data to filter fuel records"""
        with patch("fuelio.GDrive"):
            client = FuelioClient("/path/to/creds.json")

            # Based on actual Fuelio CSV structure
            csv_data = [
                # Vehicle section
                {"## Vehicle": "## Vehicle", None: []},
                {"## Vehicle": "Name", None: ["Description", "DistUnit"]},
                # Log section starts
                {"## Vehicle": "## Log", None: []},
                # Header row (should be skipped)
                {"## Vehicle": "Data", None: ["Odo (mi)", "Fuel (litres)", "Full"]},
                # Valid fuel record with complete data
                {
                    "## Vehicle": "2024-03-10 16:01",
                    None: [
                        "212477.0",  # 0: Odo
                        "46.301",  # 1: Fuel
                        "1",  # 2: Full
                        "67.09",  # 3: Price
                        "21.8",  # 4: mpg
                        "51.16514",  # 5: latitude
                        "-2.99017",  # 6: longitude
                        "Somerset - Sun all Service Station",  # 7: City/Station
                        "",  # 8: Notes (empty)
                        "0",  # 9: Missed
                        "1",  # 10: TankNumber
                        "-1",  # 11: FuelType
                        "1.449",  # 12: VolumePrice
                        "496456",  # 13: StationID
                        "0.0",  # 14: ExcludeDistance
                        "218",  # 15: UniqueId
                        "0.0",  # 16: TankCalc
                    ],
                },
                # Another valid fuel record
                {
                    "## Vehicle": "2024-03-11 10:30",
                    None: [
                        "212523.5",  # 0: Odo
                        "40.0",  # 1: Fuel
                        "1",  # 2: Full
                        "58.00",  # 3: Price
                        "28.5",  # 4: mpg
                        "51.5",  # 5: latitude
                        "-0.1",  # 6: longitude
                        "BP Station",  # 7: City/Station
                        "Highway fill",  # 8: Notes
                        "0",  # 9: Missed
                        "1",  # 10: TankNumber
                        "110",  # 11: FuelType (Petrol Regular)
                        "1.450",  # 12: VolumePrice
                        "496457",  # 13: StationID
                        "0.0",  # 14: ExcludeDistance
                        "219",  # 15: UniqueId
                        "0.0",  # 16: TankCalc
                    ],
                },
                # End of Log section (new section begins - should stop parsing fuel records)
                {"## Vehicle": "## CostCategories", None: []},
                # This should be ignored (not in Log section)
                {
                    "## Vehicle": "2024-03-12 12:00",
                    None: ["999999.0", "50.0", "1", "70.00"],
                },
            ]

            fuel_records = client._parse_csv(csv_data)  # type: ignore

            self.assertEqual(len(fuel_records), 2)
            self.assertEqual(fuel_records[0].odometer, 212477.0)
            self.assertEqual(fuel_records[0].fuel_consumed, 46.301)
            self.assertEqual(
                fuel_records[0].station, "Somerset - Sun all Service Station"
            )
            self.assertEqual(fuel_records[1].odometer, 212523.5)
            self.assertEqual(fuel_records[1].fuel_consumed, 40.0)
            self.assertEqual(fuel_records[1].notes, "Highway fill")


if __name__ == "__main__":
    unittest.main()

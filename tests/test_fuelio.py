"""Tests for Fuelio client"""

import os
import sys
import unittest
from datetime import datetime
from unittest.mock import Mock, patch

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from exceptions import FuelioDataError
from flio_models import FuelioFuelRecord, FuelioVehicleInfo
from fuelio import FuelioClient


class TestFuelioFuelRecord(unittest.TestCase):
    """Tests for FuelioFuelRecord dataclass"""

    def test_from_csv_row(self):
        """Test creating FuelioFuelRecord from CSV row"""
        # Based on actual Fuelio CSV structure with proper column names
        row = {
            "Data": "2024-03-10 16:01",
            "Odo (mi)": "212477.0",
            "Fuel (litres)": "46.301",
            "Full": "1",
            "Price (optional)": "67.09",
            "mpg (optional)": "21.8",
            "latitude (optional)": "51.16514",
            "longitude (optional)": "-2.99017",
            "City (optional)": "Somerset - Sun all Service Station",
            "Notes (optional)": "Test notes",
            "Missed": "0",
            "TankNumber": "1",
            "FuelType": "-1",
            "VolumePrice": "1.449",
            "StationID (optional)": "496456",
            "ExcludeDistance": "0.0",
            "UniqueId": "218",
            "TankCalc": "0.0",
        }

        fuel_record = FuelioFuelRecord.from_csv_row(row)

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


class TestFuelioVehicleInfo(unittest.TestCase):
    """Tests for FuelioVehicleInfo dataclass"""

    def test_from_csv_row(self):
        """Test creating FuelioVehicleInfo from CSV row"""
        row = {
            "Name": "Yamaha YBR125",
            "Description": "",
            "DistUnit": "1",
            "FuelUnit": "0",
            "ConsumptionUnit": "2",
            "ImportCSVDateFormat": "yyyy-MM-dd",
            "VIN": "",
            "Insurance": "",
            "Plate": "FG12HIJ",
            "Make": "Yamaha",
            "Model": "YBR125",
            "Year": "2013",
            "TankCount": "1",
            "Tank1Type": "100",
            "Tank2Type": "0",
            "Active": "1",
            "Tank1Capacity": "12.0",
            "Tank2Capacity": "0.0",
            "FuelUnitTank2": "0",
            "FuelConsumptionTank2": "0",
            "guid": "a2737dc2-e656-4004-b8ae-9e5ff2a1d542",
            "lastupdated": "1782556534866",
        }

        vehicle_info = FuelioVehicleInfo.from_csv_row(row, vehicle_id=7)

        self.assertEqual(vehicle_info.name, "Yamaha YBR125")
        self.assertEqual(vehicle_info.dist_unit, 1)
        self.assertEqual(vehicle_info.fuel_unit, 0)
        self.assertEqual(vehicle_info.consumption_unit, 2)
        self.assertEqual(vehicle_info.import_csv_date_format, "yyyy-MM-dd")
        self.assertEqual(vehicle_info.plate, "FG12HIJ")
        self.assertEqual(vehicle_info.make, "Yamaha")
        self.assertEqual(vehicle_info.model, "YBR125")
        self.assertEqual(vehicle_info.year, 2013)
        self.assertEqual(vehicle_info.tank_count, 1)
        self.assertEqual(vehicle_info.tank1_type, 100)
        self.assertEqual(vehicle_info.tank2_type, 0)
        self.assertTrue(vehicle_info.active)
        self.assertEqual(vehicle_info.tank1_capacity, 12.0)
        self.assertEqual(vehicle_info.tank2_capacity, 0.0)
        self.assertEqual(vehicle_info.fuel_unit_tank2, 0)
        self.assertEqual(vehicle_info.fuel_consumption_tank2, 0)
        self.assertEqual(vehicle_info.guid, "a2737dc2-e656-4004-b8ae-9e5ff2a1d542")
        self.assertEqual(vehicle_info.last_updated, 1782556534866)
        self.assertEqual(vehicle_info.id, 7)

    def test_from_csv_row_missing_required_name(self):
        """Test vehicle parsing fails when required fields are missing"""
        row = {
            "Name": "",
            "Plate": "FG12HIJ",
            "Make": "Yamaha",
            "Model": "YBR125",
            "DistUnit": "1",
            "FuelUnit": "0",
            "ConsumptionUnit": "2",
            "Year": "2013",
            "TankCount": "1",
            "Tank1Type": "100",
            "Active": "1",
            "Tank1Capacity": "12.0",
        }

        with self.assertRaisesRegex(ValueError, "Required field 'Name'"):
            FuelioVehicleInfo.from_csv_row(row, vehicle_id=7)


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

            # Simulate Log section as CSV text (already extracted)
            log_section_csv = """Data,Odo (mi),Fuel (litres),Full,Price (optional),mpg (optional),latitude (optional),longitude (optional),City (optional),Notes (optional),Missed,TankNumber,FuelType,VolumePrice,StationID (optional),ExcludeDistance,UniqueId,TankCalc
2024-03-10 16:01,212477.0,46.301,1,67.09,21.8,51.16514,-2.99017,Somerset - Sun all Service Station,,0,1,-1,1.449,496456,0.0,218,0.0
2024-03-11 10:30,212523.5,40.0,1,58.00,28.5,51.5,-0.1,BP Station,Highway fill,0,1,110,1.450,496457,0.0,219,0.0
"""

            fuel_records = client._parse_csv_fuel_log(log_section_csv)  # type: ignore

            self.assertEqual(len(fuel_records), 2)
            self.assertEqual(fuel_records[0].odometer, 212477.0)
            self.assertEqual(fuel_records[0].fuel_consumed, 46.301)
            self.assertEqual(
                fuel_records[0].station, "Somerset - Sun all Service Station"
            )
            self.assertEqual(fuel_records[1].odometer, 212523.5)
            self.assertEqual(fuel_records[1].fuel_consumed, 40.0)
            self.assertEqual(fuel_records[1].notes, "Highway fill")
            self.assertEqual(fuel_records[1].odometer, 212523.5)
            self.assertEqual(fuel_records[1].fuel_consumed, 40.0)
            self.assertEqual(fuel_records[1].notes, "Highway fill")
            self.assertEqual(fuel_records[1].fuel_consumed, 40.0)
            self.assertEqual(fuel_records[1].notes, "Highway fill")


if __name__ == "__main__":
    unittest.main()

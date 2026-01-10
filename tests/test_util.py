"""Tests for utility functions"""

import unittest

import sys
import os

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from util import from_camel_case, to_camel_case


class TestCaseConversion(unittest.TestCase):
    """Test case conversion functions"""

    def test_to_camel_case_simple(self):
        """Test simple snake_case to camelCase conversion"""
        self.assertEqual(to_camel_case("fuel_consumed"), "fuelConsumed")
        self.assertEqual(to_camel_case("is_fill_to_full"), "isFillToFull")
        self.assertEqual(to_camel_case("missed_fuel_up"), "missedFuelUp")

    def test_to_camel_case_single_word(self):
        """Test single word (no conversion needed)"""
        self.assertEqual(to_camel_case("date"), "date")
        self.assertEqual(to_camel_case("cost"), "cost")
        self.assertEqual(to_camel_case("notes"), "notes")

    def test_to_camel_case_multiple_underscores(self):
        """Test multiple underscores in sequence"""
        self.assertEqual(to_camel_case("extra_field_name"), "extraFieldName")
        self.assertEqual(to_camel_case("has_odometer_adjustment"), "hasOdometerAdjustment")

    def test_from_camel_case_simple(self):
        """Test simple camelCase to snake_case conversion"""
        self.assertEqual(from_camel_case("fuelConsumed"), "fuel_consumed")
        self.assertEqual(from_camel_case("isFillToFull"), "is_fill_to_full")
        self.assertEqual(from_camel_case("missedFuelUp"), "missed_fuel_up")

    def test_from_camel_case_single_word(self):
        """Test single word (no conversion needed)"""
        self.assertEqual(from_camel_case("date"), "date")
        self.assertEqual(from_camel_case("cost"), "cost")
        self.assertEqual(from_camel_case("notes"), "notes")

    def test_from_camel_case_multiple_capitals(self):
        """Test multiple capital letters"""
        self.assertEqual(from_camel_case("extraFieldName"), "extra_field_name")
        self.assertEqual(
            from_camel_case("hasOdometerAdjustment"), "has_odometer_adjustment"
        )

    def test_round_trip_conversion(self):
        """Test that converting back and forth preserves the value"""
        original = "fuel_consumed"
        self.assertEqual(from_camel_case(to_camel_case(original)), original)

        original = "is_fill_to_full"
        self.assertEqual(from_camel_case(to_camel_case(original)), original)

        original = "odometer_multiplier"
        self.assertEqual(from_camel_case(to_camel_case(original)), original)


if __name__ == "__main__":
    unittest.main()

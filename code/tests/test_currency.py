"""
Unit tests for CurrencyConverter.
"""

import unittest
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from code.data_loader import DataLoader
from code.currency import CurrencyConverter
from code.config import EXCHANGE_RATES_CSV


class TestCurrencyConverter(unittest.TestCase):

    def setUp(self):
        loader = DataLoader()
        rates = loader.load_exchange_rates(EXCHANGE_RATES_CSV)
        self.converter = CurrencyConverter(rates)

    def test_identity_conversion(self):
        self.assertEqual(self.converter.convert(100.0, "EUR", "EUR", "2024-01-15"), 100.0)

    def test_known_rate_conversion(self):
        # 2023-10-15 EUR -> ZAR is 20
        converted = self.converter.convert(50.0, "EUR", "ZAR", "2023-10-15")
        self.assertEqual(converted, 1000.0)

    def test_usd_to_idr_conversion(self):
        # USD -> IDR is 15833.33
        converted = self.converter.convert(10.0, "USD", "IDR", "2024-02-15")
        self.assertAlmostEqual(converted, 158333.3, places=1)


if __name__ == "__main__":
    unittest.main()

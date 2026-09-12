"""
Comprehensive unit tests for CurrencyConverter.

Covers:
- same currency
- normal conversion
- multiple exchange-rate dates
- conversion near a date boundary
- missing rate
- multiple currencies
- repeated conversions
"""

import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from code.config import EXCHANGE_RATES_CSV
from code.currency import CurrencyConverter
from code.data_loader import DataLoader
from code.models import ExchangeRate


class TestCurrencyConverter(unittest.TestCase):

    def setUp(self):
        loader = DataLoader()
        rates = loader.load_exchange_rates(EXCHANGE_RATES_CSV)
        self.converter = CurrencyConverter(rates)

    # 1. Same Currency
    def test_same_currency(self):
        audit = self.converter.convert_with_audit(500.0, "EUR", "EUR", "2025-06-15")
        self.assertEqual(audit.converted_amount, 500.0)
        self.assertEqual(audit.rate_used, 1.0)
        self.assertEqual(audit.lookup_method, "identity")

    # 2. Normal Conversion
    def test_normal_conversion(self):
        # 2023-10-15 EUR -> ZAR is 20
        audit = self.converter.convert_with_audit(50.0, "EUR", "ZAR", "2023-10-15")
        self.assertEqual(audit.converted_amount, 1000.0)
        self.assertEqual(audit.rate_used, 20.0)
        self.assertEqual(audit.lookup_method, "exact")

    # 3. Multiple Exchange-Rate Dates
    def test_multiple_exchange_rate_dates(self):
        # Test rates change deterministically across different dates
        r1 = ExchangeRate("2025-01-01", "USD", "INR", 83.0)
        r2 = ExchangeRate("2025-06-01", "USD", "INR", 85.0)
        r3 = ExchangeRate("2025-12-01", "USD", "INR", 87.0)

        custom_converter = CurrencyConverter([r1, r2, r3])

        # Exact date 2025-01-01
        self.assertEqual(custom_converter.convert(100.0, "USD", "INR", "2025-01-01"), 8300.0)

        # Exact date 2025-06-01
        self.assertEqual(custom_converter.convert(100.0, "USD", "INR", "2025-06-01"), 8500.0)

        # Exact date 2025-12-01
        self.assertEqual(custom_converter.convert(100.0, "USD", "INR", "2025-12-01"), 8700.0)

    # 4. Conversion Near a Date Boundary
    def test_conversion_near_a_date_boundary(self):
        # 2025-05-30 is closest to 2025-06-01 (1 day off) vs 2025-01-01 (149 days off)
        r1 = ExchangeRate("2025-01-01", "USD", "INR", 83.0)
        r2 = ExchangeRate("2025-06-01", "USD", "INR", 85.0)
        custom_converter = CurrencyConverter([r1, r2])

        audit = custom_converter.convert_with_audit(100.0, "USD", "INR", "2025-05-30")
        self.assertEqual(audit.rate_used, 85.0)
        self.assertEqual(audit.rate_date_used, "2025-06-01")
        self.assertEqual(audit.lookup_method, "nearest_date")

    # 5. Missing Rate
    def test_missing_rate(self):
        r1 = ExchangeRate("2025-01-01", "USD", "INR", 83.0)
        custom_converter = CurrencyConverter([r1])

        # JPY -> GBP is missing completely
        with self.assertRaises(ValueError) as ctx:
            custom_converter.convert(100.0, "JPY", "GBP", "2025-01-01")
        self.assertIn("No exchange rate found", str(ctx.exception))

    # 6. Multiple Currencies
    def test_multiple_currencies(self):
        # Real dataset covers USD, EUR, INR, IDR, ZAR
        # USD -> IDR on 2024-02-15 is 15833.33
        usd_idr = self.converter.convert_with_audit(10.0, "USD", "IDR", "2024-02-15")
        self.assertEqual(usd_idr.converted_amount, 158333.3)

        # EUR -> ZAR on 2023-10-15 is 20.0
        eur_zar = self.converter.convert_with_audit(10.0, "EUR", "ZAR", "2023-10-15")
        self.assertEqual(eur_zar.converted_amount, 200.0)

        # USD -> INR on 2024-11-15 is rate 83.33
        usd_inr = self.converter.convert(100.0, "USD", "INR", "2024-11-15")
        self.assertEqual(usd_inr, 8333.0)

    # 7. Repeated Conversions (No precision accumulation error)
    def test_repeated_conversions(self):
        r1 = ExchangeRate("2025-01-01", "USD", "EUR", 0.9)
        custom_converter = CurrencyConverter([r1])

        # Perform 100 repeated conversions and check no drift
        val = 1000.0
        for _ in range(100):
            val = custom_converter.convert(1000.0, "USD", "EUR", "2025-01-01")
        self.assertEqual(val, 900.0)

        # Inverse conversion precision check
        inv_val = custom_converter.convert(900.0, "EUR", "USD", "2025-01-01")
        self.assertAlmostEqual(inv_val, 1000.0, places=1)


if __name__ == "__main__":
    unittest.main(verbosity=2)

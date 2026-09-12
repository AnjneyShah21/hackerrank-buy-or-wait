"""
Unit tests for CashFlowForecaster.
"""

import unittest
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from code.models import UserProfile
from code.currency import CurrencyConverter
from code.forecast import CashFlowForecaster


class TestCashFlowForecaster(unittest.TestCase):

    def setUp(self):
        self.converter = CurrencyConverter()
        self.forecaster = CashFlowForecaster(self.converter)
        self.dummy_profile = UserProfile(
            user_id="user_test",
            home_currency="USD",
            current_available_balance=5000.0,
            minimum_balance_to_keep=1000.0,
        )

    def test_basic_simulation(self):
        is_safe, min_bal, daily_bals = self.forecaster.simulate_90_days(
            profile=self.dummy_profile,
            events=[],
            start_date_str="2026-01-01",
        )
        self.assertTrue(is_safe)
        self.assertEqual(min_bal, 5000.0)
        self.assertEqual(len(daily_bals), 91)  # 0 to 90 inclusive


if __name__ == "__main__":
    unittest.main()

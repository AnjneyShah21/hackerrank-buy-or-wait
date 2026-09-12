"""
Unit tests for DataLoader.
"""

import unittest
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from code.data_loader import DataLoader
from code.config import (
    FINANCIAL_PROFILES_CSV,
    FINANCIAL_EVENTS_CSV,
    EXCHANGE_RATES_CSV,
    REQUEST_PAYMENT_OPTIONS_CSV,
    REQUESTS_CSV,
    SAMPLE_REQUESTS_CSV,
    MESSAGES_CSV,
    IMAGES_CSV,
)


class TestDataLoader(unittest.TestCase):

    def setUp(self):
        self.loader = DataLoader()

    def test_load_profiles(self):
        profiles = self.loader.load_profiles(FINANCIAL_PROFILES_CSV)
        self.assertEqual(len(profiles), 275)
        self.assertIn("user_01", profiles)
        self.assertEqual(profiles["user_01"].home_currency, "ZAR")
        self.assertEqual(profiles["user_01"].minimum_balance_to_keep, 18000.0)

    def test_load_events(self):
        events = self.loader.load_events(FINANCIAL_EVENTS_CSV)
        self.assertEqual(len(events), 25342)

    def test_load_exchange_rates(self):
        rates = self.loader.load_exchange_rates(EXCHANGE_RATES_CSV)
        self.assertEqual(len(rates), 134)

    def test_load_payment_options(self):
        options = self.loader.load_payment_options(REQUEST_PAYMENT_OPTIONS_CSV)
        self.assertEqual(len(options), 790)

    def test_load_requests(self):
        reqs = self.loader.load_requests(REQUESTS_CSV)
        self.assertEqual(len(reqs), 250)

    def test_load_sample_requests(self):
        samples = self.loader.load_sample_requests(SAMPLE_REQUESTS_CSV)
        self.assertEqual(len(samples), 25)

    def test_load_messages(self):
        msgs = self.loader.load_messages(MESSAGES_CSV)
        self.assertEqual(len(msgs), 215)

    def test_load_images_index(self):
        imgs = self.loader.load_images_index(IMAGES_CSV)
        self.assertEqual(len(imgs), 16)


if __name__ == "__main__":
    unittest.main()

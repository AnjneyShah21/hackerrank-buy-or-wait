"""
Unit tests for OutputValidator.
"""

import unittest
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from code.models import OutputRecord, FinancialRequest
from code.validator import OutputValidator


class TestOutputValidator(unittest.TestCase):

    def setUp(self):
        self.dummy_req = FinancialRequest(
            request_id="request_01",
            user_id="user_01",
            request_date="2024-03-03",
            request_type="purchase",
            requested_amount=25256.0,
            desired_completion_date="2024-03-20",
            allows_partial_payment=True,
            request_text="Can I buy laptop?",
        )

    def test_valid_record(self):
        rec = OutputRecord(
            request_id="request_01",
            amount_safe_to_pay="25256",
            affordability_status="affordable_now",
            recommended_payment_method="full_payment",
            payment_plan="2024-03-03:25256",
            earliest_date_for_full_payment="2024-03-03",
            spending_changes_needed="none",
            decision_explanation="Pay ZAR 25,256 today.",
        )
        is_valid, errors = OutputValidator.validate_row(rec, self.dummy_req)
        self.assertTrue(is_valid, f"Validation failed: {errors}")

    def test_invalid_amount_bounds(self):
        rec = OutputRecord(
            request_id="request_01",
            amount_safe_to_pay="30000",  # Exceeds requested_amount 25256
            affordability_status="affordable_now",
            recommended_payment_method="full_payment",
            payment_plan="2024-03-03:25256",
            earliest_date_for_full_payment="2024-03-03",
            spending_changes_needed="none",
            decision_explanation="Pay ZAR 30,000 today.",
        )
        is_valid, errors = OutputValidator.validate_row(rec, self.dummy_req)
        self.assertFalse(is_valid)
        self.assertTrue(any("out of bounds" in e for e in errors))


if __name__ == "__main__":
    unittest.main()

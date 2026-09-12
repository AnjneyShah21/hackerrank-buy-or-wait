"""
Unit tests for edge cases and invariant boundary conditions.
"""

import unittest
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from code.models import OutputRecord, FinancialRequest
from code.validator import OutputValidator


class TestEdgeCases(unittest.TestCase):

    def test_zero_amount_safe(self):
        req = FinancialRequest(
            request_id="request_edge",
            user_id="user_edge",
            request_date="2026-01-01",
            request_type="purchase",
            requested_amount=500.0,
            desired_completion_date="2026-02-01",
            allows_partial_payment=False,
            request_text="Can I buy?",
        )
        rec = OutputRecord(
            request_id="request_edge",
            amount_safe_to_pay="0",
            affordability_status="not_affordable",
            recommended_payment_method="not_recommended",
            payment_plan="none",
            earliest_date_for_full_payment="",
            spending_changes_needed="none",
            decision_explanation="Do not proceed.",
        )
        is_valid, errors = OutputValidator.validate_row(rec, req)
        self.assertTrue(is_valid, f"Failed on zero safe amount: {errors}")


if __name__ == "__main__":
    unittest.main()

"""
Unit tests for PaymentPlanner and DecisionEngine.
"""

import unittest
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from code.models import CandidatePlan, FinancialRequest
from code.decision_engine import DecisionEngine


class TestPaymentPlans(unittest.TestCase):

    def setUp(self):
        self.engine = DecisionEngine()
        self.dummy_req = FinancialRequest(
            request_id="request_test",
            user_id="user_test",
            request_date="2026-01-01",
            request_type="purchase",
            requested_amount=1000.0,
            desired_completion_date="2026-02-01",
            allows_partial_payment=True,
            request_text="Can I buy item?",
        )

    def test_plan_ranking_empty(self):
        best = self.engine.rank_plans([], self.dummy_req)
        self.assertIsNone(best)

    def test_plan_ranking_safe_plan(self):
        plan = CandidatePlan(
            method="full_payment",
            affordability_status="affordable_now",
            is_safe=True,
            payment_plan_str="2026-01-01:1000",
            total_payable=1000.0,
        )
        best = self.engine.rank_plans([plan], self.dummy_req)
        self.assertIsNotNone(best)
        self.assertEqual(best.method, "full_payment")


if __name__ == "__main__":
    unittest.main()

"""
Comprehensive unit tests for PaymentPlanner and DecisionEngine.

Covers all 13 required scenarios:
- full payment succeeds
- full payment fails
- partial payment succeeds
- partial payment fails
- installment succeeds
- installment fails
- wait succeeds
- no safe plan
- competing safe plans
- user payment preference
- payment-option constraints
- minimum-balance violation
- future income dependency
"""

import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from code.config import EXCHANGE_RATES_CSV
from code.currency import CurrencyConverter
from code.data_loader import DataLoader
from code.decision_engine import DecisionEngine
from code.financial_engine import FinancialEngine
from code.forecast import CashFlowForecaster
from code.models import (
    CandidatePlan,
    FinancialEvent,
    FinancialRequest,
    RequestPaymentOption,
    UserProfile,
)
from code.payment_planner import PaymentPlanner


class TestPaymentPlanEngine(unittest.TestCase):

    def setUp(self):
        loader = DataLoader()
        rates = loader.load_exchange_rates(EXCHANGE_RATES_CSV)
        self.converter = CurrencyConverter(rates)
        self.forecaster = CashFlowForecaster(self.converter)
        self.engine = FinancialEngine(self.forecaster)
        self.planner = PaymentPlanner(self.forecaster)
        self.decision = DecisionEngine()

    def _base_profile(self, **overrides) -> UserProfile:
        prof = UserProfile(
            user_id="user_test",
            home_currency="INR",
            current_available_balance=50000.0,
            minimum_balance_to_keep=10000.0,
            expense_categories_to_protect={"rent"},
            expense_categories_user_is_willing_to_reduce={"dining"},
            expense_categories_user_is_willing_to_stop={"entertainment"},
            payment_methods_user_will_consider={"full_payment", "partial_payment", "installments"},
            max_installment_months=6,
        )
        for k, v in overrides.items():
            setattr(prof, k, v)
        return prof

    def _base_request(self, **overrides) -> FinancialRequest:
        req = FinancialRequest(
            request_id="req_test_01",
            user_id="user_test",
            request_date="2026-01-01",
            request_type="purchase",
            requested_amount=20000.0,
            desired_completion_date="2026-03-01",
            allows_partial_payment=True,
            request_text="Can I buy laptop?",
        )
        for k, v in overrides.items():
            setattr(req, k, v)
        return req

    def _base_option(self, **overrides) -> RequestPaymentOption:
        opt = RequestPaymentOption(
            payment_option_id="opt_01",
            request_id="req_test_01",
            payment_method="installments",
            payment_amount=5000.0,
            number_of_payments=4,
            first_payment_date="2026-01-01",
            payment_frequency_days=30,
            financing_fee=0.0,
            total_payable_amount=20000.0,
        )
        for k, v in overrides.items():
            setattr(opt, k, v)
        return opt

    # 1. Full Payment Succeeds
    def test_full_payment_succeeds(self):
        prof = self._base_profile(current_available_balance=50000.0, minimum_balance_to_keep=10000.0)
        req = self._base_request(requested_amount=20000.0)

        plans = self.planner.generate_candidate_plans(prof, [], req, [], 20000.0, "2026-01-01")
        best = self.decision.rank_plans(plans, req)

        self.assertIsNotNone(best)
        self.assertEqual(best.method, "full_payment")
        self.assertEqual(best.affordability_status, "affordable_now")

    # 2. Full Payment Fails
    def test_full_payment_fails(self):
        prof = self._base_profile(current_available_balance=15000.0, minimum_balance_to_keep=10000.0)
        req = self._base_request(requested_amount=20000.0)

        plans = self.planner.generate_candidate_plans(prof, [], req, [], 5000.0, "")
        full_plan = next((p for p in plans if p.method == "full_payment"), None)

        self.assertIsNotNone(full_plan)
        self.assertFalse(full_plan.is_safe)

    # 3. Partial Payment Succeeds
    def test_partial_payment_succeeds(self):
        prof = self._base_profile(current_available_balance=25000.0, minimum_balance_to_keep=10000.0)
        req = self._base_request(requested_amount=30000.0, desired_completion_date="2026-03-01")

        sal_evt = FinancialEvent(
            event_id="e_sal", user_id="user_test", event_type="income", description="Salary",
            category="salary", direction="credit", amount=25000.0, currency="INR", event_date="2026-01-15",
            settlement_date="2026-01-15", status="settled",
        )

        safe_amt = 15000.0  # 25000 available - 10000 min_bal = 15000
        earliest_date = "2026-01-15"

        plans = self.planner.generate_candidate_plans(prof, [sal_evt], req, [], safe_amt, earliest_date)
        partial_plan = next((p for p in plans if p.method == "partial_payment"), None)

        self.assertIsNotNone(partial_plan)
        self.assertTrue(partial_plan.is_safe)
        self.assertEqual(partial_plan.affordability_status, "affordable_with_plan")

    # 4. Partial Payment Fails (Not Allowed or Misses Deadline)
    def test_partial_payment_fails(self):
        prof = self._base_profile(current_available_balance=15000.0)
        # Request does NOT allow partial payment
        req = self._base_request(requested_amount=30000.0, allows_partial_payment=False)

        plans = self.planner.generate_candidate_plans(prof, [], req, [], 5000.0, "2026-01-15")
        partial_plan = next((p for p in plans if p.method == "partial_payment"), None)

        self.assertIsNone(partial_plan)

    # 5. Installment Succeeds
    def test_installment_succeeds(self):
        prof = self._base_profile(
            current_available_balance=20000.0,
            minimum_balance_to_keep=5000.0,
            payment_methods_user_will_consider={"installments"},
        )
        req = self._base_request(requested_amount=12000.0, desired_completion_date="2026-05-01")
        opt = self._base_option(payment_amount=3000.0, number_of_payments=4, total_payable_amount=12000.0)

        plans = self.planner.generate_candidate_plans(prof, [], req, [opt], 5000.0, "")
        best = self.decision.rank_plans(plans, req)

        self.assertIsNotNone(best)
        self.assertEqual(best.method, "installments")
        self.assertEqual(best.payment_option_id, "opt_01")

    # 6. Installment Fails (Exceeds Max Installment Months)
    def test_installment_fails_max_months(self):
        # User limits to 3 months, option has 6 payments
        prof = self._base_profile(max_installment_months=3)
        req = self._base_request(requested_amount=20000.0)
        opt = self._base_option(number_of_payments=6)

        plans = self.planner.generate_candidate_plans(prof, [], req, [opt], 5000.0, "")
        inst_plan = next((p for p in plans if p.method == "installments"), None)

        self.assertIsNone(inst_plan)

    # 7. Wait Succeeds
    def test_wait_succeeds(self):
        # User considers full_payment only
        prof = self._base_profile(
            current_available_balance=12000.0,
            minimum_balance_to_keep=10000.0,
            payment_methods_user_will_consider={"full_payment"},
        )
        req = self._base_request(requested_amount=30000.0, desired_completion_date="2026-04-01")

        sal_evt = FinancialEvent(
            event_id="e_sal", user_id="user_test", event_type="income", description="Salary",
            category="salary", direction="credit", amount=35000.0, currency="INR", event_date="2026-02-15",
            settlement_date="2026-02-15", status="settled",
        )

        plans = self.planner.generate_candidate_plans(prof, [sal_evt], req, [], 2000.0, "2026-02-15")
        best = self.decision.rank_plans(plans, req)

        self.assertIsNotNone(best)
        self.assertEqual(best.method, "wait")
        self.assertEqual(best.affordability_status, "affordable_later")

    # 8. No Safe Plan
    def test_no_safe_plan(self):
        prof = self._base_profile(current_available_balance=10000.0, minimum_balance_to_keep=10000.0)
        req = self._base_request(requested_amount=50000.0, allows_partial_payment=False)

        plans = self.planner.generate_candidate_plans(prof, [], req, [], 0.0, "")
        best = self.decision.rank_plans(plans, req)

        self.assertIsNone(best)

        decision = self.decision.make_decision(req, prof, 0.0, "", best)
        self.assertEqual(decision.recommended_payment_method, "not_recommended")
        self.assertEqual(decision.affordability_status, "not_affordable")
        self.assertEqual(decision.payment_plan, "none")

    # 9. Competing Safe Plans Ranked Deterministically
    def test_competing_safe_plans_ranking(self):
        req = self._base_request(requested_amount=20000.0, desired_completion_date="2026-03-01")

        # Plan A: Installment opt_01, total_payable = 20000.0, first date = 2026-01-01
        plan_a = CandidatePlan(
            method="installments", affordability_status="affordable_with_plan",
            payments=[("2026-01-01", 5000.0), ("2026-02-01", 5000.0)],
            payment_plan_str="2026-01-01:5000|2026-02-01:5000", earliest_date_for_full_payment="2026-02-01",
            spending_changes_str="none", total_payable=20000.0, completion_date="2026-02-01",
            payment_option_id="opt_01", is_safe=True,
        )

        # Plan B: Installment opt_02, total_payable = 22000.0 (fee added)
        plan_b = CandidatePlan(
            method="installments", affordability_status="affordable_with_plan",
            payments=[("2026-01-01", 5500.0), ("2026-02-01", 5500.0)],
            payment_plan_str="2026-01-01:5500|2026-02-01:5500", earliest_date_for_full_payment="2026-02-01",
            spending_changes_str="none", total_payable=22000.0, completion_date="2026-02-01",
            payment_option_id="opt_02", is_safe=True,
        )

        best = self.decision.rank_plans([plan_b, plan_a], req)
        # Plan A wins because total_payable is lower (20000 vs 22000)
        self.assertEqual(best.payment_option_id, "opt_01")

    # 10. User Payment Preference Reject Strategy
    def test_user_payment_preference_rejected(self):
        # User only considers "full_payment" (no installments, no partial_payment)
        prof = self._base_profile(payment_methods_user_will_consider={"full_payment"})
        req = self._base_request(requested_amount=20000.0)
        opt = self._base_option()

        plans = self.planner.generate_candidate_plans(prof, [], req, [opt], 5000.0, "")
        inst_plan = next((p for p in plans if p.method == "installments"), None)
        partial_plan = next((p for p in plans if p.method == "partial_payment"), None)

        self.assertIsNone(inst_plan)
        self.assertIsNone(partial_plan)

    # 11. Payment Option Constraints
    def test_payment_option_constraints(self):
        # max_installment_months = 2, option requires 4 payments -> rejected
        prof = self._base_profile(max_installment_months=2)
        req = self._base_request()
        opt = self._base_option(number_of_payments=4)

        plans = self.planner.generate_candidate_plans(prof, [], req, [opt], 5000.0, "")
        inst_plan = next((p for p in plans if p.method == "installments"), None)

        self.assertIsNone(inst_plan)

    # 12. Minimum Balance Violation Rejection
    def test_minimum_balance_violation(self):
        prof = self._base_profile(current_available_balance=12000.0, minimum_balance_to_keep=10000.0)
        req = self._base_request(requested_amount=5000.0)
        # Installment payment of 4000 drops balance to 8000 (< 10000 min_bal)
        opt = self._base_option(payment_amount=4000.0, number_of_payments=2)

        plans = self.planner.generate_candidate_plans(prof, [], req, [opt], 2000.0, "")
        best = self.decision.rank_plans(plans, req)

        self.assertIsNone(best)

    # 13. Future Income Dependency
    def test_future_income_dependency(self):
        prof = self._base_profile(
            current_available_balance=8000.0,
            minimum_balance_to_keep=5000.0,
            payment_methods_user_will_consider={"installments"},
        )
        req = self._base_request(requested_amount=20000.0)

        sal_evt = FinancialEvent(
            event_id="e_sal", user_id="user_test", event_type="income", description="Salary",
            category="salary", direction="credit", amount=20000.0, currency="INR", event_date="2026-01-05",
            settlement_date="2026-01-05", status="settled",
        )

        opt_after_sal = self._base_option(payment_amount=5000.0, number_of_payments=4, first_payment_date="2026-01-10")
        plans = self.planner.generate_candidate_plans(prof, [sal_evt], req, [opt_after_sal], 3000.0, "2026-01-05")
        best = self.decision.rank_plans(plans, req)

        self.assertIsNotNone(best)
        self.assertEqual(best.method, "installments")


if __name__ == "__main__":
    unittest.main(verbosity=2)

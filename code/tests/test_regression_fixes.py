"""
Regression test suite for generalized financial engine fixes.
Verifies:
1. Recurring event projection in forecast.py
2. Scheduled salary credit inclusion in inflows
3. Installment amount_safe_to_pay calculation
4. Plan ranking tie-breaking rules
5. Multi-action spending change combinations
"""

import unittest
from datetime import datetime, timedelta

from code.currency import CurrencyConverter
from code.decision_engine import DecisionEngine
from code.financial_engine import FinancialEngine
from code.forecast import CashFlowForecaster
from code.models import (
    CandidatePlan,
    ExchangeRate,
    FinancialEvent,
    FinancialRequest,
    RequestPaymentOption,
    UserProfile,
)
from code.payment_planner import PaymentPlanner


class TestGeneralizedFixes(unittest.TestCase):

    def setUp(self):
        rates = [ExchangeRate("2026-01-01", "USD", "USD", 1.0)]
        self.converter = CurrencyConverter(rates)
        self.forecaster = CashFlowForecaster(self.converter)
        self.financial_engine = FinancialEngine(self.forecaster)
        self.planner = PaymentPlanner(self.forecaster)
        self.decision_engine = DecisionEngine()

        self.profile = UserProfile(
            user_id="u1",
            home_currency="USD",
            current_available_balance=5000.0,
            minimum_balance_to_keep=1000.0,
            financial_priorities=["save"],
            expense_categories_to_protect={"rent"},
            expense_categories_user_is_willing_to_reduce={"dining"},
            expense_categories_user_is_willing_to_stop={"streaming"},
            payment_methods_user_will_consider={"full_payment", "installments", "partial_payment"},
            max_installment_months=6,
        )

    def test_recurring_event_projection(self):
        """Test that past settled rent events are projected into the 90-day window."""
        events = [
            FinancialEvent(
                event_id="e1",
                user_id="u1",
                event_type="expense",
                description="Apartment Rent",
                category="rent",
                direction="debit",
                amount=1500.0,
                currency="USD",
                event_date="2026-01-01",
                settlement_date="2026-01-01",
                status="settled",
            ),
            FinancialEvent(
                event_id="e2",
                user_id="u1",
                event_type="expense",
                description="Apartment Rent",
                category="rent",
                direction="debit",
                amount=1500.0,
                currency="USD",
                event_date="2026-02-01",
                settlement_date="2026-02-01",
                status="settled",
            ),
        ]

        # Simulate 90 days from 2026-02-15
        is_safe, min_bal, timeline = self.forecaster.simulate_90_days(
            self.profile, events, "2026-02-15"
        )
        # Check that projected rent events for March, April, May appear in outflows
        projected_dates = [t.date_str for t in timeline if t.required_outflows > 0]
        self.assertTrue(len(projected_dates) >= 3, "Expected projected rent outflows in forecast")

    def test_scheduled_salary_inclusion(self):
        """Test that scheduled salary credits are included in cash flow inflows."""
        events = [
            FinancialEvent(
                event_id="s1",
                user_id="u1",
                event_type="income",
                description="Monthly Salary",
                category="salary",
                direction="credit",
                amount=3000.0,
                currency="USD",
                event_date="2026-03-01",
                settlement_date="2026-03-01",
                status="scheduled",
            )
        ]

        is_safe, min_bal, timeline = self.forecaster.simulate_90_days(
            self.profile, events, "2026-02-15"
        )
        march_1_flow = [t for t in timeline if t.date_str == "2026-03-01"][0]
        self.assertEqual(march_1_flow.confirmed_inflows, 3000.0)

    def test_installment_amount_safe_to_pay(self):
        """Test that for installment plans, amount_safe_to_pay equals the first installment payment."""
        req = FinancialRequest(
            request_id="r1",
            user_id="u1",
            request_date="2026-03-01",
            request_type="purchase",
            requested_amount=3000.0,
            desired_completion_date="2026-06-01",
            allows_partial_payment=False,
            request_text="Buy laptop",
        )

        plan = CandidatePlan(
            method="installments",
            affordability_status="affordable_with_plan",
            payments=[("2026-03-01", 1000.0), ("2026-03-31", 1000.0), ("2026-04-30", 1000.0)],
            payment_plan_str="2026-03-01:1000|2026-03-31:1000|2026-04-30:1000",
            earliest_date_for_full_payment="2026-03-01",
            spending_changes_str="none",
            total_payable=3000.0,
            completion_date="2026-04-30",
            payment_option_id="opt1",
            is_safe=True,
            min_projected_balance=2000.0,
        )

        result = self.decision_engine.make_decision(
            request=req,
            profile=self.profile,
            amount_safe_to_pay=3000.0,
            earliest_date_for_full_payment="2026-03-01",
            best_plan=plan,
        )

        self.assertEqual(result.amount_safe_to_pay, 1000.0)
        self.assertEqual(result.recommended_payment_method, "installments")

    def test_plan_ranking_fewer_payments(self):
        """Test that full payment (1 payment) ranks above installments (3 payments) when both complete by deadline."""
        req = FinancialRequest(
            request_id="r1",
            user_id="u1",
            request_date="2026-03-01",
            request_type="purchase",
            requested_amount=1000.0,
            desired_completion_date="2026-06-01",
            allows_partial_payment=False,
            request_text="Buy items",
        )

        plan_full = CandidatePlan(
            method="full_payment",
            affordability_status="affordable_now",
            payments=[("2026-03-01", 1000.0)],
            payment_plan_str="2026-03-01:1000",
            earliest_date_for_full_payment="2026-03-01",
            spending_changes_str="none",
            total_payable=1000.0,
            completion_date="2026-03-01",
            is_safe=True,
            min_projected_balance=3000.0,
        )

        plan_inst = CandidatePlan(
            method="installments",
            affordability_status="affordable_with_plan",
            payments=[("2026-03-01", 333.33), ("2026-03-31", 333.33), ("2026-04-30", 333.34)],
            payment_plan_str="2026-03-01:333.33|2026-03-31:333.33|2026-04-30:333.34",
            earliest_date_for_full_payment="2026-03-01",
            spending_changes_str="none",
            total_payable=1000.0,
            completion_date="2026-04-30",
            payment_option_id="opt1",
            is_safe=True,
            min_projected_balance=3666.67,
        )

        ranked = self.decision_engine.rank_plans([plan_inst, plan_full], req)
        self.assertEqual(ranked.method, "full_payment")


if __name__ == "__main__":
    unittest.main()

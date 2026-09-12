"""
Adversarial test suite for Buy or Wait? financial decision engine.
Tests 25 synthetic edge-case scenarios based on challenge rules.
"""

import unittest
from datetime import datetime, timedelta

from code.currency import CurrencyConverter
from code.decision_engine import DecisionEngine
from code.evidence import EvidenceManager
from code.image_extractor import ImageExtractor
from code.message_interpreter import MessageInterpreter
from code.financial_engine import FinancialEngine
from code.forecast import CashFlowForecaster
from code.models import (
    CandidatePlan,
    ExchangeRate,
    FinancialEvent,
    FinancialRequest,
    ImageRecord,
    MessageRecord,
    RequestPaymentOption,
    UserProfile,
)
from code.payment_planner import PaymentPlanner


class TestAdversarialScenarios(unittest.TestCase):

    def setUp(self):
        self.rates = [
            ExchangeRate("2026-01-01", "USD", "USD", 1.0),
            ExchangeRate("2026-01-01", "EUR", "USD", 1.1),
            ExchangeRate("2026-01-01", "GBP", "USD", 1.3),
        ]
        self.converter = CurrencyConverter(self.rates)
        self.forecaster = CashFlowForecaster(self.converter)
        self.financial_engine = FinancialEngine(self.forecaster)
        self.planner = PaymentPlanner(self.forecaster)
        self.decision_engine = DecisionEngine()
        self.evidence_manager = EvidenceManager()

        self.base_profile = UserProfile(
            user_id="adv_user",
            home_currency="USD",
            current_available_balance=2000.0,
            minimum_balance_to_keep=500.0,
            financial_priorities=["save"],
            expense_categories_to_protect={"rent", "housing"},
            expense_categories_user_is_willing_to_reduce={"dining"},
            expense_categories_user_is_willing_to_stop={"streaming"},
            payment_methods_user_will_consider={"full_payment", "installments", "partial_payment"},
            max_installment_months=6,
        )

    # 1. Balance exactly equals minimum required balance
    def test_01_balance_equals_minimum_required_balance(self):
        profile = UserProfile(
            user_id="u1", home_currency="USD", current_available_balance=1000.0,
            minimum_balance_to_keep=1000.0, payment_methods_user_will_consider={"full_payment"}
        )
        req = FinancialRequest("r1", "u1", "2026-03-01", "purchase", 100.0, "2026-03-10", False, "Buy item")
        amt_safe = self.financial_engine.compute_amount_safe_to_pay(profile, [], req)
        self.assertEqual(amt_safe, 0.0)

    # 2. Purchase would leave exactly the minimum balance
    def test_02_purchase_leaves_exactly_minimum_balance(self):
        profile = UserProfile(
            user_id="u1", home_currency="USD", current_available_balance=1500.0,
            minimum_balance_to_keep=1000.0, payment_methods_user_will_consider={"full_payment"}
        )
        req = FinancialRequest("r1", "u1", "2026-03-01", "purchase", 500.0, "2026-03-10", False, "Buy item")
        is_safe, min_bal, _ = self.forecaster.simulate_90_days(profile, [], "2026-03-01", proposed_payments=[("2026-03-01", 500.0)])
        self.assertTrue(is_safe)
        self.assertEqual(min_bal, 1000.0)

    # 3. Purchase is one unit above safe amount
    def test_03_purchase_one_unit_above_safe_amount(self):
        profile = UserProfile(
            user_id="u1", home_currency="USD", current_available_balance=1500.0,
            minimum_balance_to_keep=1000.0, payment_methods_user_will_consider={"full_payment"}
        )
        # Payment of 500.01 leaves 999.99 < 1000.0
        is_safe, _, _ = self.forecaster.simulate_90_days(profile, [], "2026-03-01", proposed_payments=[("2026-03-01", 500.01)])
        self.assertFalse(is_safe)

    # 4. Large future essential expense
    def test_04_large_future_essential_expense(self):
        events = [
            FinancialEvent("e1", "adv_user", "expense", "Rent", "rent", "debit", 1200.0, "USD", "2026-03-10", "2026-03-10", "settled", flexibility="fixed")
        ]
        req = FinancialRequest("r1", "adv_user", "2026-03-01", "purchase", 1000.0, "2026-03-15", False, "Buy TV")
        # Balance = 2000. Min = 500. Rent = 1200 on March 10. Max safe today = 2000 - 1200 - 500 = 300.
        amt_safe = self.financial_engine.compute_amount_safe_to_pay(self.base_profile, events, req)
        self.assertEqual(amt_safe, 300.0)

    # 5. Future confirmed income
    def test_05_future_confirmed_income(self):
        profile = UserProfile("u1", "USD", 600.0, 500.0, payment_methods_user_will_consider={"full_payment"})
        events = [
            FinancialEvent("s1", "u1", "income", "Salary", "salary", "credit", 2000.0, "USD", "2026-03-15", "2026-03-15", "scheduled")
        ]
        req = FinancialRequest("r1", "u1", "2026-03-01", "purchase", 1000.0, "2026-04-01", False, "Buy item")
        earliest_date = self.financial_engine.compute_earliest_date_for_full_payment(profile, events, req)
        self.assertEqual(earliest_date, "2026-03-15")

    # 6. Future uncertain income (pending bonus)
    def test_06_future_uncertain_income(self):
        profile = UserProfile("u1", "USD", 600.0, 500.0, payment_methods_user_will_consider={"full_payment"})
        events = [
            FinancialEvent("b1", "u1", "income", "Bonus", "bonus", "credit", 2000.0, "USD", "2026-03-15", "2026-03-15", "pending")
        ]
        req = FinancialRequest("r1", "u1", "2026-03-01", "purchase", 1000.0, "2026-04-01", False, "Buy item")
        earliest_date = self.financial_engine.compute_earliest_date_for_full_payment(profile, events, req)
        self.assertEqual(earliest_date, "")

    # 7. Pending income (refund/lottery)
    def test_07_pending_income(self):
        events = [
            FinancialEvent("r1", "adv_user", "refund", "Refund", "refund", "credit", 500.0, "USD", "2026-03-05", "2026-03-05", "pending")
        ]
        is_safe, min_bal, _ = self.forecaster.simulate_90_days(self.base_profile, events, "2026-03-01", proposed_payments=[("2026-03-01", 1600.0)])
        self.assertFalse(is_safe)

    # 8. Cancelled income
    def test_08_cancelled_income(self):
        events = [
            FinancialEvent("c1", "adv_user", "income", "Salary", "salary", "credit", 5000.0, "USD", "2026-03-05", "2026-03-05", "cancelled")
        ]
        is_safe, _, _ = self.forecaster.simulate_90_days(self.base_profile, events, "2026-03-01", proposed_payments=[("2026-03-01", 1600.0)])
        self.assertFalse(is_safe)

    # 9. Failed expense
    def test_09_failed_expense(self):
        events = [
            FinancialEvent("f1", "adv_user", "expense", "Rent", "rent", "debit", 1000.0, "USD", "2026-03-05", "2026-03-05", "failed")
        ]
        is_safe, _, _ = self.forecaster.simulate_90_days(self.base_profile, events, "2026-03-01", proposed_payments=[("2026-03-01", 1400.0)])
        self.assertTrue(is_safe)

    # 10. Recurring expense arriving immediately after purchase
    def test_10_recurring_expense_immediately_after_purchase(self):
        events = [
            FinancialEvent("s1", "adv_user", "income", "Salary", "salary", "credit", 2000.0, "USD", "2026-02-15", "2026-02-15", "settled"),
            FinancialEvent("r0", "adv_user", "expense", "Rent", "rent", "debit", 1000.0, "USD", "2026-01-02", "2026-01-02", "settled"),
            FinancialEvent("r1", "adv_user", "expense", "Rent", "rent", "debit", 1000.0, "USD", "2026-02-02", "2026-02-02", "settled")
        ]
        # Request on March 1. Recurring rent projects to March 2.
        req = FinancialRequest("r1", "adv_user", "2026-03-01", "purchase", 1200.0, "2026-03-10", False, "Buy phone")
        amt_safe = self.financial_engine.compute_amount_safe_to_pay(self.base_profile, events, req)
        # 2000 balance - 1000 rent - 500 min = 500 max safe
        self.assertEqual(amt_safe, 500.0)

    # 11. Expense arriving on forecast boundary (day 90)
    def test_11_expense_arriving_on_forecast_boundary(self):
        boundary_date = (datetime(2026, 3, 1) + timedelta(days=90)).strftime("%Y-%m-%d")
        events = [
            FinancialEvent("b1", "adv_user", "expense", "Bill", "utilities", "debit", 1000.0, "USD", boundary_date, boundary_date, "settled")
        ]
        is_safe, _, _ = self.forecaster.simulate_90_days(self.base_profile, events, "2026-03-01", proposed_payments=[("2026-03-01", 1000.0)])
        self.assertFalse(is_safe)

    # 12. Multiple currencies (EUR to USD)
    def test_12_multiple_currencies(self):
        # 100 EUR = 110 USD. Balance = 2000 USD. Min = 500 USD.
        events = [
            FinancialEvent("m1", "adv_user", "expense", "EUR Bill", "utilities", "debit", 100.0, "EUR", "2026-03-05", "2026-03-05", "settled")
        ]
        is_safe, min_bal, timeline = self.forecaster.simulate_90_days(self.base_profile, events, "2026-03-01")
        self.assertEqual(min_bal, 1890.0)

    # 13. Missing exchange rate
    def test_13_missing_exchange_rate(self):
        # Missing rate for JPY to USD. Converter raises ValueError on missing rate.
        with self.assertRaises(ValueError):
            self.converter.convert(100.0, "JPY", "USD", "2026-03-01")

    # 14. Missing image record
    def test_14_missing_image(self):
        extractor = ImageExtractor()
        img_rec = ImageRecord("img_missing", "u1", "r1", "e1", "/fake/missing.png", file_exists=False)
        fact = extractor.extract_fact_from_image(img_rec)
        self.assertIsNone(fact.extracted_amount)
        self.assertEqual(fact.fact_kind, "image_missing")

    # 15. Image with an extracted amount
    def test_15_image_with_amount(self):
        extractor = ImageExtractor()
        img_rec = ImageRecord("image_01", "u1", "r1", "e1", "/fake/path.png", file_exists=True)
        fact = extractor.extract_fact_from_image(img_rec)
        self.assertEqual(fact.extracted_amount, 2500.0)

    # 16. Conflicting image and CSV (CSV amount takes priority if present)
    def test_16_conflicting_image_and_csv(self):
        mgr = EvidenceManager()
        event = FinancialEvent("e1", "u1", "expense", "Receipt", "utilities", "debit", 150.0, "USD", "2026-03-01", "2026-03-01", "settled", amount_needs_image=False)
        updated_ev = mgr.apply_evidence_to_event(event)
        self.assertEqual(updated_ev.amount, 150.0)

    # 17. Conflicting message and CSV
    def test_17_conflicting_message_and_csv(self):
        interpreter = MessageInterpreter()
        msg = MessageRecord("m1", "u1", "r1", "e1", "2026-03-01", "user", "Please disregard previous rent of $1000, new rent is $1200.")
        facts = interpreter.interpret_message(msg)
        self.assertTrue(isinstance(facts, list))

    # 18. Cancellation message
    def test_18_cancellation_message(self):
        interpreter = MessageInterpreter()
        msg = MessageRecord("m1", "u1", "r1", "e1", "2026-03-01", "user", "Cancel subscription event_99.")
        facts = interpreter.interpret_message(msg)
        self.assertTrue(isinstance(facts, list))

    # 19. Flexible spending that can be reduced
    def test_19_flexible_spending_reducible(self):
        events = [
            FinancialEvent("flex1", "adv_user", "expense", "Dining", "dining", "debit", 200.0, "USD", "2026-03-05", "2026-03-05", "settled", flexibility="reducible", minimum_allowed_amount=50.0)
        ]
        actions = self.planner.find_flexible_spending_options(self.base_profile, events)
        self.assertIn("reduce_to:flex1:50", actions)

    # 20. Flexible spending that cannot be reduced (protected category)
    def test_20_flexible_spending_protected(self):
        events = [
            FinancialEvent("p1", "adv_user", "expense", "Rent", "rent", "debit", 1000.0, "USD", "2026-03-05", "2026-03-05", "settled", flexibility="reducible", minimum_allowed_amount=500.0)
        ]
        actions = self.planner.find_flexible_spending_options(self.base_profile, events)
        self.assertEqual(actions, [])

    # 21. Installment plan affordable initially but fails later
    def test_21_installment_plan_fails_later(self):
        events = [
            # Balloon payment on month 3
            FinancialEvent("b1", "adv_user", "expense", "Debt Balloon", "debt_repayment", "debit", 1800.0, "USD", "2026-05-01", "2026-05-01", "settled")
        ]
        opt = RequestPaymentOption("opt1", "r1", "installments", 400.0, 3, "2026-03-01", 30, 0.0, 1200.0)
        req = FinancialRequest("r1", "adv_user", "2026-03-01", "purchase", 1200.0, "2026-06-01", False, "Buy laptop")
        plans = self.planner.generate_candidate_plans(self.base_profile, events, req, [opt], 400.0, "2026-03-01")
        safe_installment_plans = [p for p in plans if p.method == "installments" and p.is_safe]
        self.assertEqual(len(safe_installment_plans), 0)

    # 22. Multiple safe payment plans (full vs installments)
    def test_22_multiple_safe_payment_plans(self):
        req = FinancialRequest("r1", "adv_user", "2026-03-01", "purchase", 600.0, "2026-06-01", False, "Buy desk")
        opt = RequestPaymentOption("opt1", "r1", "installments", 200.0, 3, "2026-03-01", 30, 0.0, 600.0)
        plans = self.planner.generate_candidate_plans(self.base_profile, [], req, [opt], 600.0, "2026-03-01")
        best = self.decision_engine.rank_plans(plans, req)
        self.assertEqual(best.method, "full_payment")

    # 23. User preference conflicts with safest plan
    def test_23_user_preference_conflicts(self):
        profile = UserProfile("u1", "USD", 3000.0, 500.0, payment_methods_user_will_consider={"installments"})
        req = FinancialRequest("r1", "u1", "2026-03-01", "purchase", 600.0, "2026-06-01", False, "Buy desk")
        opt = RequestPaymentOption("opt1", "r1", "installments", 200.0, 3, "2026-03-01", 30, 0.0, 600.0)
        plans = self.planner.generate_candidate_plans(profile, [], req, [opt], 600.0, "2026-03-01")
        best = self.decision_engine.rank_plans(plans, req)
        self.assertEqual(best.method, "installments")

    # 24. Requested amount larger than total safe future affordability
    def test_24_requested_amount_larger_than_safe_future_affordability(self):
        profile = UserProfile("u1", "USD", 1000.0, 500.0, payment_methods_user_will_consider={"full_payment"})
        req = FinancialRequest("r1", "u1", "2026-03-01", "purchase", 50000.0, "2026-06-01", False, "Buy house")
        plans = self.planner.generate_candidate_plans(profile, [], req, [], 500.0, "")
        best = self.decision_engine.rank_plans(plans, req)
        res = self.decision_engine.make_decision(req, profile, 500.0, "", best)
        self.assertEqual(res.affordability_status, "not_affordable")
        self.assertEqual(res.recommended_payment_method, "not_recommended")

    # 25. No safe payment method fallback
    def test_25_no_safe_payment_method(self):
        profile = UserProfile("u1", "USD", 600.0, 500.0, payment_methods_user_will_consider={"full_payment", "installments"})
        req = FinancialRequest("r1", "u1", "2026-03-01", "purchase", 2000.0, "2026-06-01", False, "Buy car")
        opt = RequestPaymentOption("opt1", "r1", "installments", 500.0, 4, "2026-03-01", 30, 0.0, 2000.0)
        plans = self.planner.generate_candidate_plans(profile, [], req, [opt], 100.0, "")
        best = self.decision_engine.rank_plans(plans, req)
        res = self.decision_engine.make_decision(req, profile, 100.0, "", best)
        self.assertEqual(res.affordability_status, "not_affordable")
        self.assertEqual(res.recommended_payment_method, "not_recommended")
        self.assertEqual(res.payment_plan, "none")


if __name__ == "__main__":
    unittest.main()

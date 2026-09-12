"""
Comprehensive unit tests for CashFlowForecaster and FinancialEngine.

Covers all 15 required scenarios:
- enough money today
- insufficient money today
- future confirmed salary
- future essential expense
- recurring expense
- recurring income
- flexible spending
- cancelled transaction
- failed transaction
- pending transaction
- minimum balance
- foreign currency
- multiple future events
- conflicting evidence
- purchase near forecast boundary
"""

import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from code.config import EXCHANGE_RATES_CSV
from code.currency import CurrencyConverter
from code.data_loader import DataLoader
from code.evidence import EvidenceManager
from code.financial_engine import FinancialEngine
from code.forecast import CashFlowForecaster
from code.models import ExtractedFact, FinancialEvent, FinancialRequest, UserProfile


class TestDeterministicForecastEngine(unittest.TestCase):

    def setUp(self):
        loader = DataLoader()
        rates = loader.load_exchange_rates(EXCHANGE_RATES_CSV)
        self.converter = CurrencyConverter(rates)
        self.forecaster = CashFlowForecaster(self.converter)
        self.engine = FinancialEngine(self.forecaster)

    def _base_profile(self, **overrides) -> UserProfile:
        prof = UserProfile(
            user_id="user_test",
            home_currency="INR",
            current_available_balance=50000.0,
            minimum_balance_to_keep=10000.0,
            expense_categories_to_protect={"rent", "groceries"},
            expense_categories_user_is_willing_to_reduce={"dining"},
            expense_categories_user_is_willing_to_stop={"entertainment"},
            payment_methods_user_will_consider={"full_payment", "installments"},
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
            desired_completion_date="2026-02-01",
            allows_partial_payment=True,
            request_text="Can I buy a laptop?",
        )
        for k, v in overrides.items():
            setattr(req, k, v)
        return req

    # 1. Enough Money Today
    def test_enough_money_today(self):
        prof = self._base_profile(current_available_balance=50000.0, minimum_balance_to_keep=10000.0)
        req = self._base_request(requested_amount=20000.0)

        safe_amt = self.engine.compute_amount_safe_to_pay(prof, [], req)
        earliest_date = self.engine.compute_earliest_date_for_full_payment(prof, [], req)

        self.assertEqual(safe_amt, 20000.0)
        self.assertEqual(earliest_date, "2026-01-01")

    # 2. Insufficient Money Today
    def test_insufficient_money_today(self):
        prof = self._base_profile(current_available_balance=15000.0, minimum_balance_to_keep=10000.0)
        req = self._base_request(requested_amount=20000.0)

        safe_amt = self.engine.compute_amount_safe_to_pay(prof, [], req)

        # Max safe today = 15000 - 10000 = 5000
        self.assertEqual(safe_amt, 5000.0)

    # 3. Future Confirmed Salary
    def test_future_confirmed_salary(self):
        prof = self._base_profile(current_available_balance=12000.0, minimum_balance_to_keep=10000.0)
        req = self._base_request(requested_amount=20000.0)

        # Confirmed salary of 30000 on 2026-01-15
        salary_evt = FinancialEvent(
            event_id="e_sal_01",
            user_id="user_test",
            event_type="income",
            description="Monthly Salary",
            category="salary",
            direction="credit",
            amount=30000.0,
            currency="INR",
            event_date="2026-01-15",
            settlement_date="2026-01-15",
            status="settled",
        )

        safe_today = self.engine.compute_amount_safe_to_pay(prof, [salary_evt], req)
        earliest_date = self.engine.compute_earliest_date_for_full_payment(prof, [salary_evt], req)

        self.assertEqual(safe_today, 2000.0)
        self.assertEqual(earliest_date, "2026-01-15")

    # 4. Future Essential Expense
    def test_future_essential_expense(self):
        prof = self._base_profile(current_available_balance=40000.0, minimum_balance_to_keep=10000.0)
        req = self._base_request(requested_amount=25000.0)

        # Rent expense of 20000 due on 2026-01-10
        rent_evt = FinancialEvent(
            event_id="e_rent_01",
            user_id="user_test",
            event_type="expense",
            description="House Rent",
            category="rent",
            direction="debit",
            amount=20000.0,
            currency="INR",
            event_date="2026-01-10",
            settlement_date="2026-01-10",
            status="settled",
            flexibility="fixed",
        )

        safe_today = self.engine.compute_amount_safe_to_pay(prof, [rent_evt], req)

        # Total available = 40000, essential rent = 20000, min_bal = 10000 -> max safe = 10000
        self.assertEqual(safe_today, 10000.0)

    # 5. Recurring Expense
    def test_recurring_expense(self):
        prof = self._base_profile(current_available_balance=50000.0, minimum_balance_to_keep=10000.0)
        req = self._base_request(requested_amount=30000.0)

        # Two monthly recurring bills on Jan 10 and Feb 10 (15000 each)
        bill1 = FinancialEvent(
            event_id="e_bill_01", user_id="user_test", event_type="expense", description="Loan EMI",
            category="debt", direction="debit", amount=15000.0, currency="INR", event_date="2026-01-10",
            settlement_date="2026-01-10", status="settled",
        )
        bill2 = FinancialEvent(
            event_id="e_bill_02", user_id="user_test", event_type="expense", description="Loan EMI",
            category="debt", direction="debit", amount=15000.0, currency="INR", event_date="2026-02-10",
            settlement_date="2026-02-10", status="settled",
        )

        is_safe_full, min_bal, _ = self.forecaster.simulate_90_days(
            prof, [bill1, bill2], "2026-01-01", proposed_payments=[("2026-01-01", 30000.0)]
        )
        # 50000 - 30000 - 15000 = 5000 (falls below 10000 min_balance!)
        self.assertFalse(is_safe_full)

    # 6. Recurring Income
    def test_recurring_income(self):
        prof = self._base_profile(current_available_balance=20000.0, minimum_balance_to_keep=10000.0)
        req = self._base_request(requested_amount=30000.0)

        sal1 = FinancialEvent(
            event_id="e_sal_01", user_id="user_test", event_type="income", description="Salary",
            category="salary", direction="credit", amount=25000.0, currency="INR", event_date="2026-01-15",
            settlement_date="2026-01-15", status="settled",
        )
        sal2 = FinancialEvent(
            event_id="e_sal_02", user_id="user_test", event_type="income", description="Salary",
            category="salary", direction="credit", amount=25000.0, currency="INR", event_date="2026-02-15",
            settlement_date="2026-02-15", status="settled",
        )

        earliest = self.engine.compute_earliest_date_for_full_payment(prof, [sal1, sal2], req)
        self.assertEqual(earliest, "2026-01-15")

    # 7. Flexible Spending
    def test_flexible_spending(self):
        prof = self._base_profile(current_available_balance=35000.0, minimum_balance_to_keep=10000.0)

        ent_evt = FinancialEvent(
            event_id="e_ent_14", user_id="user_test", event_type="expense", description="Concert",
            category="entertainment", direction="debit", amount=10000.0, currency="INR", event_date="2026-01-05",
            settlement_date="2026-01-05", status="settled", flexibility="stoppable",
        )

        # Without stopping entertainment: 35000 - 10000 = 25000 available - 20000 purchase = 5000 (< 10000 min_bal)
        is_safe_raw, _, _ = self.forecaster.simulate_90_days(
            prof, [ent_evt], "2026-01-01", proposed_payments=[("2026-01-01", 20000.0)]
        )
        self.assertFalse(is_safe_raw)

        # With stopping entertainment: 35000 - 20000 purchase = 15000 (>= 10000 min_bal)
        is_safe_stopped, _, _ = self.forecaster.simulate_90_days(
            prof, [ent_evt], "2026-01-01", spending_changes=["stop:e_ent_14"], proposed_payments=[("2026-01-01", 20000.0)]
        )
        self.assertTrue(is_safe_stopped)

    # 8. Cancelled Transaction
    def test_cancelled_transaction(self):
        prof = self._base_profile(current_available_balance=50000.0, minimum_balance_to_keep=10000.0)

        cancelled_evt = FinancialEvent(
            event_id="e_canc_01", user_id="user_test", event_type="expense", description="Cancelled Flight",
            category="travel", direction="debit", amount=30000.0, currency="INR", event_date="2026-01-05",
            settlement_date="2026-01-05", status="cancelled",
        )

        is_safe, min_bal, _ = self.forecaster.simulate_90_days(
            prof, [cancelled_evt], "2026-01-01", proposed_payments=[("2026-01-01", 35000.0)]
        )
        self.assertTrue(is_safe)
        self.assertEqual(min_bal, 15000.0)

    # 9. Failed Transaction
    def test_failed_transaction(self):
        prof = self._base_profile(current_available_balance=50000.0, minimum_balance_to_keep=10000.0)

        failed_evt = FinancialEvent(
            event_id="e_fail_01", user_id="user_test", event_type="expense", description="Failed ATM Withdrawal",
            category="cash", direction="debit", amount=25000.0, currency="INR", event_date="2026-01-05",
            settlement_date="2026-01-05", status="failed",
        )

        is_safe, min_bal, _ = self.forecaster.simulate_90_days(
            prof, [failed_evt], "2026-01-01", proposed_payments=[("2026-01-01", 35000.0)]
        )
        self.assertTrue(is_safe)

    # 10. Pending Transaction
    def test_pending_transaction(self):
        prof = self._base_profile(current_available_balance=30000.0, minimum_balance_to_keep=10000.0)

        # Pending bonus (credit) -> MUST NOT be counted
        pending_bonus = FinancialEvent(
            event_id="e_bonus_99", user_id="user_test", event_type="income", description="Quarterly Bonus",
            category="bonus", direction="credit", amount=50000.0, currency="INR", event_date="2026-01-10",
            settlement_date="2026-01-10", status="pending",
        )

        # Pending debit -> reserved conservatively
        pending_bill = FinancialEvent(
            event_id="e_bill_pending", user_id="user_test", event_type="expense", description="Utility Bill",
            category="utility", direction="debit", amount=5000.0, currency="INR", event_date="2026-01-10",
            settlement_date="2026-01-10", status="pending",
        )

        req = self._base_request(requested_amount=20000.0)
        safe_amt = self.engine.compute_amount_safe_to_pay(prof, [pending_bonus, pending_bill], req)

        # Available = 30000 - 5000 (pending bill reserved) - 10000 (min_bal) = 15000
        self.assertEqual(safe_amt, 15000.0)

    # 11. Minimum Balance
    def test_minimum_balance_strictly_enforced(self):
        prof = self._base_profile(current_available_balance=50000.0, minimum_balance_to_keep=20000.0)

        # Purchase of 35000 leaves 15000 ending balance, which is < 20000 minimum balance!
        is_safe, min_bal, _ = self.forecaster.simulate_90_days(
            prof, [], "2026-01-01", proposed_payments=[("2026-01-01", 35000.0)]
        )
        self.assertFalse(is_safe)
        self.assertEqual(min_bal, 15000.0)

    # 12. Foreign Currency Event
    def test_foreign_currency_event(self):
        # User in ZAR, event in EUR
        prof = self._base_profile(home_currency="ZAR", current_available_balance=50000.0, minimum_balance_to_keep=10000.0)

        # EUR 1000 event on 2023-10-15 (Rate EUR -> ZAR is 20.0 = ZAR 20000)
        eur_evt = FinancialEvent(
            event_id="e_eur_01", user_id="user_test", event_type="expense", description="EUR Equipment",
            category="equipment", direction="debit", amount=1000.0, currency="EUR", event_date="2023-10-15",
            settlement_date="2023-10-15", status="settled",
        )

        is_safe, min_bal, _ = self.forecaster.simulate_90_days(
            prof, [eur_evt], "2023-10-15", proposed_payments=[("2023-10-15", 25000.0)]
        )
        # 50000 - 20000 (EUR 1000 converted) - 25000 purchase = 5000 (< 10000 min_bal)
        self.assertFalse(is_safe)
        self.assertEqual(min_bal, 5000.0)

    # 13. Multiple Future Events
    def test_multiple_future_events(self):
        prof = self._base_profile(current_available_balance=40000.0, minimum_balance_to_keep=10000.0)

        # Jan 10: -15000 rent
        e1 = FinancialEvent(
            event_id="e1", user_id="user_test", event_type="expense", description="Rent",
            category="rent", direction="debit", amount=15000.0, currency="INR", event_date="2026-01-10",
            settlement_date="2026-01-10", status="settled",
        )
        # Jan 20: +25000 salary
        e2 = FinancialEvent(
            event_id="e2", user_id="user_test", event_type="income", description="Salary",
            category="salary", direction="credit", amount=25000.0, currency="INR", event_date="2026-01-20",
            settlement_date="2026-01-20", status="settled",
        )
        # Feb 05: -10000 insurance
        e3 = FinancialEvent(
            event_id="e3", user_id="user_test", event_type="expense", description="Insurance",
            category="insurance", direction="debit", amount=10000.0, currency="INR", event_date="2026-02-05",
            settlement_date="2026-02-05", status="settled",
        )

        is_safe, min_bal, timeline = self.forecaster.simulate_90_days(
            prof, [e1, e2, e3], "2026-01-01", proposed_payments=[("2026-01-01", 10000.0)]
        )
        self.assertTrue(is_safe)
        self.assertGreaterEqual(min_bal, 10000.0)

    # 14. Conflicting Evidence Mutates Event Before Forecast
    def test_conflicting_evidence_in_forecast(self):
        prof = self._base_profile(current_available_balance=50000.0, minimum_balance_to_keep=10000.0)

        sal_evt = FinancialEvent(
            event_id="e_sal_amend", user_id="user_test", event_type="income", description="Salary",
            category="salary", direction="credit", amount=20000.0, currency="INR", event_date="2026-01-15",
            settlement_date="2026-01-15", status="settled",
        )

        # Evidence increases salary to 35000
        fact = ExtractedFact(
            fact_id="f_sal_up", source_type="message", source_id="msg_01", user_id="user_test",
            related_event_id="e_sal_amend", fact_kind="salary_update", extracted_amount=35000.0,
            confidence=1.0,
        )

        ev_mgr = EvidenceManager()
        ev_mgr.add_fact(fact)
        updated_sal = ev_mgr.apply_evidence_to_event(sal_evt)

        self.assertEqual(updated_sal.amount, 35000.0)

        req = self._base_request(requested_amount=60000.0)
        earliest = self.engine.compute_earliest_date_for_full_payment(prof, [updated_sal], req)
        # 50000 available + 35000 salary = 85000 - 60000 purchase = 25000 >= 10000 min_bal on Jan 15
        self.assertEqual(earliest, "2026-01-15")

    # 15. Purchase Near Forecast Boundary (Day 89)
    def test_purchase_near_forecast_boundary(self):
        prof = self._base_profile(current_available_balance=50000.0, minimum_balance_to_keep=10000.0)

        # Payment proposed on day 89 (2026-03-31)
        is_safe, min_bal, _ = self.forecaster.simulate_90_days(
            prof, [], "2026-01-01", proposed_payments=[("2026-03-31", 35000.0)], forecast_days=90
        )
        self.assertTrue(is_safe)
        self.assertEqual(min_bal, 15000.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)

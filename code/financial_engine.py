"""
Financial engine calculating baseline safety metrics:
- amount_safe_to_pay
- earliest_date_for_full_payment
- plan candidate safety verification
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

from code.config import FORECAST_DAYS
from code.forecast import CashFlowForecaster
from code.models import CandidatePlan, FinancialEvent, FinancialRequest, UserProfile


def _parse_date(date_str: str) -> datetime.date:
    try:
        return datetime.strptime(date_str[:10], "%Y-%m-%d").date()
    except Exception:
        return datetime(2026, 1, 1).date()


class FinancialEngine:
    """Calculates primary financial safety indicators using deterministic 90-day forecasts."""

    def __init__(self, forecaster: CashFlowForecaster):
        self.forecaster = forecaster

    def compute_amount_safe_to_pay(
        self,
        profile: UserProfile,
        events: List[FinancialEvent],
        request: FinancialRequest,
    ) -> float:
        """
        Calculates the maximum amount safe to pay on request_date
        BEFORE optional spending changes, without violating the 90-day minimum balance.
        Guarantees: 0 <= amount_safe_to_pay <= requested_amount.
        """
        req_amount = request.requested_amount
        if req_amount <= 0:
            return 0.0

        # Check if paying full requested_amount is safe today
        is_safe_full, _, _ = self.forecaster.simulate_90_days(
            profile=profile,
            events=events,
            start_date_str=request.request_date,
            proposed_payments=[(request.request_date, req_amount)],
        )
        if is_safe_full:
            return req_amount

        # Check if paying 0 is safe today
        is_safe_zero, _, _ = self.forecaster.simulate_90_days(
            profile=profile,
            events=events,
            start_date_str=request.request_date,
            proposed_payments=[],
        )
        if not is_safe_zero:
            return 0.0

        # Binary search for the maximum safe amount in [0.0, req_amount]
        low = 0.0
        high = req_amount
        best_safe = 0.0

        for _ in range(25):  # High precision binary search
            mid = round((low + high) / 2.0, 2)
            safe, _, _ = self.forecaster.simulate_90_days(
                profile=profile,
                events=events,
                start_date_str=request.request_date,
                proposed_payments=[(request.request_date, mid)],
            )
            if safe:
                best_safe = mid
                low = mid
            else:
                high = mid

        return round(best_safe, 2)

    def compute_earliest_date_for_full_payment(
        self,
        profile: UserProfile,
        events: List[FinancialEvent],
        request: FinancialRequest,
    ) -> str:
        """
        Calculates the first date when 100% of requested_amount can be paid
        without optional spending changes, maintaining minimum balance throughout 90 days.
        Returns YYYY-MM-DD or empty string "" if not safe within 90 days.
        """
        start_dt = _parse_date(request.request_date)
        req_amount = request.requested_amount

        for day_offset in range(FORECAST_DAYS + 1):
            cand_dt = start_dt + timedelta(days=day_offset)
            cand_date_str = cand_dt.strftime("%Y-%m-%d")

            forecast_horizon = max(FORECAST_DAYS, day_offset + FORECAST_DAYS)
            is_safe, _, _ = self.forecaster.simulate_90_days(
                profile=profile,
                events=events,
                start_date_str=request.request_date,
                forecast_days=forecast_horizon,
                proposed_payments=[(cand_date_str, req_amount)],
            )
            if is_safe:
                return cand_date_str

        return ""

    def evaluate_candidate_plan_safety(
        self,
        profile: UserProfile,
        events: List[FinancialEvent],
        request: FinancialRequest,
        proposed_payments: List[Tuple[str, float]],
        spending_changes: Optional[List[str]] = None,
    ) -> Tuple[bool, float]:
        """
        Evaluates whether a candidate payment plan (e.g. installments or partial payment)
        remains safe throughout the 90-day simulation.
        Returns: (is_safe, min_balance_reached)
        """
        is_safe, min_bal, _ = self.forecaster.simulate_90_days(
            profile=profile,
            events=events,
            start_date_str=request.request_date,
            spending_changes=spending_changes,
            proposed_payments=proposed_payments,
        )
        return is_safe, min_bal

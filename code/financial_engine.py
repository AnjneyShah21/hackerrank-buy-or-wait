"""
Financial engine calculating baseline safety metrics:
- amount_safe_to_pay
- earliest_date_for_full_payment
"""

from typing import List, Tuple, Optional
from code.models import UserProfile, FinancialEvent, FinancialRequest
from code.forecast import CashFlowForecaster


class FinancialEngine:
    """Calculates primary financial safety indicators."""

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
        0 <= amount_safe_to_pay <= requested_amount
        """
        # Skeleton interface definition
        return 0.0

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
        # Skeleton interface definition
        return ""

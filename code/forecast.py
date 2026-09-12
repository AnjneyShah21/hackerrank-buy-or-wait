"""
Forecast engine for 90-day daily cash-flow simulation.
Evaluates balance trajectory against minimum_balance_to_keep.
"""

from datetime import datetime, timedelta
from typing import List, Dict, Tuple, Optional, Set
from code.models import UserProfile, FinancialEvent
from code.currency import CurrencyConverter
from code.config import FORECAST_DAYS


class CashFlowForecaster:
    """Simulates daily user liquidity over a 90-day horizon."""

    def __init__(self, currency_converter: CurrencyConverter):
        self.converter = currency_converter

    def simulate_90_days(
        self,
        profile: UserProfile,
        events: List[FinancialEvent],
        start_date_str: str,
        spending_changes: Optional[List[str]] = None,
        additional_debits: Optional[List[Tuple[str, float]]] = None,
    ) -> Tuple[bool, float, Dict[str, float]]:
        """
        Simulates daily balance from start_date for 90 days.
        Returns:
            (is_safe, min_balance_reached, daily_balances_dict)
        """
        # Placeholder skeleton interface
        start_dt = datetime.strptime(start_date_str, "%Y-%m-%d").date()
        daily_balances: Dict[str, float] = {}
        current_balance = profile.current_available_balance
        min_balance = current_balance
        is_safe = True

        for day_offset in range(FORECAST_DAYS + 1):
            curr_date = start_dt + timedelta(days=day_offset)
            date_str = curr_date.strftime("%Y-%m-%d")
            daily_balances[date_str] = current_balance
            if current_balance < profile.minimum_balance_to_keep:
                is_safe = False
            if current_balance < min_balance:
                min_balance = current_balance

        return is_safe, min_balance, daily_balances

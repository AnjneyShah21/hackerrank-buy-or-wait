"""
Forecast engine for 90-day daily cash-flow simulation.
Evaluates balance trajectory against minimum_balance_to_keep deterministically.
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Tuple

from code.config import FORECAST_DAYS
from code.currency import CurrencyConverter
from code.models import DailyCashFlow, FinancialEvent, UserProfile


def _parse_date(date_str: str) -> datetime.date:
    """Parses YYYY-MM-DD string into a date object."""
    try:
        return datetime.strptime(date_str[:10], "%Y-%m-%d").date()
    except Exception:
        return datetime(2026, 1, 1).date()


class CashFlowForecaster:
    """Simulates daily user liquidity over a 90-day horizon."""

    def __init__(self, currency_converter: CurrencyConverter):
        self.converter = currency_converter

    def parse_spending_changes(
        self, spending_changes: Optional[List[str]]
    ) -> Tuple[Set[str], Dict[str, float]]:
        """
        Parses spending change directives into stopped event IDs and reduced event amounts.
        Format: 'stop:<event_id>' or 'reduce_to:<event_id>:<new_amount>'
        """
        stopped_events: Set[str] = set()
        reduced_events: Dict[str, float] = {}

        if not spending_changes:
            return stopped_events, reduced_events

        for action in spending_changes:
            if not action or action == "none":
                continue
            parts = action.split(":")
            if parts[0] == "stop" and len(parts) >= 2:
                stopped_events.add(parts[1])
            elif parts[0] == "reduce_to" and len(parts) >= 3:
                try:
                    reduced_events[parts[1]] = float(parts[2])
                except ValueError:
                    pass

        return stopped_events, reduced_events

    def simulate_90_days(
        self,
        profile: UserProfile,
        events: List[FinancialEvent],
        start_date_str: str,
        spending_changes: Optional[List[str]] = None,
        proposed_payments: Optional[List[Tuple[str, float]]] = None,
        forecast_days: int = FORECAST_DAYS,
    ) -> Tuple[bool, float, List[DailyCashFlow]]:
        """
        Simulates daily balance from start_date_str for forecast_days (90 days).
        Returns:
            (is_safe, min_balance_reached, timeline)
        """
        start_dt = _parse_date(start_date_str)
        end_dt = start_dt + timedelta(days=forecast_days)

        stopped_events, reduced_events = self.parse_spending_changes(spending_changes)

        # Proposed payments map: date_str -> list of amounts
        proposed_by_date: Dict[str, float] = {}
        if proposed_payments:
            for p_date, p_amt in proposed_payments:
                proposed_by_date[p_date] = (
                    proposed_by_date.get(p_date, 0.0) + p_amt
                )

        # Index event cash flows by date YYYY-MM-DD
        # We classify events into required_outflows, flexible_outflows, and inflows
        daily_inflows: Dict[str, List[Tuple[str, float]]] = {}
        daily_required_outflows: Dict[str, List[Tuple[str, float]]] = {}
        daily_flexible_outflows: Dict[str, List[Tuple[str, float]]] = {}

        for ev in events:
            # 1. Filter out non-cash, cancelled, failed, unrealized investment events
            if (
                ev.status in ("cancelled", "failed", "unrealized")
                or ev.direction == "non_cash"
            ):
                continue

            # Amount safety check
            if ev.amount is None or ev.amount <= 0:
                continue

            # Event date / settlement date
            effective_date_str = ev.settlement_date or ev.event_date
            if not effective_date_str:
                continue

            ev_dt = _parse_date(effective_date_str)

            # Skip events occurring before start_date (already reflected in initial available balance)
            if ev_dt < start_dt:
                continue

            # Convert event amount to profile home currency if different
            amt_home = ev.amount
            if ev.currency and ev.currency.upper() != profile.home_currency.upper():
                amt_home = self.converter.convert(
                    ev.amount, ev.currency, profile.home_currency, effective_date_str
                )

            # Process Inflows (Credits)
            if ev.direction == "credit":
                # Rule: DO NOT count pending credits, bonuses, refunds, lottery, or unconfirmed income
                if ev.status == "pending":
                    continue
                # Include confirmed/settled credits
                if ev_dt <= end_dt:
                    d_str = ev_dt.strftime("%Y-%m-%d")
                    if d_str not in daily_inflows:
                        daily_inflows[d_str] = []
                    daily_inflows[d_str].append((ev.event_id, amt_home))

            # Process Outflows (Debits)
            elif ev.direction == "debit":
                # Stopped by spending change?
                if ev.event_id in stopped_events:
                    continue

                # Reduced by spending change?
                if ev.event_id in reduced_events:
                    amt_home = min(amt_home, reduced_events[ev.event_id])

                if ev_dt <= end_dt:
                    d_str = ev_dt.strftime("%Y-%m-%d")
                    is_flexible = ev.flexibility in (
                        "reducible",
                        "stoppable",
                        "reducible_or_stoppable",
                    ) and (
                        ev.category
                        in profile.expense_categories_user_is_willing_to_reduce
                        or ev.category
                        in profile.expense_categories_user_is_willing_to_stop
                    )

                    if is_flexible:
                        if d_str not in daily_flexible_outflows:
                            daily_flexible_outflows[d_str] = []
                        daily_flexible_outflows[d_str].append(
                            (ev.event_id, amt_home)
                        )
                    else:
                        if d_str not in daily_required_outflows:
                            daily_required_outflows[d_str] = []
                        daily_required_outflows[d_str].append(
                            (ev.event_id, amt_home)
                        )

        # Run day-by-day cash flow simulation
        current_balance = float(profile.current_available_balance)
        min_balance_reached = current_balance
        is_safe = True
        timeline: List[DailyCashFlow] = []

        for day_offset in range(forecast_days + 1):
            curr_date = start_dt + timedelta(days=day_offset)
            date_str = curr_date.strftime("%Y-%m-%d")

            start_bal = current_balance

            # Calculate today's totals
            inflow_items = daily_inflows.get(date_str, [])
            req_outflow_items = daily_required_outflows.get(date_str, [])
            flex_outflow_items = daily_flexible_outflows.get(date_str, [])

            inflows_sum = sum(amt for _, amt in inflow_items)
            req_outflows_sum = sum(amt for _, amt in req_outflow_items)
            flex_outflows_sum = sum(amt for _, amt in flex_outflow_items)
            proposed_sum = proposed_by_date.get(date_str, 0.0)

            ending_bal = round(
                start_bal
                + inflows_sum
                - req_outflows_sum
                - proposed_sum
                - flex_outflows_sum,
                4,
            )

            # Safety check against minimum_balance_to_keep
            if ending_bal < profile.minimum_balance_to_keep:
                is_safe = False

            if ending_bal < min_balance_reached:
                min_balance_reached = ending_bal

            t_entry = DailyCashFlow(
                date_str=date_str,
                starting_balance=round(start_bal, 4),
                confirmed_inflows=round(inflows_sum, 4),
                required_outflows=round(req_outflows_sum, 4),
                proposed_payments=round(proposed_sum, 4),
                flexible_outflows=round(flex_outflows_sum, 4),
                ending_balance=ending_bal,
                inflow_events=[eid for eid, _ in inflow_items],
                outflow_events=[
                    eid for eid, _ in (req_outflow_items + flex_outflow_items)
                ],
            )
            timeline.append(t_entry)

            # Update current_balance for next day
            current_balance = ending_bal

        return is_safe, min_balance_reached, timeline

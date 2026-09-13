"""
Forecast engine for 90-day daily cash-flow simulation.
Evaluates balance trajectory against minimum_balance_to_keep deterministically.
"""

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set, Tuple

from code.config import FORECAST_DAYS
from code.currency import CurrencyConverter
from code.models import DailyCashFlow, FinancialEvent, UserProfile


from functools import lru_cache


_ONE_TIME_INCOME_KEYWORDS = {
    "arrears", "bonus", "commission", "promotion", "prorated",
    "seasonal", "peak-season", "one-time", "reimbursement", "severance",
}
_STABLE_SALARY_KEYWORDS = {
    "salary", "payroll", "wage", "employer", "paycheck",
    "next confirmed salary", "regular income",
}


def _is_one_time_income_event(event: FinancialEvent) -> bool:
    """Return whether a credit should be excluded from recurrence learning."""
    if event.direction != "credit":
        return False
    description = (event.description or "").lower()
    return any(keyword in description for keyword in _ONE_TIME_INCOME_KEYWORDS)


@lru_cache(maxsize=8192)
def _parse_date(date_str: str) -> Optional[datetime.date]:
    """Parses YYYY-MM-DD string into a date object with O(1) lru_cache and fast int slicing."""
    if not date_str:
        return None
    try:
        s = date_str[:10]
        return datetime(int(s[:4]), int(s[5:7]), int(s[8:10])).date()
    except Exception:
        return None


def _add_months(dt: datetime.date, n_months: int) -> datetime.date:
    """Adds n_months to a date object, clamping day to valid month end."""
    year = dt.year + (dt.month - 1 + n_months) // 12
    month = (dt.month - 1 + n_months) % 12 + 1
    if month in (1, 3, 5, 7, 8, 10, 12):
        max_d = 31
    elif month in (4, 6, 9, 11):
        max_d = 30
    else:
        max_d = 29 if (year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)) else 28
    day = min(dt.day, max_d)
    return datetime(year, month, day).date()


class CashFlowForecaster:
    """Simulates daily user liquidity over a 90-day horizon."""

    def __init__(self, currency_converter: CurrencyConverter, evidence_manager: Optional[Any] = None):
        self.converter = currency_converter
        self.evidence_manager = evidence_manager
        self._recurrence_cache: Dict[Tuple[str, str, str], List[FinancialEvent]] = {}

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

    def _project_recurring_events(
        self,
        events: List[FinancialEvent],
        start_dt: datetime.date,
        end_dt: datetime.date,
    ) -> List[FinancialEvent]:
        """
        Detects recurring historical income/expense patterns and projects future instances
        across the forecast window (start_dt to end_dt). Uses caching to avoid repeated computation.
        """
        user_id = events[0].user_id if events else "unknown"
        start_str = start_dt.strftime("%Y-%m-%d")
        end_str = end_dt.strftime("%Y-%m-%d")
        events_sig = tuple(sorted((e.event_id, e.status, str(e.amount)) for e in events))
        cache_key = (user_id, start_str, end_str, events_sig)

        if cache_key in self._recurrence_cache:
            return self._recurrence_cache[cache_key]
        # Filter settled historical events (and scheduled salary events) for pattern building
        past_events = [
            e for e in events
            if (e.status == "settled" or (e.status == "scheduled" and e.category == "salary"))
            and e.event_date
            and _parse_date(e.event_date) is not None
            and _parse_date(e.event_date) <= start_dt + timedelta(days=35)
            and e.amount is not None
            and e.amount > 0
            and e.direction in ("debit", "credit")
            and not _is_one_time_income_event(e)
        ]

        # Existing explicit future events to prevent duplicate projections
        existing_future = [
            e for e in events
            if e.event_date and _parse_date(e.event_date) is not None and _parse_date(e.event_date) > start_dt
        ]
        future_category_dates: Dict[str, Set[str]] = {}
        for fe in existing_future:
            cat = fe.category or "other"
            if cat not in future_category_dates:
                future_category_dates[cat] = set()
            future_category_dates[cat].add(fe.event_date[:10])

        fixed_monthly_categories = {
            "rent", "housing", "utilities", "debt_repayment", "music_subscription",
            "cloud_storage", "streaming", "gym", "delivery_membership", "insurance",
            "education", "salary"
        }
        ESSENTIAL_FIXED_CATEGORIES = {
            "rent", "housing", "utilities", "debt_repayment", "groceries",
            "transport", "insurance", "education", "subscription",
            "cloud_storage", "gym", "streaming", "music_subscription", "delivery_membership"
        }

        # Group past events by (category, direction, description)
        # Unify essential categories by category to avoid description variants splitting
        grouped: Dict[Tuple[str, str, str], List[FinancialEvent]] = {}
        UNIFIED_CATEGORY_GROUPING = fixed_monthly_categories | ESSENTIAL_FIXED_CATEGORIES
        for pe in past_events:
            desc_key = "" if pe.category in UNIFIED_CATEGORY_GROUPING else (pe.description or "")
            key = (pe.category or "other", pe.direction, desc_key)
            if key not in grouped:
                grouped[key] = []
            grouped[key].append(pe)

        projected: List[FinancialEvent] = []

        TERMINAL_SALARY_KEYWORDS = {
            "final", "last payroll", "terminated", "termination", "severance",
            "offboarded", "departure", "resignation", "contract ended", "employment ended"
        }

        for (cat, dirn, desc), ev_list in grouped.items():
            ev_list.sort(key=lambda x: _parse_date(x.event_date) or start_dt)
            dates = [d for d in (_parse_date(x.event_date) for x in ev_list) if d is not None]
            amounts = [x.amount for x in ev_list if x.amount is not None]

            if not dates or not amounts:
                continue

            last_ev = ev_list[-1]
            last_dt = dates[-1]
            last_amt = amounts[-1]
            avg_amt = sum(amounts) / len(amounts)

            # Check if user has any terminal salary event anywhere in history
            if cat == "salary":
                # Platform payouts and app earnings are variable income, not a
                # reliable salary stream unless the evidence explicitly describes
                # payroll/employer salary or another stable wage source.
                salary_descriptions = [
                    (e.description or "").lower() for e in ev_list
                ]
                if not any(
                    any(keyword in description for keyword in _STABLE_SALARY_KEYWORDS)
                    for description in salary_descriptions
                ):
                    continue
                user_salary_events = [e for e in events if e.category == "salary" and e.direction == "credit"]
                is_salary_terminated = False
                for se in user_salary_events:
                    desc_lower = (se.description or "").lower()
                    if any(kw in desc_lower for kw in TERMINAL_SALARY_KEYWORDS):
                        is_salary_terminated = True
                        break
                if is_salary_terminated:
                    continue

                desc_lower = (last_ev.description or "").lower()
                if any(kw in desc_lower for kw in TERMINAL_SALARY_KEYWORDS):
                    continue

            # Check user-level evidence facts for contract termination or date shifts
            user_facts = []
            if self.evidence_manager and hasattr(self.evidence_manager, "get_user_facts"):
                user_facts = self.evidence_manager.get_user_facts(last_ev.user_id)

            if cat == "salary" and user_facts:
                if any(f.fact_kind == "contract_ended" or (f.status_override == "cancelled" and not f.related_event_id) for f in user_facts):
                    continue
                # Apply salary amount update if extracted
                sal_updates = [f for f in user_facts if f.fact_kind == "salary_update" and f.extracted_amount is not None]
                if sal_updates:
                    last_amt = sal_updates[0].extracted_amount
                    avg_amt = last_amt

            # Filter credit (income) events strictly to prevent over-projecting one-time bonuses
            if dirn == "credit":
                desc_lower = (last_ev.description or "").lower()
                if _is_one_time_income_event(last_ev):
                    continue

                # Require at least 1 occurrence for salary, 2 for general credit
                min_req_count = 1 if cat == "salary" else 2
                if len(ev_list) < min_req_count:
                    continue

            # Only project essential living expenses and contractual fixed commitments
            ESSENTIAL_FIXED_CATEGORIES = {
                "rent", "housing", "utilities", "debt_repayment", "groceries",
                "transport", "insurance", "education", "subscription",
                "cloud_storage", "gym", "streaming", "music_subscription", "delivery_membership"
            }
            if dirn == "debit" and cat not in ESSENTIAL_FIXED_CATEGORIES:
                continue
            intervals = [(dates[i] - dates[i-1]).days for i in range(1, len(dates))] if len(dates) >= 2 else []
            avg_interval = sum(intervals) / len(intervals) if intervals else None

            # General Multi-cadence Recurrence Generator:
            # Supports 5-day (4-6), 7-day (6-8), 10-day (9-11), 14-day (12-16), 18-24 day, and 25-35 day (monthly)
            step_days = None
            if avg_interval:
                if 4 <= avg_interval <= 6.5:
                    step_days = 5
                elif 6.5 < avg_interval <= 8.5:
                    step_days = 7
                elif 8.5 < avg_interval <= 11.5:
                    step_days = 10
                elif 11.5 < avg_interval <= 16.5:
                    step_days = 14
                elif 16.5 < avg_interval <= 24.5 and cat != "salary":
                    step_days = int(round(avg_interval))

            # Execute fixed-interval step projection (for 5, 7, 10, 14, 18-24 day intervals)
            if step_days and (len(ev_list) >= 3 or cat in fixed_monthly_categories):
                next_dt = last_dt + timedelta(days=step_days)
                while next_dt <= end_dt:
                    if next_dt > start_dt:
                        date_str = next_dt.strftime("%Y-%m-%d")
                        if not (cat in future_category_dates and date_str in future_category_dates[cat]):
                            proj_ev = FinancialEvent(
                                event_id=f"proj_{cat}_{dirn}_{date_str}",
                                user_id=last_ev.user_id,
                                event_type=last_ev.event_type,
                                description=f"Projected {step_days}-day {cat}",
                                category=cat,
                                direction=dirn,
                                amount=round(avg_amt, 2),
                                currency=last_ev.currency,
                                event_date=date_str,
                                settlement_date=date_str,
                                status="settled",
                                flexibility=last_ev.flexibility,
                                parent_event_id=last_ev.event_id,
                            )
                            projected.append(proj_ev)
                    next_dt += timedelta(days=step_days)

            # Monthly fixed projection (interval 25 to 35 days, or salary/fixed categories with >= 1 occurrence)
            elif (avg_interval and 25 <= avg_interval <= 35) or (cat == "salary" and len(ev_list) >= 1) or (len(ev_list) >= 2 and cat in fixed_monthly_categories):
                # Check for date shift in user facts
                base_dt = last_dt
                if cat == "salary" and user_facts:
                    date_shifts = [f for f in user_facts if f.fact_kind == "date_shift" and f.extracted_date]
                    if date_shifts:
                        shifted_dt = _parse_date(date_shifts[0].extracted_date)
                        if shifted_dt and shifted_dt > start_dt:
                            # Preserve the confirmed calendar day when deriving the
                            # preceding monthly anchor.  A fixed 30-day subtraction
                            # drifts for 31-day months (for example, a confirmed
                            # 23rd becomes a 24th), which then shifts every
                            # projected payday and payment decision.
                            base_dt = _add_months(shifted_dt, -1)

                curr_m = 1
                while True:
                    next_dt = _add_months(base_dt, curr_m)
                    if next_dt > end_dt:
                        break
                    if next_dt > start_dt:
                        date_str = next_dt.strftime("%Y-%m-%d")
                        # Skip if explicit future event already exists around date
                        if not (cat in future_category_dates and date_str in future_category_dates[cat]):
                            proj_ev = FinancialEvent(
                                event_id=f"proj_{cat}_{dirn}_{date_str}",
                                user_id=last_ev.user_id,
                                event_type=last_ev.event_type,
                                description=f"Projected {cat}",
                                category=cat,
                                direction=dirn,
                                amount=last_amt if cat in fixed_monthly_categories else round(avg_amt, 2),
                                currency=last_ev.currency,
                                event_date=date_str,
                                settlement_date=date_str,
                                status="scheduled",
                                flexibility=last_ev.flexibility,
                                minimum_allowed_amount=last_ev.minimum_allowed_amount,
                                parent_event_id=last_ev.event_id,
                            )
                            projected.append(proj_ev)
                    curr_m += 1

        self._recurrence_cache[cache_key] = projected
        return projected

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

        # Generate projected recurring events for the forecast window
        projected_events = self._project_recurring_events(events, start_dt, end_dt)
        all_events = events + projected_events

        stopped_events, reduced_events = self.parse_spending_changes(spending_changes)

        # Proposed payments map: date_str -> list of amounts
        proposed_by_date: Dict[str, float] = {}
        if proposed_payments:
            for p_date, p_amt in proposed_payments:
                proposed_by_date[p_date] = (
                    proposed_by_date.get(p_date, 0.0) + p_amt
                )

        daily_inflows: Dict[str, List[Tuple[str, float]]] = {}
        daily_required_outflows: Dict[str, List[Tuple[str, float]]] = {}
        daily_flexible_outflows: Dict[str, List[Tuple[str, float]]] = {}

        for ev in all_events:
            # 1. Filter out non-cash, cancelled, failed, unrealized investment events
            if (
                ev.status in ("cancelled", "failed", "unrealized")
                or ev.direction == "non_cash"
            ):
                continue

            # 2. Do not count future non-settled/one-time credit events (bonuses, arrears, refunds)
            if ev.direction == "credit" and ev.event_date and ev.event_date > start_date_str:
                desc_lower = (ev.description or "").lower()
                ONE_TIME_CREDIT = {"bonus", "arrears", "commission", "refund", "lottery", "investment_gain", "promotion"}
                if any(kw in desc_lower for kw in ONE_TIME_CREDIT):
                    continue

            # Amount safety check
            if ev.amount is None or ev.amount <= 0:
                continue

            # Event date / settlement date
            effective_date_str = ev.settlement_date or ev.event_date
            if not effective_date_str:
                continue

            ev_dt = _parse_date(effective_date_str)
            if not ev_dt:
                continue

            # Skip events occurring before start_date (already reflected in initial available balance)
            # EXCEPTION: Pending debits before start_date have NOT settled, so reserve them on start_date
            if ev_dt < start_dt:
                if ev.direction == "debit" and ev.status == "pending":
                    ev_dt = start_dt
                else:
                    continue

            # Convert event amount to profile home currency if different
            amt_home = ev.amount
            if ev.currency and ev.currency.upper() != profile.home_currency.upper():
                amt_home = self.converter.convert(
                    ev.amount, ev.currency, profile.home_currency, effective_date_str
                )

            # Process Inflows (Credits)
            if ev.direction == "credit":
                # Rule: DO NOT count pending non-salary credits (bonuses, refunds, lottery, investment gains)
                if ev.status == "pending" and ev.category != "salary":
                    continue
                # Include confirmed/settled/scheduled credits
                if ev_dt <= end_dt:
                    d_str = ev_dt.strftime("%Y-%m-%d")
                    if d_str not in daily_inflows:
                        daily_inflows[d_str] = []
                    daily_inflows[d_str].append((ev.event_id, amt_home))

            # Process Outflows (Debits)
            elif ev.direction == "debit":
                # Stopped by spending change?
                if ev.event_id in stopped_events or (ev.parent_event_id and ev.parent_event_id in stopped_events):
                    continue

                # Reduced by spending change?
                if ev.event_id in reduced_events:
                    amt_home = min(amt_home, reduced_events[ev.event_id])
                elif ev.parent_event_id and ev.parent_event_id in reduced_events:
                    amt_home = min(amt_home, reduced_events[ev.parent_event_id])

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

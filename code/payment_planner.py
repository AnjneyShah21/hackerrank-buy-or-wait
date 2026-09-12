"""
Payment planner generating and evaluating candidate payment schedules:
- full_payment
- partial_payment
- installments
- wait
- spending-change exploration
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Tuple

from code.forecast import CashFlowForecaster
from code.models import (
    CandidatePlan,
    FinancialEvent,
    FinancialRequest,
    RequestPaymentOption,
    UserProfile,
)


def _parse_date(date_str: str) -> datetime.date:
    try:
        return datetime.strptime(date_str[:10], "%Y-%m-%d").date()
    except Exception:
        return datetime(2026, 1, 1).date()


def _format_amount(amt: float) -> str:
    """Formats amount string for output.csv plan strings (integer if whole, else 2 decimals)."""
    if amt == int(amt):
        return str(int(amt))
    return f"{amt:.2f}"


class PaymentPlanner:
    """Generates all eligible and safe candidate payment plans."""

    def __init__(self, forecaster: CashFlowForecaster):
        self.forecaster = forecaster

    def generate_installment_schedule(
        self, option: RequestPaymentOption
    ) -> Tuple[List[Tuple[str, float]], str, str]:
        """
        Generates payment schedule, payment_plan_str, and completion_date for an installment option.
        """
        payments: List[Tuple[str, float]] = []
        plan_parts: List[str] = []

        start_dt = _parse_date(option.first_payment_date)
        freq_days = option.payment_frequency_days or 30

        for i in range(option.number_of_payments):
            p_dt = start_dt + timedelta(days=i * freq_days)
            p_date_str = p_dt.strftime("%Y-%m-%d")
            amt = option.payment_amount

            payments.append((p_date_str, amt))
            plan_parts.append(f"{p_date_str}:{_format_amount(amt)}")

        completion_date = payments[-1][0] if payments else option.first_payment_date
        plan_str = "|".join(plan_parts) if plan_parts else "none"

        return payments, plan_str, completion_date

    def find_flexible_spending_options(
        self, profile: UserProfile, events: List[FinancialEvent]
    ) -> List[str]:
        """
        Identifies eligible spending change actions (stop:id or reduce_to:id:amt).
        Only non-protected, flexible events in categories user permits may be changed.
        """
        actions: List[str] = []
        seen_events: Set[str] = set()

        for ev in events:
            if ev.event_id in seen_events:
                continue
            if ev.direction != "debit" or ev.amount is None or ev.amount <= 0:
                continue
            if ev.status in ("cancelled", "failed", "unrealized"):
                continue

            # Category check: cannot change protected categories
            if ev.category in profile.expense_categories_to_protect:
                continue

            # Check if stoppable
            if (
                ev.category in profile.expense_categories_user_is_willing_to_stop
                and ev.flexibility in ("stoppable", "reducible_or_stoppable")
            ):
                actions.append(f"stop:{ev.event_id}")
                seen_events.add(ev.event_id)

            # Check if reducible
            elif (
                ev.category in profile.expense_categories_user_is_willing_to_reduce
                and ev.flexibility in ("reducible", "reducible_or_stoppable")
            ):
                min_amt = ev.minimum_allowed_amount or 0.0
                actions.append(f"reduce_to:{ev.event_id}:{_format_amount(min_amt)}")
                seen_events.add(ev.event_id)

        return actions

    def generate_candidate_plans(
        self,
        profile: UserProfile,
        events: List[FinancialEvent],
        request: FinancialRequest,
        options: List[RequestPaymentOption],
        amount_safe_to_pay: float,
        earliest_date_for_full_payment: str,
    ) -> List[CandidatePlan]:
        """
        Generates candidate plans for all considered payment methods.
        Simulates each candidate and evaluates safety and deadlines.
        """
        candidate_plans: List[CandidatePlan] = []
        considered = profile.payment_methods_user_will_consider

        # ── 1. Full Payment (No spending changes) ────────────────────────────
        if "full_payment" in considered:
            payments = [(request.request_date, request.requested_amount)]
            plan_str = f"{request.request_date}:{_format_amount(request.requested_amount)}"

            is_safe, min_bal, _ = self.forecaster.simulate_90_days(
                profile=profile,
                events=events,
                start_date_str=request.request_date,
                proposed_payments=payments,
            )

            candidate_plans.append(
                CandidatePlan(
                    method="full_payment",
                    affordability_status="affordable_now" if is_safe else "not_affordable",
                    payments=payments,
                    payment_plan_str=plan_str if is_safe else "none",
                    earliest_date_for_full_payment=earliest_date_for_full_payment,
                    spending_changes_str="none",
                    total_payable=request.requested_amount,
                    completion_date=request.request_date,
                    is_safe=is_safe,
                    min_projected_balance=min_bal,
                    rejection_reason=None if is_safe else "Minimum balance violated",
                )
            )

        # ── 2. Partial Payment (No spending changes) ─────────────────────────
        if (
            "partial_payment" in considered
            and request.allows_partial_payment
            and 0 < amount_safe_to_pay < request.requested_amount
            and earliest_date_for_full_payment
            and earliest_date_for_full_payment <= request.desired_completion_date
        ):
            rem_amt = round(request.requested_amount - amount_safe_to_pay, 2)
            payments = [
                (request.request_date, amount_safe_to_pay),
                (earliest_date_for_full_payment, rem_amt),
            ]
            plan_str = (
                f"{request.request_date}:{_format_amount(amount_safe_to_pay)}|"
                f"{earliest_date_for_full_payment}:{_format_amount(rem_amt)}"
            )

            is_safe, min_bal, _ = self.forecaster.simulate_90_days(
                profile=profile,
                events=events,
                start_date_str=request.request_date,
                proposed_payments=payments,
            )

            if is_safe:
                candidate_plans.append(
                    CandidatePlan(
                        method="partial_payment",
                        affordability_status="affordable_with_plan",
                        payments=payments,
                        payment_plan_str=plan_str,
                        earliest_date_for_full_payment=earliest_date_for_full_payment,
                        spending_changes_str="none",
                        total_payable=request.requested_amount,
                        completion_date=earliest_date_for_full_payment,
                        is_safe=True,
                        min_projected_balance=min_bal,
                    )
                )

        # ── 3. Installments (No spending changes) ───────────────────────────
        if "installments" in considered and options:
            for opt in options:
                # Respect max_installment_months constraint if set
                if (
                    profile.max_installment_months is not None
                    and opt.number_of_payments > profile.max_installment_months
                ):
                    continue

                payments, plan_str, completion_date = self.generate_installment_schedule(opt)

                is_safe, min_bal, _ = self.forecaster.simulate_90_days(
                    profile=profile,
                    events=events,
                    start_date_str=request.request_date,
                    proposed_payments=payments,
                )

                if is_safe:
                    candidate_plans.append(
                        CandidatePlan(
                            method="installments",
                            affordability_status="affordable_with_plan",
                            payments=payments,
                            payment_plan_str=plan_str,
                            earliest_date_for_full_payment=earliest_date_for_full_payment,
                            spending_changes_str="none",
                            total_payable=opt.total_payable_amount,
                            completion_date=completion_date,
                            payment_option_id=opt.payment_option_id,
                            is_safe=True,
                            min_projected_balance=min_bal,
                        )
                    )

        # ── 4. Spending Changes Exploration ────────────────────────────────
        # If no safe plan was found or deadline wasn't met, try spending changes
        has_safe_ontime_plan = any(
            p.is_safe and p.completion_date <= request.desired_completion_date
            for p in candidate_plans
        )

        if not has_safe_ontime_plan:
            spending_actions = self.find_flexible_spending_options(profile, events)
            if spending_actions:
                import itertools
                action_combos: List[List[str]] = []
                # Size 1
                for a in spending_actions[:5]:
                    action_combos.append([a])
                # Size 2
                for combo in itertools.combinations(spending_actions[:5], 2):
                    ev_ids = [act.split(":")[1] for act in combo if len(act.split(":")) >= 2]
                    if len(set(ev_ids)) == len(ev_ids):
                        action_combos.append(list(combo))
                # Size 3
                for combo in itertools.combinations(spending_actions[:5], 3):
                    ev_ids = [act.split(":")[1] for act in combo if len(act.split(":")) >= 2]
                    if len(set(ev_ids)) == len(ev_ids):
                        action_combos.append(list(combo))

                for spending_list in action_combos:
                    spending_str = "|".join(spending_list)

                    # Try full payment with spending change
                    if "full_payment" in considered:
                        payments = [(request.request_date, request.requested_amount)]
                        plan_str = f"{request.request_date}:{_format_amount(request.requested_amount)}"

                        is_safe, min_bal, _ = self.forecaster.simulate_90_days(
                            profile=profile,
                            events=events,
                            start_date_str=request.request_date,
                            spending_changes=spending_list,
                            proposed_payments=payments,
                        )

                        if is_safe:
                            candidate_plans.append(
                                CandidatePlan(
                                    method="full_payment",
                                    affordability_status="affordable_with_plan",
                                    payments=payments,
                                    payment_plan_str=plan_str,
                                    earliest_date_for_full_payment=earliest_date_for_full_payment,
                                    spending_changes_str=spending_str,
                                    total_payable=request.requested_amount,
                                    completion_date=request.request_date,
                                    is_safe=True,
                                    min_projected_balance=min_bal,
                                )
                            )

                    # Try installment options with spending change
                    if "installments" in considered and options:
                        for opt in options:
                            if (
                                profile.max_installment_months is not None
                                and opt.number_of_payments > profile.max_installment_months
                            ):
                                continue

                            payments, plan_str, completion_date = self.generate_installment_schedule(opt)

                            is_safe, min_bal, _ = self.forecaster.simulate_90_days(
                                profile=profile,
                                events=events,
                                start_date_str=request.request_date,
                                spending_changes=spending_list,
                                proposed_payments=payments,
                            )

                            if is_safe:
                                candidate_plans.append(
                                    CandidatePlan(
                                        method="installments",
                                        affordability_status="affordable_with_plan",
                                        payments=payments,
                                        payment_plan_str=plan_str,
                                        earliest_date_for_full_payment=earliest_date_for_full_payment,
                                        spending_changes_str=spending_str,
                                        total_payable=opt.total_payable_amount,
                                        completion_date=completion_date,
                                        payment_option_id=opt.payment_option_id,
                                        is_safe=True,
                                        min_projected_balance=min_bal,
                                    )
                                )

        # ── 5. Wait ──────────────────────────────────────────────────────────
        if (
            "full_payment" in considered
            and earliest_date_for_full_payment
            and earliest_date_for_full_payment > request.request_date
        ):
            payments = [(earliest_date_for_full_payment, request.requested_amount)]
            plan_str = f"{earliest_date_for_full_payment}:{_format_amount(request.requested_amount)}"

            is_safe, min_bal, _ = self.forecaster.simulate_90_days(
                profile=profile,
                events=events,
                start_date_str=request.request_date,
                proposed_payments=payments,
            )

            candidate_plans.append(
                CandidatePlan(
                    method="wait",
                    affordability_status="affordable_later",
                    payments=payments,
                    payment_plan_str=plan_str,
                    earliest_date_for_full_payment=earliest_date_for_full_payment,
                    spending_changes_str="none",
                    total_payable=request.requested_amount,
                    completion_date=earliest_date_for_full_payment,
                    is_safe=is_safe,
                    min_projected_balance=min_bal,
                )
            )

        return candidate_plans

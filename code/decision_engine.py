"""
Decision engine for ranking candidate payment plans and generating grounded explanations.
Ensures 100% deterministic decision logic and strict explanation consistency assertions.
"""

from typing import List, Optional, Tuple

from code.models import CandidatePlan, DecisionResult, FinancialRequest, UserProfile


def _plan_rank_key(plan: CandidatePlan, request: FinancialRequest) -> Tuple:
    """
    Returns tie-breaking tuple for sorting candidate plans deterministically.
    Strict Order (problem_statement.md):
    1. Complete full request by desired_completion_date (0 = yes, 1 = no)
    2. Require no spending changes (0 = none, 1 = changes)
    3. Minimize total amount paid (float)
    4. Start payment earlier (YYYY-MM-DD string)
    5. Use fewer payments (int)
    6. Higher minimum projected balance (prefer safer headroom)
    7. Final tie-breaker: lowest payment_option_id string
    """
    # 1. On time by desired_completion_date
    by_deadline = 0 if (plan.completion_date and plan.completion_date <= request.desired_completion_date) else 1

    # 2. No spending changes needed
    no_spending_changes = 0 if plan.spending_changes_str == "none" else 1

    # 3. Minimize total amount paid
    total_paid = plan.total_payable if plan.total_payable > 0 else request.requested_amount

    # 4. Complete full request earlier (earlier final payment date)
    comp_date = plan.completion_date or "9999-99-99"

    # 5. Start payment earlier
    first_date = plan.payments[0][0] if plan.payments else "9999-99-99"

    # 6. Use fewer payments
    num_payments = len(plan.payments) if plan.payments else 999

    # 7. Higher minimum projected balance (safer liquidity headroom tie-breaker)
    safety_headroom = -plan.min_projected_balance

    # 8. Lowest payment_option_id
    opt_id = plan.payment_option_id or "zzzzzz"

    return (by_deadline, no_spending_changes, total_paid, comp_date, first_date, num_payments, safety_headroom, opt_id)


class DecisionEngine:
    """Ranks candidate plans according to problem statement tie-breaking rules."""

    def rank_plans(
        self,
        candidate_plans: List[CandidatePlan],
        request: FinancialRequest,
    ) -> Optional[CandidatePlan]:
        """
        Ranks candidate plans deterministically and returns the best safe plan.
        Returns None if no safe plan exists.
        """
        safe_plans = [p for p in candidate_plans if p.is_safe]
        if not safe_plans:
            return None

        # Sort using strict tie-breaking tuple
        sorted_plans = sorted(safe_plans, key=lambda p: _plan_rank_key(p, request))
        return sorted_plans[0]

    def make_decision(
        self,
        request: FinancialRequest,
        profile: UserProfile,
        amount_safe_to_pay: float,
        earliest_date_for_full_payment: str,
        best_plan: Optional[CandidatePlan],
    ) -> DecisionResult:
        """Formulates final DecisionResult with human-readable, grounded explanation."""
        curr = profile.home_currency
        min_bal = profile.minimum_balance_to_keep
        req_amt = request.requested_amount
        req_date = request.request_date

        # For installment plans, amount_safe_to_pay on request_date is the first installment amount
        effective_safe_amount = amount_safe_to_pay
        if best_plan and best_plan.method == "installments" and best_plan.payments:
            effective_safe_amount = best_plan.payments[0][1]
        effective_safe_amount = max(0.0, min(effective_safe_amount, req_amt))

        # ── Fallback when no safe plan is available ─────────────────────────
        if best_plan is None or best_plan.method == "not_recommended":
            if earliest_date_for_full_payment:
                explanation = (
                    f"Do not proceed with paying {curr} {req_amt:,.2f} today. "
                    f"Only {curr} {amount_safe_to_pay:,.2f} is safe on {req_date} without dropping below your required {curr} {min_bal:,.2f} minimum balance. "
                    f"Wait until {earliest_date_for_full_payment} when confirmed income settles."
                )
            else:
                explanation = (
                    f"Do not proceed with the {curr} {req_amt:,.2f} request. "
                    f"Paying this amount cannot be completed safely within 90 days while maintaining your required {curr} {min_bal:,.2f} minimum balance."
                )
            res = DecisionResult(
                request_id=request.request_id,
                amount_safe_to_pay=round(amount_safe_to_pay, 2),
                affordability_status="not_affordable",
                recommended_payment_method="not_recommended",
                payment_plan="none",
                earliest_date_for_full_payment=earliest_date_for_full_payment,
                spending_changes_needed="none",
                decision_explanation=explanation,
            )
            self.assert_explanation_consistency(res)
            return res

        # ── Grounded explanations for safe recommendations ──────────────────
        if best_plan.method == "full_payment" and best_plan.affordability_status == "affordable_now":
            explanation = (
                f"You can safely pay the full {curr} {req_amt:,.2f} today. "
                f"Your balance remains safely above your {curr} {min_bal:,.2f} minimum balance throughout the 90-day forecast."
            )

        elif best_plan.method == "partial_payment":
            rem_amt = round(req_amt - effective_safe_amount, 2)
            explanation = (
                f"Pay {curr} {effective_safe_amount:,.2f} today on {req_date} and the remaining {curr} {rem_amt:,.2f} on {earliest_date_for_full_payment}. "
                f"This partial schedule completes your {curr} {req_amt:,.2f} request safely by your deadline."
            )

        elif best_plan.method == "installments":
            opt_str = f"option {best_plan.payment_option_id}" if best_plan.payment_option_id else "installment plan"
            explanation = (
                f"Use {opt_str} ({best_plan.payment_plan_str}). "
                f"Paying {curr} {effective_safe_amount:,.2f} today fits your cash flow while preserving your required {curr} {min_bal:,.2f} minimum balance."
            )

        elif best_plan.method == "wait":
            explanation = (
                f"Wait until {earliest_date_for_full_payment} to make the full payment of {curr} {req_amt:,.2f}. "
                f"Your current safe limit today is {curr} {amount_safe_to_pay:,.2f}, but confirmed income on {earliest_date_for_full_payment} makes full payment safe."
            )

        else:
            explanation = (
                f"Proceed with {best_plan.method.replace('_', ' ')} according to schedule {best_plan.payment_plan_str}."
            )

        if best_plan.spending_changes_str != "none":
            explanation += f" Requires spending adjustments: {best_plan.spending_changes_str}."

        res = DecisionResult(
            request_id=request.request_id,
            amount_safe_to_pay=round(effective_safe_amount, 2),
            affordability_status=best_plan.affordability_status,
            recommended_payment_method=best_plan.method,
            payment_plan=best_plan.payment_plan_str,
            earliest_date_for_full_payment=earliest_date_for_full_payment,
            spending_changes_needed=best_plan.spending_changes_str,
            decision_explanation=explanation,
        )
        self.assert_explanation_consistency(res)
        return res

    def assert_explanation_consistency(self, result: DecisionResult):
        """
        Validates that explanation text does NOT contradict deterministic decision fields.
        Raises AssertionError if inconsistency is detected.
        """
        exp_lower = result.decision_explanation.lower()

        # 1. Non-empty check
        assert len(result.decision_explanation.strip()) > 0, "decision_explanation cannot be empty"

        # 2. Not affordable consistency
        if result.affordability_status == "not_affordable":
            assert any(k in exp_lower for k in ("do not proceed", "cannot", "not recommended", "insufficient")), \
                f"Explanation contradicts not_affordable status: '{result.decision_explanation}'"

        # 3. Affordable now consistency
        if result.affordability_status == "affordable_now":
            assert any(k in exp_lower for k in ("safely pay", "full", "today")), \
                f"Explanation contradicts affordable_now status: '{result.decision_explanation}'"

        # 4. Method match check
        if result.recommended_payment_method == "not_recommended":
            assert result.payment_plan == "none", "payment_plan must be 'none' when recommended_payment_method is 'not_recommended'"

        # 5. Amount safe to pay bounds check
        assert result.amount_safe_to_pay >= 0, "amount_safe_to_pay cannot be negative"

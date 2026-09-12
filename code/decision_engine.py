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
    6. Final tie-breaker: lowest payment_option_id string
    """
    # 1. On time by desired_completion_date
    by_deadline = 0 if (plan.completion_date and plan.completion_date <= request.desired_completion_date) else 1

    # 2. No spending changes needed
    no_spending_changes = 0 if plan.spending_changes_str == "none" else 1

    # 3. Minimize total amount paid
    total_paid = plan.total_payable if plan.total_payable > 0 else request.requested_amount

    # 4. Start payment earlier
    first_date = plan.payments[0][0] if plan.payments else "9999-99-99"

    # 5. Use fewer payments
    num_payments = len(plan.payments) if plan.payments else 999

    # 6. Lowest payment_option_id
    opt_id = plan.payment_option_id or "zzzzzz"

    return (by_deadline, no_spending_changes, total_paid, first_date, num_payments, opt_id)


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

        # Fallback when no safe plan is available
        if best_plan is None or best_plan.method == "not_recommended":
            explanation = (
                f"Do not proceed with the {profile.home_currency} {request.requested_amount:,.2f} request. "
                f"The full amount cannot be completed safely within 90 days while maintaining "
                f"the required {profile.home_currency} {profile.minimum_balance_to_keep:,.2f} minimum balance."
            )
            return DecisionResult(
                request_id=request.request_id,
                amount_safe_to_pay=amount_safe_to_pay,
                affordability_status="not_affordable",
                recommended_payment_method="not_recommended",
                payment_plan="none",
                earliest_date_for_full_payment=earliest_date_for_full_payment,
                spending_changes_needed="none",
                decision_explanation=explanation,
            )

        # Grounded explanation generation based on best_plan method
        curr = profile.home_currency
        min_bal = profile.minimum_balance_to_keep

        if best_plan.method == "full_payment" and best_plan.affordability_status == "affordable_now":
            explanation = (
                f"You can safely pay the full {curr} {request.requested_amount:,.2f} today. "
                f"Your balance remains safely above your {curr} {min_bal:,.2f} minimum balance throughout the forecast period."
            )
        elif best_plan.method == "partial_payment":
            explanation = (
                f"Pay {curr} {amount_safe_to_pay:,.2f} on {request.request_date} and the remaining balance on {earliest_date_for_full_payment}. "
                f"This partial schedule completes the request safely by your deadline."
            )
        elif best_plan.method == "installments":
            explanation = (
                f"Use installment plan {best_plan.payment_option_id or ''} ({best_plan.payment_plan_str}). "
                f"This schedule fits your cash flow while preserving your {curr} {min_bal:,.2f} minimum balance."
            )
        elif best_plan.method == "wait":
            explanation = (
                f"Wait until {earliest_date_for_full_payment} to make the full payment of {curr} {request.requested_amount:,.2f}. "
                f"Your balance will reach safe levels on that date."
            )
        elif best_plan.spending_changes_str != "none":
            explanation = (
                f"Proceed with {best_plan.method.replace('_', ' ')} after adjusting flexible expenses ({best_plan.spending_changes_str}). "
                f"This preserves your required {curr} {min_bal:,.2f} minimum balance."
            )
        else:
            explanation = f"Proceed with {best_plan.method.replace('_', ' ')} according to schedule {best_plan.payment_plan_str}."

        return DecisionResult(
            request_id=request.request_id,
            amount_safe_to_pay=amount_safe_to_pay,
            affordability_status=best_plan.affordability_status,
            recommended_payment_method=best_plan.method,
            payment_plan=best_plan.payment_plan_str,
            earliest_date_for_full_payment=earliest_date_for_full_payment,
            spending_changes_needed=best_plan.spending_changes_str,
            decision_explanation=explanation,
        )

    def assert_explanation_consistency(self, result: DecisionResult):
        """
        Validates that explanation text does NOT contradict deterministic decision fields.
        Raises AssertionError if inconsistency is detected.
        """
        exp_lower = result.decision_explanation.lower()

        # 1. Not affordable consistency
        if result.affordability_status == "not_affordable":
            assert "do not proceed" in exp_lower or "cannot" in exp_lower or "not recommended" in exp_lower, \
                f"Explanation contradicts not_affordable status: '{result.decision_explanation}'"

        # 2. Affordable now consistency
        if result.affordability_status == "affordable_now":
            assert "safely pay" in exp_lower or "full" in exp_lower, \
                f"Explanation contradicts affordable_now status: '{result.decision_explanation}'"

        # 3. Method match check
        if result.recommended_payment_method == "not_recommended":
            assert result.payment_plan == "none", "payment_plan must be 'none' when recommended_payment_method is 'not_recommended'"

        # 4. Amount safe to pay bounds check
        assert result.amount_safe_to_pay >= 0, "amount_safe_to_pay cannot be negative"

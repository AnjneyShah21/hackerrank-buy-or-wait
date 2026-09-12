"""
Decision engine for ranking candidate payment plans and generating grounded explanations.
"""

from typing import List, Optional
from code.models import (
    CandidatePlan,
    DecisionResult,
    FinancialRequest,
    UserProfile,
)


class DecisionEngine:
    """Ranks candidate plans according to problem statement tie-breaking rules."""

    def rank_plans(
        self,
        candidate_plans: List[CandidatePlan],
        request: FinancialRequest,
    ) -> Optional[CandidatePlan]:
        """
        Ranks plans in strict order:
        1. Complete full request by desired_completion_date
        2. Require no spending changes (spending_changes_needed == 'none')
        3. Minimize total amount paid
        4. Start payment earlier
        5. Use fewer payments
        6. Final tie-breaker: lowest payment_option_id
        """
        if not candidate_plans:
            return None

        # Filter safe plans
        safe_plans = [p for p in candidate_plans if p.is_safe]
        if not safe_plans:
            return None

        # Skeleton ranking definition
        return safe_plans[0]

    def make_decision(
        self,
        request: FinancialRequest,
        profile: UserProfile,
        amount_safe_to_pay: float,
        earliest_date_for_full_payment: str,
        best_plan: Optional[CandidatePlan],
    ) -> DecisionResult:
        """Formulates final DecisionResult with human-readable explanation."""
        if best_plan is None:
            return DecisionResult(
                request_id=request.request_id,
                amount_safe_to_pay=amount_safe_to_pay,
                affordability_status="not_affordable",
                recommended_payment_method="not_recommended",
                payment_plan="none",
                earliest_date_for_full_payment=earliest_date_for_full_payment,
                spending_changes_needed="none",
                decision_explanation=f"Do not proceed with the {profile.home_currency} {request.requested_amount:,.2f} request. The full amount cannot be completed safely within 90 days.",
            )

        return DecisionResult(
            request_id=request.request_id,
            amount_safe_to_pay=amount_safe_to_pay,
            affordability_status=best_plan.affordability_status,
            recommended_payment_method=best_plan.method,
            payment_plan=best_plan.payment_plan_str,
            earliest_date_for_full_payment=earliest_date_for_full_payment,
            spending_changes_needed=best_plan.spending_changes_str,
            decision_explanation="Recommendation generated.",
        )

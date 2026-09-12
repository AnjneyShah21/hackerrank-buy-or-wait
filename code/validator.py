"""
Validation module enforcing all challenge rules and invariant bounds.
"""

from typing import List, Dict, Tuple
from code.models import OutputRecord, FinancialRequest
from code.config import (
    VALID_AFFORDABILITY_STATUSES,
    VALID_PAYMENT_METHODS,
    OUTPUT_COLUMNS,
)


class OutputValidator:
    """Validates output rows and generated dataset against contract invariants."""

    @staticmethod
    def validate_row(record: OutputRecord, request: FinancialRequest) -> Tuple[bool, List[str]]:
        """Validates a single prediction row."""
        errors = []

        # 1. Bounds check
        try:
            safe_amt = float(record.amount_safe_to_pay)
            if safe_amt < 0 or safe_amt > request.requested_amount + 1e-4:
                errors.append(f"amount_safe_to_pay {safe_amt} out of bounds [0, {request.requested_amount}]")
        except ValueError:
            errors.append(f"Invalid amount_safe_to_pay: {record.amount_safe_to_pay}")

        # 2. Status enum check
        if record.affordability_status not in VALID_AFFORDABILITY_STATUSES:
            errors.append(f"Invalid affordability_status: {record.affordability_status}")

        # 3. Method enum check
        if record.recommended_payment_method not in VALID_PAYMENT_METHODS:
            errors.append(f"Invalid recommended_payment_method: {record.recommended_payment_method}")

        # 4. Affordable now earliest date check
        if record.affordability_status == "affordable_now":
            if record.earliest_date_for_full_payment != request.request_date:
                errors.append(f"For affordable_now, earliest_date must equal request_date ({request.request_date}), got {record.earliest_date_for_full_payment}")

        # 5. Non-empty explanation
        if not record.decision_explanation or not record.decision_explanation.strip():
            errors.append("decision_explanation is empty")

        return len(errors) == 0, errors

    @staticmethod
    def validate_all(records: List[OutputRecord], requests: List[FinancialRequest]) -> Tuple[bool, List[str]]:
        """Validates complete output dataset."""
        all_errors = []
        req_map = {r.request_id: r for r in requests}

        if len(records) != len(requests):
            all_errors.append(f"Row count mismatch: expected {len(requests)}, got {len(records)}")

        for rec in records:
            req = req_map.get(rec.request_id)
            if not req:
                all_errors.append(f"Unknown request_id: {rec.request_id}")
                continue
            is_valid, errs = OutputValidator.validate_row(rec, req)
            if not is_valid:
                all_errors.extend([f"[{rec.request_id}] {e}" for e in errs])

        return len(all_errors) == 0, all_errors

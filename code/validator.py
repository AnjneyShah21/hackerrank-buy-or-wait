"""
Strict output validator enforcing all challenge rules, schema bounds, and financial invariants.
"""

import math
import re
from datetime import datetime
from typing import Dict, List, Optional, Set, Tuple

from code.config import (
    OUTPUT_COLUMNS,
    VALID_AFFORDABILITY_STATUSES,
    VALID_PAYMENT_METHODS,
)
from code.models import FinancialRequest, OutputRecord


def _parse_date(date_str: str) -> Optional[datetime.date]:
    try:
        return datetime.strptime(date_str[:10], "%Y-%m-%d").date()
    except Exception:
        return None


class OutputValidator:
    """Validates output rows and generated dataset against contract invariants."""

    @staticmethod
    def validate_row(
        record: OutputRecord, request: FinancialRequest
    ) -> Tuple[bool, List[str]]:
        """Validates a single prediction row against strict contract invariants."""
        errors: List[str] = []

        # 1. Bounds check on amount_safe_to_pay
        try:
            safe_amt = float(record.amount_safe_to_pay)
            if math.isnan(safe_amt) or math.isinf(safe_amt):
                errors.append("amount_safe_to_pay is NaN or Inf")
            elif safe_amt < 0.0 or safe_amt > request.requested_amount + 1e-4:
                errors.append(
                    f"amount_safe_to_pay {safe_amt} out of bounds [0, {request.requested_amount}]"
                )
        except (ValueError, TypeError):
            errors.append(f"Invalid amount_safe_to_pay float format: '{record.amount_safe_to_pay}'")

        # 2. Status enum check
        if record.affordability_status not in VALID_AFFORDABILITY_STATUSES:
            errors.append(
                f"Invalid affordability_status: '{record.affordability_status}'. "
                f"Must be one of {VALID_AFFORDABILITY_STATUSES}"
            )

        # 3. Method enum check
        if record.recommended_payment_method not in VALID_PAYMENT_METHODS:
            errors.append(
                f"Invalid recommended_payment_method: '{record.recommended_payment_method}'. "
                f"Must be one of {VALID_PAYMENT_METHODS}"
            )

        # 4. earliest_date_for_full_payment invariants
        earliest_dt = None
        if record.earliest_date_for_full_payment:
            earliest_dt = _parse_date(record.earliest_date_for_full_payment)
            if not earliest_dt:
                errors.append(
                    f"Invalid earliest_date_for_full_payment date format: '{record.earliest_date_for_full_payment}'"
                )
            else:
                req_dt = _parse_date(request.request_date)
                if req_dt and earliest_dt < req_dt:
                    errors.append(
                        f"earliest_date_for_full_payment '{record.earliest_date_for_full_payment}' "
                        f"is before request_date '{request.request_date}'"
                    )

        if record.affordability_status == "affordable_now":
            if record.earliest_date_for_full_payment != request.request_date:
                errors.append(
                    f"For affordable_now, earliest_date_for_full_payment must equal request_date "
                    f"('{request.request_date}'), got '{record.earliest_date_for_full_payment}'"
                )

        # 5. payment_plan structural & rule validation
        plan_str = record.payment_plan.strip()
        method = record.recommended_payment_method

        if method == "not_recommended":
            if plan_str != "none":
                errors.append(
                    f"payment_plan must be 'none' when recommended_payment_method is 'not_recommended', got '{plan_str}'"
                )
        elif plan_str == "none":
            if method not in ("not_recommended", "wait"):
                errors.append(
                    f"payment_plan cannot be 'none' when recommended_payment_method is '{method}'"
                )
        else:
            # Parse plan entries YYYY-MM-DD:amount|YYYY-MM-DD:amount
            entries = plan_str.split("|")
            prev_dt = None
            total_plan_amt = 0.0

            for entry in entries:
                parts = entry.split(":")
                if len(parts) != 2:
                    errors.append(f"Malformed payment_plan entry: '{entry}' in '{plan_str}'")
                    continue
                d_str, a_str = parts[0].strip(), parts[1].strip()
                p_dt = _parse_date(d_str)
                if not p_dt:
                    errors.append(f"Invalid date '{d_str}' in payment_plan: '{plan_str}'")
                elif prev_dt and p_dt < prev_dt:
                    errors.append(f"Payment dates not in chronological order in payment_plan: '{plan_str}'")
                prev_dt = p_dt

                try:
                    p_amt = float(a_str)
                    if math.isnan(p_amt) or math.isinf(p_amt) or p_amt <= 0:
                        errors.append(f"Invalid payment amount '{a_str}' in payment_plan: '{plan_str}'")
                    total_plan_amt += p_amt
                except ValueError:
                    errors.append(f"Invalid numeric amount '{a_str}' in payment_plan: '{plan_str}'")

            # Partial payment specific rules
            if method == "partial_payment":
                if len(entries) != 2:
                    errors.append(
                        f"partial_payment plan must contain exactly 2 payments, got {len(entries)} in '{plan_str}'"
                    )
                if not request.allows_partial_payment:
                    errors.append("partial_payment recommended but request.allows_partial_payment is False")
                if record.affordability_status != "affordable_with_plan":
                    errors.append(
                        f"affordability_status for partial_payment must be 'affordable_with_plan', got '{record.affordability_status}'"
                    )

                # Check payment 1 = amount_safe_to_pay on request_date
                try:
                    p1_parts = entries[0].split(":")
                    p1_date, p1_amt = p1_parts[0].strip(), float(p1_parts[1].strip())
                    if p1_date != request.request_date:
                        errors.append(
                            f"First partial payment date must be request_date '{request.request_date}', got '{p1_date}'"
                        )
                    if abs(p1_amt - float(record.amount_safe_to_pay)) > 0.01:
                        errors.append(
                            f"First partial payment amount ({p1_amt}) must equal amount_safe_to_pay ({record.amount_safe_to_pay})"
                        )
                except (IndexError, ValueError):
                    errors.append("Invalid first partial payment entry in payment_plan")

                # Check payment 2 = remaining on earliest_date_for_full_payment
                try:
                    p2_parts = entries[1].split(":")
                    p2_date, p2_amt = p2_parts[0].strip(), float(p2_parts[1].strip())
                    if p2_date != record.earliest_date_for_full_payment:
                        errors.append(
                            f"Second partial payment date ({p2_date}) must equal earliest_date_for_full_payment ({record.earliest_date_for_full_payment})"
                        )
                    comp_dt = _parse_date(request.desired_completion_date)
                    if p2_dt := _parse_date(p2_date):
                        if comp_dt and p2_dt > comp_dt:
                            errors.append(
                                f"Second partial payment date ({p2_date}) is after desired_completion_date ({request.desired_completion_date})"
                            )
                except (IndexError, ValueError):
                    errors.append("Invalid second partial payment entry in payment_plan")

                # Total payments sum check
                if abs(total_plan_amt - request.requested_amount) > 0.05:
                    errors.append(
                        f"Partial payment total ({total_plan_amt}) does not sum to requested_amount ({request.requested_amount})"
                    )

            # Installment plan specific rules
            if method == "installments":
                if record.affordability_status != "affordable_with_plan":
                    errors.append(
                        f"affordability_status for installments must be 'affordable_with_plan', got '{record.affordability_status}'"
                    )

        # 6. spending_changes_needed validation
        sc_str = record.spending_changes_needed.strip()
        if sc_str != "none":
            actions = sc_str.split("|")
            if len(actions) > 3:
                errors.append(f"spending_changes_needed exceeds maximum of 3 actions: {len(actions)} in '{sc_str}'")

            seen_events: Set[str] = set()
            for action in actions:
                parts = action.split(":")
                if parts[0] == "stop" and len(parts) == 2:
                    eid = parts[1]
                    if eid in seen_events:
                        errors.append(f"Duplicate event_id '{eid}' in spending_changes_needed: '{sc_str}'")
                    seen_events.add(eid)
                elif parts[0] == "reduce_to" and len(parts) == 3:
                    eid = parts[1]
                    if eid in seen_events:
                        errors.append(f"Duplicate event_id '{eid}' in spending_changes_needed: '{sc_str}'")
                    seen_events.add(eid)
                    try:
                        new_amt = float(parts[2])
                        if new_amt < 0 or math.isnan(new_amt):
                            errors.append(f"Invalid reduced amount '{parts[2]}' in '{action}'")
                    except ValueError:
                        errors.append(f"Invalid numeric reduced amount '{parts[2]}' in '{action}'")
                else:
                    errors.append(f"Malformed spending_changes_needed action: '{action}' in '{sc_str}'")

        # 7. decision_explanation validation
        exp = record.decision_explanation
        if not exp or not exp.strip():
            errors.append("decision_explanation is empty or whitespace")
        else:
            exp_lower = exp.lower()
            if "nan" in exp_lower or "null" in exp_lower or "debug" in exp_lower:
                errors.append(f"decision_explanation contains invalid/debug tokens: '{exp}'")
            if record.affordability_status == "not_affordable":
                if "can safely pay" in exp_lower and "not" not in exp_lower:
                    errors.append(f"decision_explanation contradicts not_affordable status: '{exp}'")

        return len(errors) == 0, errors

    @staticmethod
    def validate_all(
        records: List[OutputRecord],
        requests: List[FinancialRequest],
        raise_on_error: bool = False,
    ) -> Tuple[bool, List[str]]:
        """
        Validates the entire prediction dataset against global contract requirements:
        - Exact row count
        - Unique, non-missing request IDs
        - Per-row invariant checks
        Fails loudly by raising ValueError if raise_on_error is True.
        """
        all_errors: List[str] = []
        req_map: Dict[str, FinancialRequest] = {r.request_id: r for r in requests}

        # 1. Dataset size check
        if len(records) != len(requests):
            all_errors.append(
                f"Output dataset row count ({len(records)}) does not match requests.csv count ({len(requests)})"
            )

        # 2. Duplicate / missing request_id checks
        seen_ids: Set[str] = set()
        for rec in records:
            if rec.request_id in seen_ids:
                all_errors.append(f"Duplicate request_id in output: '{rec.request_id}'")
            seen_ids.add(rec.request_id)

            if rec.request_id not in req_map:
                all_errors.append(f"Unknown request_id in output: '{rec.request_id}'")

        missing_ids = set(req_map.keys()) - seen_ids
        if missing_ids:
            all_errors.append(f"Missing request_ids in output: {sorted(list(missing_ids))[:5]}")

        # 3. Per-row validation
        for rec in records:
            req = req_map.get(rec.request_id)
            if req:
                is_valid, errs = OutputValidator.validate_row(rec, req)
                if not is_valid:
                    all_errors.extend([f"[{rec.request_id}] {e}" for e in errs])

        is_clean = len(all_errors) == 0
        if not is_clean and raise_on_error:
            error_summary = "\n".join(all_errors[:10])
            raise ValueError(
                f"Output validation failed with {len(all_errors)} errors:\n{error_summary}"
            )

        return is_clean, all_errors

    @staticmethod
    def validate_csv_file(
        csv_path: str,
        requests: List[FinancialRequest],
        raise_on_error: bool = False,
    ) -> Tuple[bool, List[str]]:
        """
        Validates an output CSV file directly on disk for:
        - Exact column names and order
        - Correct row count
        - Structural correctness and invariants
        """
        import csv
        errors: List[str] = []
        records: List[OutputRecord] = []

        try:
            with open(csv_path, mode="r", encoding="utf-8") as f:
                reader = csv.reader(f)
                header = next(reader, None)
                if not header:
                    errors.append(f"CSV file '{csv_path}' is empty")
                    if raise_on_error:
                        raise ValueError(errors[0])
                    return False, errors

                # Verify exact column names and order
                if header != OUTPUT_COLUMNS:
                    errors.append(
                        f"CSV header mismatch in '{csv_path}'. Expected {OUTPUT_COLUMNS}, got {header}"
                    )

                for row_idx, row in enumerate(reader, start=2):
                    if len(row) != len(OUTPUT_COLUMNS):
                        errors.append(
                            f"Row {row_idx} has {len(row)} columns, expected {len(OUTPUT_COLUMNS)}"
                        )
                        continue
                    records.append(
                        OutputRecord(
                            request_id=row[0],
                            amount_safe_to_pay=row[1],
                            affordability_status=row[2],
                            recommended_payment_method=row[3],
                            payment_plan=row[4],
                            earliest_date_for_full_payment=row[5],
                            spending_changes_needed=row[6],
                            decision_explanation=row[7],
                        )
                    )
        except Exception as exc:
            errors.append(f"Failed to read CSV file '{csv_path}': {exc}")

        if errors and raise_on_error:
            raise ValueError(f"CSV file validation failed:\n" + "\n".join(errors))

        is_all_valid, all_errs = OutputValidator.validate_all(
            records, requests, raise_on_error=raise_on_error
        )
        return (len(errors) == 0 and is_all_valid), errors + all_errs


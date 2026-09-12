"""
Output writer module for generating the final output.csv file.
"""

import csv
from pathlib import Path
from typing import List
from code.models import OutputRecord, DecisionResult
from code.config import OUTPUT_COLUMNS, OUTPUT_CSV


class OutputWriter:
    """Serializes decisions into the standardized output.csv format."""

    @staticmethod
    def format_amount(val: float) -> str:
        """Formats amount cleanly as integer if whole, or float."""
        if val == int(val):
            return str(int(val))
        return f"{val:.2f}".rstrip("0").rstrip(".")

    @staticmethod
    def decision_to_record(decision: DecisionResult) -> OutputRecord:
        """Converts a DecisionResult domain model into an OutputRecord."""
        return OutputRecord(
            request_id=decision.request_id,
            amount_safe_to_pay=OutputWriter.format_amount(decision.amount_safe_to_pay),
            affordability_status=decision.affordability_status,
            recommended_payment_method=decision.recommended_payment_method,
            payment_plan=decision.payment_plan,
            earliest_date_for_full_payment=decision.earliest_date_for_full_payment,
            spending_changes_needed=decision.spending_changes_needed,
            decision_explanation=decision.decision_explanation,
        )

    @staticmethod
    def write_output_csv(records: List[OutputRecord], output_path: Path = OUTPUT_CSV):
        """Writes records to output.csv matching exact headers and order."""
        with open(output_path, mode="w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=OUTPUT_COLUMNS)
            writer.writeheader()
            for rec in records:
                writer.writerow(rec.to_csv_dict())

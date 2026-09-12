"""
Error analysis module for diagnosing prediction discrepancies.
"""

from typing import List, Dict, Any


def diagnose_errors(predictions: List[Dict[str, str]], ground_truth: List[Dict[str, str]]) -> List[Dict[str, Any]]:
    """Identifies and classifies discrepancies between predictions and ground truth."""
    gt_map = {r["request_id"]: r for r in ground_truth}
    discrepancies = []

    for pred in predictions:
        rid = pred["request_id"]
        gt = gt_map.get(rid)
        if not gt:
            continue

        errors = {}
        for col in [
            "amount_safe_to_pay",
            "affordability_status",
            "recommended_payment_method",
            "payment_plan",
            "earliest_date_for_full_payment",
            "spending_changes_needed",
        ]:
            if pred.get(col) != gt.get(col):
                errors[col] = {"predicted": pred.get(col), "ground_truth": gt.get(col)}

        if errors:
            discrepancies.append({
                "request_id": rid,
                "discrepant_columns": errors,
            })

    return discrepancies

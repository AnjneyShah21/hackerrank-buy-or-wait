"""
Evaluation metrics calculation module for comparing predictions against ground truth.
"""

from typing import List, Dict, Any


def compute_accuracy(predictions: List[Dict[str, str]], ground_truth: List[Dict[str, str]]) -> Dict[str, float]:
    """
    Computes exact-match accuracy for every required field:
    - amount_safe_to_pay (within 1% or exact)
    - affordability_status (exact match)
    - recommended_payment_method (exact match)
    - payment_plan (exact match)
    - earliest_date_for_full_payment (exact match)
    - spending_changes_needed (exact match)
    """
    gt_map = {r["request_id"]: r for r in ground_truth}
    total = len(predictions)
    if total == 0:
        return {}

    status_matches = 0
    method_matches = 0
    plan_matches = 0
    date_matches = 0
    spending_matches = 0
    safe_amt_matches = 0
    overall_exact_matches = 0

    for pred in predictions:
        rid = pred["request_id"]
        gt = gt_map.get(rid)
        if not gt:
            continue

        st_match = pred["affordability_status"] == gt["affordability_status"]
        m_match = pred["recommended_payment_method"] == gt["recommended_payment_method"]
        p_match = pred["payment_plan"] == gt["payment_plan"]
        d_match = pred["earliest_date_for_full_payment"] == gt["earliest_date_for_full_payment"]
        sp_match = pred["spending_changes_needed"] == gt["spending_changes_needed"]

        try:
            p_safe = float(pred["amount_safe_to_pay"])
            g_safe = float(gt["amount_safe_to_pay"])
            safe_match = abs(p_safe - g_safe) < 1.0 or abs(p_safe - g_safe) / (g_safe + 1e-6) < 0.01
        except (ValueError, KeyError):
            safe_match = pred["amount_safe_to_pay"] == gt["amount_safe_to_pay"]

        if st_match: status_matches += 1
        if m_match: method_matches += 1
        if p_match: plan_matches += 1
        if d_match: date_matches += 1
        if sp_match: spending_matches += 1
        if safe_match: safe_amt_matches += 1

        if st_match and m_match and p_match and d_match and sp_match and safe_match:
            overall_exact_matches += 1

    return {
        "total_evaluated": total,
        "overall_exact_match_rate": overall_exact_matches / total,
        "affordability_status_accuracy": status_matches / total,
        "recommended_method_accuracy": method_matches / total,
        "payment_plan_accuracy": plan_matches / total,
        "earliest_date_accuracy": date_matches / total,
        "spending_changes_accuracy": spending_matches / total,
        "amount_safe_to_pay_accuracy": safe_amt_matches / total,
    }

"""
Evaluation metrics for comparing predictions against sample ground truth.
Computes exact-match accuracy per field, partial credit, and amount tolerance.
"""

from typing import Any, Dict, List, Tuple
import math


def _amounts_close(pred_str: str, gt_str: str, rel_tol: float = 0.01, abs_tol: float = 1.0) -> bool:
    try:
        p, g = float(pred_str), float(gt_str)
        if math.isnan(p) or math.isnan(g):
            return False
        if abs(p - g) <= abs_tol:
            return True
        denom = max(abs(g), 1e-6)
        return abs(p - g) / denom <= rel_tol
    except (ValueError, TypeError):
        return pred_str == gt_str


def _payment_plan_match(pred: str, gt: str) -> Tuple[bool, str]:
    if pred == gt:
        return True, "exact"
    if pred.strip() == "none" and gt.strip() == "none":
        return True, "both_none"
    try:
        p_entries = [e.split(":") for e in pred.split("|")]
        g_entries = [e.split(":") for e in gt.split("|")]
        if len(p_entries) != len(g_entries):
            return False, f"entry_count_mismatch (pred={len(p_entries)} gt={len(g_entries)})"
        for (pd, pa), (gd, ga) in zip(p_entries, g_entries):
            if pd.strip() != gd.strip():
                return False, f"date_mismatch ({pd.strip()} vs {gd.strip()})"
            if not _amounts_close(pa.strip(), ga.strip()):
                return False, f"amount_mismatch ({pa.strip()} vs {ga.strip()})"
        return True, "tolerant"
    except Exception:
        return False, "parse_error"


def compute_accuracy(
    predictions: List[Dict[str, str]],
    ground_truth: List[Dict[str, str]],
) -> Dict[str, Any]:
    gt_map = {r["request_id"]: r for r in ground_truth}
    results = []
    status_matches = method_matches = plan_matches = date_matches = 0
    spending_matches = safe_amt_matches = overall_exact = 0

    for pred in predictions:
        rid = pred["request_id"]
        gt = gt_map.get(rid)
        if not gt:
            continue
        st_match = pred.get("affordability_status") == gt.get("affordability_status")
        m_match = pred.get("recommended_payment_method") == gt.get("recommended_payment_method")
        p_match, p_reason = _payment_plan_match(pred.get("payment_plan",""), gt.get("payment_plan",""))
        d_match = pred.get("earliest_date_for_full_payment") == gt.get("earliest_date_for_full_payment")
        sp_match = pred.get("spending_changes_needed") == gt.get("spending_changes_needed")
        safe_match = _amounts_close(pred.get("amount_safe_to_pay",""), gt.get("amount_safe_to_pay",""))
        exact = st_match and m_match and p_match and d_match and sp_match and safe_match
        if st_match:    status_matches  += 1
        if m_match:     method_matches  += 1
        if p_match:     plan_matches    += 1
        if d_match:     date_matches    += 1
        if sp_match:    spending_matches += 1
        if safe_match:  safe_amt_matches += 1
        if exact:       overall_exact   += 1
        results.append({
            "request_id": rid, "exact_match": exact,
            "affordability_status": {"pred": pred.get("affordability_status"), "gt": gt.get("affordability_status"), "match": st_match},
            "recommended_payment_method": {"pred": pred.get("recommended_payment_method"), "gt": gt.get("recommended_payment_method"), "match": m_match},
            "payment_plan": {"pred": pred.get("payment_plan"), "gt": gt.get("payment_plan"), "match": p_match, "reason": p_reason},
            "earliest_date_for_full_payment": {"pred": pred.get("earliest_date_for_full_payment"), "gt": gt.get("earliest_date_for_full_payment"), "match": d_match},
            "spending_changes_needed": {"pred": pred.get("spending_changes_needed"), "gt": gt.get("spending_changes_needed"), "match": sp_match},
            "amount_safe_to_pay": {"pred": pred.get("amount_safe_to_pay"), "gt": gt.get("amount_safe_to_pay"), "match": safe_match},
        })

    total = len(results)
    if total == 0:
        return {"total_evaluated": 0, "per_request": []}
    return {
        "total_evaluated": total,
        "overall_exact_match_rate": overall_exact / total,
        "affordability_status_accuracy": status_matches / total,
        "recommended_method_accuracy": method_matches / total,
        "payment_plan_accuracy": plan_matches / total,
        "earliest_date_accuracy": date_matches / total,
        "spending_changes_accuracy": spending_matches / total,
        "amount_safe_to_pay_accuracy": safe_amt_matches / total,
        "per_request": results,
    }

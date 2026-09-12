"""
Error analysis: classifies discrepancies between predictions and ground truth
into root-cause categories and identifies systematic failure patterns.
"""

from typing import Any, Dict, List, Tuple
from collections import defaultdict


# Root-cause categories
CATEGORY_STATUS_MISMATCH      = "wrong_affordability_status"
CATEGORY_METHOD_MISMATCH      = "wrong_payment_method"
CATEGORY_DATE_MISMATCH        = "wrong_earliest_date"
CATEGORY_AMOUNT_MISMATCH      = "wrong_amount_safe"
CATEGORY_PLAN_DATE_MISMATCH   = "wrong_plan_dates"
CATEGORY_PLAN_AMOUNT_MISMATCH = "wrong_plan_amounts"
CATEGORY_PLAN_COUNT_MISMATCH  = "wrong_plan_entry_count"
CATEGORY_SPENDING_MISMATCH    = "wrong_spending_changes"
CATEGORY_EXACT_MATCH          = "exact_match"


def categorise_failure(per_request_result: Dict[str, Any]) -> List[str]:
    """
    Given one per-request result dict from metrics.compute_accuracy(),
    returns a list of root-cause category strings.
    Empty list means exact match.
    """
    if per_request_result.get("exact_match"):
        return [CATEGORY_EXACT_MATCH]

    cats = []
    if not per_request_result["affordability_status"]["match"]:
        cats.append(CATEGORY_STATUS_MISMATCH)
    if not per_request_result["recommended_payment_method"]["match"]:
        cats.append(CATEGORY_METHOD_MISMATCH)
    if not per_request_result["amount_safe_to_pay"]["match"]:
        cats.append(CATEGORY_AMOUNT_MISMATCH)
    if not per_request_result["earliest_date_for_full_payment"]["match"]:
        cats.append(CATEGORY_DATE_MISMATCH)
    if not per_request_result["spending_changes_needed"]["match"]:
        cats.append(CATEGORY_SPENDING_MISMATCH)

    plan_info = per_request_result["payment_plan"]
    if not plan_info["match"]:
        reason = plan_info.get("reason", "")
        if "entry_count" in reason:
            cats.append(CATEGORY_PLAN_COUNT_MISMATCH)
        elif "date_mismatch" in reason:
            cats.append(CATEGORY_PLAN_DATE_MISMATCH)
        elif "amount_mismatch" in reason:
            cats.append(CATEGORY_PLAN_AMOUNT_MISMATCH)
        else:
            cats.append(CATEGORY_PLAN_DATE_MISMATCH)  # default to date
    return cats


def diagnose_errors(
    predictions: List[Dict[str, str]],
    ground_truth: List[Dict[str, str]],
) -> List[Dict[str, Any]]:
    """Legacy interface: basic column-level diff."""
    gt_map = {r["request_id"]: r for r in ground_truth}
    discrepancies = []
    for pred in predictions:
        rid = pred["request_id"]
        gt = gt_map.get(rid)
        if not gt:
            continue
        errors = {}
        for col in [
            "amount_safe_to_pay", "affordability_status", "recommended_payment_method",
            "payment_plan", "earliest_date_for_full_payment", "spending_changes_needed",
        ]:
            if pred.get(col) != gt.get(col):
                errors[col] = {"predicted": pred.get(col), "ground_truth": gt.get(col)}
        if errors:
            discrepancies.append({"request_id": rid, "discrepant_columns": errors})
    return discrepancies


def group_failures(per_request_results: List[Dict[str, Any]]) -> Dict[str, List[str]]:
    """
    Groups request_ids by root-cause category.
    Returns a dict: category -> list of request_ids.
    """
    grouped: Dict[str, List[str]] = defaultdict(list)
    for r in per_request_results:
        cats = categorise_failure(r)
        for cat in cats:
            grouped[cat].append(r["request_id"])
    return dict(grouped)


def identify_patterns(grouped: Dict[str, List[str]]) -> List[str]:
    """
    Returns human-readable pattern descriptions sorted by frequency.
    """
    patterns = []
    for cat, rids in sorted(grouped.items(), key=lambda x: -len(x[1])):
        if cat == CATEGORY_EXACT_MATCH:
            continue
        patterns.append(f"{cat}: {len(rids)} request(s) — {', '.join(sorted(rids))}")
    return patterns

"""
Main evaluation entry point.
Compares predictions against sample_requests.csv or an evaluation dataset.
"""

import sys
import csv
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from code.config import SAMPLE_REQUESTS_CSV, OUTPUT_CSV
from code.evaluation.metrics import compute_accuracy
from code.evaluation.error_analysis import diagnose_errors


def run_evaluation(predictions_csv: Path = OUTPUT_CSV, ground_truth_csv: Path = SAMPLE_REQUESTS_CSV):
    """Executes evaluation and prints detailed metrics."""
    print(f"Loading predictions from: {predictions_csv}")
    print(f"Loading ground truth from: {ground_truth_csv}")

    if not predictions_csv.exists():
        print(f"Predictions file not found at {predictions_csv}")
        return

    with open(predictions_csv, mode="r", encoding="utf-8") as f:
        predictions = list(csv.DictReader(f))

    with open(ground_truth_csv, mode="r", encoding="utf-8") as f:
        ground_truth = list(csv.DictReader(f))

    # Evaluate on intersection of IDs
    gt_ids = {r["request_id"] for r in ground_truth}
    eval_preds = [p for p in predictions if p["request_id"] in gt_ids]

    if not eval_preds:
        print("No matching request IDs found between predictions and ground truth.")
        return

    metrics = compute_accuracy(eval_preds, ground_truth)
    print("\n=== EVALUATION RESULTS ===")
    for k, v in metrics.items():
        if isinstance(v, float):
            print(f"{k}: {v:.2%}")
        else:
            print(f"{k}: {v}")

    errors = diagnose_errors(eval_preds, ground_truth)
    if errors:
        print(f"\nDiscrepancies found in {len(errors)} requests:")
        for err in errors[:5]:
            print(f"  Request {err['request_id']}: {err['discrepant_columns']}")
    else:
        print("\nPerfect 100% match on all evaluated sample requests!")


if __name__ == "__main__":
    run_evaluation()

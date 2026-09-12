import csv
import sys
from pathlib import Path
from code.data_loader import build_dataset_index
from code.currency import CurrencyConverter
from code.decision_engine import DecisionEngine
from code.evidence import EvidenceManager
from code.financial_engine import FinancialEngine
from code.forecast import CashFlowForecaster
from code.image_extractor import ImageExtractor
from code.message_interpreter import MessageInterpreter
from code.payment_planner import PaymentPlanner
from code.config import SAMPLE_REQUESTS_CSV
from code.evaluation.main import load_sample_ground_truth, ground_truth_to_requests, run_pipeline_on_requests, UsageTracker

gt_rows = load_sample_ground_truth(SAMPLE_REQUESTS_CSV)
sample_reqs = ground_truth_to_requests(gt_rows)

index = build_dataset_index()
converter = CurrencyConverter(index.exchange_rates)
evidence_mgr = EvidenceManager()
img_extractor = ImageExtractor()
msg_interpreter = MessageInterpreter()
decision_engine = DecisionEngine()

img_records = list(index.images_by_event.values())
img_facts = img_extractor.process_all_images(img_records)
evidence_mgr.add_facts(img_facts)

all_msgs = []
for msgs in index.messages_by_user.values():
    all_msgs.extend(msgs)
msg_facts = msg_interpreter.process_all_messages(all_msgs)
evidence_mgr.add_facts(msg_facts)

forecaster = CashFlowForecaster(converter, evidence_mgr)
fin_engine = FinancialEngine(forecaster)
planner = PaymentPlanner(forecaster)
tracker = UsageTracker()

preds = run_pipeline_on_requests(sample_reqs, index, fin_engine, planner, decision_engine, evidence_mgr, tracker)

exp_map = {r["request_id"]: r for r in gt_rows}

for p in preds:
    rid = p["request_id"]
    exp = exp_map[rid]
    diffs = []
    if p["affordability_status"] != exp["affordability_status"]:
        diffs.append(f"status: pred={p['affordability_status']} exp={exp['affordability_status']}")
    if p["recommended_payment_method"] != exp["recommended_payment_method"]:
        diffs.append(f"method: pred={p['recommended_payment_method']} exp={exp['recommended_payment_method']}")
    if p["earliest_date_for_full_payment"] != (exp["earliest_date_for_full_payment"] or ""):
        diffs.append(f"date: pred='{p['earliest_date_for_full_payment']}' exp='{exp['earliest_date_for_full_payment']}'")
    if p["spending_changes_needed"] != exp["spending_changes_needed"]:
        diffs.append(f"spend: pred='{p['spending_changes_needed']}' exp='{exp['spending_changes_needed']}'")
    if p["payment_plan"] != exp["payment_plan"]:
        diffs.append(f"plan: pred='{p['payment_plan']}' exp='{exp['payment_plan']}'")
    if p["amount_safe_to_pay"] != exp["amount_safe_to_pay"]:
        diffs.append(f"safe_amt: pred='{p['amount_safe_to_pay']}' exp='{exp['amount_safe_to_pay']}'")
    
    if diffs:
        print(f"=== {rid} ===")
        for d in diffs:
            print(f"  {d}")

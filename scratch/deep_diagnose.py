import sys
import csv
from pathlib import Path
sys.path.insert(0, '.')
from code.data_loader import build_dataset_index, _parse_requests, get_request_context
from code.currency import CurrencyConverter
from code.evidence import EvidenceManager
from code.image_extractor import ImageExtractor
from code.message_interpreter import MessageInterpreter
from code.forecast import CashFlowForecaster
from code.financial_engine import FinancialEngine
from code.payment_planner import PaymentPlanner
from code.decision_engine import DecisionEngine
from code.models import FinancialEvent

idx = build_dataset_index()
converter = CurrencyConverter(idx.exchange_rates)
img_ext = ImageExtractor(Path('dataset/media/images'))
msg_interp = MessageInterpreter()
ev_mgr = EvidenceManager()
for msg in idx.messages_by_user.values():
    for m in msg:
        for f in msg_interp.interpret_message(m):
            ev_mgr.add_fact(f)
for img in idx.images_by_event.values():
    fact = img_ext.extract_fact_from_image(img)
    if fact:
        ev_mgr.add_fact(fact)

forecaster = CashFlowForecaster(converter, ev_mgr)
fin_engine = FinancialEngine(forecaster)
planner = PaymentPlanner(forecaster)
decision_engine = DecisionEngine()

sample_reqs = _parse_requests(Path('dataset/sample_requests.csv'), [])
with open('dataset/sample_requests.csv', 'r', encoding='utf-8') as f:
    gt_rows = {r['request_id']: r for r in csv.DictReader(f)}

print(f"{'ID':11} | {'Diffs':5} | Description")
print('-'*90)

for req in sample_reqs:
    rid = req.request_id
    gt = gt_rows[rid]
    uctx, options = get_request_context(req, idx)
    if not uctx: continue
    profile = uctx.profile
    user_events = idx.events_by_user.get(req.user_id, [])
    enriched = [ev_mgr.apply_evidence_to_event(FinancialEvent(**e.__dict__)) for e in user_events]
    
    amt_safe = fin_engine.compute_amount_safe_to_pay(profile, enriched, req)
    earliest_date = fin_engine.compute_earliest_date_for_full_payment(profile, enriched, req)
    candidates = planner.generate_candidate_plans(profile, enriched, req, options, amt_safe, earliest_date)
    best = decision_engine.rank_plans(candidates, req)
    res = decision_engine.make_decision(req, profile, amt_safe, earliest_date, best)
    
    mismatch = []
    gt_status = gt['affordability_status']
    gt_method = gt['recommended_payment_method']
    gt_safe = float(gt['amount_safe_to_pay'])
    gt_date = gt['earliest_date_for_full_payment']
    gt_plan = gt['payment_plan']
    gt_spend = gt['spending_changes_needed']

    if res.affordability_status != gt_status:
        mismatch.append(f"status: {res.affordability_status} != {gt_status}")
    if res.recommended_payment_method != gt_method:
        mismatch.append(f"method: {res.recommended_payment_method} != {gt_method}")
    if abs(res.amount_safe_to_pay - gt_safe) > 0.01 * gt_safe and abs(res.amount_safe_to_pay - gt_safe) > 1.0:
        mismatch.append(f"safe: {res.amount_safe_to_pay} != {gt_safe}")
    if res.earliest_date_for_full_payment != gt_date:
        mismatch.append(f"date: '{res.earliest_date_for_full_payment}' != '{gt_date}'")
    if res.payment_plan != gt_plan:
        mismatch.append(f"plan: '{res.payment_plan}' != '{gt_plan}'")
    if res.spending_changes_needed != gt_spend:
        mismatch.append(f"spend: '{res.spending_changes_needed}' != '{gt_spend}'")
        
    if mismatch:
        print(f"{rid:11} | {len(mismatch):5} | {' ; '.join(mismatch)}")

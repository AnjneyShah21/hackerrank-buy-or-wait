from code.data_loader import build_dataset_index
from code.currency import CurrencyConverter
from code.evidence import EvidenceManager
from code.forecast import CashFlowForecaster
from code.config import SAMPLE_REQUESTS_CSV
from code.evaluation.main import load_sample_ground_truth, ground_truth_to_requests

index = build_dataset_index()
converter = CurrencyConverter(index.exchange_rates)
evidence_mgr = EvidenceManager()
forecaster = CashFlowForecaster(converter, evidence_mgr)

gt_rows = load_sample_ground_truth(SAMPLE_REQUESTS_CSV)
sample_reqs = ground_truth_to_requests(gt_rows)
req = [r for r in sample_reqs if r.request_id == "request_04"][0]
profile = index.profiles[req.user_id]
events = index.events_by_user[req.user_id]

is_safe, min_b, timeline = forecaster.simulate_90_days(
    profile=profile,
    events=events,
    start_date_str=req.request_date,
    proposed_payments=[(req.request_date, req.requested_amount)],
)

print(f"Is safe: {is_safe}, Min balance reached: {min_b:.2f}, Minimum required: {profile.minimum_balance_to_keep}")
print("Daily timeline:")
for t in timeline[:20]:
    print(f"  {t.date_str}: start={t.starting_balance:.2f}, in={t.confirmed_inflows:.2f}, req_out={t.required_outflows:.2f}, flex_out={t.flexible_outflows:.2f}, prop={t.proposed_payments:.2f}, end={t.ending_balance:.2f}")

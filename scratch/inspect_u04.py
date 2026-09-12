from code.data_loader import build_dataset_index
from code.financial_engine import FinancialEngine
from code.forecast import CashFlowForecaster
from code.currency import CurrencyConverter
from code.evidence import EvidenceManager

index = build_dataset_index()
converter = CurrencyConverter(index.exchange_rates)
evidence_mgr = EvidenceManager()
forecaster = CashFlowForecaster(converter, evidence_mgr)
fin_engine = FinancialEngine(forecaster)

from code.config import SAMPLE_REQUESTS_CSV
from code.evaluation.main import load_sample_ground_truth, ground_truth_to_requests

gt_rows = load_sample_ground_truth(SAMPLE_REQUESTS_CSV)
sample_reqs = ground_truth_to_requests(gt_rows)
req = [r for r in sample_reqs if r.request_id == "request_04"][0]
print("REQ 04:")
print("Req Date:", req.request_date, "Amt:", req.requested_amount)

profile = index.profiles.get(req.user_id)
print("User profile:", profile)

events = index.events_by_user[req.user_id]
print("\nUser Events (first 20):")
for e in events:
    print(f"  {e.event_id}: date={e.event_date}, cat={e.category}, type={e.event_type}, amt={e.amount} {e.currency}, status={e.status}, flex={e.flexibility}")

timeline = forecaster.project_cashflow_timeline(uctx.profile, events, req.request_date, horizon_days=45)
print("\nProjected Timeline:")
for d, bal in sorted(timeline.daily_balances.items())[:20]:
    print(f"  {d}: balance={bal:.2f}")

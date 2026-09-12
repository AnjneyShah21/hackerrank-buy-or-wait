from code.data_loader import build_dataset_index
from code.currency import CurrencyConverter
from code.evidence import EvidenceManager
from code.forecast import CashFlowForecaster
from code.financial_engine import FinancialEngine
from code.config import SAMPLE_REQUESTS_CSV
from code.evaluation.main import load_sample_ground_truth, ground_truth_to_requests

index = build_dataset_index()
converter = CurrencyConverter(index.exchange_rates)
evidence_mgr = EvidenceManager()
forecaster = CashFlowForecaster(converter, evidence_mgr)
fin_engine = FinancialEngine(forecaster)

gt_rows = load_sample_ground_truth(SAMPLE_REQUESTS_CSV)
sample_reqs = ground_truth_to_requests(gt_rows)
req = [r for r in sample_reqs if r.request_id == "request_19"][0]
profile = index.profiles[req.user_id]
events = index.events_by_user[req.user_id]

safe_amt = fin_engine.compute_amount_safe_to_pay(profile, events, req)
earliest_date = fin_engine.compute_earliest_date_for_full_payment(profile, events, req)

print(f"Req 19: date={req.request_date}, amt={req.requested_amount}, allows_partial={req.allows_partial_payment}")
print(f"Computed safe_amt: {safe_amt}, earliest_date: {earliest_date}")
print(f"Profile: bal={profile.current_available_balance}, min_bal={profile.minimum_balance_to_keep}")
print(f"Considered methods: {profile.payment_methods_user_will_consider}")

# Simulate with 28820 payment on request date
is_safe, min_b, _ = forecaster.simulate_90_days(
    profile=profile,
    events=events,
    start_date_str=req.request_date,
    proposed_payments=[(req.request_date, 28820.0)],
)
print(f"Is 28820 safe on {req.request_date}? {is_safe}, min_b={min_b:.2f}")

# Simulate partial payment (28820 on Sept 4, 10840 on Sept 15)
is_safe_p, min_b_p, _ = forecaster.simulate_90_days(
    profile=profile,
    events=events,
    start_date_str=req.request_date,
    proposed_payments=[(req.request_date, 28820.0), ("2024-09-15", 10840.0)],
)
print(f"Is partial payment safe? {is_safe_p}, min_b={min_b_p:.2f}")

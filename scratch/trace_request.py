"""
Deep trace for specific failing requests to understand why amount_safe_to_pay is wrong.
"""
import sys
import pandas as pd
from datetime import datetime, timedelta

# Request to trace
REQ_ID = "request_03"

import code.data_loader as dl
from code.forecast import CashFlowForecaster
from code.financial_engine import FinancialEngine
from code.data_loader import DataLoader

loader = DataLoader("dataset")
profiles = loader.load_profiles()
events_by_user = loader.load_events()
requests_df = pd.read_csv("dataset/sample_requests.csv")
row = requests_df[requests_df['request_id'] == REQ_ID].iloc[0]

from code.models import FinancialRequest

req = FinancialRequest(
    request_id=row['request_id'],
    user_id=row['user_id'],
    request_date=row['request_date'],
    request_type=row['request_type'],
    requested_amount=float(row['requested_amount']),
    desired_completion_date=row['desired_completion_date'],
    allows_partial_payment=str(row['allows_partial_payment']).lower() == 'true',
    request_text=row['request_text'],
)

profile = profiles[req.user_id]
events = events_by_user.get(req.user_id, [])

print(f"Request: {REQ_ID}")
print(f"User: {profile.user_id}")
print(f"Currency: {profile.home_currency}")
print(f"Balance: {profile.current_available_balance}")
print(f"Min Balance: {profile.minimum_balance_to_keep}")
print(f"Request Amount: {req.requested_amount}")
print(f"Request Date: {req.request_date}")
print(f"Expected amount_safe_to_pay: {row['amount_safe_to_pay']}")
print(f"Expected earliest_date: {row['earliest_date_for_full_payment']}")
print()

print(f"Total events for user: {len(events)}")
print("Events around request date:")
req_dt = datetime.strptime(req.request_date, "%Y-%m-%d").date()
for ev in sorted(events, key=lambda e: e.settlement_date or e.event_date or ""):
    ev_date_str = ev.settlement_date or ev.event_date or ""
    if not ev_date_str:
        continue
    try:
        ev_dt = datetime.strptime(ev_date_str[:10], "%Y-%m-%d").date()
    except:
        continue
    if abs((ev_dt - req_dt).days) <= 90 or ev_dt > req_dt - timedelta(days=365):
        print(f"  {ev_date_str} | {ev.direction:7s} | {ev.status:10s} | {ev.category:20s} | {ev.flexibility:25s} | {ev.amount:>12.2f} {ev.currency} | {ev.description[:40] if ev.description else ''}")

print()

# Now manually simulate
forecaster = CashFlowForecaster()
engine = FinancialEngine(forecaster)

# Test full payment safety
is_full, _, _ = forecaster.simulate_90_days(
    profile=profile,
    events=events,
    start_date_str=req.request_date,
    proposed_payments=[(req.request_date, req.requested_amount)],
)
print(f"Full payment safe: {is_full}")

# Test zero payment safety
is_zero, _, tl = forecaster.simulate_90_days(
    profile=profile,
    events=events,
    start_date_str=req.request_date,
    proposed_payments=[],
)
print(f"Zero payment safe: {is_zero}")

# Show timeline of balance (without payment)
print("\nBalance timeline (no payment):")
for day in tl[:30]:
    flag = " *** UNSAFE ***" if day.ending_balance < profile.minimum_balance_to_keep else ""
    print(f"  {day.date_str}: in={day.confirmed_inflows:>10.2f} req_out={day.required_outflows:>10.2f} flex={day.flexible_outflows:>10.2f} end={day.ending_balance:>12.2f}{flag}")

# Compute safe amount
safe_amount = engine.compute_amount_safe_to_pay(profile, events, req)
print(f"\nComputed amount_safe_to_pay: {safe_amount}")
print(f"Expected:                    {row['amount_safe_to_pay']}")
print()

# Compute earliest date
earliest = engine.compute_earliest_date_for_full_payment(profile, events, req)
print(f"Computed earliest_date: {earliest}")
print(f"Expected earliest_date: {row['earliest_date_for_full_payment']}")

import sys
sys.path.insert(0, 'D:/Hackerrank')
from code.data_loader import DataLoader
from code.forecast import CashFlowForecaster
from code.currency import CurrencyConverter
from code.financial_engine import FinancialEngine
from collections import defaultdict

loader = DataLoader('dataset')
profiles = loader.load_profiles()
all_events = loader.load_events()
events_by_user = defaultdict(list)
for ev in all_events:
    events_by_user[ev.user_id].append(ev)
rates = loader.load_exchange_rates()

TARGET_USER = "user_03"
REQ_DATE = "2019-09-03"
REQ_AMOUNT = 5491000.0

profile = profiles[TARGET_USER]
events = events_by_user.get(TARGET_USER, [])

print(f"Balance: {profile.current_available_balance}")
print(f"Min Balance: {profile.minimum_balance_to_keep}")
print(f"Home Currency: {profile.home_currency}")
print(f"Events count: {len(events)}")
print()

for ev in sorted(events, key=lambda e: e.event_date or ''):
    desc = (ev.description or '')[:30]
    print(f"{ev.event_date} | {ev.settlement_date or 'N/A':10s} | {(ev.direction or ''):7s} | {(ev.status or ''):10s} | {(ev.category or ''):20s} | {(ev.amount or 0):>12.2f} {ev.currency or 'N/A'} | {desc}")

print()

# Now simulate
converter = CurrencyConverter(rates)
forecaster = CashFlowForecaster(converter)
engine = FinancialEngine(forecaster)

# Simulate no-payment baseline
is_zero, min_z, tl_zero = forecaster.simulate_90_days(
    profile=profile,
    events=events,
    start_date_str=REQ_DATE,
    proposed_payments=[],
)
print(f"Zero payment safe: {is_zero}")
print()
print("Balance timeline (no payment, all days):")
for d in tl_zero:
    flag = " *** UNSAFE ***" if d.ending_balance < profile.minimum_balance_to_keep else ""
    if d.confirmed_inflows > 0 or d.required_outflows > 0 or d.flexible_outflows > 0 or flag:
        print(f"  {d.date_str}: in={d.confirmed_inflows:>10.2f} req_out={d.required_outflows:>10.2f} flex={d.flexible_outflows:>10.2f} end={d.ending_balance:>14.2f}{flag}")

print()
# Safe amount
class FakeReq:
    request_id = 'test'
    user_id = TARGET_USER
    request_date = REQ_DATE
    requested_amount = REQ_AMOUNT

safe = engine.compute_amount_safe_to_pay(profile, events, FakeReq())
print(f"Computed safe amount: {safe}")
print(f"Expected safe amount: 873000")
print()

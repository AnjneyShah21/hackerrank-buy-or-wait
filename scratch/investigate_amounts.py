import sys
sys.path.insert(0, 'D:/Hackerrank')
from code.data_loader import DataLoader
from code.forecast import CashFlowForecaster
from code.currency import CurrencyConverter
from code.financial_engine import FinancialEngine
from collections import defaultdict
import csv

loader = DataLoader('dataset')
profiles = loader.load_profiles()
all_events = loader.load_events()
events_by_user = defaultdict(list)
for ev in all_events:
    events_by_user[ev.user_id].append(ev)
rates = loader.load_exchange_rates()

# Read sample_requests.csv
requests = {}
with open('dataset/sample_requests.csv') as f:
    reader = csv.DictReader(f)
    for row in reader:
        requests[row['request_id']] = row

# Show mapping for failing requests
TARGET_REQS = ['request_25', 'request_10', 'request_05', 'request_12', 'request_17', 'request_22', 'request_20', 'request_04']
for req_id in TARGET_REQS:
    row = requests.get(req_id)
    if not row:
        print(f'{req_id}: NOT FOUND')
        continue
    user_id = row['user_id']
    req_date = row['request_date']
    req_amt = float(row['requested_amount'])
    expected_safe = float(row['amount_safe_to_pay'])
    
    profile = profiles.get(user_id)
    if not profile:
        print(f'{req_id}: user {user_id} not found in profiles')
        continue
    
    events = events_by_user.get(user_id, [])
    converter = CurrencyConverter(rates)
    forecaster = CashFlowForecaster(converter)
    engine = FinancialEngine(forecaster)
    
    class FakeReq:
        pass
    freq = FakeReq()
    freq.request_id = req_id
    freq.user_id = user_id
    freq.request_date = req_date
    freq.requested_amount = req_amt
    
    predicted = engine.compute_amount_safe_to_pay(profile, events, freq)
    
    print(f'{req_id}: user={user_id}, date={req_date}, amount={req_amt}, bal={profile.current_available_balance}, minbal={profile.minimum_balance_to_keep}')
    print(f'  expected_safe={expected_safe}, predicted={predicted}')
    
    # Check if full amount is simulatable safely
    is_full, min_bal_full, _ = forecaster.simulate_90_days(
        profile=profile, events=events, start_date_str=req_date,
        proposed_payments=[(req_date, req_amt)],
    )
    is_expected, min_bal_exp, _ = forecaster.simulate_90_days(
        profile=profile, events=events, start_date_str=req_date,
        proposed_payments=[(req_date, expected_safe)],
    )
    print(f'  Full ({req_amt}) safe={is_full}, min_bal={min_bal_full:.2f}')
    print(f'  Expected ({expected_safe}) safe={is_expected}, min_bal={min_bal_exp:.2f}')
    print()

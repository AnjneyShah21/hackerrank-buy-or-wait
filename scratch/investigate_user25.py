import sys
sys.path.insert(0, 'D:/Hackerrank')
from code.data_loader import DataLoader
from code.forecast import CashFlowForecaster
from code.currency import CurrencyConverter
from collections import defaultdict
from datetime import datetime, timedelta

loader = DataLoader('dataset')
profiles = loader.load_profiles()
all_events = loader.load_events()
events_by_user = defaultdict(list)
for ev in all_events:
    events_by_user[ev.user_id].append(ev)
rates = loader.load_exchange_rates()

user_id = 'user_25'
req_date = '2024-03-06'
profile = profiles[user_id]
events = events_by_user.get(user_id, [])
converter = CurrencyConverter(rates)
forecaster = CashFlowForecaster(converter)
start_dt = datetime.strptime(req_date, '%Y-%m-%d').date()
end_dt = start_dt + timedelta(days=90)

print(f'user_25 balance={profile.current_available_balance}, minbal={profile.minimum_balance_to_keep}, currency={profile.home_currency}')
print(f'Events count: {len(events)}')
print()
print('Recent events for user_25 (around request_date):')
for ev in sorted(events, key=lambda e: e.event_date or ''):
    ev_date = ev.event_date or ''
    if ev_date >= '2024-01-01':
        settle = ev.settlement_date or 'N/A'
        dirn = ev.direction or ''
        status = ev.status or ''
        cat = ev.category or ''
        amt = ev.amount or 0
        cur = ev.currency or 'N/A'
        desc = (ev.description or '')[:40]
        print(f'  {ev_date} | {settle:10s} | {dirn:7s} | {status:10s} | {cat:20s} | {amt:>14.2f} {cur} | {desc}')

print()
projected = forecaster._project_recurring_events(events, start_dt, end_dt)
print(f'Projected events: {len(projected)}')
for p in sorted(projected, key=lambda e: e.event_date or ''):
    print(f'  {p.event_date} | {p.direction:7s} | {p.amount:>14.2f} | {p.description}')

print()
_, _, tl = forecaster.simulate_90_days(
    profile=profile, events=events, start_date_str=req_date,
    proposed_payments=[(req_date, 1425000)],
)
print(f'Balance timeline with payment 1425000:')
print(f'Starting balance: {profile.current_available_balance}')
print(f'Min balance: {profile.minimum_balance_to_keep}')
for d in tl:
    flag = ' *** UNSAFE ***' if d.ending_balance < profile.minimum_balance_to_keep else ''
    if d.confirmed_inflows > 0 or d.required_outflows > 0 or d.flexible_outflows > 0 or d.proposed_payments > 0 or flag:
        print(f'  {d.date_str}: in={d.confirmed_inflows:>12.2f} req={d.required_outflows:>12.2f} flex={d.flexible_outflows:>12.2f} prop={d.proposed_payments:>12.2f} end={d.ending_balance:>16.2f}{flag}')

import csv
import os
from collections import Counter, defaultdict

dataset_dir = r"d:\Hackerrank\dataset"

def check_csv(filename):
    p = os.path.join(dataset_dir, filename)
    with open(p, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        fieldnames = reader.fieldnames
    return fieldnames, rows

print("=== DATASET ANOMALY SCAN ===")

# 1. Profiles
fields, profiles = check_csv("financial_profiles.csv")
print(f"Profiles: {len(profiles)} rows")
uids = [r['user_id'] for r in profiles]
dup_uids = [k for k, v in Counter(uids).items() if v > 1]
print(f"Duplicate user_ids: {dup_uids}")

# 2. Events
fields, events = check_csv("financial_events.csv")
print(f"Events: {len(events)} rows")
eids = [r['event_id'] for r in events]
dup_eids = [k for k, v in Counter(eids).items() if v > 1]
print(f"Duplicate event_ids: {dup_eids}")
missing_amounts = [r for r in events if not r['amount'].strip()]
print(f"Events with missing amounts: {len(missing_amounts)}")
missing_settlements = [r for r in events if not r['settlement_date'].strip()]
print(f"Events with missing settlement dates: {len(missing_settlements)}")

# 3. Requests
fields, reqs = check_csv("requests.csv")
print(f"Requests: {len(reqs)} rows")
rids = [r['request_id'] for r in reqs]
dup_rids = [k for k, v in Counter(rids).items() if v > 1]
print(f"Duplicate request_ids: {dup_rids}")

# 4. Images
fields, imgs = check_csv("images.csv")
print(f"Images: {len(imgs)} rows")
for img in imgs:
    path = os.path.join(dataset_dir, "media", "images", f"{img['image_id']}.png")
    exists = os.path.exists(path)
    if not exists:
        print(f"WARNING: Image file missing: {path}")

# 5. Check missing amount events vs images
missing_amt_event_ids = {r['event_id'] for r in missing_amounts}
img_event_ids = {r['related_event_id'] for r in imgs}
print(f"Missing amount event IDs match image related_event_ids exactly? {missing_amt_event_ids == img_event_ids}")

# 6. Messages
fields, msgs = check_csv("messages.csv")
print(f"Messages: {len(msgs)} rows")
mids = [r['message_id'] for r in msgs]
dup_mids = [k for k, v in Counter(mids).items() if v > 1]
print(f"Duplicate message_ids: {dup_mids}")
msg_rel_events = [r['related_event_id'] for r in msgs if r['related_event_id'].strip()]
unknown_rel_events = [e for e in msg_rel_events if e not in set(eids)]
print(f"Message related_event_ids not in financial_events: {unknown_rel_events}")

# 7. Payment options
fields, opts = check_csv("request_payment_options.csv")
print(f"Payment options: {len(opts)} rows")
pids = [r['payment_option_id'] for r in opts]
dup_pids = [k for k, v in Counter(pids).items() if v > 1]
print(f"Duplicate payment_option_ids: {dup_pids}")
opt_req_ids = [r['request_id'] for r in opts]
all_known_reqs = set(rids).union({r['request_id'] for r in check_csv("sample_requests.csv")[1]})
unknown_opt_reqs = [r for r in opt_req_ids if r not in all_known_reqs]
print(f"Payment option request_ids not in requests/samples: {unknown_opt_reqs}")

# 8. Currencies across files
currencies_in_profiles = set(r['home_currency'] for r in profiles)
currencies_in_events = set(r['currency'] for r in events)
currencies_in_rates_from = set(r['from_currency'] for r in check_csv("exchange_rates.csv")[1])
currencies_in_rates_to = set(r['to_currency'] for r in check_csv("exchange_rates.csv")[1])
print(f"Currencies in profiles: {currencies_in_profiles}")
print(f"Currencies in events: {currencies_in_events}")
print(f"Currencies in rates: from={currencies_in_rates_from}, to={currencies_in_rates_to}")

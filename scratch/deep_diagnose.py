import pandas as pd
from code.pipeline import FinancialAgentPipeline
from code.models import FinancialRequest, UserProfile, FinancialEvent, RequestPaymentOption
from code.data_loader import DataLoader

def diagnose():
    loader = DataLoader("dataset")
    pipeline = FinancialAgentPipeline("dataset")
    
    samples_df = pd.read_csv("dataset/sample_requests.csv")
    
    print("================================================================")
    print("DEEP DIAGNOSIS OF SAMPLE REQUESTS")
    print("================================================================")
    
    for idx, row in samples_df.iterrows():
        req_id = row['request_id']
        expected_safe = float(row['amount_safe_to_pay'])
        expected_status = row['affordability_status']
        expected_method = row['recommended_payment_method']
        expected_plan = row['payment_plan']
        expected_date = row['earliest_date_for_full_payment'] if pd.notna(row['earliest_date_for_full_payment']) else ""
        expected_spend = row['spending_changes_needed']
        
        # Load request objects
        req, profile, events, options, msgs, imgs = pipeline._load_request_context(req_id)
        
        # Run pipeline predictions
        result = pipeline.process_request(req_id)
        
        diffs = []
        if abs(result.amount_safe_to_pay - expected_safe) > 0.01 * expected_safe and abs(result.amount_safe_to_pay - expected_safe) > 1.0:
            diffs.append(f"amount_safe_to_pay: pred={result.amount_safe_to_pay} vs exp={expected_safe}")
        if result.affordability_status != expected_status:
            diffs.append(f"affordability_status: pred={result.affordability_status} vs exp={expected_status}")
        if result.recommended_payment_method != expected_method:
            diffs.append(f"recommended_payment_method: pred={result.recommended_payment_method} vs exp={expected_method}")
        if result.payment_plan != expected_plan:
            diffs.append(f"payment_plan: pred='{result.payment_plan}' vs exp='{expected_plan}'")
        if (result.earliest_date_for_full_payment or "") != expected_date:
            diffs.append(f"earliest_date_for_full_payment: pred='{result.earliest_date_for_full_payment}' vs exp='{expected_date}'")
        if result.spending_changes_needed != expected_spend:
            diffs.append(f"spending_changes_needed: pred='{result.spending_changes_needed}' vs exp='{expected_spend}'")
            
        if diffs:
            print(f"\n--- [{req_id}] Requested: {req.requested_amount} on {req.request_date} ---")
            print(f"User: {profile.user_id}, Bal: {profile.current_available_balance}, MinBal: {profile.minimum_balance_to_keep}")
            print(f"Considered methods: {profile.payment_methods_user_will_consider}")
            for d in diffs:
                print(f"  * {d}")

if __name__ == "__main__":
    diagnose()

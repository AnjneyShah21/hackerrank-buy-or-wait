"""
Main orchestrator entry point for the Buy or Wait? solution.
Executes data loading, evidence extraction, baseline forecasting,
payment planning, constraint ranking, invariant validation, and output generation.
"""

import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from code.config import OUTPUT_CSV
from code.currency import CurrencyConverter
from code.data_loader import build_dataset_index, get_request_context
from code.decision_engine import DecisionEngine
from code.evidence import EvidenceManager
from code.financial_engine import FinancialEngine
from code.forecast import CashFlowForecaster
from code.image_extractor import ImageExtractor
from code.message_interpreter import MessageInterpreter
from code.models import FinancialEvent, OutputRecord
from code.output_writer import OutputWriter
from code.payment_planner import PaymentPlanner
from code.validator import OutputValidator


def main():
    """Main execution pipeline processing dataset/requests.csv into dataset/output.csv."""
    print("=== HackerRank Orchestrate: Buy or Wait? ===")
    print("1. Loading dataset and indexing cross-file relationships...")

    index = build_dataset_index()
    print(
        f"   Loaded: {len(index.profiles)} profiles, {len(index.events_by_id)} events, "
        f"{len(index.exchange_rates)} rates, {len(index.requests)} requests."
    )

    print("2. Initializing engines & extracting unstructured evidence...")
    converter = CurrencyConverter(index.exchange_rates)
    evidence_mgr = EvidenceManager()
    img_extractor = ImageExtractor()
    msg_interpreter = MessageInterpreter()
    decision_engine = DecisionEngine()
    validator = OutputValidator()
    writer = OutputWriter()

    # Process image facts
    img_records = list(index.images_by_event.values())
    img_facts = img_extractor.process_all_images(img_records)
    evidence_mgr.add_facts(img_facts)

    # Process message facts
    all_msgs = []
    for msgs in index.messages_by_user.values():
        all_msgs.extend(msgs)
    msg_facts = msg_interpreter.process_all_messages(all_msgs)
    evidence_mgr.add_facts(msg_facts)

    forecaster = CashFlowForecaster(converter, evidence_mgr)
    fin_engine = FinancialEngine(forecaster)
    planner = PaymentPlanner(forecaster)

    print(f"   Extracted: {len(img_facts)} image facts, {len(msg_facts)} message facts.")

    print("3. Evaluating 250 financial requests...")
    output_records = []

    for req in index.requests:
        uctx, options = get_request_context(req, index)
        profile = uctx.profile if uctx else None

        # Apply evidence facts to user events
        user_events = index.events_by_user.get(req.user_id, [])
        enriched_events = []
        for ev in user_events:
            ev_copy = FinancialEvent(**ev.__dict__)
            ev_enriched = evidence_mgr.apply_evidence_to_event(ev_copy)
            enriched_events.append(ev_enriched)

        # Calculate baseline metrics
        amount_safe_to_pay = fin_engine.compute_amount_safe_to_pay(
            profile, enriched_events, req
        )
        earliest_date = fin_engine.compute_earliest_date_for_full_payment(
            profile, enriched_events, req
        )

        # Generate candidates
        candidates = planner.generate_candidate_plans(
            profile=profile,
            events=enriched_events,
            request=req,
            options=options,
            amount_safe_to_pay=amount_safe_to_pay,
            earliest_date_for_full_payment=earliest_date,
        )

        # Rank safe candidates
        best_plan = decision_engine.rank_plans(candidates, req)

        # Formulate decision
        decision = decision_engine.make_decision(
            request=req,
            profile=profile,
            amount_safe_to_pay=amount_safe_to_pay,
            earliest_date_for_full_payment=earliest_date,
            best_plan=best_plan,
        )

        # Assert explanation consistency
        decision_engine.assert_explanation_consistency(decision)

        # Build OutputRecord
        out_rec = OutputWriter.decision_to_record(decision)
        output_records.append(out_rec)

    print("4. Validating output records against contract invariants...")
    is_valid, errors = validator.validate_all(output_records, index.requests)
    if not is_valid:
        print(f"   [ERROR] Contract validation failed with {len(errors)} errors:")
        for err in errors[:10]:
            print(f"     - {err}")
        sys.exit(1)
    else:
        print("   [OK] All 250 output records passed schema & invariant validation!")

    print(f"5. Writing predictions to {OUTPUT_CSV}...")
    writer.write_output(output_records, OUTPUT_CSV)
    print(f"   [SUCCESS] Successfully written {len(output_records)} rows to {OUTPUT_CSV}!")


if __name__ == "__main__":
    main()

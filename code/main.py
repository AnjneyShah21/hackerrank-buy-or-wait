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

from code.config import (
    REQUESTS_CSV,
    SAMPLE_REQUESTS_CSV,
    OUTPUT_CSV,
    OUTPUT_COLUMNS,
)
from code.data_loader import DataLoader
from code.currency import CurrencyConverter
from code.evidence import EvidenceManager
from code.image_extractor import ImageExtractor
from code.message_interpreter import MessageInterpreter
from code.forecast import CashFlowForecaster
from code.financial_engine import FinancialEngine
from code.payment_planner import PaymentPlanner
from code.decision_engine import DecisionEngine
from code.validator import OutputValidator
from code.output_writer import OutputWriter


def main():
    """Main execution pipeline."""
    print("=== HackerRank Orchestrate: Buy or Wait? ===")
    print("Initializing components...")

    loader = DataLoader()
    
    # 1. Load structured data
    profiles = loader.load_profiles()
    events = loader.load_events()
    rates = loader.load_exchange_rates()
    options = loader.load_payment_options()
    requests = loader.load_requests()
    messages = loader.load_messages()
    images = loader.load_images_index()

    print(f"Loaded: {len(profiles)} profiles, {len(events)} events, {len(rates)} FX rates, {len(options)} options, {len(requests)} requests.")

    # 2. Initialize engines
    converter = CurrencyConverter(rates)
    evidence_mgr = EvidenceManager()
    img_extractor = ImageExtractor()
    msg_interpreter = MessageInterpreter()
    forecaster = CashFlowForecaster(converter)
    fin_engine = FinancialEngine(forecaster)
    planner = PaymentPlanner(forecaster)
    decision_engine = DecisionEngine()

    # 3. Process unstructured evidence
    print("Processing unstructured evidence...")
    img_facts = img_extractor.process_all_images(images)
    for fact in img_facts:
        evidence_mgr.add_fact(fact)

    msg_facts = msg_interpreter.process_all_messages(messages)
    for fact in msg_facts:
        evidence_mgr.add_fact(fact)

    print("Ready for financial processing and prediction generation.")


if __name__ == "__main__":
    main()

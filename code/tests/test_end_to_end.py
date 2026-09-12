"""
End-to-end integration tests on sample requests from dataset/sample_requests.csv.
Verifies full pipeline execution, decision formulation, explanation consistency,
and schema validation.
"""

import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from code.currency import CurrencyConverter
from code.data_loader import build_dataset_index, get_request_context
from code.decision_engine import DecisionEngine
from code.evidence import EvidenceManager
from code.financial_engine import FinancialEngine
from code.forecast import CashFlowForecaster
from code.image_extractor import ImageExtractor
from code.message_interpreter import MessageInterpreter
from code.models import FinancialEvent, FinancialRequest, OutputRecord
from code.payment_planner import PaymentPlanner
from code.validator import OutputValidator


class TestEndToEndPipeline(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.index = build_dataset_index()
        cls.converter = CurrencyConverter(cls.index.exchange_rates)
        cls.evidence_mgr = EvidenceManager()
        cls.img_extractor = ImageExtractor()
        cls.msg_interpreter = MessageInterpreter()

        # Process unstructured evidence
        img_facts = cls.img_extractor.process_all_images(list(cls.index.images_by_event.values()))
        cls.evidence_mgr.add_facts(img_facts)

        msg_list = []
        for msgs in cls.index.messages_by_user.values():
            msg_list.extend(msgs)
        msg_facts = cls.msg_interpreter.process_all_messages(msg_list)
        cls.evidence_mgr.add_facts(msg_facts)

        cls.forecaster = CashFlowForecaster(cls.converter)
        cls.fin_engine = FinancialEngine(cls.forecaster)
        cls.planner = PaymentPlanner(cls.forecaster)
        cls.decision_engine = DecisionEngine()
        cls.validator = OutputValidator()

    def process_single_request(self, request: FinancialRequest):
        uctx, options = get_request_context(request, self.index)
        self.assertIsNotNone(uctx, f"No profile found for user {request.user_id}")
        profile = uctx.profile

        # Apply evidence to events (copy events to avoid mutating global index state)
        enriched_events = []
        for ev in uctx.events:
            ev_copy = FinancialEvent(**ev.__dict__)
            ev_enriched = self.evidence_mgr.apply_evidence_to_event(ev_copy)
            enriched_events.append(ev_enriched)

        # Baseline metrics
        amount_safe_to_pay = self.fin_engine.compute_amount_safe_to_pay(profile, enriched_events, request)
        earliest_date_for_full_payment = self.fin_engine.compute_earliest_date_for_full_payment(profile, enriched_events, request)

        # Generate candidates
        candidates = self.planner.generate_candidate_plans(
            profile=profile,
            events=enriched_events,
            request=request,
            options=options,
            amount_safe_to_pay=amount_safe_to_pay,
            earliest_date_for_full_payment=earliest_date_for_full_payment,
        )

        # Rank candidates
        best_plan = self.decision_engine.rank_plans(candidates, request)

        # Formulate decision
        decision = self.decision_engine.make_decision(
            request=request,
            profile=profile,
            amount_safe_to_pay=amount_safe_to_pay,
            earliest_date_for_full_payment=earliest_date_for_full_payment,
            best_plan=best_plan,
        )

        # Check explanation consistency
        self.decision_engine.assert_explanation_consistency(decision)

        # Convert to OutputRecord and validate schema
        out_rec = OutputRecord(
            request_id=decision.request_id,
            amount_safe_to_pay=str(decision.amount_safe_to_pay),
            affordability_status=decision.affordability_status,
            recommended_payment_method=decision.recommended_payment_method,
            payment_plan=decision.payment_plan,
            earliest_date_for_full_payment=decision.earliest_date_for_full_payment,
            spending_changes_needed=decision.spending_changes_needed,
            decision_explanation=decision.decision_explanation,
        )

        is_valid, err_msg = self.validator.validate_row(out_rec, request)
        self.assertTrue(is_valid, f"Validation failed for request {request.request_id}: {err_msg}")

        return decision

    def test_sample_requests_e2e(self):
        """Processes first 25 evaluation requests end-to-end."""
        sample_reqs = self.index.requests[:25]
        self.assertEqual(len(sample_reqs), 25)

        for req in sample_reqs:
            decision = self.process_single_request(req)
            self.assertIn(decision.affordability_status, [
                "affordable_now", "affordable_with_plan", "affordable_later", "not_affordable"
            ])
            self.assertIn(decision.recommended_payment_method, [
                "full_payment", "partial_payment", "installments", "wait", "not_recommended"
            ])

    def test_full_dataset_250_requests_e2e(self):
        """Processes all 250 evaluation requests end-to-end."""
        self.assertEqual(len(self.index.requests), 250)
        decisions = []
        for req in self.index.requests:
            d = self.process_single_request(req)
            decisions.append(d)

        self.assertEqual(len(decisions), 250)


if __name__ == "__main__":
    unittest.main(verbosity=2)

"""
Evidence management and conflict resolution module.
Coordinates extracted facts from images and messages.
"""

from typing import Dict, List, Optional
from code.models import ExtractedFact, FinancialEvent


class EvidenceManager:
    """Stores structured evidence and provides conflict resolution."""

    def __init__(self):
        # Key: related_event_id -> List[ExtractedFact]
        self.facts_by_event: Dict[str, List[ExtractedFact]] = {}
        # Key: user_id -> List[ExtractedFact]
        self.facts_by_user: Dict[str, List[ExtractedFact]] = {}
        # Key: request_id -> List[ExtractedFact]
        self.facts_by_request: Dict[str, List[ExtractedFact]] = {}

    def add_fact(self, fact: ExtractedFact):
        """Registers a structured fact."""
        if fact.related_event_id:
            if fact.related_event_id not in self.facts_by_event:
                self.facts_by_event[fact.related_event_id] = []
            self.facts_by_event[fact.related_event_id].append(fact)

        if fact.user_id not in self.facts_by_user:
            self.facts_by_user[fact.user_id] = []
        self.facts_by_user[fact.user_id].append(fact)

        if fact.request_id:
            if fact.request_id not in self.facts_by_request:
                self.facts_by_request[fact.request_id] = []
            self.facts_by_request[fact.request_id].append(fact)

    def apply_evidence_to_event(self, event: FinancialEvent) -> FinancialEvent:
        """
        Applies extracted facts to mutate or enrich a financial event,
        following strict conflict resolution precedence:
        1. Explicit cancellation / settlement / amendment
        2. Newer record from same source
        3. Settled event over estimate
        4. Financially safer interpretation
        """
        facts = self.facts_by_event.get(event.event_id, [])
        if not facts:
            return event

        for fact in facts:
            if fact.extracted_amount is not None:
                # If original amount is None, fill it directly
                if event.amount is None:
                    event.amount = fact.extracted_amount
                else:
                    # Explicit amendment overrides
                    event.amount = fact.extracted_amount

            if fact.extracted_date:
                event.settlement_date = fact.extracted_date

            if fact.status_override:
                event.status = fact.status_override

            if fact.percentage_change is not None and event.amount is not None:
                event.amount = event.amount * (1.0 + fact.percentage_change / 100.0)

        return event

    def get_user_facts(self, user_id: str) -> List[ExtractedFact]:
        """Returns all facts associated with a user."""
        return self.facts_by_user.get(user_id, [])

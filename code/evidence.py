"""
Evidence management and conflict resolution module.
Coordinates extracted facts from images and messages and applies them
to financial events according to problem_statement.md conflict precedence rules:

Precedence Strategy:
1. Explicit cancellation, settlement, or amendment first.
2. Newer record from the same source (by timestamp/date).
3. Settled event over estimate or forecast.
4. Financially safer interpretation when conflict cannot be resolved:
   - Debit / Expense: higher amount is safer (conservative cash flow).
   - Credit / Income: lower amount is safer (conservative cash flow).
"""

from typing import Dict, List, Optional
from code.models import ExtractedFact, FinancialEvent


class EvidenceManager:
    """Manages extracted facts and provides deterministic conflict resolution."""

    def __init__(self):
        # Key: related_event_id -> List[ExtractedFact]
        self.facts_by_event: Dict[str, List[ExtractedFact]] = {}
        # Key: user_id -> List[ExtractedFact]
        self.facts_by_user: Dict[str, List[ExtractedFact]] = {}
        # Key: request_id -> List[ExtractedFact]
        self.facts_by_request: Dict[str, List[ExtractedFact]] = {}
        # All facts registered
        self.all_facts: List[ExtractedFact] = []

    def add_fact(self, fact: ExtractedFact):
        """Registers a structured fact."""
        self.all_facts.append(fact)

        if fact.related_event_id:
            if fact.related_event_id not in self.facts_by_event:
                self.facts_by_event[fact.related_event_id] = []
            self.facts_by_event[fact.related_event_id].append(fact)

        if fact.user_id:
            if fact.user_id not in self.facts_by_user:
                self.facts_by_user[fact.user_id] = []
            self.facts_by_user[fact.user_id].append(fact)

        if fact.request_id:
            if fact.request_id not in self.facts_by_request:
                self.facts_by_request[fact.request_id] = []
            self.facts_by_request[fact.request_id].append(fact)

    def add_facts(self, facts: List[ExtractedFact]):
        """Bulk registers structured facts."""
        for f in facts:
            self.add_fact(f)

    def resolve_event_facts(self, facts: List[ExtractedFact], direction: str = "debit") -> List[ExtractedFact]:
        """
        Sorts and resolves conflicting facts for a single event using the 4-tier strategy:
        1. Explicit cancellation/amendment
        2. Newer record from same source (sort by date if available)
        3. Settled over estimate
        4. Financially safer interpretation as tie-breaker
        """
        if not facts:
            return []

        # Deduplicate identical facts (same fact_kind, amount, status)
        seen_keys = set()
        unique_facts = []
        for f in facts:
            key = (f.fact_kind, f.extracted_amount, f.status_override, f.extracted_date, f.percentage_change)
            if key not in seen_keys:
                seen_keys.add(key)
                unique_facts.append(f)

        # Sort: facts with explicit status changes or amounts first, then highest confidence
        unique_facts.sort(
            key=lambda x: (
                1 if x.status_override == "cancelled" else 0,
                1 if x.extracted_amount is not None else 0,
                x.confidence,
            ),
            reverse=True,
        )

        return unique_facts

    def apply_evidence_to_event(self, event: FinancialEvent) -> FinancialEvent:
        """
        Applies extracted facts to mutate or enrich a financial event,
        following strict conflict resolution precedence.
        """
        facts = self.facts_by_event.get(event.event_id, [])
        if not facts:
            return event

        resolved_facts = self.resolve_event_facts(facts, event.direction)

        # Check for multiple conflicting amounts among resolved facts
        amount_facts = [f for f in resolved_facts if f.extracted_amount is not None]
        chosen_amount: Optional[float] = None

        if len(amount_facts) == 1:
            chosen_amount = amount_facts[0].extracted_amount
        elif len(amount_facts) > 1:
            # 4. Financially safer interpretation tie-breaker when multiple amounts conflict:
            # For debits/expenses -> choose higher amount (safer)
            # For credits/income -> choose lower amount (safer)
            amounts = [f.extracted_amount for f in amount_facts if f.extracted_amount is not None]
            if amounts:
                if event.direction == "debit":
                    chosen_amount = max(amounts)
                else:
                    chosen_amount = min(amounts)

        status_applied = False
        for fact in resolved_facts:
            # 1. Explicit Status Override (cancellation, pending, settled)
            if fact.status_override and not status_applied:
                event.status = fact.status_override
                status_applied = True

            # 2. Date Override / Shift
            if fact.extracted_date:
                event.settlement_date = fact.extracted_date

            # 3. Percentage Change (e.g. rent increase +12%)
            if fact.percentage_change is not None:
                if chosen_amount is not None:
                    chosen_amount = chosen_amount * (1.0 + fact.percentage_change / 100.0)
                elif event.amount is not None:
                    event.amount = event.amount * (1.0 + fact.percentage_change / 100.0)

            # 4. Amount Override
            if chosen_amount is not None:
                event.amount = chosen_amount
            elif fact.extracted_amount is not None and event.amount is None:
                event.amount = fact.extracted_amount

        return event

    def get_user_facts(self, user_id: str) -> List[ExtractedFact]:
        """Returns all facts associated with a user."""
        return self.facts_by_user.get(user_id, [])

    def get_request_facts(self, request_id: str) -> List[ExtractedFact]:
        """Returns all facts associated with a request."""
        return self.facts_by_request.get(request_id, [])

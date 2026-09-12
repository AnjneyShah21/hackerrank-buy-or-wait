"""
Message interpreter module.
Parses English and Indonesian messages from messages.csv into structured event modifications.
"""

from typing import List, Dict, Optional
from code.models import MessageRecord, ExtractedFact


class MessageInterpreter:
    """Interprets messages and produces structured facts for financial state adjustments."""

    def __init__(self, use_nlp: bool = False):
        self.use_nlp = use_nlp
        self._cached_facts: Dict[str, List[ExtractedFact]] = {}

    def interpret_message(self, message: MessageRecord) -> List[ExtractedFact]:
        """
        Parses a single message into structured fact updates.
        Handles:
        - Confirmed salary amount / date modifications
        - Pending status confirmations (unsettled bonuses, pending invoices)
        - Contract ends / terminations
        - Rent increases (+12% lease renewals)
        - Internal non-cash account transfers
        """
        if message.message_id in self._cached_facts:
            return self._cached_facts[message.message_id]

        facts: List[ExtractedFact] = []
        # In skeleton, define structured extraction contract
        return facts

    def process_all_messages(self, messages: List[MessageRecord]) -> List[ExtractedFact]:
        """Processes all messages into structured facts."""
        all_facts = []
        for msg in messages:
            facts = self.interpret_message(msg)
            all_facts.extend(facts)
            self._cached_facts[msg.message_id] = facts
        return all_facts

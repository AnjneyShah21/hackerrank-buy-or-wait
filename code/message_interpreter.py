"""
Message interpreter module.
Parses messages from messages.csv (English and Indonesian) into structured facts.
Enforces relevance filtering, fact extraction, and prompt injection sanitization.
"""

import re
from typing import Dict, List, Optional
from code.models import ExtractedFact, MessageRecord
from code.image_extractor import sanitize_untrusted_text


# Keywords that signal financial relevance in message text
RELEVANCE_KEYWORDS = [
    # English
    "salary", "pay", "payroll", "bonus", "rent", "lease", "contract",
    "refund", "reversal", "charge", "pending", "settled", "cancelled",
    "cancel", "ended", "reduced", "increased", "increase", "resumes",
    "proceeds", "investment", "invoice", "payment", "due",
    # Indonesian
    "gaji", "bonus", "sewa", "pembayaran", "kontrak", "selesai",
    "dibatalkan", "ditunda", "investasi", "tagihan", "dana",
]


class MessageInterpreter:
    """Interprets messages into structured financial facts with prompt injection defense."""

    def __init__(self, use_nlp: bool = False):
        self.use_nlp = use_nlp
        self._cached_facts: Dict[str, List[ExtractedFact]] = {}

    def is_message_relevant(self, message: MessageRecord) -> bool:
        """Determines if a message contains financial facts relevant to cash flow."""
        text = message.message_text.lower()
        # Message linked to an event is always relevant
        if message.related_event_id:
            return True
        return any(kw in text for kw in RELEVANCE_KEYWORDS)

    def interpret_message(self, message: MessageRecord) -> List[ExtractedFact]:
        """
        Parses a single message into structured facts.
        Extracts:
        - Rent increases (% change, e.g. "increases monthly rent by 12%")
        - Salary changes, temporary pay, new start salary, date shifts
        - Unsettled / pending bonuses & refunds (marked status="pending")
        - Contract ends / terminations (marked status="cancelled")
        - Explicit cancellations / reversals
        - Prompt injection sanitization
        """
        mid = message.message_id
        if mid in self._cached_facts:
            return self._cached_facts[mid]

        facts: List[ExtractedFact] = []

        if not self.is_message_relevant(message):
            self._cached_facts[mid] = []
            return []

        # Sanitize prompt injection first
        raw_text = message.message_text
        clean_text = sanitize_untrusted_text(raw_text)
        text_lower = clean_text.lower()

        # 1. Check for Lease / Rent Increase (% change)
        rent_match = re.search(r"increases\s+monthly\s+rent\s+by\s+(\d+(?:\.\d+)?)%", text_lower)
        if rent_match:
            pct = float(rent_match.group(1))
            facts.append(ExtractedFact(
                fact_id=f"fact_{mid}_rent",
                source_type="message",
                source_id=mid,
                user_id=message.user_id,
                related_event_id=message.related_event_id,
                request_id=message.request_id,
                fact_kind="lease_increase",
                percentage_change=pct,
                confidence=1.0,
                provenance=f"Rent increase +{pct}% extracted from {mid}",
            ))

        # 2. Check for Salary / Pay Changes
        # Salary increase to X: "salary has increased to EUR 1188"
        sal_inc = re.search(r"salary\s+has\s+increased\s+to\s+([A-Z]{3})\s+([\d,\.]+)", clean_text, re.IGNORECASE)
        if sal_inc:
            curr, amt_str = sal_inc.group(1).upper(), sal_inc.group(2).replace(",", "").rstrip(".")
            try:
                facts.append(ExtractedFact(
                    fact_id=f"fact_{mid}_sal_inc",
                    source_type="message",
                    source_id=mid,
                    user_id=message.user_id,
                    related_event_id=message.related_event_id,
                    request_id=message.request_id,
                    fact_kind="salary_update",
                    extracted_amount=float(amt_str),
                    extracted_currency=curr,
                    confidence=1.0,
                    provenance=f"Salary increase to {curr} {amt_str} from {mid}",
                ))
            except ValueError:
                pass

        # Temporary reduced pay: "temporary monthly pay is EUR 1750.32" / "reduced to USD 1731.60"
        temp_pay = re.search(r"(?:temporary\s+monthly\s+pay\s+is|reduced\s+to)\s+([A-Z]{3})\s+([\d,\.]+)", clean_text, re.IGNORECASE)
        if temp_pay and not sal_inc:
            curr, amt_str = temp_pay.group(1).upper(), temp_pay.group(2).replace(",", "").rstrip(".")
            try:
                facts.append(ExtractedFact(
                    fact_id=f"fact_{mid}_temp_pay",
                    source_type="message",
                    source_id=mid,
                    user_id=message.user_id,
                    related_event_id=message.related_event_id,
                    request_id=message.request_id,
                    fact_kind="salary_update",
                    extracted_amount=float(amt_str),
                    extracted_currency=curr,
                    confidence=1.0,
                    provenance=f"Temporary/reduced salary {curr} {amt_str} from {mid}",
                ))
            except ValueError:
                pass

        # Date shift: "confirmed salary is now expected on 2025-05-23"
        date_shift = re.search(r"(?:expected|confirmed)\s+on\s+(\d{4}-\d{2}-\d{2})", text_lower)
        if date_shift:
            new_date = date_shift.group(1)
            facts.append(ExtractedFact(
                fact_id=f"fact_{mid}_date_shift",
                source_type="message",
                source_id=mid,
                user_id=message.user_id,
                related_event_id=message.related_event_id,
                request_id=message.request_id,
                fact_kind="date_shift",
                extracted_date=new_date,
                confidence=1.0,
                provenance=f"Salary date shifted to {new_date} from {mid}",
            ))

        # 3. Contract Ended / Terminated (No off-season income)
        if "contract has ended" in text_lower or "contract ended" in text_lower or "record has ended" in text_lower or "kontrak selesai" in text_lower:
            facts.append(ExtractedFact(
                fact_id=f"fact_{mid}_contract_ended",
                source_type="message",
                source_id=mid,
                user_id=message.user_id,
                related_event_id=message.related_event_id,
                request_id=message.request_id,
                fact_kind="contract_ended",
                status_override="cancelled",
                extracted_amount=0.0,
                confidence=1.0,
                provenance=f"Contract ended status extracted from {mid}",
            ))

        # 4. Unsettled / Pending Bonus / Pending Refund
        # "bonus is still subject to the final performance review" or "menunggu hasil akhir"
        if "subject to the final performance review" in text_lower or "menunggu hasil akhir" in text_lower or "bonus is still pending" in text_lower:
            facts.append(ExtractedFact(
                fact_id=f"fact_{mid}_unsettled_bonus",
                source_type="message",
                source_id=mid,
                user_id=message.user_id,
                related_event_id=message.related_event_id,
                request_id=message.request_id,
                fact_kind="unsettled_bonus",
                status_override="pending",
                confidence=1.0,
                provenance=f"Unsettled bonus ignored from cash flow in {mid}",
            ))

        # "refund has been initiated but has not reached your account" or "refund is still processing"
        if "has not reached your account" in text_lower or "still processing" in text_lower or "still pending" in text_lower:
            facts.append(ExtractedFact(
                fact_id=f"fact_{mid}_unsettled_payout",
                source_type="message",
                source_id=mid,
                user_id=message.user_id,
                related_event_id=message.related_event_id,
                request_id=message.request_id,
                fact_kind="unsettled_payout",
                status_override="pending",
                confidence=1.0,
                provenance=f"Unsettled payout/refund pending in {mid}",
            ))

        # 5. Explicit Cancellation / Reversal
        if "cancelled" in text_lower or "canceled" in text_lower or "dibatalkan" in text_lower:
            facts.append(ExtractedFact(
                fact_id=f"fact_{mid}_cancel",
                source_type="message",
                source_id=mid,
                user_id=message.user_id,
                related_event_id=message.related_event_id,
                request_id=message.request_id,
                fact_kind="cancellation",
                status_override="cancelled",
                confidence=1.0,
                provenance=f"Explicit cancellation in {mid}",
            ))

        # 6. Generic Amended Amount (e.g. "amended to 500" or "updated amount: 1200")
        amt_amend = re.search(r"(?:amended\s+to|updated\s+amount\s*:?)\s*([A-Z]{3})?\s*([\d,\.]+)", clean_text, re.IGNORECASE)
        if amt_amend and not sal_inc and not temp_pay:
            curr = amt_amend.group(1).upper() if amt_amend.group(1) else None
            amt = float(amt_amend.group(2).replace(",", ""))
            facts.append(ExtractedFact(
                fact_id=f"fact_{mid}_amt_amend",
                source_type="message",
                source_id=mid,
                user_id=message.user_id,
                related_event_id=message.related_event_id,
                request_id=message.request_id,
                fact_kind="amount_override",
                extracted_amount=amt,
                extracted_currency=curr,
                confidence=1.0,
                provenance=f"Amended amount {amt} extracted from {mid}",
            ))

        self._cached_facts[mid] = facts
        return facts

    def process_all_messages(self, messages: List[MessageRecord]) -> List[ExtractedFact]:
        """Processes all messages into structured facts."""
        all_facts = []
        for msg in messages:
            facts = self.interpret_message(msg)
            all_facts.extend(facts)
        return all_facts

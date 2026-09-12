"""
Data models and typed structures for the Buy or Wait? system.
"""

from dataclasses import dataclass, field
from datetime import date
from typing import List, Optional, Set, Dict, Any


@dataclass
class UserProfile:
    """Represents a user's financial profile from financial_profiles.csv."""
    user_id: str
    home_currency: str
    current_available_balance: float
    minimum_balance_to_keep: float
    financial_priorities: List[str] = field(default_factory=list)
    expense_categories_to_protect: Set[str] = field(default_factory=set)
    expense_categories_user_is_willing_to_reduce: Set[str] = field(default_factory=set)
    expense_categories_user_is_willing_to_stop: Set[str] = field(default_factory=set)
    payment_methods_user_will_consider: Set[str] = field(default_factory=set)
    max_installment_months: Optional[int] = None


@dataclass
class FinancialEvent:
    """Represents a transaction/event from financial_events.csv."""
    event_id: str
    user_id: str
    event_type: str  # expense, subscription, income, debt_payment, etc.
    description: str
    category: str
    direction: str  # debit, credit, non_cash
    amount: Optional[float]  # May be None initially if extracted from image
    currency: str
    event_date: str  # YYYY-MM-DD
    settlement_date: str  # YYYY-MM-DD
    status: str  # settled, pending, scheduled, cancelled, failed, unrealized
    linked_event_id: Optional[str] = None
    flexibility: str = "fixed"  # fixed, reducible, stoppable, reducible_or_stoppable
    minimum_allowed_amount: Optional[float] = None
    is_recurring: bool = False
    cadence_days: Optional[int] = None


@dataclass
class ExchangeRate:
    """Represents a dated currency conversion rate."""
    rate_date: str  # YYYY-MM-DD
    from_currency: str
    to_currency: str
    rate: float


@dataclass
class RequestPaymentOption:
    """Represents a provider/seller payment offer from request_payment_options.csv."""
    payment_option_id: str
    request_id: str
    payment_method: str  # full_payment, installments
    payment_amount: float
    number_of_payments: int
    first_payment_date: str  # YYYY-MM-DD
    payment_frequency_days: Optional[int] = None
    financing_fee: float = 0.0
    total_payable_amount: float = 0.0


@dataclass
class FinancialRequest:
    """Represents an evaluation request from requests.csv."""
    request_id: str
    user_id: str
    request_date: str  # YYYY-MM-DD
    request_type: str
    requested_amount: float
    desired_completion_date: str  # YYYY-MM-DD
    allows_partial_payment: bool
    request_text: str


@dataclass
class MessageRecord:
    """Represents a message from messages.csv."""
    message_id: str
    user_id: str
    request_id: Optional[str]
    related_event_id: Optional[str]
    sent_at: str  # ISO-8601
    source_type: str  # employer, service_provider, financial_service, bank, merchant
    message_text: str


@dataclass
class ImageRecord:
    """Represents an image mapping from images.csv."""
    image_id: str
    user_id: str
    request_id: str
    related_event_id: str
    file_path: Optional[str] = None


@dataclass
class ExtractedFact:
    """Structured fact extracted from unstructured image or message."""
    fact_id: str
    source_type: str  # 'image' or 'message'
    source_id: str  # image_id or message_id
    user_id: str
    related_event_id: Optional[str] = None
    request_id: Optional[str] = None
    fact_kind: str = "amount_override"  # amount_override, date_override, status_change, lease_increase, etc.
    extracted_amount: Optional[float] = None
    extracted_currency: Optional[str] = None
    extracted_date: Optional[str] = None
    percentage_change: Optional[float] = None
    status_override: Optional[str] = None
    confidence: float = 1.0
    provenance: str = ""


@dataclass
class CandidatePlan:
    """Represents an evaluated candidate payment schedule."""
    method: str  # full_payment, partial_payment, installments, wait, not_recommended
    affordability_status: str  # affordable_now, affordable_with_plan, affordable_later, not_affordable
    payments: List[tuple] = field(default_factory=list)  # List of (date_str, amount)
    payment_plan_str: str = "none"
    earliest_date_for_full_payment: str = ""
    spending_changes: List[str] = field(default_factory=list)  # List of "stop:id" or "reduce_to:id:amt"
    spending_changes_str: str = "none"
    total_payable: float = 0.0
    completion_date: str = ""
    payment_option_id: Optional[str] = None
    is_safe: bool = False
    min_projected_balance: float = 0.0
    rejection_reason: Optional[str] = None


@dataclass
class DecisionResult:
    """Final decision for a request."""
    request_id: str
    amount_safe_to_pay: float
    affordability_status: str
    recommended_payment_method: str
    payment_plan: str
    earliest_date_for_full_payment: str
    spending_changes_needed: str
    decision_explanation: str
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class OutputRecord:
    """Represents a single row matching output.csv schema."""
    request_id: str
    amount_safe_to_pay: str
    affordability_status: str
    recommended_payment_method: str
    payment_plan: str
    earliest_date_for_full_payment: str
    spending_changes_needed: str
    decision_explanation: str

    def to_csv_dict(self) -> Dict[str, str]:
        return {
            "request_id": self.request_id,
            "amount_safe_to_pay": self.amount_safe_to_pay,
            "affordability_status": self.affordability_status,
            "recommended_payment_method": self.recommended_payment_method,
            "payment_plan": self.payment_plan,
            "earliest_date_for_full_payment": self.earliest_date_for_full_payment,
            "spending_changes_needed": self.spending_changes_needed,
            "decision_explanation": self.decision_explanation,
        }

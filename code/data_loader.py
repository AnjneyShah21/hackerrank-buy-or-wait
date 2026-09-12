"""
Data loader module for reading and parsing all CSV files into typed domain models.
"""

import csv
from pathlib import Path
from typing import Dict, List, Optional

from code.config import (
    FINANCIAL_EVENTS_CSV,
    FINANCIAL_PROFILES_CSV,
    EXCHANGE_RATES_CSV,
    REQUEST_PAYMENT_OPTIONS_CSV,
    REQUESTS_CSV,
    SAMPLE_REQUESTS_CSV,
    MESSAGES_CSV,
    IMAGES_CSV,
    IMAGES_DIR,
)
from code.models import (
    UserProfile,
    FinancialEvent,
    ExchangeRate,
    RequestPaymentOption,
    FinancialRequest,
    MessageRecord,
    ImageRecord,
)


def parse_pipe_set(val: Optional[str]) -> set:
    """Helper to parse a pipe-separated string into a set of non-empty strings."""
    if not val or not val.strip():
        return set()
    return {item.strip() for item in val.strip().split("|") if item.strip()}


def parse_pipe_list(val: Optional[str]) -> List[str]:
    """Helper to parse a pipe-separated string into a list of non-empty strings."""
    if not val or not val.strip():
        return []
    return [item.strip() for item in val.strip().split("|") if item.strip()]


class DataLoader:
    """Loads and indexes dataset CSVs."""

    def __init__(self, data_dir: Optional[Path] = None):
        self.data_dir = data_dir

    def load_profiles(self, path: Path = FINANCIAL_PROFILES_CSV) -> Dict[str, UserProfile]:
        """Loads financial_profiles.csv keyed by user_id."""
        profiles = {}
        with open(path, mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                uid = row["user_id"].strip()
                max_inst = int(row["max_installment_months"]) if row["max_installment_months"].strip() else None
                profiles[uid] = UserProfile(
                    user_id=uid,
                    home_currency=row["home_currency"].strip(),
                    current_available_balance=float(row["current_available_balance"]),
                    minimum_balance_to_keep=float(row["minimum_balance_to_keep"]),
                    financial_priorities=parse_pipe_list(row.get("financial_priorities")),
                    expense_categories_to_protect=parse_pipe_set(row.get("expense_categories_to_protect")),
                    expense_categories_user_is_willing_to_reduce=parse_pipe_set(row.get("expense_categories_user_is_willing_to_reduce")),
                    expense_categories_user_is_willing_to_stop=parse_pipe_set(row.get("expense_categories_user_is_willing_to_stop")),
                    payment_methods_user_will_consider=parse_pipe_set(row.get("payment_methods_user_will_consider")),
                    max_installment_months=max_inst,
                )
        return profiles

    def load_events(self, path: Path = FINANCIAL_EVENTS_CSV) -> List[FinancialEvent]:
        """Loads all transactions from financial_events.csv."""
        events = []
        with open(path, mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                amt_str = row["amount"].strip()
                amt = float(amt_str) if amt_str else None
                
                min_amt_str = row["minimum_allowed_amount"].strip()
                min_amt = float(min_amt_str) if min_amt_str else None
                
                settlement = row["settlement_date"].strip() if row["settlement_date"].strip() else row["event_date"].strip()
                linked = row["linked_event_id"].strip() if row.get("linked_event_id") and row["linked_event_id"].strip() else None

                events.append(FinancialEvent(
                    event_id=row["event_id"].strip(),
                    user_id=row["user_id"].strip(),
                    event_type=row["event_type"].strip(),
                    description=row["description"].strip(),
                    category=row["category"].strip(),
                    direction=row["direction"].strip(),
                    amount=amt,
                    currency=row["currency"].strip(),
                    event_date=row["event_date"].strip(),
                    settlement_date=settlement,
                    status=row["status"].strip(),
                    linked_event_id=linked,
                    flexibility=row.get("flexibility", "fixed").strip() or "fixed",
                    minimum_allowed_amount=min_amt,
                ))
        return events

    def load_exchange_rates(self, path: Path = EXCHANGE_RATES_CSV) -> List[ExchangeRate]:
        """Loads exchange_rates.csv."""
        rates = []
        with open(path, mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                rates.append(ExchangeRate(
                    rate_date=row["rate_date"].strip(),
                    from_currency=row["from_currency"].strip(),
                    to_currency=row["to_currency"].strip(),
                    rate=float(row["rate"]),
                ))
        return rates

    def load_payment_options(self, path: Path = REQUEST_PAYMENT_OPTIONS_CSV) -> List[RequestPaymentOption]:
        """Loads request_payment_options.csv."""
        options = []
        with open(path, mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                freq_str = row["payment_frequency_days"].strip()
                freq = int(freq_str) if freq_str else None
                options.append(RequestPaymentOption(
                    payment_option_id=row["payment_option_id"].strip(),
                    request_id=row["request_id"].strip(),
                    payment_method=row["payment_method"].strip(),
                    payment_amount=float(row["payment_amount"]),
                    number_of_payments=int(row["number_of_payments"]),
                    first_payment_date=row["first_payment_date"].strip(),
                    payment_frequency_days=freq,
                    financing_fee=float(row.get("financing_fee", 0.0) or 0.0),
                    total_payable_amount=float(row["total_payable_amount"]),
                ))
        return options

    def load_requests(self, path: Path = REQUESTS_CSV) -> List[FinancialRequest]:
        """Loads evaluation requests from requests.csv."""
        requests = []
        with open(path, mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                allows_partial = row["allows_partial_payment"].strip().lower() in ("true", "1", "yes")
                requests.append(FinancialRequest(
                    request_id=row["request_id"].strip(),
                    user_id=row["user_id"].strip(),
                    request_date=row["request_date"].strip(),
                    request_type=row["request_type"].strip(),
                    requested_amount=float(row["requested_amount"]),
                    desired_completion_date=row["desired_completion_date"].strip(),
                    allows_partial_payment=allows_partial,
                    request_text=row["request_text"].strip(),
                ))
        return requests

    def load_sample_requests(self, path: Path = SAMPLE_REQUESTS_CSV) -> List[Dict[str, str]]:
        """Loads sample requests with ground truth labels."""
        samples = []
        with open(path, mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                samples.append(dict(row))
        return samples

    def load_messages(self, path: Path = MESSAGES_CSV) -> List[MessageRecord]:
        """Loads messages.csv."""
        messages = []
        with open(path, mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                req_id = row["request_id"].strip() if row.get("request_id") and row["request_id"].strip() else None
                rel_ev = row["related_event_id"].strip() if row.get("related_event_id") and row["related_event_id"].strip() else None
                messages.append(MessageRecord(
                    message_id=row["message_id"].strip(),
                    user_id=row["user_id"].strip(),
                    request_id=req_id,
                    related_event_id=rel_ev,
                    sent_at=row["sent_at"].strip(),
                    source_type=row["source_type"].strip(),
                    message_text=row["message_text"].strip(),
                ))
        return messages

    def load_images_index(self, path: Path = IMAGES_CSV) -> List[ImageRecord]:
        """Loads images.csv."""
        records = []
        with open(path, mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                img_id = row["image_id"].strip()
                file_path = str(IMAGES_DIR / f"{img_id}.png")
                records.append(ImageRecord(
                    image_id=img_id,
                    user_id=row["user_id"].strip(),
                    request_id=row["request_id"].strip(),
                    related_event_id=row["related_event_id"].strip(),
                    file_path=file_path,
                ))
        return records

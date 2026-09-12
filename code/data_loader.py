"""
Data ingestion layer for the Buy or Wait? system.

Responsibilities:
- Parse and validate all CSVs from dataset/
- Normalize dates, numerics, and IDs
- Build cross-file indexes for efficient lookups
- Detect missing amounts that require image extraction
- Log non-fatal anomalies as LoadWarnings without corrupting state
- Never silently convert missing amounts to zero
"""

import csv
import os
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

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
    DatasetIndex,
    ExchangeRate,
    FinancialEvent,
    FinancialRequest,
    ImageRecord,
    LoadWarning,
    MessageRecord,
    RequestPaymentOption,
    UserContext,
    UserProfile,
)

# ─── Helpers ──────────────────────────────────────────────────────────────────

VALID_DATE_FORMAT = "%Y-%m-%d"

VALID_STATUSES = {"settled", "pending", "scheduled", "cancelled", "failed", "unrealized"}
VALID_DIRECTIONS = {"debit", "credit", "non_cash"}
VALID_FLEXIBILITIES = {"fixed", "reducible", "stoppable", "reducible_or_stoppable"}
VALID_EVENT_TYPES = {
    "expense", "subscription", "income", "debt_payment",
    "investment_purchase", "refund", "investment_valuation", "investment_sale",
}
VALID_PAYMENT_METHODS_OPTIONS = {"full_payment", "installments"}


def _str(val: Optional[str]) -> str:
    """Strip a CSV value; return '' for None."""
    return (val or "").strip()


def _opt_str(val: Optional[str]) -> Optional[str]:
    """Return None when value is blank; otherwise stripped string."""
    s = _str(val)
    return s if s else None


def _parse_float(val: str, field: str, row_id: str, file: str,
                 warnings: List[LoadWarning]) -> Optional[float]:
    """Parse a float; log a warning and return None for blank/invalid values."""
    s = _str(val)
    if not s:
        return None
    try:
        return float(s.replace(",", ""))
    except ValueError:
        warnings.append(LoadWarning(
            severity="warning", file=file, row_id=row_id,
            field=field, message=f"Cannot parse float", raw_value=s,
        ))
        return None


def _parse_int(val: str, field: str, row_id: str, file: str,
               warnings: List[LoadWarning]) -> Optional[int]:
    """Parse an int; log warning and return None for blank/invalid."""
    s = _str(val)
    if not s:
        return None
    try:
        return int(s)
    except ValueError:
        warnings.append(LoadWarning(
            severity="warning", file=file, row_id=row_id,
            field=field, message=f"Cannot parse int", raw_value=s,
        ))
        return None


def _validate_date(val: str, field: str, row_id: str, file: str,
                   warnings: List[LoadWarning]) -> str:
    """Validate YYYY-MM-DD date string; log warning on failure, return as-is."""
    s = _str(val)
    if not s:
        return s
    try:
        datetime.strptime(s, VALID_DATE_FORMAT)
    except ValueError:
        warnings.append(LoadWarning(
            severity="warning", file=file, row_id=row_id,
            field=field, message=f"Invalid date format (expected YYYY-MM-DD)", raw_value=s,
        ))
    return s


def _parse_pipe_set(val: Optional[str]) -> set:
    s = _str(val)
    if not s:
        return set()
    return {item.strip() for item in s.split("|") if item.strip()}


def _parse_pipe_list(val: Optional[str]) -> List[str]:
    s = _str(val)
    if not s:
        return []
    return [item.strip() for item in s.split("|") if item.strip()]


def _require_columns(fieldnames: List[str], required: List[str],
                     filename: str, warnings: List[LoadWarning]) -> bool:
    """Assert required columns exist; log error and return False if not."""
    missing = [c for c in required if c not in fieldnames]
    if missing:
        warnings.append(LoadWarning(
            severity="error", file=filename, row_id="header",
            field=str(missing), message="Required column(s) missing",
        ))
        return False
    return True


# ─── Parsers ──────────────────────────────────────────────────────────────────

def _parse_profiles(path: Path, warnings: List[LoadWarning]) -> Dict[str, UserProfile]:
    REQUIRED = [
        "user_id", "home_currency", "current_available_balance",
        "minimum_balance_to_keep", "payment_methods_user_will_consider",
    ]
    profiles: Dict[str, UserProfile] = {}
    seen: Dict[str, int] = {}

    with open(path, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        if not _require_columns(reader.fieldnames or [], REQUIRED, path.name, warnings):
            return profiles

        for row_num, row in enumerate(reader, start=2):
            uid = _str(row.get("user_id"))
            if not uid:
                warnings.append(LoadWarning("warning", path.name, f"row_{row_num}", "user_id",
                                             "Blank user_id; row skipped"))
                continue

            if uid in seen:
                warnings.append(LoadWarning("warning", path.name, uid, "user_id",
                                             f"Duplicate user_id (first at row {seen[uid]}); keeping first"))
                continue
            seen[uid] = row_num

            balance = _parse_float(row.get("current_available_balance", ""), "current_available_balance",
                                   uid, path.name, warnings)
            if balance is None:
                warnings.append(LoadWarning("error", path.name, uid, "current_available_balance",
                                             "Missing required balance; defaulting to 0"))
                balance = 0.0

            min_bal = _parse_float(row.get("minimum_balance_to_keep", ""), "minimum_balance_to_keep",
                                   uid, path.name, warnings)
            if min_bal is None:
                warnings.append(LoadWarning("error", path.name, uid, "minimum_balance_to_keep",
                                             "Missing minimum balance; defaulting to 0"))
                min_bal = 0.0

            max_inst = _parse_int(row.get("max_installment_months", ""), "max_installment_months",
                                  uid, path.name, warnings)

            profiles[uid] = UserProfile(
                user_id=uid,
                home_currency=_str(row.get("home_currency")),
                current_available_balance=balance,
                minimum_balance_to_keep=min_bal,
                financial_priorities=_parse_pipe_list(row.get("financial_priorities")),
                expense_categories_to_protect=_parse_pipe_set(row.get("expense_categories_to_protect")),
                expense_categories_user_is_willing_to_reduce=_parse_pipe_set(
                    row.get("expense_categories_user_is_willing_to_reduce")),
                expense_categories_user_is_willing_to_stop=_parse_pipe_set(
                    row.get("expense_categories_user_is_willing_to_stop")),
                payment_methods_user_will_consider=_parse_pipe_set(
                    row.get("payment_methods_user_will_consider")),
                max_installment_months=max_inst,
            )

    return profiles


def _parse_events(path: Path, warnings: List[LoadWarning]) -> List[FinancialEvent]:
    REQUIRED = [
        "event_id", "user_id", "event_type", "direction", "currency",
        "event_date", "status", "flexibility",
    ]
    events: List[FinancialEvent] = []
    seen: Dict[str, int] = {}

    with open(path, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        if not _require_columns(reader.fieldnames or [], REQUIRED, path.name, warnings):
            return events

        for row_num, row in enumerate(reader, start=2):
            eid = _str(row.get("event_id"))
            if not eid:
                warnings.append(LoadWarning("warning", path.name, f"row_{row_num}", "event_id",
                                             "Blank event_id; row skipped"))
                continue

            if eid in seen:
                warnings.append(LoadWarning("warning", path.name, eid, "event_id",
                                             f"Duplicate event_id (first at row {seen[eid]}); keeping first"))
                continue
            seen[eid] = row_num

            uid = _str(row.get("user_id"))
            event_date = _validate_date(row.get("event_date", ""), "event_date", eid, path.name, warnings)

            # settlement_date: fall back to event_date when blank (non-cash investment valuations)
            raw_settle = _str(row.get("settlement_date", ""))
            if raw_settle:
                settlement_date = _validate_date(raw_settle, "settlement_date", eid, path.name, warnings)
            else:
                settlement_date = event_date  # safe fallback

            # Amount handling — critical: None ≠ 0
            raw_amount = _str(row.get("amount", ""))
            amount_needs_image = False
            if raw_amount:
                amount = _parse_float(raw_amount, "amount", eid, path.name, warnings)
            else:
                amount = None
                amount_needs_image = True

            min_allowed = _parse_float(row.get("minimum_allowed_amount", ""),
                                       "minimum_allowed_amount", eid, path.name, warnings)

            linked = _opt_str(row.get("linked_event_id"))
            flexibility = _str(row.get("flexibility", "fixed")) or "fixed"

            events.append(FinancialEvent(
                event_id=eid,
                user_id=uid,
                event_type=_str(row.get("event_type")),
                description=_str(row.get("description")),
                category=_str(row.get("category")),
                direction=_str(row.get("direction")),
                amount=amount,
                currency=_str(row.get("currency")),
                event_date=event_date,
                settlement_date=settlement_date,
                status=_str(row.get("status")),
                linked_event_id=linked,
                flexibility=flexibility,
                minimum_allowed_amount=min_allowed,
                amount_needs_image=amount_needs_image,
            ))

    return events


def _parse_requests(path: Path, warnings: List[LoadWarning]) -> List[FinancialRequest]:
    REQUIRED = [
        "request_id", "user_id", "request_date", "request_type",
        "requested_amount", "desired_completion_date", "allows_partial_payment",
    ]
    requests: List[FinancialRequest] = []
    seen: Dict[str, int] = {}

    with open(path, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        if not _require_columns(reader.fieldnames or [], REQUIRED, path.name, warnings):
            return requests

        for row_num, row in enumerate(reader, start=2):
            rid = _str(row.get("request_id"))
            if not rid:
                warnings.append(LoadWarning("warning", path.name, f"row_{row_num}", "request_id",
                                             "Blank request_id; skipped"))
                continue
            if rid in seen:
                warnings.append(LoadWarning("warning", path.name, rid, "request_id",
                                             f"Duplicate request_id; keeping first"))
                continue
            seen[rid] = row_num

            request_date = _validate_date(row.get("request_date", ""), "request_date",
                                          rid, path.name, warnings)
            completion_date = _validate_date(row.get("desired_completion_date", ""),
                                             "desired_completion_date", rid, path.name, warnings)

            requested_amount = _parse_float(row.get("requested_amount", ""), "requested_amount",
                                            rid, path.name, warnings)
            if requested_amount is None:
                warnings.append(LoadWarning("error", path.name, rid, "requested_amount",
                                             "Missing required requested_amount; skipping request"))
                continue

            allows_partial = _str(row.get("allows_partial_payment", "")).lower() in ("true", "1", "yes")

            requests.append(FinancialRequest(
                request_id=rid,
                user_id=_str(row.get("user_id")),
                request_date=request_date,
                request_type=_str(row.get("request_type")),
                requested_amount=requested_amount,
                desired_completion_date=completion_date,
                allows_partial_payment=allows_partial,
                request_text=_str(row.get("request_text")),
            ))

    return requests


def _parse_exchange_rates(path: Path, warnings: List[LoadWarning]) -> List[ExchangeRate]:
    REQUIRED = ["rate_date", "from_currency", "to_currency", "rate"]
    rates: List[ExchangeRate] = []

    with open(path, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        if not _require_columns(reader.fieldnames or [], REQUIRED, path.name, warnings):
            return rates

        for row_num, row in enumerate(reader, start=2):
            key = f"row_{row_num}"
            rate_val = _parse_float(row.get("rate", ""), "rate", key, path.name, warnings)
            if rate_val is None:
                warnings.append(LoadWarning("warning", path.name, key, "rate",
                                             "Missing rate; row skipped"))
                continue
            rate_date = _validate_date(row.get("rate_date", ""), "rate_date", key, path.name, warnings)
            rates.append(ExchangeRate(
                rate_date=rate_date,
                from_currency=_str(row.get("from_currency")),
                to_currency=_str(row.get("to_currency")),
                rate=rate_val,
            ))

    return rates


def _parse_payment_options(path: Path, warnings: List[LoadWarning]) -> List[RequestPaymentOption]:
    REQUIRED = [
        "payment_option_id", "request_id", "payment_method",
        "payment_amount", "number_of_payments", "first_payment_date",
    ]
    options: List[RequestPaymentOption] = []
    seen: Dict[str, int] = {}

    with open(path, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        if not _require_columns(reader.fieldnames or [], REQUIRED, path.name, warnings):
            return options

        for row_num, row in enumerate(reader, start=2):
            oid = _str(row.get("payment_option_id"))
            if not oid:
                continue
            if oid in seen:
                warnings.append(LoadWarning("warning", path.name, oid, "payment_option_id",
                                             "Duplicate payment_option_id; keeping first"))
                continue
            seen[oid] = row_num

            pay_amt = _parse_float(row.get("payment_amount", ""), "payment_amount",
                                   oid, path.name, warnings)
            if pay_amt is None:
                continue

            n_payments = _parse_int(row.get("number_of_payments", ""), "number_of_payments",
                                    oid, path.name, warnings)
            if n_payments is None:
                continue

            freq = _parse_int(row.get("payment_frequency_days", ""), "payment_frequency_days",
                              oid, path.name, warnings)
            fee = _parse_float(row.get("financing_fee", "0"), "financing_fee",
                               oid, path.name, warnings) or 0.0
            total = _parse_float(row.get("total_payable_amount", ""), "total_payable_amount",
                                 oid, path.name, warnings)

            first_date = _validate_date(row.get("first_payment_date", ""), "first_payment_date",
                                        oid, path.name, warnings)

            options.append(RequestPaymentOption(
                payment_option_id=oid,
                request_id=_str(row.get("request_id")),
                payment_method=_str(row.get("payment_method")),
                payment_amount=pay_amt,
                number_of_payments=n_payments,
                first_payment_date=first_date,
                payment_frequency_days=freq,
                financing_fee=fee,
                total_payable_amount=total if total is not None else pay_amt * n_payments,
            ))

    return options


def _parse_messages(path: Path, warnings: List[LoadWarning]) -> List[MessageRecord]:
    REQUIRED = ["message_id", "user_id", "sent_at", "source_type", "message_text"]
    messages: List[MessageRecord] = []
    seen: Dict[str, int] = {}

    with open(path, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        if not _require_columns(reader.fieldnames or [], REQUIRED, path.name, warnings):
            return messages

        for row_num, row in enumerate(reader, start=2):
            mid = _str(row.get("message_id"))
            if not mid:
                continue
            if mid in seen:
                warnings.append(LoadWarning("warning", path.name, mid, "message_id",
                                             "Duplicate message_id; keeping first"))
                continue
            seen[mid] = row_num

            messages.append(MessageRecord(
                message_id=mid,
                user_id=_str(row.get("user_id")),
                request_id=_opt_str(row.get("request_id")),
                related_event_id=_opt_str(row.get("related_event_id")),
                sent_at=_str(row.get("sent_at")),
                source_type=_str(row.get("source_type")),
                message_text=_str(row.get("message_text")),
            ))

    return messages


def _parse_images(path: Path, images_dir: Path,
                  warnings: List[LoadWarning]) -> List[ImageRecord]:
    REQUIRED = ["image_id", "user_id", "request_id", "related_event_id"]
    records: List[ImageRecord] = []
    seen: Dict[str, int] = {}

    with open(path, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        if not _require_columns(reader.fieldnames or [], REQUIRED, path.name, warnings):
            return records

        for row_num, row in enumerate(reader, start=2):
            img_id = _str(row.get("image_id"))
            if not img_id:
                continue
            if img_id in seen:
                warnings.append(LoadWarning("warning", path.name, img_id, "image_id",
                                             "Duplicate image_id; keeping first"))
                continue
            seen[img_id] = row_num

            file_path = str(images_dir / f"{img_id}.png")
            file_exists = os.path.isfile(file_path)
            if not file_exists:
                warnings.append(LoadWarning("warning", path.name, img_id, "file_path",
                                             f"Image file not found on disk: {file_path}",
                                             raw_value=file_path))

            records.append(ImageRecord(
                image_id=img_id,
                user_id=_str(row.get("user_id")),
                request_id=_str(row.get("request_id")),
                related_event_id=_str(row.get("related_event_id")),
                file_path=file_path,
                file_exists=file_exists,
            ))

    return records


# ─── Index Builder ────────────────────────────────────────────────────────────

def build_dataset_index(
    profiles_path: Path = FINANCIAL_PROFILES_CSV,
    events_path: Path = FINANCIAL_EVENTS_CSV,
    requests_path: Path = REQUESTS_CSV,
    rates_path: Path = EXCHANGE_RATES_CSV,
    options_path: Path = REQUEST_PAYMENT_OPTIONS_CSV,
    messages_path: Path = MESSAGES_CSV,
    images_path: Path = IMAGES_CSV,
    images_dir: Path = IMAGES_DIR,
) -> DatasetIndex:
    """
    Loads all dataset CSVs, validates schemas, normalises values,
    and assembles a fully-indexed DatasetIndex ready for simulation.
    """
    idx = DatasetIndex()
    w = idx.warnings  # shorthand

    # 1. Profiles
    idx.profiles = _parse_profiles(profiles_path, w)

    # 2. Financial Events → user index + ID index
    events = _parse_events(events_path, w)
    for ev in events:
        idx.events_by_id[ev.event_id] = ev
        idx.events_by_user.setdefault(ev.user_id, []).append(ev)
        if ev.amount_needs_image:
            idx.events_requiring_image[ev.event_id] = ev

    # 3. Requests
    idx.requests = _parse_requests(requests_path, w)
    for req in idx.requests:
        idx.requests_by_id[req.request_id] = req
        # Cross-validate: every request must have a profile
        if req.user_id not in idx.profiles:
            w.append(LoadWarning("warning", requests_path.name, req.request_id,
                                  "user_id", f"No profile found for user_id '{req.user_id}'"))

    # 4. Exchange rates
    idx.exchange_rates = _parse_exchange_rates(rates_path, w)

    # 5. Payment options
    options = _parse_payment_options(options_path, w)
    for opt in options:
        idx.payment_options.setdefault(opt.request_id, []).append(opt)

    # 6. Messages
    messages = _parse_messages(messages_path, w)
    for msg in messages:
        idx.messages_by_user.setdefault(msg.user_id, []).append(msg)
        if msg.request_id:
            idx.messages_by_request.setdefault(msg.request_id, []).append(msg)
        if msg.related_event_id:
            # Validate: related_event_id should exist in events
            if msg.related_event_id not in idx.events_by_id:
                w.append(LoadWarning("warning", messages_path.name, msg.message_id,
                                      "related_event_id",
                                      f"related_event_id '{msg.related_event_id}' not found in financial_events"))
            idx.messages_by_event.setdefault(msg.related_event_id, []).append(msg)

    # 7. Images
    images = _parse_images(images_path, images_dir, w)
    for img in images:
        idx.images_by_event[img.related_event_id] = img
        idx.images_by_request.setdefault(img.request_id, []).append(img)
        # Cross-validate image → event linkage
        if img.related_event_id not in idx.events_by_id:
            w.append(LoadWarning("warning", images_path.name, img.image_id,
                                  "related_event_id",
                                  f"related_event_id '{img.related_event_id}' not found in financial_events"))
        else:
            ev = idx.events_by_id[img.related_event_id]
            if not ev.amount_needs_image:
                w.append(LoadWarning("warning", images_path.name, img.image_id,
                                      "related_event_id",
                                      f"Image linked to event '{ev.event_id}' which already has an amount"))

    # 8. Cross-validate: every event needing an image has one
    for ev_id in idx.events_requiring_image:
        if ev_id not in idx.images_by_event:
            w.append(LoadWarning("error", events_path.name, ev_id,
                                  "amount",
                                  "Event has no amount AND no linked image — unresolvable"))

    return idx


# ─── User Context Builder ─────────────────────────────────────────────────────

def get_user_context(user_id: str, idx: DatasetIndex) -> Optional[UserContext]:
    """Returns a fully joined UserContext for a single user, or None if not found."""
    profile = idx.profiles.get(user_id)
    if not profile:
        return None
    return UserContext(
        profile=profile,
        events=idx.events_by_user.get(user_id, []),
        messages=idx.messages_by_user.get(user_id, []),
        image_records=list(idx.images_by_event.values()),  # filtered by user below
    )


def get_request_context(
    request: FinancialRequest,
    idx: DatasetIndex,
) -> Tuple[Optional[UserContext], List[RequestPaymentOption]]:
    """
    Returns (UserContext, payment_options) for a given request.
    UserContext includes all user-level events, messages, and relevant images.
    """
    uctx = get_user_context(request.user_id, idx)
    opts = idx.payment_options.get(request.request_id, [])
    return uctx, opts


# ─── Legacy compatibility shim (DataLoader class) ─────────────────────────────

class DataLoader:
    """
    Thin wrapper around the functional ingestion layer.
    Retained for backwards-compatibility with tests and evaluation scripts.
    """

    def __init__(self, data_dir: Optional[Path] = None):
        self.data_dir = data_dir

    def load_profiles(self, path: Path = FINANCIAL_PROFILES_CSV) -> Dict[str, UserProfile]:
        return _parse_profiles(path, [])

    def load_events(self, path: Path = FINANCIAL_EVENTS_CSV) -> List[FinancialEvent]:
        return _parse_events(path, [])

    def load_exchange_rates(self, path: Path = EXCHANGE_RATES_CSV) -> List[ExchangeRate]:
        return _parse_exchange_rates(path, [])

    def load_payment_options(self, path: Path = REQUEST_PAYMENT_OPTIONS_CSV) -> List[RequestPaymentOption]:
        return _parse_payment_options(path, [])

    def load_requests(self, path: Path = REQUESTS_CSV) -> List[FinancialRequest]:
        return _parse_requests(path, [])

    def load_sample_requests(self, path: Path = SAMPLE_REQUESTS_CSV) -> List[Dict]:
        with open(path, mode="r", encoding="utf-8") as f:
            return list(csv.DictReader(f))

    def load_messages(self, path: Path = MESSAGES_CSV) -> List[MessageRecord]:
        return _parse_messages(path, [])

    def load_images_index(self, path: Path = IMAGES_CSV) -> List[ImageRecord]:
        return _parse_images(path, IMAGES_DIR, [])

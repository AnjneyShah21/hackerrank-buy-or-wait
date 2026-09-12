"""
Comprehensive unit tests for the data ingestion layer.

Covers:
- Normal joins and indexing
- Missing fields
- Duplicate IDs
- Missing linked records
- Missing image files
- Missing amounts (None, never zero)
- Invalid dates
- Foreign currency events
- Empty datasets
- Real dataset loading and cross-validation
"""

import csv
import io
import os
import sys
import tempfile
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from code.data_loader import (
    DataLoader,
    _parse_events,
    _parse_images,
    _parse_messages,
    _parse_payment_options,
    _parse_profiles,
    _parse_requests,
    _parse_exchange_rates,
    build_dataset_index,
    get_user_context,
    get_request_context,
)
from code.config import (
    FINANCIAL_PROFILES_CSV,
    FINANCIAL_EVENTS_CSV,
    EXCHANGE_RATES_CSV,
    REQUEST_PAYMENT_OPTIONS_CSV,
    REQUESTS_CSV,
    SAMPLE_REQUESTS_CSV,
    MESSAGES_CSV,
    IMAGES_CSV,
    IMAGES_DIR,
)
from code.models import LoadWarning


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _write_csv(tmp_dir: str, filename: str, rows: list[dict], fieldnames: list[str]) -> Path:
    p = Path(tmp_dir) / filename
    with open(p, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)
    return p


# ─── Profiles ────────────────────────────────────────────────────────────────

class TestProfileParsing(unittest.TestCase):

    def _profile_csv(self, tmp, rows):
        fields = [
            "user_id", "home_currency", "current_available_balance",
            "minimum_balance_to_keep", "financial_priorities",
            "expense_categories_to_protect", "expense_categories_user_is_willing_to_reduce",
            "expense_categories_user_is_willing_to_stop",
            "payment_methods_user_will_consider", "max_installment_months",
        ]
        return _write_csv(tmp, "profiles.csv", rows, fields)

    def test_normal_profile_parse(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = self._profile_csv(tmp, [{
                "user_id": "u1", "home_currency": "INR",
                "current_available_balance": "50000",
                "minimum_balance_to_keep": "10000",
                "financial_priorities": "education|savings",
                "expense_categories_to_protect": "rent|groceries",
                "expense_categories_user_is_willing_to_reduce": "dining",
                "expense_categories_user_is_willing_to_stop": "streaming",
                "payment_methods_user_will_consider": "full_payment|installments",
                "max_installment_months": "6",
            }])
            warnings = []
            profiles = _parse_profiles(p, warnings)
            self.assertIn("u1", profiles)
            self.assertEqual(profiles["u1"].home_currency, "INR")
            self.assertEqual(profiles["u1"].current_available_balance, 50000.0)
            self.assertEqual(profiles["u1"].minimum_balance_to_keep, 10000.0)
            self.assertEqual(profiles["u1"].max_installment_months, 6)
            self.assertIn("rent", profiles["u1"].expense_categories_to_protect)
            self.assertIn("full_payment", profiles["u1"].payment_methods_user_will_consider)
            self.assertEqual(len(warnings), 0)

    def test_duplicate_user_id(self):
        with tempfile.TemporaryDirectory() as tmp:
            row = {
                "user_id": "u1", "home_currency": "EUR",
                "current_available_balance": "1000", "minimum_balance_to_keep": "500",
                "financial_priorities": "", "expense_categories_to_protect": "",
                "expense_categories_user_is_willing_to_reduce": "",
                "expense_categories_user_is_willing_to_stop": "",
                "payment_methods_user_will_consider": "full_payment",
                "max_installment_months": "",
            }
            p = self._profile_csv(tmp, [row, row])  # duplicate
            warnings = []
            profiles = _parse_profiles(p, warnings)
            self.assertEqual(len(profiles), 1)
            self.assertTrue(any("Duplicate" in w.message for w in warnings))

    def test_blank_user_id_skipped(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = self._profile_csv(tmp, [{
                "user_id": "", "home_currency": "USD",
                "current_available_balance": "1000", "minimum_balance_to_keep": "100",
                "financial_priorities": "", "expense_categories_to_protect": "",
                "expense_categories_user_is_willing_to_reduce": "",
                "expense_categories_user_is_willing_to_stop": "",
                "payment_methods_user_will_consider": "full_payment",
                "max_installment_months": "",
            }])
            warnings = []
            profiles = _parse_profiles(p, warnings)
            self.assertEqual(len(profiles), 0)
            self.assertTrue(any("Blank user_id" in w.message for w in warnings))

    def test_missing_balance_defaults_to_zero_with_warning(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = self._profile_csv(tmp, [{
                "user_id": "u2", "home_currency": "ZAR",
                "current_available_balance": "",  # blank
                "minimum_balance_to_keep": "1000",
                "financial_priorities": "", "expense_categories_to_protect": "",
                "expense_categories_user_is_willing_to_reduce": "",
                "expense_categories_user_is_willing_to_stop": "",
                "payment_methods_user_will_consider": "full_payment",
                "max_installment_months": "",
            }])
            warnings = []
            profiles = _parse_profiles(p, warnings)
            self.assertIn("u2", profiles)
            self.assertEqual(profiles["u2"].current_available_balance, 0.0)
            self.assertTrue(any("balance" in w.message.lower() for w in warnings))

    def test_empty_dataset(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = self._profile_csv(tmp, [])
            warnings = []
            profiles = _parse_profiles(p, warnings)
            self.assertEqual(len(profiles), 0)
            self.assertEqual(len(warnings), 0)

    def test_missing_required_column(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "bad.csv"
            with open(p, "w", newline="", encoding="utf-8") as f:
                f.write("user_id,home_currency\nu1,INR\n")
            warnings = []
            profiles = _parse_profiles(p, warnings)
            self.assertEqual(len(profiles), 0)
            self.assertTrue(any(w.severity == "error" for w in warnings))


# ─── Events ──────────────────────────────────────────────────────────────────

class TestEventParsing(unittest.TestCase):

    def _event_csv(self, tmp, rows):
        fields = [
            "event_id", "user_id", "event_type", "description", "category",
            "direction", "amount", "currency", "event_date", "settlement_date",
            "status", "linked_event_id", "flexibility", "minimum_allowed_amount",
        ]
        return _write_csv(tmp, "events.csv", rows, fields)

    def _base_row(self, **overrides):
        row = {
            "event_id": "e1", "user_id": "u1", "event_type": "expense",
            "description": "Rent", "category": "rent", "direction": "debit",
            "amount": "5000", "currency": "INR", "event_date": "2026-01-01",
            "settlement_date": "2026-01-01", "status": "settled",
            "linked_event_id": "", "flexibility": "fixed",
            "minimum_allowed_amount": "",
        }
        row.update(overrides)
        return row

    def test_normal_event_parse(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = self._event_csv(tmp, [self._base_row()])
            warnings = []
            events = _parse_events(p, warnings)
            self.assertEqual(len(events), 1)
            self.assertEqual(events[0].event_id, "e1")
            self.assertEqual(events[0].amount, 5000.0)
            self.assertFalse(events[0].amount_needs_image)
            self.assertEqual(len(warnings), 0)

    def test_missing_amount_is_none_not_zero(self):
        """Critical: blank amount must be None, never 0."""
        with tempfile.TemporaryDirectory() as tmp:
            p = self._event_csv(tmp, [self._base_row(amount="")])
            warnings = []
            events = _parse_events(p, warnings)
            self.assertEqual(len(events), 1)
            self.assertIsNone(events[0].amount)
            self.assertTrue(events[0].amount_needs_image)

    def test_missing_settlement_date_falls_back_to_event_date(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = self._event_csv(tmp, [self._base_row(settlement_date="")])
            warnings = []
            events = _parse_events(p, warnings)
            self.assertEqual(events[0].settlement_date, "2026-01-01")

    def test_invalid_date_logs_warning(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = self._event_csv(tmp, [self._base_row(event_date="not-a-date")])
            warnings = []
            events = _parse_events(p, warnings)
            self.assertEqual(len(events), 1)  # Row still loaded
            self.assertTrue(any("Invalid date" in w.message for w in warnings))

    def test_duplicate_event_id(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = self._event_csv(tmp, [self._base_row(), self._base_row(amount="9999")])
            warnings = []
            events = _parse_events(p, warnings)
            self.assertEqual(len(events), 1)
            self.assertEqual(events[0].amount, 5000.0)  # First one kept
            self.assertTrue(any("Duplicate" in w.message for w in warnings))

    def test_foreign_currency_event_preserved(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = self._event_csv(tmp, [self._base_row(currency="USD", amount="100")])
            warnings = []
            events = _parse_events(p, warnings)
            self.assertEqual(events[0].currency, "USD")
            self.assertEqual(events[0].amount, 100.0)

    def test_empty_events(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = self._event_csv(tmp, [])
            warnings = []
            events = _parse_events(p, warnings)
            self.assertEqual(len(events), 0)

    def test_reducible_flexibility_parsed(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = self._event_csv(tmp, [self._base_row(
                flexibility="reducible_or_stoppable",
                minimum_allowed_amount="2000",
            )])
            warnings = []
            events = _parse_events(p, warnings)
            self.assertEqual(events[0].flexibility, "reducible_or_stoppable")
            self.assertEqual(events[0].minimum_allowed_amount, 2000.0)


# ─── Requests ────────────────────────────────────────────────────────────────

class TestRequestParsing(unittest.TestCase):

    def _req_csv(self, tmp, rows):
        fields = [
            "request_id", "user_id", "request_date", "request_type",
            "requested_amount", "desired_completion_date",
            "allows_partial_payment", "request_text",
        ]
        return _write_csv(tmp, "reqs.csv", rows, fields)

    def _base_row(self, **overrides):
        row = {
            "request_id": "req_01", "user_id": "u1",
            "request_date": "2026-01-01", "request_type": "purchase",
            "requested_amount": "25000",
            "desired_completion_date": "2026-02-01",
            "allows_partial_payment": "true",
            "request_text": "Can I buy laptop?",
        }
        row.update(overrides)
        return row

    def test_normal_request(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = self._req_csv(tmp, [self._base_row()])
            warnings = []
            reqs = _parse_requests(p, warnings)
            self.assertEqual(len(reqs), 1)
            self.assertTrue(reqs[0].allows_partial_payment)
            self.assertEqual(reqs[0].requested_amount, 25000.0)

    def test_allows_partial_false(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = self._req_csv(tmp, [self._base_row(allows_partial_payment="false")])
            warnings = []
            reqs = _parse_requests(p, warnings)
            self.assertFalse(reqs[0].allows_partial_payment)

    def test_missing_requested_amount_skips_row(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = self._req_csv(tmp, [self._base_row(requested_amount="")])
            warnings = []
            reqs = _parse_requests(p, warnings)
            self.assertEqual(len(reqs), 0)
            self.assertTrue(any("requested_amount" in w.field for w in warnings))

    def test_duplicate_request_id(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = self._req_csv(tmp, [self._base_row(), self._base_row(requested_amount="99999")])
            warnings = []
            reqs = _parse_requests(p, warnings)
            self.assertEqual(len(reqs), 1)
            self.assertEqual(reqs[0].requested_amount, 25000.0)

    def test_invalid_date_logged(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = self._req_csv(tmp, [self._base_row(request_date="2026-13-99")])
            warnings = []
            reqs = _parse_requests(p, warnings)
            self.assertEqual(len(reqs), 1)
            self.assertTrue(any("Invalid date" in w.message for w in warnings))


# ─── Images ──────────────────────────────────────────────────────────────────

class TestImageParsing(unittest.TestCase):

    def _img_csv(self, tmp, rows):
        fields = ["image_id", "user_id", "request_id", "related_event_id"]
        return _write_csv(tmp, "images.csv", rows, fields)

    def test_image_file_found(self):
        with tempfile.TemporaryDirectory() as tmp:
            img_dir = Path(tmp) / "images"
            img_dir.mkdir()
            (img_dir / "image_01.png").touch()
            p = self._img_csv(tmp, [{
                "image_id": "image_01", "user_id": "u1",
                "request_id": "req_01", "related_event_id": "e1",
            }])
            warnings = []
            imgs = _parse_images(p, img_dir, warnings)
            self.assertTrue(imgs[0].file_exists)
            self.assertEqual(len(warnings), 0)

    def test_missing_image_file_warns(self):
        with tempfile.TemporaryDirectory() as tmp:
            img_dir = Path(tmp) / "images"
            img_dir.mkdir()
            # Do NOT create the png file
            p = self._img_csv(tmp, [{
                "image_id": "image_99", "user_id": "u1",
                "request_id": "req_01", "related_event_id": "e1",
            }])
            warnings = []
            imgs = _parse_images(p, img_dir, warnings)
            self.assertEqual(len(imgs), 1)
            self.assertFalse(imgs[0].file_exists)
            self.assertTrue(any("not found" in w.message for w in warnings))

    def test_empty_images(self):
        with tempfile.TemporaryDirectory() as tmp:
            img_dir = Path(tmp) / "images"
            img_dir.mkdir()
            p = self._img_csv(tmp, [])
            warnings = []
            imgs = _parse_images(p, img_dir, warnings)
            self.assertEqual(len(imgs), 0)


# ─── Exchange Rates ──────────────────────────────────────────────────────────

class TestExchangeRateParsing(unittest.TestCase):

    def _rate_csv(self, tmp, rows):
        fields = ["rate_date", "from_currency", "to_currency", "rate"]
        return _write_csv(tmp, "rates.csv", rows, fields)

    def test_normal_rate(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = self._rate_csv(tmp, [{
                "rate_date": "2026-01-15", "from_currency": "USD",
                "to_currency": "INR", "rate": "83.33",
            }])
            warnings = []
            rates = _parse_exchange_rates(p, warnings)
            self.assertEqual(len(rates), 1)
            self.assertAlmostEqual(rates[0].rate, 83.33)

    def test_missing_rate_skipped(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = self._rate_csv(tmp, [{
                "rate_date": "2026-01-15", "from_currency": "USD",
                "to_currency": "INR", "rate": "",
            }])
            warnings = []
            rates = _parse_exchange_rates(p, warnings)
            self.assertEqual(len(rates), 0)
            self.assertTrue(any("rate" in w.field for w in warnings))

    def test_empty_rates(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = self._rate_csv(tmp, [])
            warnings = []
            rates = _parse_exchange_rates(p, warnings)
            self.assertEqual(len(rates), 0)


# ─── Full Index & Cross-Joins ─────────────────────────────────────────────────

class TestDatasetIndex(unittest.TestCase):

    def test_real_dataset_builds_cleanly(self):
        """Integration test: build full index from real dataset."""
        idx = build_dataset_index()

        # Basic counts
        self.assertEqual(len(idx.profiles), 275)
        self.assertEqual(len(idx.requests), 250)
        self.assertGreater(len(idx.events_by_id), 25000)
        self.assertEqual(len(idx.exchange_rates), 134)

        # Every request has a profile
        for req in idx.requests:
            self.assertIn(req.user_id, idx.profiles,
                          f"Request {req.request_id} has no profile for {req.user_id}")

        # All 16 image-linked events exist
        self.assertEqual(len(idx.events_requiring_image), 16)
        for ev_id in idx.events_requiring_image:
            self.assertIn(ev_id, idx.images_by_event,
                          f"Event {ev_id} needs image but none found")

        # All 16 image files exist on disk
        for ev_id, img in idx.images_by_event.items():
            self.assertTrue(img.file_exists,
                            f"Image file missing for event {ev_id}: {img.file_path}")

        # No unresolvable events
        for w in idx.warnings:
            self.assertNotEqual(w.message, "Event has no amount AND no linked image — unresolvable",
                                f"Unresolvable event: {w.row_id}")

        print(f"\n[Integration] Warnings generated: {len(idx.warnings)}")
        for w in idx.warnings:
            print(f"  [{w.severity}] {w.file}::{w.row_id} — {w.message}")

    def test_user_context_join(self):
        """Verify UserContext assembles events and messages for a user."""
        idx = build_dataset_index()
        # user_01 appears in sample data
        ctx = get_user_context("user_01", idx)
        self.assertIsNotNone(ctx)
        self.assertEqual(ctx.profile.home_currency, "ZAR")
        self.assertGreater(len(ctx.events), 0)

    def test_unknown_user_context_returns_none(self):
        idx = build_dataset_index()
        ctx = get_user_context("user_nonexistent_xyz", idx)
        self.assertIsNone(ctx)

    def test_request_context_join(self):
        """Verify request context includes options and profile."""
        idx = build_dataset_index()
        req = idx.requests_by_id.get("request_26")
        self.assertIsNotNone(req)
        ctx, opts = get_request_context(req, idx)
        self.assertIsNotNone(ctx)
        self.assertGreater(len(opts), 0)

    def test_messages_indexed_by_request(self):
        idx = build_dataset_index()
        # Spot-check: request_02 has a message (message_01 links user_02)
        self.assertGreater(len(idx.messages_by_user.get("user_02", [])), 0)

    def test_events_amount_none_not_zero(self):
        """Critical invariant: image-linked events must have amount=None, not 0."""
        idx = build_dataset_index()
        for ev_id, ev in idx.events_requiring_image.items():
            self.assertIsNone(ev.amount,
                              f"Event {ev_id} should have amount=None, got {ev.amount}")
            self.assertTrue(ev.amount_needs_image)

    def test_payment_options_indexed_by_request(self):
        idx = build_dataset_index()
        # request_01 is in sample_requests, payment options cover requests 1-25 too
        # Use first real request
        first_req = idx.requests[0]
        opts = idx.payment_options.get(first_req.request_id, [])
        self.assertGreater(len(opts), 0,
                           f"No payment options for {first_req.request_id}")

    def test_no_duplicate_ids(self):
        idx = build_dataset_index()
        # All event IDs unique
        seen = set()
        for uid, evts in idx.events_by_user.items():
            for ev in evts:
                self.assertNotIn(ev.event_id, seen, f"Duplicate event: {ev.event_id}")
                seen.add(ev.event_id)

    def test_missing_linked_records_warned(self):
        """Messages referencing non-existent events generate warnings."""
        with tempfile.TemporaryDirectory() as tmp:
            img_dir = Path(tmp) / "images"
            img_dir.mkdir()

            # Minimal profiles
            prof_p = _write_csv(tmp, "profiles.csv", [{
                "user_id": "u1", "home_currency": "EUR",
                "current_available_balance": "1000",
                "minimum_balance_to_keep": "200",
                "financial_priorities": "",
                "expense_categories_to_protect": "",
                "expense_categories_user_is_willing_to_reduce": "",
                "expense_categories_user_is_willing_to_stop": "",
                "payment_methods_user_will_consider": "full_payment",
                "max_installment_months": "",
            }], ["user_id", "home_currency", "current_available_balance",
                 "minimum_balance_to_keep", "financial_priorities",
                 "expense_categories_to_protect",
                 "expense_categories_user_is_willing_to_reduce",
                 "expense_categories_user_is_willing_to_stop",
                 "payment_methods_user_will_consider", "max_installment_months"])

            events_p = _write_csv(tmp, "events.csv", [], [
                "event_id", "user_id", "event_type", "description", "category",
                "direction", "amount", "currency", "event_date", "settlement_date",
                "status", "linked_event_id", "flexibility", "minimum_allowed_amount",
            ])
            reqs_p = _write_csv(tmp, "requests.csv", [], [
                "request_id", "user_id", "request_date", "request_type",
                "requested_amount", "desired_completion_date",
                "allows_partial_payment", "request_text",
            ])
            rates_p = _write_csv(tmp, "rates.csv", [], [
                "rate_date", "from_currency", "to_currency", "rate",
            ])
            opts_p = _write_csv(tmp, "options.csv", [], [
                "payment_option_id", "request_id", "payment_method",
                "payment_amount", "number_of_payments", "first_payment_date",
                "payment_frequency_days", "financing_fee", "total_payable_amount",
            ])
            # Message referencing a nonexistent event
            msgs_p = _write_csv(tmp, "messages.csv", [{
                "message_id": "m1", "user_id": "u1", "request_id": "",
                "related_event_id": "nonexistent_event",
                "sent_at": "2026-01-01T10:00:00Z",
                "source_type": "employer",
                "message_text": "Your salary has been updated.",
            }], ["message_id", "user_id", "request_id", "related_event_id",
                 "sent_at", "source_type", "message_text"])
            imgs_p = _write_csv(tmp, "images.csv", [], [
                "image_id", "user_id", "request_id", "related_event_id",
            ])

            idx = build_dataset_index(
                profiles_path=prof_p, events_path=events_p, requests_path=reqs_p,
                rates_path=rates_p, options_path=opts_p, messages_path=msgs_p,
                images_path=imgs_p, images_dir=img_dir,
            )
            # Should warn about nonexistent linked event
            self.assertTrue(any("not found in financial_events" in w.message for w in idx.warnings))


# ─── DataLoader (compatibility shim) ─────────────────────────────────────────

class TestDataLoaderCompat(unittest.TestCase):

    def setUp(self):
        self.loader = DataLoader()

    def test_load_profiles_count(self):
        profiles = self.loader.load_profiles()
        self.assertEqual(len(profiles), 275)

    def test_load_events_count(self):
        events = self.loader.load_events()
        self.assertEqual(len(events), 25342)

    def test_load_requests_count(self):
        reqs = self.loader.load_requests()
        self.assertEqual(len(reqs), 250)

    def test_load_sample_requests_count(self):
        samples = self.loader.load_sample_requests()
        self.assertEqual(len(samples), 25)

    def test_load_exchange_rates_count(self):
        rates = self.loader.load_exchange_rates()
        self.assertEqual(len(rates), 134)

    def test_load_payment_options_count(self):
        opts = self.loader.load_payment_options()
        self.assertEqual(len(opts), 790)

    def test_load_messages_count(self):
        msgs = self.loader.load_messages()
        self.assertEqual(len(msgs), 215)

    def test_load_images_count(self):
        imgs = self.loader.load_images_index()
        self.assertEqual(len(imgs), 16)


if __name__ == "__main__":
    unittest.main(verbosity=2)

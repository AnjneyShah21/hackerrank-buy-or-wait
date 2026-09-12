"""
Comprehensive unit tests for OutputValidator.
Tests valid records as well as all invalid output failure scenarios and loud error reporting.
"""

import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from code.models import FinancialRequest, OutputRecord
from code.validator import OutputValidator


class TestOutputValidator(unittest.TestCase):

    def setUp(self):
        self.validator = OutputValidator()
        self.base_request = FinancialRequest(
            request_id="req_test_01",
            user_id="user_test",
            request_date="2026-01-01",
            request_type="purchase",
            requested_amount=20000.0,
            desired_completion_date="2026-03-01",
            allows_partial_payment=True,
            request_text="Can I buy laptop?",
        )
        self.base_record = OutputRecord(
            request_id="req_test_01",
            amount_safe_to_pay="20000.0",
            affordability_status="affordable_now",
            recommended_payment_method="full_payment",
            payment_plan="2026-01-01:20000",
            earliest_date_for_full_payment="2026-01-01",
            spending_changes_needed="none",
            decision_explanation="You can safely pay the full amount today.",
        )

    # 1. Valid Record
    def test_valid_record(self):
        is_valid, errors = self.validator.validate_row(self.base_record, self.base_request)
        self.assertTrue(is_valid, f"Unexpected validation errors: {errors}")
        self.assertEqual(len(errors), 0)

    # 2. Negative Amount Safe to Pay
    def test_amount_safe_to_pay_negative(self):
        rec = OutputRecord(**{**self.base_record.__dict__, "amount_safe_to_pay": "-500.0"})
        is_valid, errors = self.validator.validate_row(rec, self.base_request)
        self.assertFalse(is_valid)
        self.assertTrue(any("out of bounds" in e for e in errors))

    # 3. Amount Exceeding Requested Amount
    def test_amount_safe_to_pay_exceeds_requested(self):
        rec = OutputRecord(**{**self.base_record.__dict__, "amount_safe_to_pay": "25000.0"})
        is_valid, errors = self.validator.validate_row(rec, self.base_request)
        self.assertFalse(is_valid)
        self.assertTrue(any("out of bounds" in e for e in errors))

    # 4. Amount Safe to Pay NaN or Inf
    def test_amount_safe_to_pay_nan(self):
        rec = OutputRecord(**{**self.base_record.__dict__, "amount_safe_to_pay": "NaN"})
        is_valid, errors = self.validator.validate_row(rec, self.base_request)
        self.assertFalse(is_valid)
        self.assertTrue(any("NaN" in e for e in errors))

    # 5. Invalid Affordability Status
    def test_invalid_affordability_status(self):
        rec = OutputRecord(**{**self.base_record.__dict__, "affordability_status": "super_affordable"})
        is_valid, errors = self.validator.validate_row(rec, self.base_request)
        self.assertFalse(is_valid)
        self.assertTrue(any("Invalid affordability_status" in e for e in errors))

    # 6. Invalid Recommended Payment Method
    def test_invalid_recommended_payment_method(self):
        rec = OutputRecord(**{**self.base_record.__dict__, "recommended_payment_method": "credit_card"})
        is_valid, errors = self.validator.validate_row(rec, self.base_request)
        self.assertFalse(is_valid)
        self.assertTrue(any("Invalid recommended_payment_method" in e for e in errors))

    # 7. Payment Plan Not None for Not Recommended
    def test_payment_plan_not_none_for_not_recommended(self):
        rec = OutputRecord(
            request_id="req_test_01",
            amount_safe_to_pay="0.0",
            affordability_status="not_affordable",
            recommended_payment_method="not_recommended",
            payment_plan="2026-01-01:5000",  # Should be "none"
            earliest_date_for_full_payment="",
            spending_changes_needed="none",
            decision_explanation="Do not proceed with the request.",
        )
        is_valid, errors = self.validator.validate_row(rec, self.base_request)
        self.assertFalse(is_valid)
        self.assertTrue(any("payment_plan must be 'none'" in e for e in errors))

    # 8. Payment Plan None for Full Payment
    def test_payment_plan_none_for_full_payment(self):
        rec = OutputRecord(**{**self.base_record.__dict__, "payment_plan": "none"})
        is_valid, errors = self.validator.validate_row(rec, self.base_request)
        self.assertFalse(is_valid)
        self.assertTrue(any("payment_plan cannot be 'none'" in e for e in errors))

    # 9. Partial Payment Invalid Entry Count
    def test_partial_payment_invalid_count(self):
        rec = OutputRecord(
            request_id="req_test_01",
            amount_safe_to_pay="5000.0",
            affordability_status="affordable_with_plan",
            recommended_payment_method="partial_payment",
            payment_plan="2026-01-01:5000|2026-02-01:7500|2026-02-15:7500",  # 3 entries instead of 2
            earliest_date_for_full_payment="2026-02-01",
            spending_changes_needed="none",
            decision_explanation="Partial payment recommended.",
        )
        is_valid, errors = self.validator.validate_row(rec, self.base_request)
        self.assertFalse(is_valid)
        self.assertTrue(any("exactly 2 payments" in e for e in errors))

    # 10. Partial Payment Disallowed by Request
    def test_partial_payment_disallowed(self):
        req_no_partial = FinancialRequest(**{**self.base_request.__dict__, "allows_partial_payment": False})
        rec = OutputRecord(
            request_id="req_test_01",
            amount_safe_to_pay="5000.0",
            affordability_status="affordable_with_plan",
            recommended_payment_method="partial_payment",
            payment_plan="2026-01-01:5000|2026-02-01:15000",
            earliest_date_for_full_payment="2026-02-01",
            spending_changes_needed="none",
            decision_explanation="Partial payment recommended.",
        )
        is_valid, errors = self.validator.validate_row(rec, req_no_partial)
        self.assertFalse(is_valid)
        self.assertTrue(any("allows_partial_payment is False" in e for e in errors))

    # 11. Partial Payment Sum Mismatch
    def test_partial_payment_sum_mismatch(self):
        rec = OutputRecord(
            request_id="req_test_01",
            amount_safe_to_pay="5000.0",
            affordability_status="affordable_with_plan",
            recommended_payment_method="partial_payment",
            payment_plan="2026-01-01:5000|2026-02-01:10000",  # 5000 + 10000 = 15000 != 20000
            earliest_date_for_full_payment="2026-02-01",
            spending_changes_needed="none",
            decision_explanation="Partial payment recommended.",
        )
        is_valid, errors = self.validator.validate_row(rec, self.base_request)
        self.assertFalse(is_valid)
        self.assertTrue(any("sum to requested_amount" in e for e in errors))

    # 12. Partial Payment Misses Completion Date
    def test_partial_payment_misses_completion_date(self):
        rec = OutputRecord(
            request_id="req_test_01",
            amount_safe_to_pay="5000.0",
            affordability_status="affordable_with_plan",
            recommended_payment_method="partial_payment",
            payment_plan="2026-01-01:5000|2026-05-01:15000",  # May 01 is after desired completion date Mar 01
            earliest_date_for_full_payment="2026-05-01",
            spending_changes_needed="none",
            decision_explanation="Partial payment recommended.",
        )
        is_valid, errors = self.validator.validate_row(rec, self.base_request)
        self.assertFalse(is_valid)
        self.assertTrue(any("after desired_completion_date" in e for e in errors))

    # 13. Earliest Date Before Request Date
    def test_earliest_date_before_request_date(self):
        rec = OutputRecord(**{**self.base_record.__dict__, "earliest_date_for_full_payment": "2025-12-01"})
        is_valid, errors = self.validator.validate_row(rec, self.base_request)
        self.assertFalse(is_valid)
        self.assertTrue(any("before request_date" in e for e in errors))

    # 14. Affordable Now Date Mismatch
    def test_affordable_now_date_mismatch(self):
        rec = OutputRecord(**{**self.base_record.__dict__, "earliest_date_for_full_payment": "2026-02-01"})
        is_valid, errors = self.validator.validate_row(rec, self.base_request)
        self.assertFalse(is_valid)
        self.assertTrue(any("earliest_date_for_full_payment must equal request_date" in e for e in errors))

    # 15. Spending Changes Exceed Maximum Actions (4 actions)
    def test_spending_changes_exceed_max(self):
        rec = OutputRecord(
            **{**self.base_record.__dict__,
               "spending_changes_needed": "stop:e1|stop:e2|stop:e3|stop:e4"}
        )
        is_valid, errors = self.validator.validate_row(rec, self.base_request)
        self.assertFalse(is_valid)
        self.assertTrue(any("exceeds maximum of 3 actions" in e for e in errors))

    # 16. Spending Changes Duplicate Events
    def test_spending_changes_duplicate_events(self):
        rec = OutputRecord(
            **{**self.base_record.__dict__,
               "spending_changes_needed": "stop:e1|reduce_to:e1:100"}
        )
        is_valid, errors = self.validator.validate_row(rec, self.base_request)
        self.assertFalse(is_valid)
        self.assertTrue(any("Duplicate event_id" in e for e in errors))

    # 17. Decision Explanation Empty
    def test_decision_explanation_empty(self):
        rec = OutputRecord(**{**self.base_record.__dict__, "decision_explanation": "   "})
        is_valid, errors = self.validator.validate_row(rec, self.base_request)
        self.assertFalse(is_valid)
        self.assertTrue(any("empty" in e for e in errors))

    # 18. Decision Explanation Contradiction
    def test_decision_explanation_contradiction(self):
        rec = OutputRecord(
            request_id="req_test_01",
            amount_safe_to_pay="0.0",
            affordability_status="not_affordable",
            recommended_payment_method="not_recommended",
            payment_plan="none",
            earliest_date_for_full_payment="",
            spending_changes_needed="none",
            decision_explanation="You can safely pay the full amount today without any issue.",
        )
        is_valid, errors = self.validator.validate_row(rec, self.base_request)
        self.assertFalse(is_valid)
        self.assertTrue(any("contradicts" in e for e in errors))

    # 19. Dataset Missing Request IDs
    def test_dataset_missing_request_ids(self):
        req2 = FinancialRequest(**{**self.base_request.__dict__, "request_id": "req_test_02"})
        records = [self.base_record]  # Missing req_test_02 record
        is_valid, errors = self.validator.validate_all(records, [self.base_request, req2])
        self.assertFalse(is_valid)
        self.assertTrue(any("Missing request_ids" in e or "row count" in e.lower() for e in errors))

    # 20. Dataset Duplicate Request IDs
    def test_dataset_duplicate_request_ids(self):
        rec_dup = OutputRecord(**self.base_record.__dict__)
        records = [self.base_record, rec_dup]
        is_valid, errors = self.validator.validate_all(records, [self.base_request])
        self.assertFalse(is_valid)
        self.assertTrue(any("Duplicate request_id" in e for e in errors))

    # 21. Fail Loudly (raise_on_error=True)
    def test_fail_loudly_raise_on_error(self):
        bad_rec = OutputRecord(**{**self.base_record.__dict__, "amount_safe_to_pay": "-999.0"})
        with self.assertRaises(ValueError) as ctx:
            self.validator.validate_all([bad_rec], [self.base_request], raise_on_error=True)
        self.assertIn("Output validation failed with 1 errors", str(ctx.exception))

    # 22. CSV File Validation Success & Failure
    def test_validate_csv_file(self):
        import tempfile
        import os

        with tempfile.NamedTemporaryFile("w", delete=False, suffix=".csv", encoding="utf-8") as tf:
            tf.write("request_id,amount_safe_to_pay,affordability_status,recommended_payment_method,payment_plan,earliest_date_for_full_payment,spending_changes_needed,decision_explanation\n")
            tf.write("req_test_01,20000.0,affordable_now,full_payment,2026-01-01:20000,2026-01-01,none,You can safely pay the full amount today.\n")
            temp_path = tf.name

        try:
            is_valid, errors = self.validator.validate_csv_file(temp_path, [self.base_request])
            self.assertTrue(is_valid, f"CSV file validation failed: {errors}")
        finally:
            os.remove(temp_path)

    # 23. CSV Header Mismatch
    def test_validate_csv_header_mismatch(self):
        import tempfile
        import os

        with tempfile.NamedTemporaryFile("w", delete=False, suffix=".csv", encoding="utf-8") as tf:
            tf.write("wrong_id,amount,status,method,plan,earliest_date,changes,explanation\n")
            tf.write("req_test_01,20000.0,affordable_now,full_payment,2026-01-01:20000,2026-01-01,none,You can safely pay the full amount today.\n")
            temp_path = tf.name

        try:
            is_valid, errors = self.validator.validate_csv_file(temp_path, [self.base_request])
            self.assertFalse(is_valid)
            self.assertTrue(any("CSV header mismatch" in e for e in errors))
        finally:
            os.remove(temp_path)


if __name__ == "__main__":
    unittest.main(verbosity=2)


"""Acceptance tests for Lab 5. Run: python3 -m unittest discover -s tests -v"""
import csv
from pathlib import Path
import tempfile
import unittest

from tools.profile_csv import profile_csv


class CSVProfilerTests(unittest.TestCase):
    def test_dirty_dataset_exact_counts(self):
        profile = profile_csv("data/orders_dirty.csv")
        self.assertEqual(profile["total_records"], 7)
        self.assertEqual(len(profile["columns"]), 5)
        expected = {
            "MISSING_CUSTOMER_ID": 1,
            "DUPLICATE_RECORD": 1,
            "INVALID_AMOUNT": 0,
            "NEGATIVE_AMOUNT": 1,
            "INVALID_DATE": 1,
            "HIGH_VALUE_REVIEW": 1,
        }
        self.assertEqual(profile["issue_counts"], expected)
        self.assertEqual(len(profile["issues"]), 5)

    def test_evidence_and_heuristic_label(self):
        profile = profile_csv("data/orders_dirty.csv")
        by_type = {item["type"]: item for item in profile["issues"]}
        self.assertEqual(by_type["DUPLICATE_RECORD"]["order_id"], "O-102")
        self.assertEqual(by_type["DUPLICATE_RECORD"]["row_number"], 7)
        self.assertEqual(by_type["HIGH_VALUE_REVIEW"]["severity"], "review")
        self.assertFalse(profile["rules"]["high_value_is_error"])

    def test_clean_dataset_no_issues(self):
        profile = profile_csv("data/orders_clean.csv")
        self.assertEqual(profile["total_records"], 3)
        self.assertEqual(sum(profile["issue_counts"].values()), 0)

    def test_missing_file_fails_clearly(self):
        with self.assertRaises(FileNotFoundError):
            profile_csv("data/this_does_not_exist.csv")

    def test_missing_column_fails_clearly(self):
        with tempfile.TemporaryDirectory() as folder:
            src = Path(folder) / "bad.csv"
            src.write_text("order_id,amount\nA1,25\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "Missing required columns"):
                profile_csv(src)

    def test_invalid_amount_and_source_not_changed(self):
        with tempfile.TemporaryDirectory() as folder:
            src = Path(folder) / "amount.csv"
            src.write_text(
                "order_id,customer_id,amount,order_date,status\n"
                "A1,C1,not-a-number,2026-10-01,PAID\n", encoding="utf-8"
            )
            original = src.read_bytes()
            report = profile_csv(src)
            self.assertEqual(report["issue_counts"]["INVALID_AMOUNT"], 1)
            self.assertEqual(src.read_bytes(), original)


if __name__ == "__main__":
    unittest.main()

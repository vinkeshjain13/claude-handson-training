"""Baseline tests for TicketOps. SLA tests are intentionally absent."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from app.repository import load_tickets
from app.service import filter_tickets, summarize_tickets

DATA_FILE = Path(__file__).resolve().parents[1] / "data" / "tickets.csv"


class TicketOpsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tickets = load_tickets(DATA_FILE)

    def test_loads_twelve_tickets(self):
        self.assertEqual(len(self.tickets), 12)

    def test_all_ids_are_unique(self):
        self.assertEqual(len({x.ticket_id for x in self.tickets}), 12)

    def test_priorities_are_balanced(self):
        self.assertEqual(summarize_tickets(self.tickets)["by_priority"],
                         {"HIGH": 4, "MEDIUM": 4, "LOW": 4})

    def test_status_counts(self):
        self.assertEqual(summarize_tickets(self.tickets)["by_status"],
                         {"OPEN": 6, "IN_PROGRESS": 3, "RESOLVED": 3})

    def test_unresolved_count(self):
        self.assertEqual(summarize_tickets(self.tickets)["unresolved"], 9)

    def test_filter_high_priority(self):
        actual = filter_tickets(self.tickets, priority="HIGH")
        self.assertEqual({ticket.ticket_id for ticket in actual},
                         {"T-1001", "T-1004", "T-1005", "T-1008"})

    def test_filter_resolved(self):
        actual = filter_tickets(self.tickets, status="RESOLVED")
        self.assertEqual({ticket.ticket_id for ticket in actual},
                         {"T-1004", "T-1009", "T-1012"})

    def test_filter_combined(self):
        self.assertEqual(filter_tickets(self.tickets, priority="LOW", status="RESOLVED")[0].ticket_id,
                         "T-1012")

    def test_invalid_priority_is_rejected(self):
        with self.assertRaises(ValueError):
            filter_tickets(self.tickets, priority="URGENT")

    def test_missing_required_header_is_rejected(self):
        with tempfile.TemporaryDirectory() as tempdir:
            path = Path(tempdir) / "bad.csv"
            path.write_text("ticket_id,customer_id\nT-99,C-99\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "Missing required CSV columns"):
                load_tickets(path)

    def test_naive_date_is_rejected(self):
        with tempfile.TemporaryDirectory() as tempdir:
            path = Path(tempdir) / "bad.csv"
            path.write_text(
                "ticket_id,customer_id,category,priority,status,created_at,summary\n"
                "T-99,C-99,General,LOW,OPEN,2026-10-20T08:00:00,Example\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "timezone"):
                load_tickets(path)


if __name__ == "__main__":
    unittest.main()

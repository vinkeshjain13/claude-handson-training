"""Acceptance tests for the SLA escalation feature used in Day 2 Lab 3."""
from __future__ import annotations

import subprocess
import sys
import unittest
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path

from app.repository import load_tickets
from app.service import get_escalated_tickets

ROOT = Path(__file__).resolve().parents[1]
DATA_FILE = ROOT / "data" / "tickets.csv"
AS_OF = datetime(2026, 10, 22, 12, tzinfo=timezone.utc)
EXPECTED_IDS = {
    "T-1001", "T-1002", "T-1005", "T-1006",
    "T-1007", "T-1008", "T-1010", "T-1011",
}


class TestSlaEscalation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tickets = load_tickets(DATA_FILE)

    def test_eight_escalations_in_starter_data(self):
        result = get_escalated_tickets(self.tickets, as_of=AS_OF)
        self.assertEqual({t.ticket_id for t in result}, EXPECTED_IDS)
        self.assertEqual(len(result), 8)

    def test_resolved_ticket_never_escalates(self):
        original = self.tickets[0]  # HIGH ticket
        resolved = replace(original, status="RESOLVED", created_at=AS_OF - timedelta(days=100))
        self.assertEqual(get_escalated_tickets([resolved], as_of=AS_OF), [])

    def test_each_priority_exact_boundary_is_included(self):
        for priority, hours in (("HIGH", 24), ("MEDIUM", 48), ("LOW", 72)):
            with self.subTest(priority=priority):
                ticket = replace(self.tickets[0], priority=priority,
                                 created_at=AS_OF - timedelta(hours=hours), status="OPEN")
                self.assertEqual(get_escalated_tickets([ticket], as_of=AS_OF), [ticket])

    def test_one_second_before_threshold_is_not_escalated(self):
        ticket = replace(self.tickets[0], created_at=AS_OF - timedelta(hours=24) + timedelta(seconds=1))
        self.assertEqual(get_escalated_tickets([ticket], as_of=AS_OF), [])

    def test_future_dated_ticket_is_not_escalated(self):
        ticket = replace(self.tickets[0], created_at=AS_OF + timedelta(hours=1))
        self.assertEqual(get_escalated_tickets([ticket], as_of=AS_OF), [])

    def test_naive_reference_time_fails(self):
        with self.assertRaisesRegex(ValueError, "timezone-aware"):
            get_escalated_tickets(self.tickets, as_of=datetime(2026, 10, 22, 12))

    def test_input_ticket_list_not_mutated(self):
        original = list(self.tickets)
        get_escalated_tickets(self.tickets, as_of=AS_OF)
        self.assertEqual(self.tickets, original)

    def test_cli_escalated_mode_reports_eight(self):
        result = subprocess.run([sys.executable, "-m", "app.main", "--escalated", "--as-of",
                                 "2026-10-22T12:00:00Z"], cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('"total": 8', result.stdout)
        for id in EXPECTED_IDS:
            self.assertIn(id, result.stdout)
        self.assertNotIn("T-1004", result.stdout)

    def test_original_cli_still_works(self):
        result = subprocess.run([sys.executable, "-m", "app.main"], cwd=ROOT,
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('"total": 12', result.stdout)

    def test_cli_missing_as_of_rejected(self):
        result = subprocess.run([sys.executable, "-m", "app.main", "--escalated"], cwd=ROOT,
                                capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("--escalated requires --as-of", result.stderr)


if __name__ == "__main__":
    unittest.main()

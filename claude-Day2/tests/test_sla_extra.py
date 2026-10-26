"""Additional SLA escalation tests: boundaries, timezones, future, resolved, CLI."""
from __future__ import annotations

import subprocess
import sys
import unittest
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path

from app.repository import load_tickets
from app.service import SLA_ESCALATION_HOURS, get_escalated_tickets

ROOT = Path(__file__).resolve().parents[1]
DATA_FILE = ROOT / "data" / "tickets.csv"
AS_OF = datetime(2026, 10, 22, 12, tzinfo=timezone.utc)
EXPECTED_ORDER = ["T-1001", "T-1002", "T-1005", "T-1006", "T-1007", "T-1008", "T-1010", "T-1011"]


def run_cli(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, "-m", "app.main", *args], cwd=ROOT,
                          capture_output=True, text=True)


class TestSlaExtra(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tickets = load_tickets(DATA_FILE)
        cls.base = cls.tickets[0]

    def make(self, **changes):
        return replace(self.base, **changes)

    def test_threshold_equality_and_just_short_for_every_priority(self):
        for priority, hours in SLA_ESCALATION_HOURS.items():
            threshold = timedelta(hours=hours)
            with self.subTest(priority=priority):
                just_short = self.make(priority=priority, status="OPEN",
                                       created_at=AS_OF - threshold + timedelta(microseconds=1))
                on_boundary = self.make(priority=priority, status="OPEN",
                                        created_at=AS_OF - threshold)
                past = self.make(priority=priority, status="OPEN",
                                 created_at=AS_OF - threshold - timedelta(seconds=1))
                self.assertEqual(get_escalated_tickets([just_short], as_of=AS_OF), [])
                self.assertEqual(get_escalated_tickets([on_boundary], as_of=AS_OF), [on_boundary])
                self.assertEqual(get_escalated_tickets([past], as_of=AS_OF), [past])

    def test_in_progress_escalates_at_boundary(self):
        ticket = self.make(priority="MEDIUM", status="IN_PROGRESS",
                           created_at=AS_OF - timedelta(hours=48))
        self.assertEqual(get_escalated_tickets([ticket], as_of=AS_OF), [ticket])

    def test_resolved_never_escalates_for_any_priority(self):
        for priority in SLA_ESCALATION_HOURS:
            with self.subTest(priority=priority):
                ticket = self.make(priority=priority, status="RESOLVED",
                                   created_at=AS_OF - timedelta(days=365))
                self.assertEqual(get_escalated_tickets([ticket], as_of=AS_OF), [])

    def test_future_and_equal_created_at_never_escalate(self):
        for priority in SLA_ESCALATION_HOURS:
            for offset in (timedelta(0), timedelta(seconds=1), timedelta(days=365)):
                with self.subTest(priority=priority, offset=offset):
                    ticket = self.make(priority=priority, status="OPEN",
                                       created_at=AS_OF + offset)
                    self.assertEqual(get_escalated_tickets([ticket], as_of=AS_OF), [])

    def test_output_preserves_input_order(self):
        result = get_escalated_tickets(self.tickets, as_of=AS_OF)
        self.assertEqual([t.ticket_id for t in result], EXPECTED_ORDER)
        reversed_result = get_escalated_tickets(list(reversed(self.tickets)), as_of=AS_OF)
        self.assertEqual([t.ticket_id for t in reversed_result], EXPECTED_ORDER[::-1])

    def test_returns_same_ticket_objects(self):
        result = get_escalated_tickets(self.tickets, as_of=AS_OF)
        for ticket in result:
            self.assertTrue(any(ticket is original for original in self.tickets))

    def test_non_utc_as_of_same_instant_gives_same_result(self):
        ist = timezone(timedelta(hours=5, minutes=30))
        as_of_ist = AS_OF.astimezone(ist)
        self.assertEqual(get_escalated_tickets(self.tickets, as_of=as_of_ist),
                         get_escalated_tickets(self.tickets, as_of=AS_OF))

    def test_non_utc_created_at_compared_on_utc_basis(self):
        ist = timezone(timedelta(hours=5, minutes=30))
        boundary = (AS_OF - timedelta(hours=24)).astimezone(ist)
        ticket = self.make(priority="HIGH", status="OPEN", created_at=boundary)
        self.assertEqual(get_escalated_tickets([ticket], as_of=AS_OF), [ticket])
        later = self.make(priority="HIGH", status="OPEN",
                          created_at=boundary + timedelta(seconds=1))
        self.assertEqual(get_escalated_tickets([later], as_of=AS_OF), [])

    def test_naive_as_of_rejected_even_for_empty_input(self):
        with self.assertRaisesRegex(ValueError, "timezone-aware"):
            get_escalated_tickets([], as_of=datetime(2026, 10, 22, 12))

    def test_naive_created_at_rejected(self):
        ticket = self.make(created_at=datetime(2026, 10, 20, 8))
        with self.assertRaisesRegex(ValueError, "timezone-aware"):
            get_escalated_tickets([ticket], as_of=AS_OF)

    def test_unknown_priority_rejected(self):
        with self.assertRaisesRegex(ValueError, "priority"):
            get_escalated_tickets([self.make(priority="URGENT")], as_of=AS_OF)

    def test_empty_input_and_generator_input(self):
        self.assertEqual(get_escalated_tickets([], as_of=AS_OF), [])
        generated = get_escalated_tickets((t for t in self.tickets), as_of=AS_OF)
        self.assertEqual([t.ticket_id for t in generated], EXPECTED_ORDER)

    def test_tickets_unchanged_after_call(self):
        snapshot = [replace(t) for t in self.tickets]
        get_escalated_tickets(self.tickets, as_of=AS_OF)
        self.assertEqual(self.tickets, snapshot)


class TestSlaCliExtra(unittest.TestCase):
    AS_OF_ARG = "2026-10-22T12:00:00Z"

    def test_naive_as_of_rejected(self):
        result = run_cli("--escalated", "--as-of", "2026-10-22T12:00:00")
        self.assertEqual(result.returncode, 2)
        self.assertIn("timezone-aware", result.stderr)
        self.assertNotIn("Traceback", result.stderr)

    def test_garbage_as_of_rejected(self):
        result = run_cli("--escalated", "--as-of", "not-a-date")
        self.assertEqual(result.returncode, 2)
        self.assertNotIn("Traceback", result.stderr)

    def test_as_of_without_escalated_rejected(self):
        result = run_cli("--as-of", self.AS_OF_ARG)
        self.assertEqual(result.returncode, 2)
        self.assertIn("--as-of requires --escalated", result.stderr)

    def test_offset_as_of_accepted(self):
        result = run_cli("--escalated", "--as-of", "2026-10-22T17:30:00+05:30")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('"total": 8', result.stdout)

    def test_escalated_with_priority_filter(self):
        result = run_cli("--escalated", "--as-of", self.AS_OF_ARG, "--priority", "HIGH")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('"total": 3', result.stdout)
        self.assertIn("Selected ticket IDs: T-1001, T-1005, T-1008", result.stdout)

    def test_escalated_with_status_filter(self):
        result = run_cli("--escalated", "--as-of", self.AS_OF_ARG, "--status", "OPEN")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Selected ticket IDs: T-1001, T-1005, T-1006, T-1010, T-1011",
                      result.stdout)

    def test_escalated_resolved_is_empty(self):
        result = run_cli("--escalated", "--as-of", self.AS_OF_ARG, "--status", "RESOLVED")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('"total": 0', result.stdout)
        self.assertIn("(none)", result.stdout)

    def test_escalated_ids_in_csv_order(self):
        result = run_cli("--escalated", "--as-of", self.AS_OF_ARG)
        self.assertIn("Selected ticket IDs: " + ", ".join(EXPECTED_ORDER), result.stdout)


if __name__ == "__main__":
    unittest.main()

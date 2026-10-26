"""L2 service tests: manager dashboard figures.

Covers AC-37, AC-39..AC-43, AC-59, AC-65 and FR-16, FR-18..FR-20, FR-23, FR-24.
"""

from __future__ import annotations

import dataclasses
from collections import Counter

import pytest

from ticketing import config
from ticketing.models import DashboardStats

WORK = [  # (status, priority, category) mix used for populated tests
    ("Open", "Low", "Hardware"),
    ("Open", "Medium", "Software"),
    ("Open", "High", "Network"),
    ("In Progress", "High", "Network"),
    ("In Progress", "Critical", "Other"),
    ("Resolved", "Low", "Account Access"),
    ("Resolved", "Low", "Hardware"),
    ("Resolved", "Medium", "Software"),
    ("Closed", "Critical", "Hardware"),
    ("Closed", "High", "Hardware"),
    ("Closed", "High", "Other"),
]


@pytest.fixture
def populated(ticket_in_status):
    for status, priority, category in WORK:
        ticket_in_status(status, priority=priority, category=category)
    return WORK


def assert_invariants(stats: DashboardStats) -> None:
    assert stats.total == sum(stats.by_status.values())
    assert stats.total == sum(stats.by_priority.values())
    assert stats.total == sum(stats.by_category.values())


def test_ac42_fr20_fr24_empty_database_is_zero_filled_without_error(service):
    """AC-42 / FR-20, FR-24: total, all statuses, priorities and categories are 0."""
    stats = service.get_dashboard_stats()
    assert stats.total == 0
    assert stats.by_status == {s: 0 for s in config.STATUSES}
    assert stats.by_priority == {p: 0 for p in config.PRIORITIES}
    assert stats.by_category == {c: 0 for c in config.CATEGORIES}
    assert_invariants(stats)


def test_ac41_ac65_fr19_fr24_keys_are_exactly_the_configured_lists_in_order(service):
    """AC-41, AC-65 / FR-19, FR-24: all levels present (including zero) in config order."""
    stats = service.get_dashboard_stats()
    assert list(stats.by_status) == ["Open", "In Progress", "Resolved", "Closed"]
    assert list(stats.by_priority) == ["Low", "Medium", "High", "Critical"]
    assert list(stats.by_category) == [
        "Hardware",
        "Software",
        "Network",
        "Account Access",
        "Other",
    ]


def test_ac37_fr16_total_equals_number_of_tickets(service, make_ticket):
    """AC-37 / FR-16: total equals N after N creates."""
    for n in range(1, 6):
        make_ticket()
        assert service.get_dashboard_stats().total == n


def test_ac39_ac59_fr18_fr23_status_counts_match_actual(service, populated):
    """AC-39, AC-59 / FR-18, FR-23: Open, In Progress, Resolved, Closed counts."""
    stats = service.get_dashboard_stats()
    expected = Counter(s for s, _, _ in populated)
    assert stats.by_status == {s: expected.get(s, 0) for s in config.STATUSES}
    assert (
        stats.by_status["Open"],
        stats.by_status["In Progress"],
        stats.by_status["Resolved"],
        stats.by_status["Closed"],
    ) == (3, 2, 3, 3)


def test_ac41_fr19_priority_counts_match_actual(service, populated):
    """AC-41 / FR-19: counts per priority, including zero-count levels."""
    stats = service.get_dashboard_stats()
    expected = Counter(p for _, p, _ in populated)
    assert stats.by_priority == {p: expected.get(p, 0) for p in config.PRIORITIES}
    assert stats.by_priority == {"Low": 3, "Medium": 2, "High": 4, "Critical": 2}


def test_ac65_fr24_category_counts_match_actual(service, populated):
    """AC-65 / FR-24: counts per category."""
    stats = service.get_dashboard_stats()
    expected = Counter(c for _, _, c in populated)
    assert stats.by_category == {c: expected.get(c, 0) for c in config.CATEGORIES}
    assert stats.by_category == {
        "Hardware": 4,
        "Software": 2,
        "Network": 2,
        "Account Access": 1,
        "Other": 2,
    }


def test_ac40_ac41_ac65_invariants_hold_on_populated_data(service, populated):
    """AC-40, AC-41, AC-65: total == sum(status) == sum(priority) == sum(category)."""
    stats = service.get_dashboard_stats()
    assert stats.total == len(WORK)
    assert_invariants(stats)


def test_ac41_fr19_zero_levels_are_shown_when_other_levels_have_tickets(service, make_ticket):
    """AC-41, AC-65 / FR-19, FR-24: unused levels appear with 0."""
    make_ticket(priority="Low", category="Other")
    stats = service.get_dashboard_stats()
    assert stats.by_priority == {"Low": 1, "Medium": 0, "High": 0, "Critical": 0}
    assert stats.by_category["Hardware"] == 0 and stats.by_category["Other"] == 1
    assert stats.by_status == {"Open": 1, "In Progress": 0, "Resolved": 0, "Closed": 0}


def test_ac43_fr20_dashboard_reflects_create_without_restart(service, make_ticket):
    """AC-43 / FR-20: figures change after a create on the same service instance."""
    before = service.get_dashboard_stats()
    make_ticket(priority="Critical", category="Network")
    after = service.get_dashboard_stats()
    assert after.total == before.total + 1
    assert after.by_priority["Critical"] == 1 and after.by_category["Network"] == 1
    assert after.by_status["Open"] == 1


def test_ac43_fr20_dashboard_reflects_status_change(service, make_ticket):
    """AC-43 / FR-20: status counts move after change_status."""
    t = make_ticket()
    service.change_status(t.id, "In Progress")
    s = service.get_dashboard_stats()
    assert (s.by_status["Open"], s.by_status["In Progress"]) == (0, 1)
    service.change_status(t.id, "Resolved", "done")
    s = service.get_dashboard_stats()
    assert (s.by_status["In Progress"], s.by_status["Resolved"]) == (0, 1)
    service.change_status(t.id, "Closed")
    s = service.get_dashboard_stats()
    assert (s.by_status["Resolved"], s.by_status["Closed"]) == (0, 1)
    assert s.total == 1
    assert_invariants(s)


def test_ac43_fr20_dashboard_reflects_priority_change_and_total_is_stable(service, make_ticket):
    """AC-43 / FR-20: priority counts move after change_priority; total unchanged."""
    t = make_ticket(priority="Low")
    service.change_priority(t.id, "Critical")
    s = service.get_dashboard_stats()
    assert (s.by_priority["Low"], s.by_priority["Critical"], s.total) == (0, 1, 1)


def test_ac43_fr20_rejected_updates_do_not_change_dashboard(service, make_ticket):
    """AC-43 / FR-20, NFR-06: rejected operations leave figures untouched."""
    t = make_ticket()
    before = service.get_dashboard_stats()
    for call in (
        lambda: service.change_status(t.id, "Closed"),
        lambda: service.change_priority(t.id, "Bogus"),
        lambda: service.create_ticket("", "", "", "x", "y"),
    ):
        with pytest.raises(Exception):  # noqa: B017 - any TicketError subclass is fine here
            call()
    assert service.get_dashboard_stats() == before


def test_ac59_fr23_closed_count_is_visible_and_counts_only_closed(service, ticket_in_status):
    """AC-59 / FR-23: Closed count equals number of Closed tickets."""
    ticket_in_status("Closed")
    ticket_in_status("Resolved")
    ticket_in_status("Open")
    s = service.get_dashboard_stats()
    assert s.by_status["Closed"] == 1 and s.by_status["Resolved"] == 1
    assert s.by_status["Open"] == 1 and s.by_status["In Progress"] == 0


def test_ac40_fr16_dashboard_has_no_pending_figure(service):
    """AC-38 retired / ASM-22: no 'pending' field exists on the dashboard type."""
    names = {f.name for f in dataclasses.fields(DashboardStats)}
    assert names == {"total", "by_status", "by_priority", "by_category"}


def test_ac42_fr20_dashboard_is_read_only(service, populated, snapshot):
    """FR-20, NFR-06: reading the dashboard does not modify data."""
    before = snapshot()
    service.get_dashboard_stats()
    assert snapshot() == before


def test_ac40_ac41_ac65_invariants_hold_for_every_prefix_of_a_mixed_sequence(
    service, ticket_in_status
):
    """AC-40, AC-41, AC-65: invariant after every single create."""
    for status, priority, category in WORK:
        ticket_in_status(status, priority=priority, category=category)
        assert_invariants(service.get_dashboard_stats())

"""L2 service tests: retrieval, listing, filtering, My tickets.

Covers AC-12..AC-20, AC-60, AC-66, AC-02, AC-14, AC-15 (service level) and FR-06, FR-07, FR-08,
FR-26.
"""

from __future__ import annotations

import pytest

from tests.helpers import SQL_INJECTION_TEXTS, raw_count
from ticketing import config
from ticketing.models import NotFoundError, TicketError, ValidationError

TICKET_FIELDS = [
    "id",
    "title",
    "description",
    "category",
    "priority",
    "status",
    "creator",
    "created_at",
    "updated_at",
    "resolution_note",
]


@pytest.fixture
def mixed(service, fake_clock, ticket_in_status):
    """Seven tickets with a spread of status/priority/category/creator. Returns by key."""
    t = {}
    t["a"] = ticket_in_status(
        "Open", creator="Ann", title="VPN down", category="Network", priority="High"
    )
    fake_clock.advance(10)
    t["b"] = ticket_in_status(
        "In Progress", creator="Bob", title="Printer jam", category="Hardware", priority="Low"
    )
    fake_clock.advance(10)
    t["c"] = ticket_in_status(
        "Resolved", creator="ann", title="Excel crash", category="Software", priority="Medium"
    )
    fake_clock.advance(10)
    t["d"] = ticket_in_status(
        "Closed",
        creator="Cara",
        title="Reset password",
        category="Account Access",
        priority="Critical",
    )
    fake_clock.advance(10)
    t["e"] = ticket_in_status(
        "Open", creator="Bob", title="Wifi slow", category="Network", priority="High"
    )
    fake_clock.advance(10)
    t["f"] = ticket_in_status(
        "Open", creator="Ann", title="Mouse broken", category="Hardware", priority="Low"
    )
    fake_clock.advance(10)
    t["g"] = ticket_in_status(
        "In Progress", creator="Dan", title="Mail bounce", category="Other", priority="Critical"
    )
    return t


def ids(tickets):
    return [t.id for t in tickets]


# ------------------------------------------------------------------ get_ticket -------------


def test_ac14_fr07_details_contain_all_ten_fields(service, make_ticket):
    """AC-14 / FR-07: ID, title, creator, description, category, priority, status, timestamps,
    resolution_note (empty when none)."""
    created = make_ticket()
    ticket = service.get_ticket(created.id)
    assert [f for f in TICKET_FIELDS if not hasattr(ticket, f)] == []
    assert ticket.resolution_note == ""
    assert ticket.created_at and ticket.updated_at


@pytest.mark.parametrize("missing", [999, 2, 0, -1, -999, 2**31, 2**63 - 1, -(2**63)])
def test_ac15_fr07_unknown_id_raises_not_found(service, make_ticket, missing):
    """AC-15 / FR-07 (service level): unknown IDs give NotFoundError with a plain message."""
    make_ticket()  # only ID 1 exists
    with pytest.raises(NotFoundError) as exc:
        service.get_ticket(missing)
    assert str(exc.value) == f"Ticket {missing} was not found."


@pytest.mark.parametrize("huge", [2**63, 2**64, 2**70, -(2**63) - 1, 10**30])
def test_ac15_fr07_id_beyond_sqlite_integer_range_gives_clean_error(service, huge):
    """AC-15 / FR-07: 'no error/crash occurs' for a ticket ID that does not exist, including IDs
    larger than SQLite's 64-bit INTEGER. Expect a TicketError (NotFoundError/ValidationError)."""
    with pytest.raises(TicketError):
        service.get_ticket(huge)


@pytest.mark.parametrize(
    "bad", ["7", "abc", "", None, 7.0, 1.5, True, False, [1], (1,), b"1"], ids=repr
)
def test_ac15_fr07_non_integer_id_is_validation_error(service, make_ticket, bad):
    """AC-15 / FR-07 (VR section 3): non-int (incl. bool) ticket ID -> ValidationError."""
    make_ticket()
    with pytest.raises(ValidationError) as exc:
        service.get_ticket(bad)
    assert exc.value.errors == {"ticket_id": "Ticket ID must be a whole number."}


@pytest.mark.parametrize("bad", ["7", None, 7.0, True], ids=repr)
def test_ac29_fr09_non_integer_id_rejected_by_every_update_operation(service, make_ticket, bad):
    """AC-29 / FR-09, FR-11, FR-15: update operations validate the ticket ID type too."""
    make_ticket()
    with pytest.raises(ValidationError) as e1:
        service.change_status(bad, "In Progress")
    with pytest.raises(ValidationError) as e2:
        service.change_priority(bad, "Low")
    with pytest.raises(ValidationError) as e3:
        service.set_resolution_note(bad, "note")
    for exc in (e1, e2, e3):
        assert "ticket_id" in exc.value.errors


def test_ac15_fr07_sql_injection_looking_id_string_is_not_executed(service, make_ticket, db_path):
    """AC-15 / FR-07, NFR-08: a string ID with SQL text is rejected as non-int, table intact."""
    make_ticket()
    with pytest.raises(ValidationError):
        service.get_ticket("1 OR 1=1")
    with pytest.raises(ValidationError):
        service.get_ticket("1; DROP TABLE tickets")
    assert raw_count(db_path) == 1


# ------------------------------------------------------------- list ordering ----------------


def test_ac13_fr06_empty_database_lists_nothing_without_error(service):
    """AC-13 / FR-06: no tickets -> empty list, no exception."""
    assert service.list_tickets() == []
    assert service.list_tickets(status="Open", priority="High", category="Other", creator="x") == []
    assert service.list_my_tickets("Nobody") == []


def test_ac12_fr06_list_is_newest_first_with_all_columns(service, make_ticket, fake_clock):
    """AC-12 / FR-06: >=3 tickets, descending ID order, listed fields present."""
    made = []
    for n in range(4):
        made.append(make_ticket(title=f"T{n}"))
        fake_clock.advance(5)
    listed = service.list_tickets()
    assert ids(listed) == sorted(ids(made), reverse=True)
    for t in listed:
        for field in ("id", "title", "creator", "category", "priority", "status", "created_at"):
            assert getattr(t, field) not in (None, "")


def test_ac12_fr06_newest_first_is_by_id_even_with_identical_timestamps(service, make_ticket):
    """AC-12 / FR-06: ordering is stable when the clock does not move."""
    a, b, c = make_ticket(), make_ticket(), make_ticket()
    assert ids(service.list_tickets()) == [c.id, b.id, a.id]


# ----------------------------------------------------------------- filters -----------------


def test_ac16_fr08_filter_by_status_only_returns_that_status(service, mixed):
    """AC-16 / FR-08: status filter."""
    result = service.list_tickets(status="Open")
    assert ids(result) == [mixed["f"].id, mixed["e"].id, mixed["a"].id]
    assert {t.status for t in result} == {"Open"}


@pytest.mark.parametrize("status", config.STATUSES)
def test_ac16_fr08_each_status_filter_matches_exactly(service, mixed, status):
    """AC-16 / FR-08: every status value filters correctly."""
    result = service.list_tickets(status=status)
    assert result and {t.status for t in result} == {status}
    assert len(result) == len([t for t in service.list_tickets() if t.status == status])


def test_ac17_fr08_filter_by_priority_only_returns_that_priority(service, mixed):
    """AC-17 / FR-08: priority filter."""
    result = service.list_tickets(priority="High")
    assert ids(result) == [mixed["e"].id, mixed["a"].id]


@pytest.mark.parametrize("priority", config.PRIORITIES)
def test_ac17_fr08_each_priority_filter_matches_exactly(service, mixed, priority):
    """AC-17 / FR-08: every priority value filters correctly."""
    result = service.list_tickets(priority=priority)
    assert result and {t.priority for t in result} == {priority}


def test_ac60_fr08_filter_by_category(service, mixed):
    """AC-60 / FR-08: category filter alone and combined with status."""
    assert ids(service.list_tickets(category="Network")) == [mixed["e"].id, mixed["a"].id]
    both = service.list_tickets(category="Network", status="In Progress")
    assert both == []
    both = service.list_tickets(category="Hardware", status="In Progress")
    assert ids(both) == [mixed["b"].id]


@pytest.mark.parametrize("category", config.CATEGORIES)
def test_ac60_fr08_each_category_filter_matches_exactly(service, mixed, category):
    """AC-60 / FR-08: every category value filters correctly."""
    result = service.list_tickets(category=category)
    assert result and {t.category for t in result} == {category}


def test_ac18_fr08_status_and_priority_combine_with_and(service, mixed):
    """AC-18 / FR-08: both filters must match."""
    result = service.list_tickets(status="Open", priority="Low")
    assert ids(result) == [mixed["f"].id]
    assert service.list_tickets(status="Closed", priority="Low") == []


def test_ac18_fr08_all_four_filters_combine(service, mixed):
    """AC-18 / FR-08: status + priority + category + creator."""
    result = service.list_tickets(status="Open", priority="High", category="Network", creator="ANN")
    assert ids(result) == [mixed["a"].id]


def test_ac19_fr08_creator_filter_is_case_insensitive_and_trimmed(service, mixed):
    """AC-19 / FR-08: creator match ignores case and surrounding spaces."""
    expected = [mixed["f"].id, mixed["c"].id, mixed["a"].id]  # "Ann", "ann", "Ann"
    for typed in ("Ann", "ann", "ANN", "  aNn  ", "\tann\n"):
        assert ids(service.list_tickets(creator=typed)) == expected


def test_ac19_fr08_creator_filter_is_exact_not_substring(service, mixed):
    """AC-19 / FR-08: 'An' does not match 'Ann'; no wildcard meaning for % or _."""
    assert service.list_tickets(creator="An") == []
    assert service.list_tickets(creator="%") == []
    assert service.list_tickets(creator="A_n") == []
    assert service.list_tickets(creator="Ann%") == []


def test_ac19_fr08_creator_filter_uses_unicode_casefold(service, make_ticket):
    """AC-19 / FR-08: casefold semantics (ß == ss, Σ forms)."""
    t = make_ticket(creator="Straße")
    assert ids(service.list_tickets(creator="STRASSE")) == [t.id]
    assert ids(service.list_tickets(creator="straße")) == [t.id]
    z = make_ticket(creator="ZOË")
    assert ids(service.list_tickets(creator="zoë")) == [z.id]


def test_ac20_fr08_filter_combination_with_no_match_returns_empty_list(service, mixed):
    """AC-20 / FR-08: no match -> [] and no error."""
    assert service.list_tickets(status="Closed", priority="Low", category="Network") == []
    assert service.list_tickets(creator="Nobody") == []


@pytest.mark.parametrize("blank", [None, "", "   ", "\t\n"], ids=repr)
@pytest.mark.parametrize("name", ["status", "priority", "category", "creator"])
def test_fr08_blank_or_none_filter_means_no_filter(service, mixed, name, blank):
    """FR-08 (IC S3): None/blank text means 'no filter' for each filter."""
    assert service.list_tickets(**{name: blank}) == service.list_tickets()
    assert len(service.list_tickets(**{name: blank})) == 7


def test_fr08_status_filter_value_is_trimmed(service, mixed):
    """FR-08 (build-time clarification): list filters are trimmed."""
    assert service.list_tickets(status="  Open ") == service.list_tickets(status="Open")


@pytest.mark.parametrize(
    ("name", "bad"),
    [
        ("status", "Pending"),
        ("status", "open"),
        ("status", "OPEN"),
        ("status", "In progress"),
        ("priority", "Urgent"),
        ("priority", "high"),
        ("category", "Printers"),
        ("category", "network"),
        ("status", 5),
        ("priority", ["High"]),
        ("category", 1.5),
    ],
    ids=repr,
)
def test_fr08_invalid_filter_value_is_validation_error(service, mixed, name, bad):
    """FR-08 / IC S3: unknown or wrong-case status/priority/category filters are rejected."""
    with pytest.raises(ValidationError) as exc:
        service.list_tickets(**{name: bad})
    assert name in exc.value.errors


def test_fr08_non_string_creator_filter_is_validation_error(service, mixed):
    """FR-08: a non-str creator filter is rejected."""
    with pytest.raises(ValidationError) as exc:
        service.list_tickets(creator=123)  # type: ignore[arg-type]
    assert "creator" in exc.value.errors


def test_fr08_several_invalid_filters_are_collected(service, mixed):
    """FR-08 (build-time clarification): all invalid filters reported at once."""
    with pytest.raises(ValidationError) as exc:
        service.list_tickets(status="x", priority="y", category="z")
    assert set(exc.value.errors) == {"status", "priority", "category"}


@pytest.mark.parametrize("text", SQL_INJECTION_TEXTS)
def test_fr08_nfr08_injection_text_in_creator_filter_is_literal(service, mixed, db_path, text):
    """FR-08 / NFR-08: SQL-looking creator filter matches nothing and damages nothing."""
    assert service.list_tickets(creator=text) == []
    assert raw_count(db_path) == 7
    assert len(service.list_tickets()) == 7


@pytest.mark.parametrize("name", ["status", "priority", "category"])
def test_fr08_nfr08_injection_text_in_enum_filters_is_validation_error(service, mixed, name):
    """FR-08 / NFR-08: SQL-looking enum filter is rejected, never executed."""
    with pytest.raises(ValidationError):
        service.list_tickets(**{name: "Open' OR '1'='1"})
    assert len(service.list_tickets()) == 7


def test_fr08_creator_filter_lone_surrogate_fails_cleanly(service, mixed):
    """FR-08 robustness: unencodable text in the creator filter must not escape as a raw
    UnicodeEncodeError (either no match or a TicketError)."""
    try:
        result = service.list_tickets(creator="\ud800")
    except TicketError:
        return
    assert result == []


def test_fr08_filtering_does_not_modify_data(service, mixed, snapshot):
    """FR-08, NFR-06: listing is read-only."""
    before = snapshot()
    service.list_tickets(status="Open", creator="ann")
    service.list_my_tickets("Bob")
    assert snapshot() == before


# ----------------------------------------------------------------- My tickets --------------


def test_ac66_fr26_my_tickets_returns_only_own_tickets_trimmed_case_insensitive(service, mixed):
    """AC-66 / FR-26: ' ann ' returns Ann's tickets only (both 'Ann' and 'ann' spellings)."""
    result = service.list_my_tickets(" ann ")
    assert ids(result) == [mixed["f"].id, mixed["c"].id, mixed["a"].id]
    assert {t.creator.casefold() for t in result} == {"ann"}
    assert mixed["b"].id not in ids(result)


def test_ac66_fr26_my_tickets_exposes_status_and_resolution_note(service, ticket_in_status):
    """AC-66 / FR-26, FR-07: status and resolution note are visible in each result."""
    ticket_in_status("Resolved", creator="Ann")
    (mine,) = service.list_my_tickets("Ann")
    assert mine.status == "Resolved"
    assert mine.resolution_note == "Fixed by QA fixture."


def test_ac66_fr26_name_without_tickets_returns_empty_list(service, mixed):
    """AC-66 / FR-26: unknown name -> [] (UI shows a 'no tickets' message)."""
    assert service.list_my_tickets("Nobody") == []
    assert service.list_my_tickets("An") == []  # exact match only


@pytest.mark.parametrize("blank", ["", "   ", "\t\n", None, 5, ["Ann"]], ids=repr)
def test_ac66_fr26_blank_or_invalid_name_is_rejected_and_never_means_all(service, mixed, blank):
    """AC-66 / FR-26 (IC S4): blank name raises ValidationError['creator'], never all tickets."""
    with pytest.raises(ValidationError) as exc:
        service.list_my_tickets(blank)  # type: ignore[arg-type]
    assert "creator" in exc.value.errors


def test_ac66_fr26_my_tickets_wildcards_and_injection_are_literal(service, mixed):
    """AC-66 / FR-26, NFR-08: % _ and SQL text never widen the match."""
    for text in ("%", "_", "A%", "Ann' OR '1'='1", "'; DROP TABLE tickets; --"):
        assert service.list_my_tickets(text) == []
    assert len(service.list_tickets()) == 7


def test_ac66_fr26_my_tickets_name_over_limit_is_rejected(service):
    """FR-26: list_my_tickets validates the name like a creator (limit 100)."""
    with pytest.raises(ValidationError):
        service.list_my_tickets("x" * 101)
    assert service.list_my_tickets("x" * 100) == []


def test_ac66_fr26_my_tickets_newest_first(service, make_ticket):
    """AC-66 / FR-26, FR-06: own tickets are newest first."""
    a = make_ticket(creator="Ann")
    b = make_ticket(creator="Ann")
    assert ids(service.list_my_tickets("Ann")) == [b.id, a.id]

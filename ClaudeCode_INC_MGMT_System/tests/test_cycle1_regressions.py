"""QA cycle 1 regression tests for the DEF-01, DEF-02 and DEF-03 fixes.

DEF-01 (AC-15, AC-29, FR-07, FR-09, FR-11, FR-15): ticket IDs outside SQLite's 64-bit range
  must give NotFoundError, never OverflowError/ValueError/StorageError.
DEF-02 (FR-08, AC-19): creator filter with non-storable text gives ValidationError on "creator".
DEF-03 (FR-02, AC-03..06): NUL anywhere / non-UTF-8-encodable text gives ValidationError that
  names the field; ordinary tabs, newlines, unicode and emoji are still accepted.

Note on docs/validation-rules.md: it states only non-UTF-8-encodable text is content-rejected.
The build also rejects NUL; the tests below pin the build behaviour (documented as doc drift).
"""

from __future__ import annotations

import logging

import pytest

from tests.helpers import VALID, raw_count
from ticketing import db
from ticketing.models import (
    NotFoundError,
    StorageError,
    TicketError,
    ValidationError,
)

INT64_MAX = 2**63 - 1
INT64_MIN = -(2**63)

OUT_OF_RANGE_IDS = [
    2**63,
    -(2**63) - 1,
    2**64,
    -(2**64),
    2**70,
    10**30,
    -(10**30),
    10**5000,  # 5001 digits: str() of this int raises ValueError (int max str digits)
    -(10**5000),
    10**4300,  # exactly at the str() digit limit +1 digit
    10**20000,
]
IN_RANGE_UNKNOWN_IDS = [INT64_MAX, INT64_MIN, 0, -1, 999_999]


def _call_each_operation(service, ticket_id):
    """Yield (name, callable) for the four ID-taking operations."""
    return [
        ("get_ticket", lambda: service.get_ticket(ticket_id)),
        ("change_status", lambda: service.change_status(ticket_id, "In Progress")),
        ("change_priority", lambda: service.change_priority(ticket_id, "Low")),
        ("set_resolution_note", lambda: service.set_resolution_note(ticket_id, "note")),
    ]


# --------------------------------------------------------------------- DEF-01 ----------------


@pytest.mark.parametrize(
    "ticket_id", OUT_OF_RANGE_IDS, ids=[f"id{i}" for i in range(len(OUT_OF_RANGE_IDS))]
)
def test_ac15_ac29_fr07_fr09_out_of_range_id_is_not_found_for_every_operation(
    service, make_ticket, snapshot, ticket_id
):
    """AC-15 / AC-29 / FR-07 / FR-09: IDs outside the 64-bit range -> NotFoundError (exactly)
    from get/status/priority/note, with a plain message and no data change."""
    make_ticket()
    before = snapshot()
    for name, call in _call_each_operation(service, ticket_id):
        with pytest.raises(NotFoundError) as exc:
            call()
        assert type(exc.value) is NotFoundError, name
        message = str(exc.value)
        assert "not found" in message, name
        assert len(message) < 100, f"{name}: message must not echo a 5000-digit number"
    assert snapshot() == before


@pytest.mark.parametrize("ticket_id", [2**63, -(2**63) - 1, 2**70, 10**30])
def test_ac15_fr07_moderately_large_id_message_names_the_id(service, ticket_id):
    """AC-15 / FR-07: when the ID can be rendered, the message is 'Ticket <id> was not found.'"""
    with pytest.raises(NotFoundError) as exc:
        service.get_ticket(ticket_id)
    assert str(exc.value) == f"Ticket {ticket_id} was not found."


def test_ac15_fr07_five_thousand_digit_id_message_is_generic_not_a_valueerror(service):
    """AC-15 / FR-07: a 5000-digit ID cannot be formatted with f-string; the helper falls back."""
    huge = 10**5000 - 1
    with pytest.raises(NotFoundError) as exc:
        service.get_ticket(huge)
    assert str(exc.value) == "Ticket was not found."
    with pytest.raises(NotFoundError):
        service.change_status(-huge, "In Progress")


@pytest.mark.parametrize("ticket_id", IN_RANGE_UNKNOWN_IDS, ids=repr)
def test_ac15_ac29_fr07_fr09_in_range_unknown_id_boundaries_are_not_found(
    service, make_ticket, snapshot, ticket_id
):
    """AC-15 / AC-29: 2**63-1 and -2**63 are valid SQLite integers; unknown -> NotFoundError."""
    make_ticket()
    before = snapshot()
    for name, call in _call_each_operation(service, ticket_id):
        with pytest.raises(NotFoundError) as exc:
            call()
        assert str(exc.value) == f"Ticket {ticket_id} was not found.", name
    assert snapshot() == before


def test_ac15_fr07_largest_storable_id_can_be_read_when_it_exists(service, db_path):
    """AC-15 / FR-07: the boundary ID 2**63-1 is queried (not short-circuited) when it exists."""
    import sqlite3

    service.create_ticket(**VALID)  # creates the table via the service
    conn = sqlite3.connect(str(db_path))
    try:
        conn.execute(
            "INSERT INTO tickets (id, title, description, category, priority, status, creator, "
            "created_at, updated_at) VALUES (?, 't', 'd', 'Other', 'Low', 'Open', 'c', "
            "'2026-10-24 09:00:00', '2026-10-24 09:00:00')",
            (INT64_MAX,),
        )
        conn.commit()
    finally:
        conn.close()
    assert service.get_ticket(INT64_MAX).id == INT64_MAX
    with pytest.raises(NotFoundError):
        service.get_ticket(INT64_MAX + 1)


@pytest.mark.parametrize("bad", [True, False, 1.0, 2.0**63, 1e30, float("inf"), "9" * 30, None])
def test_ac15_ac29_fr07_fr09_non_int_ids_are_still_validation_errors(service, make_ticket, bad):
    """AC-15 / AC-29: bool/float/str/None IDs are rejected as before the fix (never NotFound)."""
    make_ticket()
    for name, call in _call_each_operation(service, bad):
        with pytest.raises(ValidationError) as exc:
            call()
        assert exc.value.errors == {"ticket_id": "Ticket ID must be a whole number."}, name


def test_ac29_fr09_validation_errors_take_precedence_over_out_of_range_id(service, make_ticket):
    """AC-29 / FR-09: a bad status/priority/note alongside an out-of-range ID is collected as a
    ValidationError (field checks first), not NotFoundError."""
    make_ticket()
    with pytest.raises(ValidationError) as exc:
        service.change_status(2**70, "Bogus")
    assert set(exc.value.errors) == {"status"}
    with pytest.raises(ValidationError) as exc:
        service.change_priority(2**70, "Urgent")
    assert set(exc.value.errors) == {"priority"}
    with pytest.raises(ValidationError) as exc:
        service.set_resolution_note(2**70, "  ")
    assert set(exc.value.errors) == {"resolution_note"}


def test_ac15_fr07_out_of_range_lookup_is_not_a_storage_failure_and_logs_nothing(
    service, make_ticket, caplog
):
    """AC-15 / NFR-06: NotFound is a normal outcome: not StorageError, no error log record."""
    make_ticket()
    with caplog.at_level(logging.DEBUG):
        for ticket_id in (2**63, 10**5000):
            for _name, call in _call_each_operation(service, ticket_id):
                with pytest.raises(TicketError) as exc:
                    call()
                assert not isinstance(exc.value, StorageError)
    assert [r for r in caplog.records if r.levelno >= logging.WARNING] == []


def test_ac15_fr07_service_still_works_after_out_of_range_lookups(service, make_ticket):
    """AC-15: a failed huge-ID call leaves no open transaction/lock: writes still succeed."""
    ticket = make_ticket()
    for _name, call in _call_each_operation(service, 2**64):
        with pytest.raises(NotFoundError):
            call()
    assert service.change_status(ticket.id, "In Progress").status == "In Progress"
    assert service.create_ticket(**VALID).id == ticket.id + 1


def test_fr07_db_fetch_ticket_returns_none_outside_int64_and_row_inside(db_path, service):
    """FR-07 (db layer): fetch_ticket returns None for out-of-range IDs and does not raise."""
    ticket = service.create_ticket(**VALID)
    with db.session(db_path) as conn:
        assert db.fetch_ticket(conn, 2**63) is None
        assert db.fetch_ticket(conn, -(2**63) - 1) is None
        assert db.fetch_ticket(conn, 10**5000) is None
        assert db.fetch_ticket(conn, INT64_MAX) is None
        assert db.fetch_ticket(conn, INT64_MIN) is None
        assert db.fetch_ticket(conn, ticket.id)["id"] == ticket.id


# --------------------------------------------------------------------- DEF-02 ----------------

SURROGATES = ["\ud800", "\udfff", "a\ud800b", " \ud800 ", "abc\udfff"]


@pytest.mark.parametrize("value", SURROGATES, ids=repr)
def test_fr08_ac19_creator_filter_with_unstorable_text_is_validation_error_on_creator(
    service, make_ticket, snapshot, value
):
    """FR-08 / AC-19: non-UTF-8-encodable creator filter -> ValidationError keyed 'creator'."""
    make_ticket()
    before = snapshot()
    with pytest.raises(ValidationError) as exc:
        service.list_tickets(creator=value)
    assert set(exc.value.errors) == {"creator"}
    assert "cannot be stored" in exc.value.errors["creator"]
    assert snapshot() == before


@pytest.mark.parametrize("value", ["\x00", "a\x00b", "abc\x00", "\x00abc", " \x00 "], ids=repr)
def test_fr08_creator_filter_containing_nul_is_validation_error_on_creator(
    service, make_ticket, value
):
    """FR-08: NUL in the creator filter is rejected on key 'creator' (matches create_ticket)."""
    make_ticket()
    with pytest.raises(ValidationError) as exc:
        service.list_tickets(creator=value)
    assert set(exc.value.errors) == {"creator"}


def test_fr08_creator_filter_error_is_collected_with_other_filter_errors(service):
    """FR-08: a bad creator is reported together with an invalid status filter."""
    with pytest.raises(ValidationError) as exc:
        service.list_tickets(status="Nope", creator="\ud800")
    assert set(exc.value.errors) == {"status", "creator"}


def test_fr08_creator_filter_error_does_not_leave_the_service_broken(service, make_ticket):
    """FR-08: after the rejected filter, normal listing and filtering still work."""
    ticket = make_ticket(creator="Alice")
    with pytest.raises(ValidationError):
        service.list_tickets(creator="\ud800")
    assert [t.id for t in service.list_tickets(creator="alice")] == [ticket.id]
    assert [t.id for t in service.list_tickets()] == [ticket.id]


@pytest.mark.parametrize("blank", ["", "   ", "\t\n "], ids=repr)
def test_fr08_blank_creator_filter_still_means_no_filter(service, make_ticket, blank):
    """FR-08: whitespace-only creator filter is unchanged by the fix (no filter)."""
    make_ticket()
    make_ticket(creator="Bob")
    assert len(service.list_tickets(creator=blank)) == 2


@pytest.mark.parametrize("bad", [123, 1.5, True, ["a"], b"alice"], ids=repr)
def test_fr08_non_string_creator_filter_is_still_validation_error(service, bad):
    """FR-08: non-string creator filter still ValidationError on 'creator' (unchanged)."""
    with pytest.raises(ValidationError) as exc:
        service.list_tickets(creator=bad)
    assert set(exc.value.errors) == {"creator"}


@pytest.mark.parametrize("value", SURROGATES + ["\x00", "a\x00b"], ids=repr)
def test_ac66_fr26_my_tickets_rejects_unstorable_names(service, make_ticket, value):
    """FR-26 / AC-66: My tickets with a non-storable name -> ValidationError on 'creator'."""
    make_ticket()
    with pytest.raises(ValidationError) as exc:
        service.list_my_tickets(value)
    assert set(exc.value.errors) == {"creator"}


@pytest.mark.parametrize(
    "name", ["Zoë", "日本語 さん", "Alice \U0001f600", "O'Brien", "tab\tname", "ÄÖÜ"], ids=repr
)
def test_fr08_creator_filter_accepts_unicode_emoji_and_tabs(service, make_ticket, name):
    """FR-08: storable unicode/emoji/punctuation creator filters work (and match case-folded)."""
    ticket = make_ticket(creator=name)
    make_ticket(creator="Someone else")
    assert [t.id for t in service.list_tickets(creator=name)] == [ticket.id]
    assert [t.id for t in service.list_tickets(creator=name.upper())] == [ticket.id]
    assert [t.id for t in service.list_my_tickets(name)] == [ticket.id]


# --------------------------------------------------------------------- DEF-03 ----------------

TEXT_FIELDS = ["title", "description", "creator"]
NUL_VALUES = ["\x00", "\x00abc", "a\x00b", "abc\x00", "a\x00", "  \x00  ", " a\x00b ", "\x00\x00"]


@pytest.mark.parametrize("field", TEXT_FIELDS)
@pytest.mark.parametrize("value", NUL_VALUES, ids=repr)
def test_ac06_fr02_nul_anywhere_is_rejected_with_validation_message_naming_the_field(
    service, snapshot, field, value
):
    """FR-02 / AC-06: NUL at start, middle, end or alone -> ValidationError on exactly that
    field, nothing stored, and the ID counter is not consumed."""
    with pytest.raises(ValidationError) as exc:
        service.create_ticket(**{**VALID, field: value})
    assert set(exc.value.errors) == {field}
    assert "cannot be stored" in exc.value.errors[field]
    assert snapshot() == []
    assert service.create_ticket(**VALID).id == 1


@pytest.mark.parametrize("field", ["resolution_note"])
@pytest.mark.parametrize("value", ["\x00abc", "a\x00b", "abc\x00", "\x00"], ids=repr)
def test_ac36_fr15_fr02_nul_in_note_is_rejected_by_set_note_and_change_status(
    service, ticket_in_status, snapshot, field, value
):
    """AC-36 / FR-15: NUL in the resolution note is rejected on both entry points, unchanged."""
    ticket = ticket_in_status("In Progress")
    before = snapshot()
    with pytest.raises(ValidationError) as exc:
        service.set_resolution_note(ticket.id, value)
    assert set(exc.value.errors) == {field}
    with pytest.raises(ValidationError) as exc:
        service.change_status(ticket.id, "Resolved", value)
    assert set(exc.value.errors) == {field}
    assert snapshot() == before


def test_ac03_fr02_all_text_fields_with_nul_are_collected_in_one_error(service):
    """FR-02: all three NUL fields plus a bad category are reported together."""
    with pytest.raises(ValidationError) as exc:
        service.create_ticket("a\x00", "\x00b", "c\x00d", "Nope", "Low")
    assert set(exc.value.errors) == {"creator", "title", "description", "category"}


@pytest.mark.parametrize("field", TEXT_FIELDS)
def test_ac05_fr02_oversized_text_containing_nul_is_rejected_cleanly(service, snapshot, field):
    """AC-05 / FR-02: over-limit text that also contains NUL is still a ValidationError."""
    with pytest.raises(ValidationError) as exc:
        service.create_ticket(**{**VALID, field: "x" * 5000 + "\x00"})
    assert field in exc.value.errors
    assert snapshot() == []


@pytest.mark.parametrize("field", TEXT_FIELDS)
@pytest.mark.parametrize("value", ["\ud800", "a\udfffb"], ids=repr)
def test_ac06_fr02_surrogates_in_each_field_still_rejected_with_field_name(service, field, value):
    """FR-02: non-UTF-8-encodable text -> ValidationError naming the field (unchanged)."""
    with pytest.raises(ValidationError) as exc:
        service.create_ticket(**{**VALID, field: value})
    assert set(exc.value.errors) == {field}


ACCEPTED_TEXTS = [
    "line one\nline two",
    "tab\tseparated",
    "crlf\r\nline",
    "\ttabbed start",
    "café ñ ß Ünï",
    "日本語のテキスト",
    "עברית ועוד العربية",
    "emoji \U0001f600\U0001f4a5 done",
    "family \U0001f468‍\U0001f469‍\U0001f467",  # ZWJ sequence
    "combining é",
    "\U0010ffff max code point",
    "ctrl \x01 \x1f \x7f chars",
    "zero​width",
    "nbsp inside",
    "quote ' and \" and `",
    "backslash \\ and \\x00 literal text",
    "percent % and underscore _",
]


@pytest.mark.parametrize("field", TEXT_FIELDS)
@pytest.mark.parametrize("value", ACCEPTED_TEXTS, ids=repr)
def test_ac06_fr02_ordinary_special_text_is_still_accepted_and_roundtrips(
    service, db_path, field, value
):
    """AC-06 / FR-02: tabs, newlines, unicode, emoji, ZWJ and control chars except NUL are
    still accepted and stored literally (trimmed only)."""
    ticket = service.create_ticket(**{**VALID, field: value})
    assert getattr(ticket, field) == value.strip()
    from ticketing.service import TicketService

    reread = TicketService(db_path=db_path).get_ticket(ticket.id)  # new connection/service
    assert getattr(reread, field) == value.strip()


@pytest.mark.parametrize("value", ACCEPTED_TEXTS, ids=repr)
def test_ac36_fr15_ordinary_special_text_is_still_accepted_as_a_note(
    service, ticket_in_status, value
):
    """AC-36 / FR-15: the same texts are accepted as resolution notes."""
    ticket = ticket_in_status("In Progress")
    assert service.set_resolution_note(ticket.id, value).resolution_note == value.strip()
    assert service.change_status(ticket.id, "Resolved", value + "!").resolution_note == (
        (value + "!").strip()
    )


def test_ac05_fr02_boundary_length_text_with_emoji_is_still_accepted(service):
    """AC-05 / FR-02: exactly-at-limit text of astral characters is accepted (chars, not bytes)."""
    ticket = service.create_ticket(**{**VALID, "title": "\U0001f600" * 100})
    assert len(ticket.title) == 100
    with pytest.raises(ValidationError):
        service.create_ticket(**{**VALID, "title": "\U0001f600" * 100 + "\x00"})


def test_nfr06_rejected_nul_text_does_not_log_a_storage_failure(service, caplog):
    """NFR-06: a NUL validation failure is not a storage failure (no ERROR log record)."""
    with caplog.at_level(logging.DEBUG):
        with pytest.raises(ValidationError):
            service.create_ticket(**{**VALID, "title": "\x00abc"})
    assert [r for r in caplog.records if r.levelno >= logging.ERROR] == []


def test_ac55_nfr06_nul_rejection_leaves_database_row_count_unchanged(
    service, db_path, make_ticket
):
    """AC-55: rejected NUL create after a successful create leaves exactly one row."""
    make_ticket()
    for value in ("\x00", "a\x00b", "abc\x00"):
        with pytest.raises(ValidationError):
            service.create_ticket(**{**VALID, "description": value})
    assert raw_count(db_path) == 1


# ------------------------------------------------------- UI (AppTest) behaviour for DEF-03 ----


@pytest.mark.parametrize(
    ("field", "label"),
    [("creator", "Your name"), ("title", "Title"), ("description", "Description")],
)
@pytest.mark.parametrize("value", ["a\x00b", "\x00x", "x\x00"], ids=repr)
def test_ac03_ac06_fr02_ui_form_with_nul_shows_named_error_and_creates_nothing(
    new_app, ui_service, field, label, value
):
    """AC-03 / AC-06 / FR-02: the create form shows a message naming the field (no crash)."""
    at = new_app("Employee")
    values = {"creator": "Alice", "title": "Printer jam", "description": "Jammed."}
    values[field] = value
    at.text_input(key="create_creator_0").input(values["creator"])
    at.text_input(key="create_title_0").input(values["title"])
    at.text_area(key="create_description_0").input(values["description"])
    at.button(key="create_submit_0").click().run()
    assert len(at.exception) == 0
    assert [e.value for e in at.error] == [f"{label} contains characters that cannot be stored."]
    assert ui_service.list_tickets() == []


@pytest.mark.parametrize(
    "value", ["a\x00b", "\x00"], ids=repr
)  # lone surrogates cannot be sent via the widget protocol
def test_ac66_fr26_ui_my_tickets_name_with_unstorable_text_does_not_crash(
    new_app, ui_service, value
):
    """AC-66 / FR-26: an unstorable name in My tickets shows an error, not an exception."""
    ui_service.create_ticket(**VALID)
    at = new_app("Employee")
    at.text_input(key="my_tickets_name").input(value).run()
    assert len(at.exception) == 0

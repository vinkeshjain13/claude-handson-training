"""L2 service tests: ticket creation and validation.

Covers AC-01..AC-11, AC-33 (create part), AC-67 and FR-01..FR-05, FR-13, FR-25.
"""

from __future__ import annotations

import re
import sqlite3
import threading

import pytest

from tests.helpers import SPECIAL_TEXTS, VALID, raw_count, raw_rows
from ticketing import config
from ticketing.models import Ticket, TicketError, ValidationError

TS_RE = re.compile(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$")
TEXT_FIELDS = ["creator", "title", "description"]
LABELS = {"creator": "Your name", "title": "Title", "description": "Description"}


# ---------------------------------------------------------------- happy path -----------------


def test_ac01_fr01_valid_ticket_is_created_and_listed(service):
    """AC-01 / FR-01: valid submission creates a ticket that shows up in the list."""
    ticket = service.create_ticket(**VALID)
    assert isinstance(ticket, Ticket)
    assert isinstance(ticket.id, int) and ticket.id >= 1
    assert [t.id for t in service.list_tickets()] == [ticket.id]


def test_ac02_fr01_fr07_stored_values_equal_input(service):
    """AC-02 / FR-01, FR-07: details equal what was entered."""
    ticket = service.create_ticket(**VALID)
    again = service.get_ticket(ticket.id)
    for field, value in VALID.items():
        assert getattr(ticket, field) == value
        assert getattr(again, field) == value
    assert again == ticket


def test_ac02_fr02_text_fields_are_trimmed(service):
    """AC-02 / FR-02: surrounding whitespace is removed, inner whitespace kept."""
    ticket = service.create_ticket(
        creator="  Alice  ",
        title="\tPrinter   jam\n",
        description="  line1\nline2  \n",
        category="Hardware",
        priority="High",
    )
    assert ticket.creator == "Alice"
    assert ticket.title == "Printer   jam"
    assert ticket.description == "line1\nline2"
    assert service.get_ticket(ticket.id).title == "Printer   jam"


def test_ac11_fr05_new_ticket_status_is_open(service):
    """AC-11 / FR-05: new tickets are Open, no resolution note."""
    ticket = service.create_ticket(**VALID)
    assert ticket.status == "Open" == config.DEFAULT_STATUS
    assert ticket.resolution_note == ""


def test_ac33_fr13_new_ticket_updated_at_equals_created_at(service, fake_clock):
    """AC-33 / FR-13 (create part): created_at == updated_at, system-set from the clock."""
    ticket = service.create_ticket(**VALID)
    assert ticket.created_at == ticket.updated_at == fake_clock.stamp == "2026-10-24 09:00:00"
    assert TS_RE.match(ticket.created_at)


def test_ac09_fr04_ids_increase_and_created_at_not_earlier(service, fake_clock):
    """AC-09 / FR-04: IDs differ and increase; created_at of the second is not earlier."""
    first = service.create_ticket(**VALID)
    fake_clock.advance(90)
    second = service.create_ticket(**VALID)
    assert second.id > first.id
    assert first.created_at and second.created_at
    assert second.created_at >= first.created_at
    assert second.created_at == "2026-10-24 09:01:30"


def test_ac09_fr04_ids_are_never_reused_after_deletion(service, db_path):
    """AC-09 / FR-04: AUTOINCREMENT semantics. A deleted highest ID is not handed out again."""
    t1 = service.create_ticket(**VALID)
    t2 = service.create_ticket(**VALID)
    conn = sqlite3.connect(str(db_path))
    conn.execute("DELETE FROM tickets WHERE id = ?", (t2.id,))
    conn.commit()
    conn.close()
    t3 = service.create_ticket(**VALID)
    assert t3.id > t2.id > t1.id


def test_ac09_fr04_failed_create_does_not_consume_or_leave_rows(service, db_path):
    """AC-09 / FR-04: a rejected submission creates no row and no gap in IDs."""
    first = service.create_ticket(**VALID)
    with pytest.raises(ValidationError):
        service.create_ticket(**{**VALID, "title": ""})
    second = service.create_ticket(**VALID)
    assert second.id == first.id + 1
    assert raw_count(db_path) == 2


def test_ac10_fr04_asm13_identical_submissions_create_two_tickets(service):
    """AC-10 / FR-04 (ASM-13): duplicates are allowed and get distinct IDs."""
    a = service.create_ticket(**VALID)
    b = service.create_ticket(**VALID)
    assert a.id != b.id
    assert (a.title, a.description, a.creator) == (b.title, b.description, b.creator)
    assert len(service.list_tickets()) == 2


def test_ac10_fr04_many_repeated_creates_get_unique_ids(service):
    """AC-10 / FR-04: 60 identical creates in a row all succeed with unique increasing IDs."""
    ids = [service.create_ticket(**VALID).id for _ in range(60)]
    assert ids == sorted(set(ids))
    assert len(ids) == 60


def test_ac10_fr04_concurrent_creates_from_threads_have_unique_ids(db_path, fake_clock):
    """AC-10 / FR-04, NFR-06: several services on one file creating concurrently."""
    from ticketing.service import TicketService

    TicketService(db_path=db_path, clock=fake_clock)  # create schema once
    ids: list[int] = []
    errors: list[BaseException] = []
    lock = threading.Lock()

    def worker():
        try:
            svc = TicketService(db_path=db_path, clock=fake_clock)
            for _ in range(5):
                t = svc.create_ticket(**VALID)
                with lock:
                    ids.append(t.id)
        except BaseException as exc:  # pragma: no cover - only on failure
            errors.append(exc)

    threads = [threading.Thread(target=worker) for _ in range(6)]
    for th in threads:
        th.start()
    for th in threads:
        th.join()
    assert not errors
    assert len(ids) == 30 and len(set(ids)) == 30
    assert raw_count(db_path) == 30


# ------------------------------------------------------- required-field validation ------------


@pytest.mark.parametrize("field", TEXT_FIELDS)
@pytest.mark.parametrize(
    "bad", ["", "   ", "\t\n  \r\n", None], ids=["empty", "spaces", "ws", "none"]
)
def test_ac03_fr02_empty_required_text_is_rejected_with_field_message(service, db_path, field, bad):
    """AC-03 / FR-02: empty creator/title/description is rejected, message names the field."""
    with pytest.raises(ValidationError) as exc:
        service.create_ticket(**{**VALID, field: bad})
    assert set(exc.value.errors) == {field}
    assert exc.value.errors[field] == f"{LABELS[field]} is required."
    assert LABELS[field] in str(exc.value)
    assert raw_count(db_path) == 0
    assert service.get_dashboard_stats().total == 0


@pytest.mark.parametrize("field", TEXT_FIELDS)
@pytest.mark.parametrize(
    "ws",
    ["     ", "\t\t", "\n\n", " \t\r\n ", "  ", "　"],
    ids=["spaces", "tabs", "newlines", "mixed", "nbsp-emsp", "ideographic"],
)
def test_ac04_fr02_whitespace_only_text_counts_as_empty(service, field, ws):
    """AC-04 / FR-02: whitespace-only (incl. unicode spaces) is treated as empty."""
    with pytest.raises(ValidationError) as exc:
        service.create_ticket(**{**VALID, field: ws})
    assert exc.value.errors[field] == f"{LABELS[field]} is required."
    assert service.list_tickets() == []


@pytest.mark.parametrize("field", TEXT_FIELDS)
@pytest.mark.parametrize("bad", [123, 4.5, ["a"], b"bytes", {"a": 1}, True], ids=repr)
def test_ac03_fr02_non_string_text_is_rejected(service, field, bad):
    """AC-03 / FR-02: non-str text values (IC section 5) raise ValidationError."""
    with pytest.raises(ValidationError) as exc:
        service.create_ticket(**{**VALID, field: bad})
    assert field in exc.value.errors
    assert service.list_tickets() == []


def test_ac03_fr02_missing_arguments_raise_type_error(service):
    """AC-03 / FR-02: omitting a required argument is a programming error, no ticket is made."""
    with pytest.raises(TypeError):
        service.create_ticket("Alice", "Title")  # type: ignore[call-arg]
    assert service.list_tickets() == []


def test_ac03_fr02_all_errors_are_collected_in_one_validation_error(service, db_path):
    """AC-03 / FR-02: several invalid fields are reported together, nothing stored."""
    with pytest.raises(ValidationError) as exc:
        service.create_ticket(creator="", title="  ", description=None, category="x", priority="y")
    assert set(exc.value.errors) == {"creator", "title", "description", "category", "priority"}
    text = str(exc.value)
    for label in ("Your name", "Title", "Description", "Category", "Priority"):
        assert label in text
    assert raw_count(db_path) == 0


def test_ac03_fr02_two_invalid_fields_only_reports_those_two(service):
    """AC-03 / FR-02: valid fields do not appear in errors."""
    with pytest.raises(ValidationError) as exc:
        service.create_ticket(**{**VALID, "title": "", "priority": "Urgent"})
    assert set(exc.value.errors) == {"title", "priority"}


# --------------------------------------------------------------------- length limits ---------


@pytest.mark.parametrize("field", TEXT_FIELDS)
def test_ac05_fr02_exactly_at_limit_is_accepted(service, field):
    """AC-05 / FR-02: exactly 100 / 100 / 2000 characters is accepted."""
    limit = config.LIMITS[field]
    assert limit == {"creator": 100, "title": 100, "description": 2000}[field]
    value = "x" * limit
    ticket = service.create_ticket(**{**VALID, field: value})
    assert getattr(service.get_ticket(ticket.id), field) == value


@pytest.mark.parametrize("field", TEXT_FIELDS)
def test_ac05_fr02_one_over_limit_is_rejected_with_limit_in_message(service, db_path, field):
    """AC-05 / FR-02: limit + 1 rejected, message states the limit and the entered length."""
    limit = config.LIMITS[field]
    with pytest.raises(ValidationError) as exc:
        service.create_ticket(**{**VALID, field: "x" * (limit + 1)})
    message = exc.value.errors[field]
    assert str(limit) in message and str(limit + 1) in message
    assert message == (
        f"{LABELS[field]} must be at most {limit} characters (you entered {limit + 1})."
    )
    assert raw_count(db_path) == 0


@pytest.mark.parametrize("field", TEXT_FIELDS)
def test_ac05_fr02_surrounding_whitespace_does_not_count_toward_limit(service, field):
    """AC-05 / FR-02 (VR section 2): limit counts trimmed characters only."""
    limit = config.LIMITS[field]
    ticket = service.create_ticket(**{**VALID, field: "  " + "y" * limit + "\n\t "})
    assert getattr(ticket, field) == "y" * limit


@pytest.mark.parametrize("field", TEXT_FIELDS)
def test_ac05_fr02_limit_counts_characters_not_bytes(service, field):
    """AC-05 / FR-02: multi-byte characters count once each (code points)."""
    limit = config.LIMITS[field]
    value = "\U0001f600" * limit
    assert len(service.create_ticket(**{**VALID, field: value}).__dict__[field]) == limit
    with pytest.raises(ValidationError):
        service.create_ticket(**{**VALID, field: value + "\U0001f600"})


@pytest.mark.parametrize("field", TEXT_FIELDS)
def test_edge_fr02_hugely_oversized_input_is_rejected_cleanly(service, db_path, field):
    """FR-02: a 1 MB value is rejected with a validation message, nothing stored."""
    with pytest.raises(ValidationError) as exc:
        service.create_ticket(**{**VALID, field: "z" * 1_000_000})
    assert "1000000" in exc.value.errors[field]
    assert raw_count(db_path) == 0


# -------------------------------------------------------------- special characters -----------


@pytest.mark.parametrize("text", SPECIAL_TEXTS, ids=range(len(SPECIAL_TEXTS)))
def test_ac06_fr02_special_characters_roundtrip_literally(service, db_path, text):
    """AC-06 / FR-02: special text is stored/returned exactly (after trim); DB stays intact."""
    other = service.create_ticket(**VALID)
    before = raw_rows(db_path)
    ticket = service.create_ticket(
        creator=text, title=text, description=text, category="Software", priority="Low"
    )
    stored = service.get_ticket(ticket.id)
    assert stored.title == stored.creator == stored.description == text.strip()
    assert raw_count(db_path) == 2
    assert raw_rows(db_path)[0] == before[0]  # other tickets unchanged
    assert service.get_ticket(other.id) == other


@pytest.mark.parametrize("text", ["\x01\x02 control", "zero​width", "﻿bom", "\x7f del"])
def test_ac06_fr02_control_and_invisible_characters_roundtrip(service, text):
    """AC-06 / FR-02: control/invisible characters are stored literally when not whitespace."""
    ticket = service.create_ticket(**{**VALID, "title": text, "description": text})
    assert service.get_ticket(ticket.id).title == text.strip()


def test_ac06_fr02_description_keeps_internal_line_breaks(service):
    """AC-06 / FR-02: line breaks in the description are kept exactly."""
    text = "first line\n\nthird line\r\nfourth"
    assert service.create_ticket(**{**VALID, "description": text}).description == text


def test_ac06_nfr08_sql_injection_text_does_not_damage_table(service, db_path):
    """AC-06 / NFR-08: SQL-looking text is data; the table and other rows survive."""
    first = service.create_ticket(**VALID)
    evil = "x'); DROP TABLE tickets; --"
    ticket = service.create_ticket(**{**VALID, "title": evil, "creator": evil, "description": evil})
    assert service.get_ticket(ticket.id).title == evil
    assert raw_count(db_path) == 2
    assert service.get_ticket(first.id) == first


def test_edge_fr02_lone_surrogate_is_rejected_with_cannot_be_stored(service, db_path):
    """FR-02 (VR section 5): text that cannot be encoded as UTF-8 is a validation error."""
    with pytest.raises(ValidationError) as exc:
        service.create_ticket(**{**VALID, "title": "bad \ud800 text"})
    assert exc.value.errors["title"] == "Title contains characters that cannot be stored."
    assert raw_count(db_path) == 0


@pytest.mark.parametrize("field", TEXT_FIELDS)
def test_edge_fr02_lone_surrogate_in_each_text_field(service, field):
    """FR-02: every text field rejects unencodable text instead of crashing."""
    with pytest.raises(ValidationError) as exc:
        service.create_ticket(**{**VALID, field: "\udfff"})
    assert "cannot be stored" in exc.value.errors[field]


@pytest.mark.parametrize("field", ["title", "description", "creator"])
@pytest.mark.parametrize("value", ["a\x00b", "\x00", "\x00abc", "abc\x00"], ids=repr)
def test_edge_fr02_nul_character_is_stored_literally_or_rejected_with_validation_message(
    service, field, value
):
    """FR-02 robustness: text containing NUL is either stored literally or rejected with a
    ValidationError naming the field. A generic StorageError ('could not be read or saved')
    is not an acceptable answer to a user input problem."""
    try:
        ticket = service.create_ticket(**{**VALID, field: value})
    except ValidationError as exc:
        assert field in exc.errors
        return
    assert getattr(service.get_ticket(ticket.id), field) == value.strip()


# ----------------------------------------------------- priority / category choices -----------


def test_ac07_fr03_priority_options_and_default_are_as_specified():
    """AC-07 / FR-03: exactly Low, Medium, High, Critical with Medium as default."""
    assert config.PRIORITIES == ("Low", "Medium", "High", "Critical")
    assert config.DEFAULT_PRIORITY == "Medium"


@pytest.mark.parametrize("priority", ["Low", "Medium", "High", "Critical"])
def test_ac07_fr03_every_listed_priority_is_accepted(service, priority):
    """AC-07 / FR-03: each listed priority can be used at creation."""
    assert service.create_ticket(**{**VALID, "priority": priority}).priority == priority


@pytest.mark.parametrize(
    "bad",
    ["Urgent", "", "   ", "high", "HIGH", " High", "High ", "Medium\n", None, 3, ["High"], True],
    ids=repr,
)
def test_ac08_fr03_invalid_priority_is_rejected(service, db_path, bad):
    """AC-08 / FR-03: values outside the list (exact, case-sensitive) are rejected."""
    with pytest.raises(ValidationError) as exc:
        service.create_ticket(**{**VALID, "priority": bad})
    assert set(exc.value.errors) == {"priority"}
    assert exc.value.errors["priority"] == "Priority must be one of: Low, Medium, High, Critical."
    assert raw_count(db_path) == 0


def test_ac67_fr25_category_options_and_default_are_as_specified():
    """AC-67 / FR-25: exact category list with Other as default."""
    assert config.CATEGORIES == ("Hardware", "Software", "Network", "Account Access", "Other")
    assert config.DEFAULT_CATEGORY == "Other"


@pytest.mark.parametrize("category", ["Hardware", "Software", "Network", "Account Access", "Other"])
def test_ac67_fr25_every_listed_category_is_accepted(service, category):
    """AC-67 / FR-25: each listed category can be used at creation."""
    assert service.create_ticket(**{**VALID, "category": category}).category == category


@pytest.mark.parametrize(
    "bad",
    [
        "Printers",
        "",
        "  ",
        "hardware",
        "HARDWARE",
        "account access",
        "Network ",
        None,
        1,
        ["Other"],
    ],
    ids=repr,
)
def test_ac67_fr25_invalid_category_is_rejected(service, db_path, bad):
    """AC-67 / FR-25, FR-02: unknown/wrong-case/empty/non-str category is rejected."""
    with pytest.raises(ValidationError) as exc:
        service.create_ticket(**{**VALID, "category": bad})
    assert set(exc.value.errors) == {"category"}
    assert exc.value.errors["category"] == (
        "Category must be one of: Hardware, Software, Network, Account Access, Other."
    )
    assert raw_count(db_path) == 0


def test_ac67_fr25_category_cannot_be_changed_after_creation(service):
    """FR-25: the service offers no category-change operation."""
    assert not hasattr(service, "change_category")
    assert not hasattr(service, "update_ticket")


def test_ac01_fr01_create_has_no_way_to_set_status_or_id(service):
    """FR-04, FR-05: system-set values cannot be supplied by the caller."""
    with pytest.raises(TypeError):
        service.create_ticket(**VALID, status="Closed")  # type: ignore[call-arg]
    with pytest.raises(TypeError):
        service.create_ticket(**VALID, id=99)  # type: ignore[call-arg]


def test_ac55_nfr06_rejected_create_leaves_database_identical(service, db_path):
    """AC-55 / NFR-06: invalid creates change nothing."""
    service.create_ticket(**VALID)
    before = raw_rows(db_path)
    for bad in (
        {"title": ""},
        {"priority": "Urgent"},
        {"category": "Printers"},
        {"description": "x" * 2001},
    ):
        with pytest.raises(TicketError):
            service.create_ticket(**{**VALID, **bad})
    assert raw_rows(db_path) == before

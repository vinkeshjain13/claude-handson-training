"""L2 persistence, integrity, error-translation and timing tests.

Covers AC-47, AC-48, AC-54 (service-level timing), AC-55, AC-56 and NFR-01, NFR-05, NFR-06.
"""

from __future__ import annotations

import logging
import sqlite3
import time

import pytest

from tests.helpers import SPECIAL_TEXTS, VALID, FakeClock, raw_count, raw_rows
from ticketing import db
from ticketing.models import (
    StorageError,
    TicketError,
    TicketStateError,
    ValidationError,
)
from ticketing.service import TicketService

STORAGE_MESSAGE = "The ticket data could not be read or saved. Please try again."


def build_history(service, fake_clock):
    """Create tickets with changed statuses/priorities/notes; returns the final ticket list."""
    a = service.create_ticket(**VALID)
    fake_clock.advance(10)
    b = service.create_ticket(**{**VALID, "title": "Second", "creator": "Bob", "category": "Other"})
    fake_clock.advance(10)
    c = service.create_ticket(**{**VALID, "title": "Third \U0001f600 'q'", "priority": "Low"})
    fake_clock.advance(10)
    service.change_status(a.id, "In Progress")
    service.change_status(a.id, "Resolved", "Toner replaced.\nSecond line")
    service.change_priority(b.id, "Critical")
    service.set_resolution_note(c.id, "Waiting for part")
    fake_clock.advance(10)
    service.change_status(a.id, "Closed")
    return service.list_tickets()


def test_ac47_nfr01_new_service_on_same_file_sees_every_field_and_dashboard(db_path, fake_clock):
    """AC-47 / NFR-01: a restart (new TicketService, same file) shows identical data."""
    first = TicketService(db_path=db_path, clock=fake_clock)
    tickets = build_history(first, fake_clock)
    stats = first.get_dashboard_stats()
    del first

    second = TicketService(db_path=db_path, clock=FakeClock())
    assert second.list_tickets() == tickets
    for t in tickets:
        assert second.get_ticket(t.id) == t
    assert second.get_dashboard_stats() == stats
    assert [t.status for t in tickets].count("Closed") == 1


def test_ac47_nfr01_data_survives_updates_across_restarts(db_path, fake_clock):
    """AC-47 / NFR-01: update through one instance, read through another, repeatedly."""
    created = TicketService(db_path=db_path, clock=fake_clock).create_ticket(**VALID)
    for step, note in (("In Progress", None), ("Resolved", "done")):
        fake_clock.advance(60)
        TicketService(db_path=db_path, clock=fake_clock).change_status(created.id, step, note)
        again = TicketService(db_path=db_path).get_ticket(created.id)
        assert again.status == step
    assert again.resolution_note == "done"
    assert again.updated_at == "2026-10-24 09:02:00"
    assert again.created_at == created.created_at


def test_ac48_nfr01_data_visible_after_connection_is_closed_and_reopened(db_path, fake_clock):
    """AC-48 / NFR-01: no state is held in a connection; repeated reads agree."""
    svc = TicketService(db_path=db_path, clock=fake_clock)
    t = svc.create_ticket(**VALID)
    first = svc.list_tickets()
    # Raw connection opened and closed in between must not disturb anything.
    conn = sqlite3.connect(str(db_path))
    conn.close()
    assert svc.list_tickets() == first == [t]


@pytest.mark.parametrize("text", SPECIAL_TEXTS[:8], ids=range(8))
def test_ac47_ac06_special_characters_survive_restart(db_path, text):
    """AC-47 / NFR-01, AC-06: special text persists byte-for-byte across instances."""
    t = TicketService(db_path=db_path).create_ticket(
        creator="Zed", title=text, description=text, category="Other", priority="Low"
    )
    assert TicketService(db_path=db_path).get_ticket(t.id).title == text.strip()


def test_ac47_nfr01_schema_creation_is_idempotent(db_path, fake_clock):
    """NFR-01: constructing services repeatedly neither fails nor changes stored data."""
    svc = TicketService(db_path=db_path, clock=fake_clock)
    t = svc.create_ticket(**VALID)
    for _ in range(5):
        TicketService(db_path=db_path, clock=fake_clock)
    assert TicketService(db_path=db_path).list_tickets() == [t]
    conn = sqlite3.connect(str(db_path))
    names = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")]
    conn.close()
    assert names.count("tickets") == 1


def test_ac56_nfr07_database_file_is_created_inside_tmp_path_only(tmp_path, db_path):
    """AC-56 / NFR-07: the fixture DB lives in tmp_path; the parent dir is created if needed."""
    assert not db_path.exists()
    TicketService(db_path=db_path)
    assert db_path.exists() and db_path.parent == tmp_path
    nested = tmp_path / "a" / "b" / "c.db"
    TicketService(db_path=nested)
    assert nested.exists()
    assert not list(tmp_path.glob("**/tickets.db"))


def test_ac56_nfr07_str_path_and_path_object_are_both_accepted(tmp_path):
    """NFR-07: db_path may be str or Path."""
    TicketService(db_path=str(tmp_path / "s.db")).create_ticket(**VALID)
    assert TicketService(db_path=tmp_path / "s.db").list_tickets()


def test_ac56_nfr07_two_databases_do_not_share_data(tmp_path):
    """NFR-07: separate files are independent."""
    a = TicketService(db_path=tmp_path / "a.db")
    b = TicketService(db_path=tmp_path / "b.db")
    a.create_ticket(**VALID)
    assert len(a.list_tickets()) == 1 and b.list_tickets() == []


# ----------------------------------------------------------------- integrity (AC-55) -------


def test_ac55_nfr06_rejected_operations_leave_snapshot_identical(
    service, make_ticket, ticket_in_status, snapshot, fake_clock
):
    """AC-55 / NFR-06: invalid create, invalid transition, unknown ID, invalid priority/category
    leave the stored data byte-identical."""
    open_t = make_ticket()
    closed_t = ticket_in_status("Closed", title="Closed one")
    before = snapshot()
    fake_clock.advance(999)
    rejected = [
        lambda: service.create_ticket("", "t", "d", "Other", "Low"),
        lambda: service.create_ticket("c", "t", "d", "Printers", "Low"),
        lambda: service.create_ticket("c", "t", "d", "Other", "Urgent"),
        lambda: service.create_ticket("c", "x" * 101, "d", "Other", "Low"),
        lambda: service.change_status(open_t.id, "Closed"),
        lambda: service.change_status(open_t.id, "Resolved", "n"),
        lambda: service.change_status(open_t.id, "Open"),
        lambda: service.change_status(open_t.id, "Nope"),
        lambda: service.change_status(9999, "In Progress"),
        lambda: service.change_status(closed_t.id, "In Progress"),
        lambda: service.change_priority(open_t.id, "Urgent"),
        lambda: service.change_priority(open_t.id, open_t.priority),
        lambda: service.change_priority(closed_t.id, "Low"),
        lambda: service.change_priority(9999, "Low"),
        lambda: service.set_resolution_note(open_t.id, "   "),
        lambda: service.set_resolution_note(open_t.id, "n" * 1001),
        lambda: service.set_resolution_note(closed_t.id, "late"),
        lambda: service.set_resolution_note(9999, "note"),
        lambda: service.get_ticket(9999),
        lambda: service.list_tickets(status="Bogus"),
        lambda: service.list_my_tickets(""),
    ]
    for call in rejected:
        with pytest.raises(TicketError):
            call()
    assert snapshot() == before


def test_ac55_nfr06_failed_status_change_with_note_does_not_partially_apply(
    service, ticket_in_status, snapshot
):
    """AC-55 / NFR-06: a rejected combined status+note change stores neither part."""
    t = ticket_in_status("Open")
    before = snapshot()
    with pytest.raises(TicketStateError):
        service.change_status(t.id, "Closed", "this note must not be saved")
    assert snapshot() == before
    assert service.get_ticket(t.id).resolution_note == ""


def test_ac55_nfr06_storage_error_during_insert_leaves_no_row(service, db_path, monkeypatch):
    """AC-55 / NFR-06: a forced sqlite3.Error becomes StorageError and no row is written."""

    def boom(*args, **kwargs):
        raise sqlite3.OperationalError("disk I/O error (simulated)")

    monkeypatch.setattr(db, "insert_ticket", boom)
    with pytest.raises(StorageError) as exc:
        service.create_ticket(**VALID)
    assert str(exc.value) == STORAGE_MESSAGE
    assert isinstance(exc.value.__cause__, sqlite3.OperationalError)
    assert raw_count(db_path) == 0


def test_ac55_nfr06_storage_error_during_update_rolls_back(
    service, make_ticket, monkeypatch, snapshot
):
    """AC-55 / NFR-06: failure after the fetch step rolls the transaction back."""
    t = make_ticket()
    before = snapshot()

    def boom(*args, **kwargs):
        raise sqlite3.OperationalError("simulated")

    monkeypatch.setattr(db, "update_ticket", boom)
    with pytest.raises(StorageError):
        service.change_status(t.id, "In Progress")
    with pytest.raises(StorageError):
        service.change_priority(t.id, "Low")
    with pytest.raises(StorageError):
        service.set_resolution_note(t.id, "n")
    assert snapshot() == before


# ------------------------------------------------------------ StorageError translation -----


def test_nfr06_dropped_table_is_translated_to_storage_error(service, make_ticket, db_path):
    """NFR-06: 'no such table' (unusable DB) surfaces as StorageError on every read/write."""
    t = make_ticket()
    conn = sqlite3.connect(str(db_path))
    conn.execute("DROP TABLE tickets")
    conn.commit()
    conn.close()
    calls = [
        lambda: service.create_ticket(**VALID),
        lambda: service.get_ticket(t.id),
        lambda: service.list_tickets(),
        lambda: service.list_my_tickets("Alice"),
        lambda: service.change_status(t.id, "In Progress"),
        lambda: service.change_priority(t.id, "Low"),
        lambda: service.set_resolution_note(t.id, "n"),
        lambda: service.get_dashboard_stats(),
    ]
    for call in calls:
        with pytest.raises(StorageError) as exc:
            call()
        assert str(exc.value) == STORAGE_MESSAGE


def test_nfr06_directory_as_database_path_is_translated_to_storage_error(tmp_path):
    """NFR-06: pointing the DB at a directory gives StorageError, not a raw sqlite3 error."""
    with pytest.raises(StorageError) as exc:
        TicketService(db_path=tmp_path)
    assert str(exc.value) == STORAGE_MESSAGE


def test_nfr06_non_database_file_is_translated_to_storage_error(tmp_path):
    """NFR-06: a garbage file at the DB path gives StorageError."""
    bad = tmp_path / "garbage.db"
    bad.write_bytes(b"this is definitely not a sqlite database file" * 50)
    with pytest.raises(StorageError):
        TicketService(db_path=bad).list_tickets()


def test_nfr06_parent_path_is_a_file_is_translated_to_storage_error(tmp_path):
    """NFR-06: DB path below a regular file (cannot create directory) -> StorageError."""
    blocker = tmp_path / "blocker"
    blocker.write_text("x")
    with pytest.raises(StorageError):
        TicketService(db_path=blocker / "sub" / "t.db")


def test_nfr06_storage_error_message_and_log_do_not_leak_ticket_text(
    service, db_path, monkeypatch, caplog
):
    """NFR-06 (IC 8): StorageError text is generic; the log holds ID and exception class only."""
    secret = "SECRET-TICKET-TEXT-12345"
    t = service.create_ticket(**{**VALID, "title": secret})
    conn = sqlite3.connect(str(db_path))
    conn.execute("DROP TABLE tickets")
    conn.commit()
    conn.close()
    with caplog.at_level(logging.ERROR, logger="ticketing"):
        with pytest.raises(StorageError) as exc:
            service.change_status(t.id, "In Progress", secret)
    assert secret not in str(exc.value)
    assert caplog.records, "expected one logged storage failure"
    for record in caplog.records:
        assert secret not in record.getMessage()
        assert "OperationalError" in record.getMessage()


def test_nfr06_validation_errors_are_not_logged_as_storage_failures(service, caplog):
    """NFR-06: normal rejections do not produce error-level storage logs."""
    with caplog.at_level(logging.ERROR, logger="ticketing"):
        with pytest.raises(ValidationError):
            service.create_ticket("", "", "", "x", "y")
    assert caplog.records == []


# --------------------------------------------------------------------- timing (AC-54) -----


def test_ac54_nfr05_list_and_dashboard_with_1000_tickets_load_within_2_seconds(
    service, db_path, record_property
):
    """AC-54 / NFR-05 (service level): 1,000 tickets, list and dashboard each <= 2 s."""
    with db.session(db_path, write=True) as conn:
        for n in range(1000):
            db.insert_ticket(
                conn,
                title=f"Ticket {n}",
                description="d" * 200,
                category="Other",
                priority="Medium",
                status="Open",
                creator=f"User{n % 25}",
                created_at="2026-10-24 09:00:00",
                updated_at="2026-10-24 09:00:00",
            )
    t0 = time.perf_counter()
    listed = service.list_tickets()
    t_list = time.perf_counter() - t0
    t0 = time.perf_counter()
    stats = service.get_dashboard_stats()
    t_dash = time.perf_counter() - t0
    t0 = time.perf_counter()
    mine = service.list_my_tickets("user3")
    t_mine = time.perf_counter() - t0
    record_property("list_tickets_seconds", round(t_list, 4))
    record_property("dashboard_seconds", round(t_dash, 4))
    record_property("list_my_tickets_seconds", round(t_mine, 4))
    print(f"\nAC-54 timing: list={t_list:.4f}s dashboard={t_dash:.4f}s my={t_mine:.4f}s")
    assert len(listed) == 1000 and stats.total == 1000 and len(mine) == 40
    assert t_list <= 2.0 and t_dash <= 2.0 and t_mine <= 2.0


def test_ac55_nfr06_raw_rows_helper_matches_service_view(service, make_ticket, db_path):
    """AC-55: the snapshot helper used for integrity checks reads the same rows."""
    t = make_ticket()
    (row,) = raw_rows(db_path)
    assert row[0] == t.id and row[1] == t.title

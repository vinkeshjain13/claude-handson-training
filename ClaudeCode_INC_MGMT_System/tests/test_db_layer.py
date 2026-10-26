"""L1 data-layer tests (ticketing/db.py): schema, CHECK constraints, binding, transactions.

Covers NFR-06, NFR-08, FR-04 (ID never reused), FR-13 and AC-06, AC-09, AC-55, AC-57 (data side).
"""

from __future__ import annotations

import sqlite3

import pytest

from ticketing import config, db

NOW = "2026-10-24 09:00:00"
GOOD = dict(
    title="T",
    description="D",
    category="Hardware",
    priority="High",
    status="Open",
    creator="C",
    created_at=NOW,
    updated_at=NOW,
)


@pytest.fixture
def conn(db_path):
    db.init_schema(db_path)
    c = db.connect(db_path)
    yield c
    c.close()


def insert(conn, **over):
    return db.insert_ticket(conn, **{**GOOD, **over})


def test_ac47_nfr01_init_schema_is_idempotent_and_creates_parent_directory(tmp_path):
    """NFR-01 / AC-47: init_schema twice keeps data; creates missing parent directories."""
    path = tmp_path / "nested" / "deeper" / "t.db"
    db.init_schema(path)
    assert path.exists()
    c = db.connect(path)
    insert(c)
    c.close()
    db.init_schema(path)
    db.init_schema(path)
    c = db.connect(path)
    assert db.count_all(c) == 1
    tables = [r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'")]
    c.close()
    assert tables.count("tickets") == 1


def test_nfr06_schema_columns_match_baseline_bl06(conn):
    """BL-06 / FR-07: ticket table has exactly the approved fields."""
    cols = [r["name"] for r in conn.execute("PRAGMA table_info(tickets)")]
    assert cols == [
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


@pytest.mark.parametrize(
    "over",
    [
        {"status": "Pending"},
        {"status": "open"},
        {"priority": "Urgent"},
        {"priority": "high"},
        {"category": "Printers"},
        {"title": ""},
        {"title": "   "},
        {"description": ""},
        {"creator": ""},
        {"creator": "  "},
        {"title": None},
        {"created_at": None},
    ],
    ids=repr,
)
def test_nfr06_check_constraints_reject_bad_rows_defence_in_depth(conn, over):
    """NFR-06 (DM section 2): CHECK / NOT NULL constraints reject invalid direct inserts."""
    with pytest.raises(sqlite3.IntegrityError):
        insert(conn, **over)
    assert db.count_all(conn) == 0


def test_ac09_fr04_ids_increase_and_are_not_reused(conn):
    """AC-09 / FR-04: AUTOINCREMENT - a deleted highest ID is never reissued."""
    a, b = insert(conn), insert(conn)
    assert b > a
    conn.execute("DELETE FROM tickets WHERE id = ?", (b,))
    c = insert(conn)
    assert c > b


def test_ac06_nfr08_values_with_sql_text_roundtrip_unchanged(conn):
    """AC-06 / NFR-08: bound parameters keep quotes and SQL fragments as data."""
    evil = "x'); DROP TABLE tickets; --"
    new_id = insert(conn, title=evil, description=evil, creator=evil)
    row = db.fetch_ticket(conn, new_id)
    assert (row["title"], row["description"], row["creator"]) == (evil, evil, evil)
    assert db.count_all(conn) == 1


def test_fr08_select_tickets_filters_and_combine_with_and(conn):
    """FR-08: AND-combination, None ignores a filter, newest first."""
    a = insert(conn, status="Open", priority="Low", category="Hardware", creator="Ann")
    b = insert(conn, status="Open", priority="High", category="Network", creator="Bob")
    c = insert(conn, status="Closed", priority="High", category="Network", creator="Ann")
    assert [r["id"] for r in db.select_tickets(conn)] == [c, b, a]
    assert [r["id"] for r in db.select_tickets(conn, status="Open")] == [b, a]
    assert [r["id"] for r in db.select_tickets(conn, priority="High", category="Network")] == [c, b]
    assert [r["id"] for r in db.select_tickets(conn, status="Open", creator_key="ann")] == [a]
    assert db.select_tickets(conn, status="Closed", priority="Low") == []


def test_fr08_casefold_function_matches_non_ascii_names(conn):
    """FR-08 / AC-19: the registered casefold SQL function folds Unicode like Python."""
    new_id = insert(conn, creator="Straße")
    assert [r["id"] for r in db.select_tickets(conn, creator_key="STRASSE".casefold())] == [new_id]
    z = insert(conn, creator="ZOË")
    assert [r["id"] for r in db.select_tickets(conn, creator_key="zoë")] == [z]


def test_fr08_creator_key_is_not_a_wildcard_pattern(conn):
    """FR-08 / NFR-08: % and _ in the creator key are literal."""
    insert(conn, creator="Ann")
    assert db.select_tickets(conn, creator_key="%") == []
    assert db.select_tickets(conn, creator_key="a_n") == []


def test_fr13_update_ticket_changes_only_given_fields_and_updated_at(conn):
    """FR-13 / FR-15: None leaves a column unchanged, updated_at always set."""
    tid = insert(conn)
    assert db.update_ticket(conn, tid, updated_at="2026-10-24 10:00:00", status="In Progress") == 1
    row = db.fetch_ticket(conn, tid)
    assert (row["status"], row["priority"], row["resolution_note"]) == ("In Progress", "High", "")
    assert row["updated_at"] == "2026-10-24 10:00:00" and row["created_at"] == NOW
    db.update_ticket(conn, tid, updated_at="2026-10-24 11:00:00", resolution_note="n")
    row = db.fetch_ticket(conn, tid)
    assert row["resolution_note"] == "n" and row["status"] == "In Progress"


def test_nfr06_update_of_unknown_id_affects_zero_rows(conn):
    """NFR-06: update on a missing ID changes nothing and reports 0 rows."""
    assert db.update_ticket(conn, 12345, updated_at=NOW, status="Open") == 0


def test_fr16_count_by_returns_only_present_values_and_rejects_unknown_columns(conn):
    """FR-16..FR-24 / NFR-08: count_by returns present values; column name is not injectable."""
    insert(conn, status="Open")
    insert(conn, status="Open")
    insert(conn, status="Closed")
    assert db.count_by(conn, "status") == {"Open": 2, "Closed": 1}
    assert db.count_by(conn, "priority") == {"High": 3}
    assert db.count_all(conn) == 3
    for bad in ("name; DROP TABLE tickets", "title", "", "status OR 1=1"):
        with pytest.raises(ValueError):
            db.count_by(conn, bad)
    assert db.count_all(conn) == 3


def test_nfr06_write_session_rolls_back_on_exception(db_path):
    """NFR-06: an exception inside a write session leaves no row behind."""
    db.init_schema(db_path)
    with pytest.raises(RuntimeError), db.session(db_path, write=True) as c:
        insert(c)
        raise RuntimeError("boom")
    with db.session(db_path) as c:
        assert db.count_all(c) == 0


def test_nfr06_write_session_commits_on_success_and_is_visible_to_new_connection(db_path):
    """NFR-01 / NFR-06: committed data is visible to a fresh connection."""
    db.init_schema(db_path)
    with db.session(db_path, write=True) as c:
        tid = insert(c)
    with db.session(db_path) as c:
        assert db.fetch_ticket(c, tid)["title"] == "T"


def test_nfr06_failed_multi_statement_session_is_atomic(db_path):
    """NFR-06: a CHECK violation in the second statement rolls back the first insert."""
    db.init_schema(db_path)
    with pytest.raises(sqlite3.IntegrityError), db.session(db_path, write=True) as c:
        insert(c)
        insert(c, status="Bogus")
    with db.session(db_path) as c:
        assert db.count_all(c) == 0


def test_nfr08_get_db_path_uses_env_var_then_default(monkeypatch, tmp_path):
    """NFR-09 / AC-56: TICKET_DB_PATH wins when non-empty; blank falls back to the default."""
    monkeypatch.setenv(config.DB_PATH_ENV_VAR, str(tmp_path / "x.db"))
    assert config.get_db_path() == tmp_path / "x.db"
    monkeypatch.setenv(config.DB_PATH_ENV_VAR, "   ")
    assert config.get_db_path() == config.DEFAULT_DB_PATH
    monkeypatch.delenv(config.DB_PATH_ENV_VAR)
    assert config.get_db_path() == config.DEFAULT_DB_PATH


def test_ac14_fr07_fetch_ticket_returns_all_ten_fields(conn):
    """FR-07: fetch_ticket returns all ten fields."""
    tid = insert(conn)
    assert set(db.fetch_ticket(conn, tid)) == {
        "id", "title", "description", "category", "priority",
        "status", "creator", "created_at", "updated_at", "resolution_note",
    }  # fmt: skip
    assert db.fetch_ticket(conn, tid + 1) is None

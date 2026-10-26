"""SQLite data layer. Static SQL with `?` placeholders only; no validation or workflow rules."""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from ticketing import config


def _sql_list(values: tuple[str, ...]) -> str:
    """Render config constants as a quoted SQL list for the DDL (never user input)."""
    for value in values:
        if "'" in value:
            raise ValueError("config values must not contain quotes")
    return ",".join("'" + value + "'" for value in values)


def _build_ddl() -> str:
    """DDL is the only SQL generated at runtime, from config constants only (DM section 2)."""
    return (
        "CREATE TABLE IF NOT EXISTS tickets ("
        " id INTEGER PRIMARY KEY AUTOINCREMENT,"
        " title TEXT NOT NULL CHECK (length(trim(title)) > 0),"
        " description TEXT NOT NULL CHECK (length(trim(description)) > 0),"
        " category TEXT NOT NULL CHECK (category IN (" + _sql_list(config.CATEGORIES) + ")),"
        " priority TEXT NOT NULL DEFAULT '" + config.DEFAULT_PRIORITY + "'"
        " CHECK (priority IN (" + _sql_list(config.PRIORITIES) + ")),"
        " status TEXT NOT NULL DEFAULT '" + config.DEFAULT_STATUS + "'"
        " CHECK (status IN (" + _sql_list(config.STATUSES) + ")),"
        " creator TEXT NOT NULL CHECK (length(trim(creator)) > 0),"
        " created_at TEXT NOT NULL,"
        " updated_at TEXT NOT NULL,"
        " resolution_note TEXT NOT NULL DEFAULT ''"
        ")"
    )


_COUNT_BY_SQL = {
    "status": "SELECT status, COUNT(*) FROM tickets GROUP BY status",
    "priority": "SELECT priority, COUNT(*) FROM tickets GROUP BY priority",
    "category": "SELECT category, COUNT(*) FROM tickets GROUP BY category",
}


_SQLITE_MIN, _SQLITE_MAX = -(2**63), 2**63 - 1


def _casefold(value: Any) -> Any:
    return value.casefold() if isinstance(value, str) else value


def connect(db_path: str | Path) -> sqlite3.Connection:
    """Open a connection (explicit transactions, Row factory, casefold function)."""
    conn = sqlite3.connect(
        str(db_path),
        timeout=config.DB_BUSY_TIMEOUT_SECONDS,
        isolation_level=None,
    )
    conn.row_factory = sqlite3.Row
    conn.create_function("casefold", 1, _casefold, deterministic=True)
    return conn


@contextmanager
def session(db_path: str | Path, write: bool = False) -> Iterator[sqlite3.Connection]:
    """Short-lived connection in one transaction; rolls back on any exception."""
    conn = connect(db_path)
    try:
        conn.execute("BEGIN IMMEDIATE" if write else "BEGIN")
        try:
            yield conn
        except BaseException:
            conn.execute("ROLLBACK")
            raise
        else:
            conn.execute("COMMIT")
    finally:
        conn.close()


def init_schema(db_path: str | Path) -> None:
    """Create the parent directory and the tickets table (idempotent)."""
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    conn = connect(db_path)
    try:
        conn.execute(_build_ddl())
    finally:
        conn.close()


def _row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    return dict(zip(row.keys(), tuple(row), strict=True))


def insert_ticket(
    conn: sqlite3.Connection,
    *,
    title: str,
    description: str,
    category: str,
    priority: str,
    status: str,
    creator: str,
    created_at: str,
    updated_at: str,
) -> int:
    cur = conn.execute(
        "INSERT INTO tickets (title, description, category, priority, status, creator, "
        "created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (title, description, category, priority, status, creator, created_at, updated_at),
    )
    return int(cur.lastrowid)


def fetch_ticket(conn: sqlite3.Connection, ticket_id: int) -> dict[str, Any] | None:
    if not _SQLITE_MIN <= ticket_id <= _SQLITE_MAX:  # cannot exist; avoid OverflowError
        return None
    row = conn.execute(
        "SELECT id, title, description, category, priority, status, creator, "
        "created_at, updated_at, resolution_note FROM tickets WHERE id = ?",
        (ticket_id,),
    ).fetchone()
    return _row_to_dict(row) if row is not None else None


def select_tickets(
    conn: sqlite3.Connection,
    *,
    status: str | None = None,
    priority: str | None = None,
    category: str | None = None,
    creator_key: str | None = None,
) -> list[dict[str, Any]]:
    """Newest first; None filters are ignored. `creator_key` must already be casefolded."""
    rows = conn.execute(
        "SELECT id, title, description, category, priority, status, creator, "
        "created_at, updated_at, resolution_note FROM tickets "
        "WHERE (? IS NULL OR status = ?) AND (? IS NULL OR priority = ?) "
        "AND (? IS NULL OR category = ?) AND (? IS NULL OR casefold(creator) = ?) "
        "ORDER BY id DESC",
        (
            status,
            status,
            priority,
            priority,
            category,
            category,
            creator_key,
            creator_key,
        ),
    ).fetchall()
    return [_row_to_dict(row) for row in rows]


def update_ticket(
    conn: sqlite3.Connection,
    ticket_id: int,
    *,
    updated_at: str,
    status: str | None = None,
    priority: str | None = None,
    resolution_note: str | None = None,
) -> int:
    """Set the non-None fields plus updated_at; returns affected rows."""
    cur = conn.execute(
        "UPDATE tickets SET status = COALESCE(?, status), priority = COALESCE(?, priority), "
        "resolution_note = COALESCE(?, resolution_note), updated_at = ? WHERE id = ?",
        (status, priority, resolution_note, updated_at, ticket_id),
    )
    return cur.rowcount


def count_by(conn: sqlite3.Connection, column: str) -> dict[str, int]:
    """Counts per distinct value of status, priority or category (fixed statements)."""
    sql = _COUNT_BY_SQL.get(column)
    if sql is None:
        raise ValueError("column must be one of: status, priority, category")
    return {row[0]: int(row[1]) for row in conn.execute(sql).fetchall()}


def count_all(conn: sqlite3.Connection) -> int:
    return int(conn.execute("SELECT COUNT(*) FROM tickets").fetchone()[0])

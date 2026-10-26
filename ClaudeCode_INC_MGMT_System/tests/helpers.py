"""Shared constants and small helpers for the test suite (no fixtures here)."""

from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

VALID = {
    "creator": "Alice",
    "title": "Printer jam",
    "description": "The printer on floor 2 is jammed.",
    "category": "Hardware",
    "priority": "High",
}

# Shared special-character sample set (test-strategy section 7; AC-06, AC-77, NFR-08).
SPECIAL_TEXTS = [
    "'; DROP TABLE tickets; --",
    '" OR 1=1 --',
    "Robert'); DROP TABLE tickets;--",
    "%",
    "_",
    "\\",
    "<script>alert(1)</script>",
    "**bold**",
    "[link](http://example.com)",
    'He said "hi"; it\'s fine',
    "café 日本語 \U0001f600",
    "line one\nline two",
    "tab\tseparated",
    "%" * 100,
    "a_c and 100% sure",
    "<b>x</b> & &amp; &lt;",
]

SQL_INJECTION_TEXTS = [
    "'; DROP TABLE tickets; --",
    '" OR 1=1 --',
    "Robert'); DROP TABLE tickets;--",
    "' OR '1'='1",
    "1; DELETE FROM tickets",
]


class FakeClock:
    """Deterministic injectable clock. Call it for the current time; advance() moves it."""

    def __init__(self, start: datetime | None = None) -> None:
        self.now = start or datetime(2026, 10, 24, 9, 0, 0)

    def __call__(self) -> datetime:
        return self.now

    def advance(self, seconds: int = 60) -> None:
        self.now = self.now + timedelta(seconds=seconds)

    @property
    def stamp(self) -> str:
        return self.now.strftime("%Y-%m-%d %H:%M:%S")


def raw_rows(db_path: Path) -> list[tuple]:
    """All ticket rows read with raw sqlite3 (allowed in tests), ordered by id."""
    conn = sqlite3.connect(str(db_path))
    try:
        return [tuple(r) for r in conn.execute("SELECT * FROM tickets ORDER BY id").fetchall()]
    finally:
        conn.close()


def raw_count(db_path: Path) -> int:
    conn = sqlite3.connect(str(db_path))
    try:
        return int(conn.execute("SELECT COUNT(*) FROM tickets").fetchone()[0])
    finally:
        conn.close()

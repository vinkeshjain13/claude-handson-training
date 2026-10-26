"""Fixtures and real-data guards (AC-56, NFR-07; CLAUDE.md section 7).

Real-data safety layers (task 11):
1. At import time TICKET_DB_PATH is pointed at a throw-away temp directory, so even code
   executed during collection can never fall back to data/tickets.db.
2. An autouse fixture re-points TICKET_DB_PATH to the per-test tmp_path.
3. An autouse fixture wraps ticketing.db.connect and fails the test if anything tries to open
   the real default database file.
4. A session-scoped autouse fixture hashes data/tickets.db (if it exists) before and after the
   whole run and fails at teardown if the content changed.
"""

from __future__ import annotations

import hashlib
import os
import tempfile
from pathlib import Path

import pytest

_SESSION_TMP = Path(tempfile.mkdtemp(prefix="ticketops_qa_session_"))
os.environ["TICKET_DB_PATH"] = str(_SESSION_TMP / "session_guard.db")

from tests.helpers import VALID, FakeClock, raw_rows  # noqa: E402
from ticketing import config, db  # noqa: E402
from ticketing.service import TicketService  # noqa: E402

REAL_DB = config.DEFAULT_DB_PATH.resolve()


def _sha(path: Path) -> str | None:
    if not path.exists():
        return None
    return hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.fixture(scope="session", autouse=True)
def _real_db_unchanged_for_whole_session():
    before = _sha(REAL_DB)
    yield
    after = _sha(REAL_DB)
    assert before == after, "data/tickets.db content changed during the test session"


@pytest.fixture(autouse=True)
def guard_default_db(tmp_path, monkeypatch):
    """Point the env-var fallback at tmp_path and refuse any connection to the real DB."""
    monkeypatch.setenv(config.DB_PATH_ENV_VAR, str(tmp_path / "guard.db"))
    real_connect = db.connect

    def guarded_connect(db_path):
        if Path(db_path).resolve() == REAL_DB:
            raise AssertionError(f"test attempted to open the real database {REAL_DB}")
        return real_connect(db_path)

    monkeypatch.setattr(db, "connect", guarded_connect)


@pytest.fixture
def db_path(tmp_path) -> Path:
    return tmp_path / "test.db"


@pytest.fixture
def fake_clock() -> FakeClock:
    return FakeClock()


@pytest.fixture
def service(db_path, fake_clock) -> TicketService:
    return TicketService(db_path=db_path, clock=fake_clock)


@pytest.fixture
def make_ticket(service):
    def _make(**overrides):
        return service.create_ticket(**{**VALID, **overrides})

    return _make


@pytest.fixture
def snapshot(db_path):
    return lambda: raw_rows(db_path)


@pytest.fixture
def ticket_in_status(service, make_ticket):
    """Create a ticket and walk it to the requested status through valid transitions."""

    def _make(status: str, **overrides):
        ticket = make_ticket(**overrides)
        path = {
            "Open": [],
            "In Progress": ["In Progress"],
            "Resolved": ["In Progress", "Resolved"],
            "Closed": ["In Progress", "Resolved", "Closed"],
        }[status]
        for step in path:
            note = "Fixed by QA fixture." if step == "Resolved" else None
            ticket = service.change_status(ticket.id, step, note)
        return ticket

    return _make


# ------------------------------------------------------------------ UI (AppTest) fixtures --


@pytest.fixture
def ui_db(tmp_path, monkeypatch) -> Path:
    """Temp database used by the Streamlit app under test (TICKET_DB_PATH -> tmp_path)."""
    path = tmp_path / "ui.db"
    monkeypatch.setenv(config.DB_PATH_ENV_VAR, str(path))
    return path


@pytest.fixture
def ui_service(ui_db) -> TicketService:
    """Service on the same temp DB the UI uses; used to seed and inspect data."""
    return TicketService(db_path=ui_db)


@pytest.fixture
def new_app(ui_db):
    """Factory returning a started AppTest for app/main.py bound to the temp database."""
    from streamlit.testing.v1 import AppTest

    from tests.helpers import REPO_ROOT

    def _start(role: str | None = None):
        at = AppTest.from_file(str(REPO_ROOT / "app" / "main.py"), default_timeout=30)
        at.run()
        if role is not None:
            at.sidebar.radio(key="demo_role").set_value(role).run()
        return at

    return _start


@pytest.fixture
def ui_snapshot(ui_db):
    """Raw-row snapshot of the temp database that the UI under test uses."""
    return lambda: raw_rows(ui_db)

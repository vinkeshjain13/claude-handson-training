"""Real-data safety guard tests (task 11; AC-56, NFR-07; CLAUDE.md section 7).

These tests prove the suite cannot read or write data/tickets.db.
"""

from __future__ import annotations

import hashlib
import os
from pathlib import Path

import pytest

from tests.conftest import REAL_DB
from tests.helpers import VALID
from ticketing import config, db
from ticketing.service import TicketService


def sha_and_mtime(path: Path):
    if not path.exists():
        return None
    return hashlib.sha256(path.read_bytes()).hexdigest(), path.stat().st_mtime_ns


def test_ac56_nfr07_env_var_points_to_a_tmp_path_not_the_real_db(tmp_path):
    """AC-56 / NFR-07: TICKET_DB_PATH is set to this test's tmp_path for every test."""
    value = Path(os.environ[config.DB_PATH_ENV_VAR]).resolve()
    assert value != REAL_DB
    assert value.parent == tmp_path.resolve()
    assert config.get_db_path().resolve() == value


def test_ac56_nfr07_service_fixture_uses_explicit_tmp_database(service, db_path, tmp_path):
    """AC-56 / NFR-07: the service fixture is bound to an explicit tmp_path file."""
    assert db_path.parent == tmp_path
    assert db_path.resolve() != REAL_DB
    assert service._db_path == db_path


def test_ac56_nfr07_default_constructor_never_touches_the_real_database(tmp_path):
    """AC-56 / NFR-07: TicketService() with no arguments resolves to the env-var tmp path and
    leaves data/tickets.db byte- and mtime-identical."""
    before = sha_and_mtime(REAL_DB)
    svc = TicketService()
    svc.create_ticket(**VALID)
    assert svc._db_path.resolve() != REAL_DB
    assert svc._db_path.parent == tmp_path
    assert (tmp_path / "guard.db").exists()
    assert sha_and_mtime(REAL_DB) == before


def test_ac56_nfr07_guard_refuses_connections_to_the_real_database():
    """AC-56 / NFR-07: the autouse guard raises if code tries to open data/tickets.db."""
    with pytest.raises(AssertionError, match="real database"):
        db.connect(REAL_DB)
    with pytest.raises(AssertionError, match="real database"):
        TicketService(db_path=REAL_DB)
    with pytest.raises(AssertionError, match="real database"):
        TicketService(db_path=str(REAL_DB))


def test_ac56_nfr07_guard_also_blocks_relative_and_dotdot_spellings_of_real_path():
    """AC-56 / NFR-07: the guard resolves paths, so alternate spellings are caught too."""
    sneaky = REAL_DB.parent / ".." / "data" / "tickets.db"
    with pytest.raises(AssertionError):
        db.connect(sneaky)


def test_ac56_nfr07_blank_env_var_would_fall_back_to_default_but_is_never_connected(monkeypatch):
    """AC-56 / NFR-07: config falls back to the real path for blank env, and the guard then
    refuses to open it (demonstrates the second safety layer)."""
    monkeypatch.setenv(config.DB_PATH_ENV_VAR, "")
    assert config.get_db_path().resolve() == REAL_DB
    with pytest.raises(AssertionError):
        TicketService()


def test_ac56_nfr07_real_database_file_is_unchanged_by_a_service_workout(service, make_ticket):
    """AC-56 / NFR-07: heavy use of the service leaves data/tickets.db identical (if present)."""
    before = sha_and_mtime(REAL_DB)
    t = make_ticket()
    service.change_status(t.id, "In Progress")
    service.change_priority(t.id, "Low")
    service.get_dashboard_stats()
    assert sha_and_mtime(REAL_DB) == before


def test_ac56_nfr07_default_db_path_is_inside_repo_data_directory():
    """AC-56 / NFR-07: documents where the real file lives (git-ignored data/ directory)."""
    assert REAL_DB == (Path(__file__).resolve().parent.parent / "data" / "tickets.db").resolve()
    gitignore = (Path(__file__).resolve().parent.parent / ".gitignore").read_text()
    assert "data/" in gitignore.splitlines()

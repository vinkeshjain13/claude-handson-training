"""Ticket business logic: validation, status workflow and persistence calls.

The service has no concept of role, session or user (IC section 1). `creator` is ordinary
ticket data, not an identity.
"""

from __future__ import annotations

import logging
import sqlite3
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any

from ticketing import config, db
from ticketing.models import (
    DashboardStats,
    NotFoundError,
    StorageError,
    Ticket,
    TicketStateError,
    ValidationError,
)

_log = logging.getLogger(config.LOGGER_NAME)

_STORAGE_MESSAGE = "The ticket data could not be read or saved. Please try again."


def _label(field: str) -> str:
    return config.FIELD_LABELS[field]


def _msg_required(field: str) -> str:
    return f"{_label(field)} is required."


def _msg_too_long(field: str, limit: int, length: int) -> str:
    return f"{_label(field)} must be at most {limit} characters (you entered {length})."


def _msg_not_in_list(field: str, values: tuple[str, ...]) -> str:
    return f"{_label(field)} must be one of: {', '.join(values)}."


def _msg_unencodable(field: str) -> str:
    return f"{_label(field)} contains characters that cannot be stored."


def _not_found(ticket_id: int) -> NotFoundError:
    try:
        return NotFoundError(f"Ticket {ticket_id} was not found.")
    except ValueError:  # int too large to render as text
        return NotFoundError("Ticket was not found.")


def _storable(text: str) -> bool:
    """False for text SQLite cannot hold faithfully: not UTF-8 encodable, or containing NUL."""
    if "\x00" in text:
        return False
    try:
        text.encode("utf-8")
    except UnicodeEncodeError:
        return False
    return True


def _check_text(field: str, value: Any, errors: dict[str, str]) -> str:
    """Trim and validate a required text field; record an error and return '' on failure."""
    if not isinstance(value, str):
        errors[field] = _msg_required(field)
        return ""
    text = value.strip()
    if not text:
        errors[field] = _msg_required(field)
        return ""
    if not _storable(text):
        errors[field] = _msg_unencodable(field)
        return ""
    limit = config.LIMITS[field]
    if len(text) > limit:
        errors[field] = _msg_too_long(field, limit, len(text))
        return ""
    return text


def _check_choice(field: str, value: Any, allowed: tuple[str, ...], errors: dict[str, str]) -> str:
    if not isinstance(value, str) or value not in allowed:
        errors[field] = _msg_not_in_list(field, allowed)
        return ""
    return value


def _check_ticket_id(ticket_id: Any, errors: dict[str, str]) -> None:
    if isinstance(ticket_id, bool) or not isinstance(ticket_id, int):
        errors["ticket_id"] = "Ticket ID must be a whole number."


def _check_optional_note(note: Any, errors: dict[str, str]) -> str:
    """Return the trimmed note, or '' when none supplied (None/blank)."""
    if note is None:
        return ""
    if isinstance(note, str) and not note.strip():
        return ""
    return _check_text("resolution_note", note, errors)


def _optional_filter(
    field: str, value: Any, allowed: tuple[str, ...], errors: dict[str, str]
) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        errors[field] = _msg_not_in_list(field, allowed)
        return None
    text = value.strip()
    if not text:
        return None
    if text not in allowed:
        errors[field] = _msg_not_in_list(field, allowed)
        return None
    return text


def _to_ticket(row: dict[str, Any]) -> Ticket:
    return Ticket(**row)


class TicketService:
    """Create, read and update tickets. Every operation opens its own short-lived connection."""

    def __init__(
        self,
        db_path: str | Path | None = None,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._db_path = Path(db_path) if db_path is not None else config.get_db_path()
        self._clock = clock if clock is not None else datetime.now
        with self._storage_guard("init"):
            db.init_schema(self._db_path)

    # ---- helpers -------------------------------------------------------------------------

    @contextmanager
    def _storage_guard(self, operation: str, ticket_id: Any = None) -> Iterator[None]:
        """Translate sqlite3/OS errors to StorageError and log once (no ticket text)."""
        try:
            yield
        except (sqlite3.Error, OSError) as exc:
            id_part = ticket_id if isinstance(ticket_id, int) else "n/a"
            _log.error(
                "Storage failure in %s (ticket %s): %s", operation, id_part, type(exc).__name__
            )
            raise StorageError(_STORAGE_MESSAGE) from exc

    def _now(self) -> str:
        return self._clock().strftime(config.STORE_TS_FORMAT)

    # ---- S1 ------------------------------------------------------------------------------

    def create_ticket(
        self, creator: str, title: str, description: str, category: str, priority: str
    ) -> Ticket:
        """FR-01..05, 13, 25. Collects all field errors before touching the database."""
        errors: dict[str, str] = {}
        creator_v = _check_text("creator", creator, errors)
        title_v = _check_text("title", title, errors)
        description_v = _check_text("description", description, errors)
        category_v = _check_choice("category", category, config.CATEGORIES, errors)
        priority_v = _check_choice("priority", priority, config.PRIORITIES, errors)
        if errors:
            raise ValidationError(errors)
        now = self._now()
        with self._storage_guard("create_ticket"), db.session(self._db_path, write=True) as conn:
            new_id = db.insert_ticket(
                conn,
                title=title_v,
                description=description_v,
                category=category_v,
                priority=priority_v,
                status=config.DEFAULT_STATUS,
                creator=creator_v,
                created_at=now,
                updated_at=now,
            )
            row = db.fetch_ticket(conn, new_id)
        if row is None:  # pragma: no cover - defensive
            raise StorageError(_STORAGE_MESSAGE)
        return _to_ticket(row)

    # ---- S2 ------------------------------------------------------------------------------

    def get_ticket(self, ticket_id: int) -> Ticket:
        """FR-07."""
        errors: dict[str, str] = {}
        _check_ticket_id(ticket_id, errors)
        if errors:
            raise ValidationError(errors)
        with self._storage_guard("get_ticket", ticket_id), db.session(self._db_path) as conn:
            row = db.fetch_ticket(conn, ticket_id)
        if row is None:
            raise _not_found(ticket_id)
        return _to_ticket(row)

    # ---- S3 / S4 -------------------------------------------------------------------------

    def list_tickets(
        self,
        status: str | None = None,
        priority: str | None = None,
        category: str | None = None,
        creator: str | None = None,
    ) -> list[Ticket]:
        """FR-06, 08. Newest first; None/blank filters are ignored; filters combine with AND."""
        errors: dict[str, str] = {}
        status_v = _optional_filter("status", status, config.STATUSES, errors)
        priority_v = _optional_filter("priority", priority, config.PRIORITIES, errors)
        category_v = _optional_filter("category", category, config.CATEGORIES, errors)
        creator_key: str | None = None
        if creator is not None:
            if not isinstance(creator, str):
                errors["creator"] = _msg_required("creator")
            elif not _storable(creator):
                errors["creator"] = _msg_unencodable("creator")
            elif creator.strip():
                creator_key = creator.strip().casefold()
        if errors:
            raise ValidationError(errors)
        return self._select(status_v, priority_v, category_v, creator_key)

    def list_my_tickets(self, creator_name: str) -> list[Ticket]:
        """FR-26. A convenience filter on the typed name; a blank name is rejected."""
        errors: dict[str, str] = {}
        name = _check_text("creator", creator_name, errors)
        if errors:
            raise ValidationError(errors)
        return self._select(None, None, None, name.casefold())

    def _select(
        self,
        status: str | None,
        priority: str | None,
        category: str | None,
        creator_key: str | None,
    ) -> list[Ticket]:
        with self._storage_guard("list_tickets"), db.session(self._db_path) as conn:
            rows = db.select_tickets(
                conn,
                status=status,
                priority=priority,
                category=category,
                creator_key=creator_key,
            )
        return [_to_ticket(row) for row in rows]

    # ---- S5..S7 --------------------------------------------------------------------------

    def change_status(
        self, ticket_id: int, new_status: str, resolution_note: str | None = None
    ) -> Ticket:
        """FR-09, 10, 13, 15. Check order follows IC section 5.2."""
        errors: dict[str, str] = {}
        _check_ticket_id(ticket_id, errors)
        status_v = _check_choice("status", new_status, config.STATUSES, errors)
        note_v = _check_optional_note(resolution_note, errors)
        if errors:
            raise ValidationError(errors)
        with (
            self._storage_guard("change_status", ticket_id),
            db.session(self._db_path, write=True) as conn,
        ):
            current = self._load_editable(conn, ticket_id)
            self._check_transition(ticket_id, current["status"], status_v)
            if (
                status_v == config.RESOLVED
                and config.RESOLVED_REQUIRES_NOTE
                and not note_v
                and not current["resolution_note"]
            ):
                raise ValidationError(
                    {
                        "resolution_note": (
                            f"{_label('resolution_note')} is required to set a ticket to "
                            f"{config.RESOLVED}."
                        )
                    }
                )
            db.update_ticket(
                conn,
                ticket_id,
                updated_at=self._now(),
                status=status_v,
                resolution_note=note_v or None,
            )
            row = db.fetch_ticket(conn, ticket_id)
        if row is None:  # pragma: no cover - defensive
            raise StorageError(_STORAGE_MESSAGE)
        return _to_ticket(row)

    def change_priority(self, ticket_id: int, new_priority: str) -> Ticket:
        """FR-11, 13."""
        errors: dict[str, str] = {}
        _check_ticket_id(ticket_id, errors)
        priority_v = _check_choice("priority", new_priority, config.PRIORITIES, errors)
        if errors:
            raise ValidationError(errors)
        with (
            self._storage_guard("change_priority", ticket_id),
            db.session(self._db_path, write=True) as conn,
        ):
            current = self._load_editable(conn, ticket_id)
            if current["priority"] == priority_v:
                raise TicketStateError(f"Priority is already {priority_v}.")
            db.update_ticket(conn, ticket_id, updated_at=self._now(), priority=priority_v)
            row = db.fetch_ticket(conn, ticket_id)
        if row is None:  # pragma: no cover - defensive
            raise StorageError(_STORAGE_MESSAGE)
        return _to_ticket(row)

    def set_resolution_note(self, ticket_id: int, note: str) -> Ticket:
        """FR-15, 13. The note replaces any previous note."""
        errors: dict[str, str] = {}
        _check_ticket_id(ticket_id, errors)
        note_v = _check_text("resolution_note", note, errors)
        if errors:
            raise ValidationError(errors)
        with (
            self._storage_guard("set_resolution_note", ticket_id),
            db.session(self._db_path, write=True) as conn,
        ):
            self._load_editable(conn, ticket_id)
            db.update_ticket(conn, ticket_id, updated_at=self._now(), resolution_note=note_v)
            row = db.fetch_ticket(conn, ticket_id)
        if row is None:  # pragma: no cover - defensive
            raise StorageError(_STORAGE_MESSAGE)
        return _to_ticket(row)

    @staticmethod
    def _load_editable(conn: sqlite3.Connection, ticket_id: int) -> dict[str, Any]:
        """Fetch the ticket; NotFoundError if missing, TicketStateError if read-only."""
        current = db.fetch_ticket(conn, ticket_id)
        if current is None:
            raise _not_found(ticket_id)
        if current["status"] in config.READ_ONLY_STATUSES:
            raise TicketStateError(
                f"Ticket {ticket_id} is {current['status']} and cannot be changed."
            )
        return current

    @staticmethod
    def _check_transition(ticket_id: int, current: str, new: str) -> None:
        allowed = config.TRANSITIONS.get(current, ())
        if new in allowed:
            return
        if new == current:
            raise TicketStateError(f"Ticket {ticket_id} is already {current}.")
        allowed_text = ", ".join(allowed) if allowed else "none"
        raise TicketStateError(
            f"Cannot change status from {current} to {new}. Allowed: {allowed_text}."
        )

    # ---- S8 / S9 -------------------------------------------------------------------------

    def get_dashboard_stats(self) -> DashboardStats:
        """FR-16, 18..20, 23, 24. Zero-filled, read in one transaction."""
        with self._storage_guard("get_dashboard_stats"), db.session(self._db_path) as conn:
            total = db.count_all(conn)
            raw_status = db.count_by(conn, "status")
            raw_priority = db.count_by(conn, "priority")
            raw_category = db.count_by(conn, "category")
        return DashboardStats(
            total=total,
            by_status={v: raw_status.get(v, 0) for v in config.STATUSES},
            by_priority={v: raw_priority.get(v, 0) for v in config.PRIORITIES},
            by_category={v: raw_category.get(v, 0) for v in config.CATEGORIES},
        )

    def allowed_next_statuses(self, current_status: str) -> tuple[str, ...]:
        """Pure lookup in config.TRANSITIONS; empty for unknown or Closed."""
        if not isinstance(current_status, str):
            return ()
        return tuple(config.TRANSITIONS.get(current_status, ()))

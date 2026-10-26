"""Shared types and error classes."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from ticketing import config


@dataclass(frozen=True)
class Ticket:
    id: int
    title: str
    description: str
    category: str
    priority: str
    status: str
    creator: str
    created_at: str  # "YYYY-MM-DD HH:MM:SS" local time
    updated_at: str  # same format; equals created_at on creation (FR-13)
    resolution_note: str  # "" when none (FR-07)


@dataclass(frozen=True)
class DashboardStats:
    """FR-16, 18, 19, 20, 23, 24. total == sum of each breakdown (AC-40, 41, 65)."""

    total: int
    by_status: dict[str, int]
    by_priority: dict[str, int]
    by_category: dict[str, int]


class TicketError(Exception):
    """Base class; str(exc) is a safe, user-readable message."""


class ValidationError(TicketError):
    """Bad input value(s). `errors` maps field name -> message."""

    def __init__(self, errors: dict[str, str]) -> None:
        self.errors = dict(errors)
        super().__init__(" ".join(self.errors.values()))


class NotFoundError(TicketError):
    """Unknown ticket ID."""


class TicketStateError(TicketError):
    """Input is valid but the ticket state forbids the operation."""


class StorageError(TicketError):
    """Unexpected sqlite3.Error (already logged)."""


def format_timestamp(value: str) -> str:
    """'2026-10-24 09:05:33' -> '2026-10-24 09:05'. Unparseable input is returned unchanged."""
    try:
        parsed = datetime.strptime(value, config.STORE_TS_FORMAT)
    except (TypeError, ValueError):
        return value
    return parsed.strftime(config.DISPLAY_TS_FORMAT)

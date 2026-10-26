"""Configuration constants. Rules that depend on unapproved assumptions live here only."""

from __future__ import annotations

import os
from pathlib import Path

STATUSES = ("Open", "In Progress", "Resolved", "Closed")  # BL-07
PRIORITIES = ("Low", "Medium", "High", "Critical")  # BL-08
CATEGORIES = ("Hardware", "Software", "Network", "Account Access", "Other")  # ASM-19

DEFAULT_STATUS = "Open"
DEFAULT_PRIORITY = "Medium"
DEFAULT_CATEGORY = "Other"
RESOLVED = "Resolved"

LIMITS = {"creator": 100, "title": 100, "description": 2000, "resolution_note": 1000}  # ASM-03

TRANSITIONS = {  # ASM-06, ASM-20
    "Open": ("In Progress",),
    "In Progress": ("Open", "Resolved"),
    "Resolved": ("In Progress", "Closed"),
    "Closed": (),
}
READ_ONLY_STATUSES = ("Closed",)  # ASM-20: no status/priority/note change
RESOLVED_REQUIRES_NOTE = True  # ASM-21

FIELD_LABELS = {
    "creator": "Your name",
    "title": "Title",
    "description": "Description",
    "category": "Category",
    "priority": "Priority",
    "status": "Status",
    "resolution_note": "Resolution note",
    "ticket_id": "Ticket ID",
}

STORE_TS_FORMAT = "%Y-%m-%d %H:%M:%S"  # ASM-15
DISPLAY_TS_FORMAT = "%Y-%m-%d %H:%M"

DB_PATH_ENV_VAR = "TICKET_DB_PATH"
DEFAULT_DB_PATH = Path(__file__).resolve().parent.parent / "data" / "tickets.db"

LOGGER_NAME = "ticketing"
DB_BUSY_TIMEOUT_SECONDS = 5.0


def get_db_path() -> Path:
    """Return the env-var path if set and non-empty, else the default path."""
    value = os.environ.get(DB_PATH_ENV_VAR, "").strip()
    return Path(value) if value else DEFAULT_DB_PATH

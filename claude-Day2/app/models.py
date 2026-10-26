"""Ticket model and supported categorical values."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

PRIORITIES = ("HIGH", "MEDIUM", "LOW")
STATUSES = ("OPEN", "IN_PROGRESS", "RESOLVED")


@dataclass(frozen=True)
class Ticket:
    ticket_id: str
    customer_id: str
    category: str
    priority: str
    status: str
    created_at: datetime
    summary: str

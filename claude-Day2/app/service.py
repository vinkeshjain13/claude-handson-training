"""Simple, deterministic ticket operations. SLA logic is intentionally absent."""
from __future__ import annotations

from collections import Counter
from collections.abc import Iterable

from app.models import PRIORITIES, STATUSES, Ticket


def filter_tickets(
    tickets: Iterable[Ticket], *, priority: str | None = None, status: str | None = None
) -> list[Ticket]:
    """Filter a collection without changing its objects."""
    if priority is not None and priority not in PRIORITIES:
        raise ValueError(f"Unsupported priority: {priority}")
    if status is not None and status not in STATUSES:
        raise ValueError(f"Unsupported status: {status}")
    return [
        ticket for ticket in tickets
        if (priority is None or ticket.priority == priority)
        and (status is None or ticket.status == status)
    ]


def summarize_tickets(tickets: Iterable[Ticket]) -> dict[str, object]:
    """Return totals and counts for the supplied ticket collection."""
    rows = list(tickets)
    priority_counts = Counter(ticket.priority for ticket in rows)
    status_counts = Counter(ticket.status for ticket in rows)
    return {
        "total": len(rows),
        "by_priority": {p: priority_counts[p] for p in PRIORITIES},
        "by_status": {s: status_counts[s] for s in STATUSES},
        "unresolved": sum(ticket.status != "RESOLVED" for ticket in rows),
    }

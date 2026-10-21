"""Simple, deterministic ticket operations, including SLA escalation."""
# TicketOps hook demo: automatic validation after edits.
from __future__ import annotations

from collections import Counter
from collections.abc import Iterable
from datetime import datetime, timedelta, timezone

from app.models import PRIORITIES, STATUSES, Ticket

SLA_ESCALATION_HOURS = {"HIGH": 24, "MEDIUM": 48, "LOW": 72}


def _require_aware(value: datetime, name: str) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{name} must be timezone-aware")
    return value.astimezone(timezone.utc)


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


def get_escalated_tickets(tickets: Iterable[Ticket], *, as_of: datetime) -> list[Ticket]:
    """Return unresolved tickets whose age at `as_of` meets their priority's SLA threshold.

    All comparisons use UTC. Age exactly at the threshold escalates; future-dated
    and RESOLVED tickets never do. Input order is preserved and nothing is mutated.
    """
    reference = _require_aware(as_of, "as_of")
    escalated: list[Ticket] = []
    for ticket in tickets:
        if ticket.priority not in SLA_ESCALATION_HOURS:
            raise ValueError(f"Unsupported priority: {ticket.priority}")
        if ticket.status == "RESOLVED":
            continue
        created = _require_aware(ticket.created_at, f"created_at of {ticket.ticket_id}")
        if created > reference:
            continue
        if reference - created >= timedelta(hours=SLA_ESCALATION_HOURS[ticket.priority]):
            escalated.append(ticket)
    return escalated


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

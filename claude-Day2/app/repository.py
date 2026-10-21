"""Read-only CSV repository for synthetic support tickets."""
from __future__ import annotations

import csv
from datetime import datetime, timezone
from pathlib import Path

from app.models import PRIORITIES, STATUSES, Ticket

REQUIRED_COLUMNS = (
    "ticket_id", "customer_id", "category", "priority", "status", "created_at", "summary"
)


def _parse_datetime(value: str, row_number: int) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"CSV row {row_number}: invalid created_at '{value}'") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(f"CSV row {row_number}: created_at must include timezone")
    return parsed.astimezone(timezone.utc)


def load_tickets(csv_path: str | Path) -> list[Ticket]:
    """Load tickets, rejecting missing fields and invalid values."""
    path = Path(csv_path)
    with path.open("r", newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        columns = reader.fieldnames or []
        missing = [column for column in REQUIRED_COLUMNS if column not in columns]
        if missing:
            raise ValueError(f"Missing required CSV columns: {', '.join(missing)}")

        tickets: list[Ticket] = []
        seen_ids: set[str] = set()
        for row_number, row in enumerate(reader, start=2):
            values = {key: (row.get(key) or "").strip() for key in REQUIRED_COLUMNS}
            empty = [key for key, value in values.items() if not value]
            if empty:
                raise ValueError(f"CSV row {row_number}: missing values for {', '.join(empty)}")
            if values["priority"] not in PRIORITIES:
                raise ValueError(f"CSV row {row_number}: unsupported priority {values['priority']}")
            if values["status"] not in STATUSES:
                raise ValueError(f"CSV row {row_number}: unsupported status {values['status']}")
            if values["ticket_id"] in seen_ids:
                raise ValueError(f"CSV row {row_number}: duplicate ticket ID {values['ticket_id']}")
            seen_ids.add(values["ticket_id"])
            tickets.append(
                Ticket(
                    ticket_id=values["ticket_id"],
                    customer_id=values["customer_id"],
                    category=values["category"],
                    priority=values["priority"],
                    status=values["status"],
                    created_at=_parse_datetime(values["created_at"], row_number),
                    summary=values["summary"],
                )
            )
    return tickets

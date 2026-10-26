"""CLI entry point for TicketOps."""
from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path

from app.models import PRIORITIES, STATUSES
from app.repository import load_tickets
from app.service import filter_tickets, get_escalated_tickets, summarize_tickets

DEFAULT_CSV = Path(__file__).resolve().parents[1] / "data" / "tickets.csv"


def _parse_as_of(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"invalid ISO-8601 datetime: '{value}'") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise argparse.ArgumentTypeError(f"as-of must be timezone-aware: '{value}'")
    return parsed


def main() -> None:
    parser = argparse.ArgumentParser(description="TicketOps synthetic helpdesk summary")
    parser.add_argument("--input", default=str(DEFAULT_CSV), help="Path to ticket CSV")
    parser.add_argument("--priority", choices=PRIORITIES, help="Filter by priority")
    parser.add_argument("--status", choices=STATUSES, help="Filter by status")
    parser.add_argument("--escalated", action="store_true",
                        help="Only tickets past their SLA threshold (requires --as-of)")
    parser.add_argument("--as-of", type=_parse_as_of, metavar="ISO8601",
                        help="Timezone-aware reference time, e.g. 2026-10-22T12:00:00Z")
    args = parser.parse_args()
    if args.escalated and args.as_of is None:
        parser.error("--escalated requires --as-of")
    if args.as_of is not None and not args.escalated:
        parser.error("--as-of requires --escalated")

    tickets = load_tickets(args.input)
    if args.escalated:
        tickets = get_escalated_tickets(tickets, as_of=args.as_of)
    selected = filter_tickets(tickets, priority=args.priority, status=args.status)
    print(json.dumps(summarize_tickets(selected), indent=2))
    print("Selected ticket IDs:", ", ".join(ticket.ticket_id for ticket in selected) or "(none)")


if __name__ == "__main__":
    main()

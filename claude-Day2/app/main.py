"""CLI entry point for TicketOps."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from app.models import PRIORITIES, STATUSES
from app.repository import load_tickets
from app.service import filter_tickets, summarize_tickets

DEFAULT_CSV = Path(__file__).resolve().parents[1] / "data" / "tickets.csv"


def main() -> None:
    parser = argparse.ArgumentParser(description="TicketOps synthetic helpdesk summary")
    parser.add_argument("--input", default=str(DEFAULT_CSV), help="Path to ticket CSV")
    parser.add_argument("--priority", choices=PRIORITIES, help="Filter by priority")
    parser.add_argument("--status", choices=STATUSES, help="Filter by status")
    args = parser.parse_args()

    tickets = load_tickets(args.input)
    selected = filter_tickets(tickets, priority=args.priority, status=args.status)
    print(json.dumps(summarize_tickets(selected), indent=2))
    print("Selected ticket IDs:", ", ".join(ticket.ticket_id for ticket in selected) or "(none)")


if __name__ == "__main__":
    main()

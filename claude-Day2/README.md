# TicketOps — Claude Code Day 2 Starter

A synthetic, domain-neutral support-ticket application for a 4-hour Claude Code engineering workshop.

## Current capabilities

- Read and validate support tickets from a CSV file.
- Filter by priority or status.
- Summarize tickets by priority, status, and unresolved count.
- Run a small command-line interface and standard-library unit tests.

**Not implemented yet:** SLA escalation. That is the feature students will plan and implement in Day 2 Lab 3.

## Layout

- `app/models.py`: `Ticket` dataclass and allowed field values.
- `app/repository.py`: load and validate CSV records.
- `app/service.py`: filtering and aggregation functions.
- `app/main.py`: command-line entry point.
- `data/tickets.csv`: 12 synthetic support tickets.
- `tests/test_service.py`: baseline tests.

## Prerequisites

Python 3.10 or newer; no third-party packages needed.

## Run

From this project directory:

```bash
python3 -m unittest discover -s tests -v
python3 -m app.main
python3 -m app.main --priority HIGH
python3 -m app.main --status OPEN
```

## Day 2 Lab 1 goals

First, explore this unfamiliar codebase with Claude Code. Then use `/init` to generate a project `CLAUDE.md` file, refine the file with the lab's engineering rules, and verify the instructions were loaded in a fresh Claude Code session.

**Important:** This starter deliberately does not include `CLAUDE.md`. Students generate it in Lab 1.

All records are synthetic. No customer data or external systems are used.

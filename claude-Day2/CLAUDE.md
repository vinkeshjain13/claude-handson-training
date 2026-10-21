# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

TicketOps is a small, synthetic support-ticket app (workshop starter for Claude Code Day 2). Python 3.10+, standard library only: no dependencies, build step, or linter configured. All data is synthetic.

## Commands

Run from the repo root (imports are `app.*`, so use `-m` rather than running files directly):

```bash
python3 -m unittest discover -s tests -v                              # all tests
python3 -m unittest tests.test_service.TicketOpsTests.test_filter_combined   # single test
python3 -m app.main                                                   # summary of all tickets
python3 -m app.main --priority HIGH --status OPEN                     # filters (also --input <csv>)
```

## Architecture

Three layers with one-way dependencies: `main.py` -> `service.py` / `repository.py` -> `models.py`.

- `app/models.py`: frozen `Ticket` dataclass plus `PRIORITIES` and `STATUSES` tuples. These tuples are the single source of truth for allowed values, used by the repository validation, service validation, and the CLI argparse `choices`. Add new values here only.
- `app/repository.py`: `load_tickets(path)` reads the CSV and fails fast with a `ValueError` naming the CSV row number (rows are numbered from 2, as the header is row 1). It checks required columns, empty fields, priority/status membership, duplicate `ticket_id`, and `created_at` (ISO 8601, must include a timezone, normalized to UTC; a trailing `Z` is accepted).
- `app/service.py`: pure, deterministic functions over `Iterable[Ticket]`. `filter_tickets` (keyword-only `priority`/`status`), `get_escalated_tickets` (keyword-only `as_of`), and `summarize_tickets` (total, `by_priority`, `by_status`, `unresolved` = status != RESOLVED).
- `app/main.py`: argparse CLI that loads, optionally escalates (`--escalated --as-of`), filters, prints the summary as JSON, then the selected ticket IDs.

## Testing notes

`tests/test_service.py` (unittest) loads the real `data/tickets.csv` and asserts exact counts (12 tickets, 4/4/4 priorities, 6/3/3 statuses, 9 unresolved). Editing the CSV will break these tests, so update them together. Validation-failure tests write temporary CSVs. Several repository checks (empty field, invalid status, duplicate ID, malformed date) have no tests yet.

## SLA escalation

`get_escalated_tickets(tickets, *, as_of)` in `app/service.py` returns unresolved tickets whose age at `as_of` is >= the `SLA_ESCALATION_HOURS` threshold for their priority (HIGH 24, MEDIUM 48, LOW 72). Boundary equality escalates; RESOLVED and future-dated tickets never do; `as_of` must be timezone-aware and all comparisons are in UTC. CLI: `--escalated` requires `--as-of` (and vice versa) and runs before `--priority`/`--status`. Tests: `tests/test_sla.py` (acceptance, 8 escalated at 2026-10-22T12:00:00Z) and `tests/test_sla_extra.py`.

## TicketOps Engineering Rules
  - Use Python standard-library modules only unless approval is given.
  - Run `python3 -m unittest discover -s tests -v` after code changes.
  - Preserve existing public function signatures unless the task requires changes.
  - Add automated tests for new business rules.
  - Never modify the synthetic `data/tickets.csv` to make tests pass.
  - Keep timestamps timezone-aware and in UTC.
  - Explain changed files and test results when finishing coding work.

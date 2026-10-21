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
- `app/service.py`: pure, deterministic functions over `Iterable[Ticket]`. `filter_tickets` (keyword-only `priority`/`status`) and `summarize_tickets` (total, `by_priority`, `by_status`, `unresolved` = status != RESOLVED).
- `app/main.py`: argparse CLI that loads, filters, prints the summary as JSON, then the selected ticket IDs.

## Testing notes

`tests/test_service.py` (unittest) loads the real `data/tickets.csv` and asserts exact counts (12 tickets, 4/4/4 priorities, 6/3/3 statuses, 9 unresolved). Editing the CSV will break these tests, so update them together. Validation-failure tests write temporary CSVs. Several repository checks (empty field, invalid status, duplicate ID, malformed date) have no tests yet.

## Planned feature

SLA escalation is intentionally not implemented; it is the Day 2 Lab 3 feature (see `README.md`, and the docstrings in `app/service.py` and `tests/test_service.py`). Do not add it unless asked.

## TicketOps Engineering Rules
  - Use Python standard-library modules only unless approval is given.
  - Run `python3 -m unittest discover -s tests -v` after code changes.
  - Preserve existing public function signatures unless the task requires changes.
  - Add automated tests for new business rules.
  - Never modify the synthetic `data/tickets.csv` to make tests pass.
  - Keep timestamps timezone-aware and in UTC.
  - Explain changed files and test results when finishing coding work.

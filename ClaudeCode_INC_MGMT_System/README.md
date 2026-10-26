# IT Support Ticket Management System

A small local classroom MVP for raising, tracking and resolving IT support tickets. Streamlit UI, Python `sqlite3` storage, local only.

## DEMO ONLY: roles are not security

The Employee / Support Engineer / Manager selector in the sidebar is a **demonstration switch**. It is **not authentication and not authorization**. Anyone who opens the application can pick any role and use any screen. The application makes no security, privacy or access-control claim.

- Do not enter confidential or real customer information.
- Creator names are free text. "My tickets" is a convenience filter by typed name, not privacy.
- Parameterized SQL and input validation are code-quality rules, not security guarantees.

## Requirements

- Python 3.10 or newer (developed and run here with Python 3.14.4).
- Packages in `requirements.txt` (Streamlit, pytest, Ruff). Streamlit 1.66.1 was installed here.

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```

## Run

From the repository root:

```bash
.venv/bin/python -m streamlit run app/main.py
```

(or `python -m streamlit run app/main.py` with the virtual environment activated). The app is served on localhost only, with Streamlit usage statistics disabled (`.streamlit/config.toml`). Open the URL it prints (default http://localhost:8501).

Data is stored in `data/tickets.db` (created automatically, git-ignored). Set `TICKET_DB_PATH` to use another file. To reset, stop the app and delete the file; this is also required after changing the category, status or priority lists in `ticketing/config.py` (there are no migrations).

## Screens

- **Employee:** raise a ticket; "My tickets" (by typed name) with search and status view.
- **Support Engineer:** list with status/priority/category/creator filters and search; ticket details; change status, change priority, add a resolution note. Closed tickets are read-only.
- **Manager:** dashboard with total, Open, In Progress, Resolved and Closed counts plus priority, category and status charts.

## Lint and tests

```bash
.venv/bin/ruff check .
.venv/bin/python -m pytest -v
```

Test results and evidence are recorded in `docs/test-report.md` once QA has run them.

## Layout

| Path | Purpose |
|---|---|
| `app/` | Streamlit UI (`main.py` entry point, role views); no SQL |
| `ticketing/` | Backend: `config.py`, `models.py`, `db.py` (all SQL), `service.py` (validation and rules) |
| `docs/` | Requirements, design, traceability, test and review documents |
| `data/` | Local SQLite database (runtime only) |

## Known limitations

Single local file, no backup, no authentication, no ticket deletion, no status history, no attachments or notifications.

## Documents

See `docs/requirements-analysis.md`, `docs/architecture.md`, `docs/interface-contracts.md`, `docs/ui-design.md`, `docs/test-strategy.md` and `docs/traceability-matrix.md`.

# Manual Test Checklist

Owner: qa-engineer. QA cycle 0 (initial run), 2026-10-24. Status of every item: NOT YET EXECUTED (needs a human with a browser). Automated evidence for the related ACs is in `reports/test-report.md`.

Before starting a manual session, use a throw-away database so no real data is touched:

```bash
export TICKET_DB_PATH=/tmp/manual_qa/tickets.db      # any path outside data/
.venv/bin/python -m streamlit run app/main.py        # run from the repository root
```

Record for each item: date, tester, browser and version, result (pass/fail), notes.

| ID | AC / NFR | Why manual | Steps | Expected result | Result (date, tester, browser, pass/fail, notes) |
|---|---|---|---|---|---|
| M-01 | AC-49 / NFR-02 | Needs real browsers; AppTest has no browser | 1. Start the app with the command above. 2. Open `http://localhost:8501` in the latest Chrome, then Firefox, then Edge. 3. In each: raise a ticket (Employee), change its status and priority (Support Engineer), open the dashboard (Manager). | All three tasks complete in each browser with no client software installed and no browser error. | |
| M-02 | AC-50 / NFR-03 | Human usability judgement (ASM-17) | Ask a first-time user with no instructions to raise a ticket. Time them. | They succeed in about 2 minutes or less. Record the time and any confusion. | |
| M-03 | AC-53 / NFR-04 | Scope review is a human judgement against `docs/requirements-analysis.md` section 9 | Walk through every screen in all three roles. Tick off that none of these exist: attachments, notifications/email, SLA/due dates, comment threads, status history, assignee, ticket delete, bulk actions, import/export, editing title/description/category, a "pending" figure, manager ticket list, search outside the two lists of FR-27. | None of the out-of-scope features is present. | |
| M-04 | AC-54 / NFR-05 (UI half) | Browser-rendered timing; the service half is automated (`test_ac54_nfr05_...`) | Seed 1,000 tickets into the throw-away DB (for example a short script calling `TicketService(db_path=...).create_ticket` 1,000 times). Open Support Engineer and Manager views; time each load (stopwatch or browser dev tools). | Ticket list and dashboard each load in 2 seconds or less. Record measured times. | |
| M-05 | AC-47, AC-48 / NFR-01 (real restart) | Needs a real server stop/start and browser actions | 1. Create tickets, change statuses/priorities, add notes. 2. Stop the server (Ctrl+C), start it again with the same `TICKET_DB_PATH`. 3. Refresh the browser; then close and reopen the browser tab. 4. Compare ticket list, details and dashboard figures with what you had before. | Every ticket and field is unchanged; dashboard figures identical. | |
| M-06 | AC-44 (visual) | Layout judgement | Switch the sidebar role to Employee, Support Engineer, Manager. | Employee: raise-ticket form plus My tickets. Engineer: list, filters, search, status/priority/note controls. Manager: dashboard only. | |
| M-07 | AC-45 (visual) | Visibility/readability of the notice | In each role, check the yellow DEMO warning at the top of the page and the caption under the role selector. | The notice is clearly visible on every role screen and says it is not authentication or access control. | |
| M-08 | AC-51 (visual) / NFR-03 | Readability judgement; label text and required markers are automated | Open the raise-ticket form, trigger a validation error (empty submit). | All fields labelled, required fields marked with `*`, messages are plain language and name the field. | |
| M-09 | AC-52 (browser) / NFR-03 | Real browser form behaviour | Fill creator, description, category and priority; leave title empty; submit. | Error appears; the other typed values are still in the form. | |
| M-10 | AC-57 (review part) / NFR-08 | Human code inspection; static scans are automated in `test_code_rules.py` | Read `ticketing/db.py`, `ticketing/service.py`, `app/*.py`. The security-reviewer also inspects. | Every statement is parameterized (`?`), no SQL in `app/`. Not a security guarantee. | |
| M-11 | AC-58 / NFR-09 (network monitor) | Needs an OS-level network monitor; code scans, config check and a socket-blocked app walkthrough are automated | Start the app with outbound network disabled or monitored (for example `ss -tnp` or a firewall log) and use all three roles. | No outbound connection, no telemetry; `.streamlit/config.toml` has `gatherUsageStats = false`. | |
| M-12 | AC-68 / NFR-12 (reading) | Document reading | Read `README.md` and the design docs. | They say roles are a demo selector, not authentication or authorization, and make no security claim. (README wording is also checked automatically.) | |
| M-13 | AC-69 / NFR-10 | Python 3.10 compatibility cannot be shown here: only Python 3.14.4 is installed | Create a venv with Python 3.10 or 3.11, install `requirements.txt`, run `ruff check .` and `python -m pytest -v`. | Everything passes on Python 3.10+. | |
| M-14 | AC-81 (inspection) / FR-27 | Part is automated; inspection is a record | Read `app/common.py` `search_tickets` and the engineer/employee views. | Search runs on the list already returned by the service; no SQL built from search text; service has no search method. | |

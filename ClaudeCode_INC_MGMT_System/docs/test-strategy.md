# Test Strategy

Status: DESIGN v1 (awaiting approval). Author: solution-architect, 2026-10-24. Owner of the implementation: qa-engineer (`tests/`, `pytest.ini`, QA documents). Rules from `CLAUDE.md` section 7 apply: every AC has at least one test or recorded manual evidence referencing its ID; isolated temporary databases only; "done" means the command was run and its output is recorded in `docs/test-report.md`.

## 1. Test levels

| Level | Scope | Tool | Share of ACs |
|---|---|---|---|
| L1 Data layer | schema, constraints, parameter binding, queries, transactions | pytest + `sqlite3` | NFR-06, NFR-08 |
| L2 Service layer | validation, workflow, `updated_at`, dashboard, filters, persistence | pytest + `TicketService` on a temp DB | most functional ACs (NFR-07, AC-56) |
| L3 UI smoke | app starts, role views render, DEMO notice present, form round-trip | `streamlit.testing.v1.AppTest` | UI parts of AC-01, 07, 13, 41, 42, 44, 45, 51, 52, 66, 67 |
| L4 Static rules | no SQL in UI, no network/cloud imports, Ruff clean | pytest scan + `ruff` | AC-57, 58, 70 |
| L5 Manual / document checks | browsers, usability, scope review, disclosure wording, UI timing | checklist in `docs/manual-test-checklist.md` | AC-49, 50, 53, 54 (UI part), 68, 69 and the manual halves of 44, 45, 47, 48, 51, 52 |

## 2. Layout

```
tests/
  __init__.py                    (empty, optional)
  conftest.py                    fixtures and helpers (section 3)
  test_db_layer.py               L1: DDL, CHECKs, binding, count_by, update_ticket, session rollback
  test_service_create.py         L2: AC-01..11, 33(create part), 67
  test_service_read.py           L2: AC-02, 12..20, 60, 66
  test_service_update.py         L2: AC-21..31, 33, 36, 61..64
  test_service_dashboard.py      L2: AC-37, 39..43, 59, 65
  test_persistence_integrity.py  L2: AC-47, 48, 55, 54 (service-level timing)
  test_code_rules.py             L4: AC-57, 58, 69 (partial), 56 (meta), 68 (doc grep, when README exists)
  test_ui_smoke.py               L3: AppTest
pytest.ini                       testpaths = tests ; pythonpath = . ; addopts = -ra
```

`pytest.ini` (owner qa-engineer):

```ini
[pytest]
testpaths = tests
pythonpath = .
addopts = -ra
```

`pythonpath` lets tests import `ticketing` and `ui` from the repository root without installing a package.

## 3. Fixtures (`tests/conftest.py`)

| Fixture / helper | Behaviour |
|---|---|
| `db_path(tmp_path)` | returns `tmp_path / "test.db"` (a fresh file per test; never `data/tickets.db`) |
| `guard_default_db` (autouse) | `monkeypatch.setenv("TICKET_DB_PATH", str(tmp_path / "guard.db"))` so any code path that falls back to the default location still stays inside a temp dir (AC-56) |
| `fake_clock` | object with `.now` (a `datetime`) and `__call__`; `advance(seconds)` method. Passed as `clock=` to `TicketService` so `updated_at`/`created_at` can be controlled (AC-09, AC-33) |
| `service(db_path, fake_clock)` | `TicketService(db_path=db_path, clock=fake_clock)` |
| `make_ticket(service)` | factory with valid defaults and keyword overrides; returns `Ticket` |
| `snapshot(db_path)` | reads all rows with raw `sqlite3` (allowed in tests) as a sorted list of tuples; used to prove rejected operations changed nothing (AC-55) |
| `ticket_in_status(service, status)` | helper that walks a new ticket through the valid transitions to the requested status (adds a note when moving to Resolved) |

## 4. Naming convention

Test functions: `test_<ac id lower-case>_<fr id lower-case>_<what>` for example `test_ac05_fr02_title_boundary_100_ok_101_rejected`. Multi-AC tests list each ID: `test_ac21_ac33_fr10_open_to_in_progress_refreshes_updated_at`. The first docstring line repeats the IDs in the form `AC-05 / FR-02: ...`. Parameterized tests use readable `ids=`. Evidence collection command (recorded in the report): `grep -rhoE "ac[0-9]{2}" tests | sort -u` compared with the active AC list; any missing ID must appear in the manual checklist.

## 5. Streamlit UI testing (realistic scope)

- Use `streamlit.testing.v1.AppTest.from_file("app.py", default_timeout=15)`; set `TICKET_DB_PATH` with `monkeypatch.setenv` to a temp path before `run()`. `app.py` builds `TicketService()` on every run (ARCH D10), so each test sees its own DB.
- Widgets are located by the stable `key` values in `docs/ui-design.md` (for example `at.sidebar.radio(key="demo_role")`, `create_title_0`). The `{nonce}` suffix is 0 on a fresh session.
- Smoke tests (each small): app renders without exception in all three roles (`at.exception` empty); the DEMO warning text is present in each role (AC-45); Employee shows the form and "My tickets" and no status/priority controls (AC-44, AC-66); Engineer shows filters and, with a ticket created via the service, the update forms (AC-44); Manager shows metrics only (AC-44); manager metrics are 0 on an empty DB (AC-42); submit with empty title shows an error naming Title and keeps other typed values (AC-03, AC-52); a valid submit creates a ticket and shows its ID (AC-01); category/priority options and defaults (AC-07, AC-67).
- AppTest is an experimental testing API and can differ between Streamlit versions. If a UI test is flaky or unsupported, the qa-engineer moves that check to the manual checklist and records the reason; business rules are never tested only through the UI.
- Manual-only: real browsers (AC-49), first-time user walk-through (AC-50), visual labelling/readability (AC-51), scope review against out-of-scope list (AC-53), UI timing with 1,000 tickets (AC-54 UI half).

## 6. What each level tests

### L1 Data layer (`test_db_layer.py`; NFR-06, NFR-08, FR-04, FR-13)
- `init_schema` is idempotent and creates the parent directory.
- Direct inserts with a status/priority/category outside the lists, or blank title/description/creator, raise `sqlite3.IntegrityError` (CHECK constraints).
- IDs increase and are not reused (AUTOINCREMENT) (AC-09).
- `select_tickets` filters AND-combine; `None` ignores a filter; `casefold` matching works for non-ASCII (for example "Zoë" style and "STRASSE" vs "strasse"-style names; exact cases chosen by QA).
- `count_by("status")` returns only present values; `count_by("name; DROP TABLE tickets")` raises `ValueError`.
- `session(write=True)` rolls back on exception: insert inside the block, raise, new connection sees no row (NFR-06).
- Values containing quotes and SQL fragments round-trip unchanged (AC-06, NFR-08).

### L2 Service layer
- Create (AC-01..11, 67): valid create returns status Open, `created_at == updated_at`, trimmed values; empty/whitespace-only each of creator/title/description (parametrized, AC-03, 04) leaves count unchanged and `errors` names the field; boundary 100/101 and 2000/2001 (AC-05); special characters list (section 7) round-trips (AC-06); invalid priority/category/non-str types (AC-08, 67); two identical creates give two IDs (AC-10); IDs strictly increase and `created_at` not earlier (AC-09, using `fake_clock`); multiple invalid fields reported together.
- Read (AC-02, 12..20, 60, 66): newest first; empty DB returns `[]` (AC-13); unknown ID raises `NotFoundError` (AC-15); each filter alone and combined; no-match returns `[]` (AC-20); creator filter case-insensitive and trimmed (AC-19); `list_my_tickets(" ann ")` returns only Ann's tickets, a blank name raises `ValidationError` and never returns all tickets (AC-66); unknown filter value raises `ValidationError`.
- Update (AC-21..31, 33, 36, 61..64): every allowed transition; every rejected transition parametrized over the full 4x4 table including same-status (AC-25..27, 63); invalid status value (AC-28); unknown ID (AC-29); Resolved needs a note: rejected without one with `errors["resolution_note"]`, accepted with an existing note or a note supplied in the same call (AC-22, 64); reopen keeps the note (AC-23); priority change, same-value rejection, invalid value (AC-30, 31); `updated_at` equals new clock time after success and is unchanged after each rejection (AC-33 with `fake_clock`); resolution note 1..1000, blank, 1001, special chars, replace (AC-36); all three updates rejected on Closed (AC-62); `allowed_next_statuses` equals the transition table.
- Dashboard (AC-37..43, 59, 65): empty DB gives total 0 and all zero-filled dicts with exact key lists/order (AC-42); mixed data counts match; sums equal total (AC-40, 41, 65); counts update after create/change without restarting (AC-43).
- Persistence and integrity (AC-47, 48, 55): create and update tickets with service A, build service B on the same file and compare every field and the dashboard (AC-47, 48); a sequence of rejected operations leaves `snapshot()` identical (AC-55); a forced `sqlite3.Error` (monkeypatch `db.insert_ticket` to raise) yields `StorageError` and no row.
- Performance (AC-54 service part): insert 1,000 tickets, assert `list_tickets()` and `get_dashboard_stats()` each finish within 2 seconds, and record the measured times in the test report. Mark with `@pytest.mark.slow` only if it takes more than a few seconds; no marker is needed otherwise.

### L4 Static rules (`test_code_rules.py`)
- AC-57: scan `app.py` and `ui/*.py` for `import sqlite3`, `ticketing.db` and SQL keywords at statement start inside string literals (`SELECT `, `INSERT `, `UPDATE `, `DELETE `, `CREATE TABLE`); fail if found. Scan `ticketing/db.py` for f-strings or `%`/`.format` used with SQL text (heuristic; plus Ruff `S608`). Scan `ticketing/service.py` for `import sqlite3` limited to catching `sqlite3.Error`, and for any `role` parameter name.
- AC-58: scan source for imports of `requests`, `urllib`, `http.client`, `socket`, `boto3`, `smtplib` and for URLs `http://`/`https://` outside comments; confirm no `.env`, key or token files in the repo.
- AC-69: assert `sys.version_info >= (3, 10)`; assert `streamlit` and `sqlite3` are imported by the expected modules.
- AC-68: when `README.md` exists, assert it contains the phrases "demo" and "not authentication"; the human-readable review stays in the manual checklist.

### Edge cases (explicit list, CLAUDE.md section 7)
invalid/empty/oversized input; whitespace-only; unicode and emoji; `'; DROP TABLE tickets; --`, `" OR 1=1 --`, `Robert'); DROP TABLE tickets;--`, `%`, `_`, `\`; `<script>alert(1)</script>`, `**bold**`, `[link](http://example.com)`; line breaks in description/note; text longer than the limit by one; invalid priority/status/category; invalid transitions (all 16 pairs); duplicates; unknown IDs including `0`, negative, `True`, `"7"`; persistence across reconnects; empty database; non-str arguments (`None`, `123`); rejected operations leaving data unchanged.

## 7. Special-character sample set (shared by tests)

Defined once in `conftest.py` as `SPECIAL_TEXTS` (list): the injection-looking strings and markup above, `He said "hi"; it's fine`, `café 日本語 \U0001F600`, a two-line text with `\n`, and a 100-character string of `%`. For each: create ticket, `get_ticket` returns an identical string (after strip), the table still exists and the ticket count rose by exactly one, and other tickets are unchanged (AC-06).

## 8. Ruff (NFR-11, AC-70)

`ruff.toml` (owner orchestrator, content specified here):

```toml
line-length = 100
target-version = "py310"
extend-exclude = ["data"]

[lint]
select = ["E", "F", "I", "B", "UP", "S608"]
```

Commands (run from the repository root):

- `ruff check .` must report no errors; paste the command and its output into `docs/test-report.md` (AC-70).
- The qa-engineer does not edit production code to satisfy Ruff; findings in production files go to the owning developer through the orchestrator, findings in `tests/` are fixed by QA.
- Formatting (`ruff format`) is not required by NFR-11 and is not part of the gate.

## 9. Running tests and recording evidence

| Step | Command | Evidence |
|---|---|---|
| Full suite | `python -m pytest -v` | full output in `docs/test-report.md` with date, Python and Streamlit versions |
| Single level | `python -m pytest tests/test_service_update.py -v` | optional |
| Lint | `ruff check .` | output in the report (AC-70) |
| AC reference check | `grep -rhoE "ac[0-9]{2}" tests \| sort -u` | list compared with the 65 active ACs; gaps listed as manual |
| Manual checklist | `docs/manual-test-checklist.md` | each item with date, tester, browser, pass/fail, notes |

`docs/test-report.md` (owner qa-engineer) contains: environment, commands and raw output, AC-by-AC result table (AC, FR, test names or manual item, result), defect list with evidence, and the statement of which ACs are manual. No claim of passing without the output.

## 10. AC verification map (65 active ACs)

| ACs | Level | File or manual item |
|---|---|---|
| AC-01 | L2 + L3 | `test_service_create.py`; `test_ui_smoke.py` end to end |
| AC-02, 03, 04, 05, 06, 08, 09, 10, 11, 67 | L2 | `test_service_create.py` (AC-03, 07, 67 option lists also in L3) |
| AC-07 | L2 (config constants) + L3 | `test_service_create.py`; `test_ui_smoke.py` options and default |
| AC-12, 14, 15, 16, 17, 18, 19, 20, 60 | L2 | `test_service_read.py` |
| AC-13 | L2 + L3 | `test_service_read.py`; `test_ui_smoke.py` empty message |
| AC-66 | L2 + L3 | `test_service_read.py`; `test_ui_smoke.py` (no update controls) |
| AC-21..31, 33, 36, 61, 62, 63, 64 | L2 | `test_service_update.py` (AC-15, 29: service level only, see UI section 5) |
| AC-37, 39, 40, 41, 42, 43, 59, 65 | L2 (+ L3 for 41, 42 numbers) | `test_service_dashboard.py`; `test_ui_smoke.py` |
| AC-44, 45 | L3 + L5 | `test_ui_smoke.py`; checklist items for visual confirmation |
| AC-47, 48 | L2 + L5 | `test_persistence_integrity.py`; checklist: real app restart and browser refresh |
| AC-49 | L5 | checklist: Chrome, Firefox, Edge |
| AC-50 | L5 | checklist: first-time user walk-through |
| AC-51, 52 | L3 + L5 | `test_ui_smoke.py` (labels, retained values); checklist visual review |
| AC-53 | L5 | checklist: review against the out-of-scope list |
| AC-54 | L2 + L5 | `test_persistence_integrity.py` (service timing); checklist (UI timing, human-measured) |
| AC-55 | L1/L2 | `test_persistence_integrity.py` |
| AC-56 | L2 (meta) | conftest fixtures and the passing suite itself; `guard_default_db` |
| AC-57 | L4 + review | `test_code_rules.py`, Ruff `S608`, security-reviewer inspection |
| AC-58 | L4 + L5 | `test_code_rules.py`; checklist (no network use observed, telemetry setting) |
| AC-68 | L4 + L5 | `test_code_rules.py` grep (once README exists); checklist reading of README and docs |
| AC-69 | L4 + L5 | `test_code_rules.py`; checklist (run on Python 3.10+) |
| AC-70 | L4 | `ruff check .` output in the report |

Manual or document-evidence ACs (as in the requirements analysis plus AC-69 and AC-70): AC-49, 50, 53, 54 (UI timing), 57 (review part), 58, 68, 69, 70, and the UI parts of AC-44, 45, 51, 52.

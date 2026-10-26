# Implementation Status

Legend: [ ] not started, [~] in progress, [x] done. Last updated: 2026-10-26.

| # | Deliverable | Status |
|---|---|---|
| 0 | Planning docs, data/sample_tickets.csv (22 synthetic rows) | [x] |
| 1 | .gitignore, requirements.txt (streamlit, pandas, pytest) | [x] |
| 2 | src/ticket_logic.py (normalize_tickets, classify_ticket, analyze_tickets, draft_response + helpers) | [x] |
| 3 | app.py (title, uploader, metrics, category/priority charts, CSV download, filterable table) | [x] (not launched or manually tested) |
| 4 | tests/test_ticket_logic.py (28 tests, written by qa-engineer) | [x] |
| 5 | README.md (startup, CSV rules, limitations) | [x] |
| 6 | Editable reply area + reset (US-7.2/7.3) | [ ] replies are shown in the table/CSV only |
| 7 | Security review fixes (see below) | [x] medium finding mitigated only |
| 8 | Manual UI QA, AT-8.x grep checks | [ ] |

## Test results
- qa-engineer run: 18 passed, 1 failed. The failure was a real bug: `to_safe_csv` skipped
  string columns under pandas 3 (dtype `str`, not `object`), so CSV-injection neutralisation did nothing.
- Fixed in src/ticket_logic.py (also neutralises tab/CR prefixes). Re-run of the suite: 19 passed.
- The venv had no pip/packages; qa-engineer installed pandas and pytest. Streamlit is not installed, so app.py has never been run.

## Deviations
- Single `src/ticket_logic.py` instead of the multi-module layout in architecture.md, per the MVP brief.
- UI-level acceptance tests (AT-1.x display, 2.2, 5.2, 5.3, 7.x) are not covered by unit tests.

## QA run (2026-10-26)
- qa-engineer added 9 tests (upload, missing headers, blank text, duplicate IDs, cross-process determinism). Run: 28 passed, 0 failed (pytest 9.1.1, Python 3.14.4). No app bugs found, so nothing delegated to app-developer.
- Not covered by tests: MAX_UPLOAD_BYTES limit and the non-UTF-8 rejection path.

## Security code review (security-reviewer, read-only; a code review, not a full security audit; no dynamic testing)
- No high findings. No secrets, external API calls, unsafe file handling or exception leakage found; CSV formula neutralisation in `to_safe_csv` was reviewed and found adequate.
- MEDIUM: no authentication (by design). Mitigated, not resolved: `.streamlit/config.toml` binds to 127.0.0.1 and the app caption states there is no authentication. Any shared deployment still needs an auth layer.
- LOW, not fixed: upload size limit applies only after Streamlit buffers the file (could set `server.maxUploadSize = 5`); no row/column cap in `parse_csv`; unpinned dependencies with pytest in requirements.txt; unexpected exceptions are not logged.
- After the changes: pytest 28 passed. app.py has still not been launched.

1. What we observed, including which metrics were actually visible.
2. Difference: automatic prompt caching vs CLAUDE.md vs artifact reuse.
3. How role-based Haiku/Sonnet routing can help and when quality matters.
# Test Report - IT Support Ticket Management System

**Current state: QA cycle 1 (fix + retest) is recorded first (section C1 to C9). The unchanged cycle 0 record (initial run) follows from "Cycle 0 record" below.** Author: qa-engineer. Date: 2026-10-24. Baseline: requirements v3 (76 active ACs, 5 retired).
Primary location of this report: `reports/test-report.md` (human-specified). `docs/test-report.md` is a pointer to this file.

# Cycle 1 (fix + retest)

## C1. Summary

| Item | Result |
|---|---|
| Tests collected | **879** (692 cycle 0 tests + 187 new regression cases in `tests/test_cycle1_regressions.py`) |
| Passed | **879** |
| Failed / errors | **0 / 0** |
| Skipped / xfail | 0 / 0 (no test was skipped, xfailed, deleted or weakened) |
| Ruff (`ruff check .`) | All checks passed (exit 0); `ruff format --check tests`: 16 files already formatted |
| The 14 cycle 0 failing tests | **All 14 now pass** (section C3) |
| DEF-01 / DEF-02 / DEF-03 | **Verified fixed** (independent review of the code plus 187 new tests). Flagged: DEF-03 fix is stricter than the written rule (NUL is rejected; section C5) |
| New defects | None (DEF-04 not raised). One test-harness limit noted (section C6) |
| Real data file `data/tickets.db` | SHA-256, mtime and size identical before and after (section C8) |
| Active ACs (76) | **73 PASS by automated tests** (AC-15 and AC-29 moved FAIL to PASS); 3 manual-only (AC-49, AC-50, AC-53). Manual halves of other ACs still pending (cycle 0 section 5 and C7). |

**Verdict: all three defects are closed at the automated level; automated suite 879/879.** QA sign-off still depends on the human executing the manual checklist (M-01 to M-14) and on the doc updates listed in C7.

## C2. Independent review of the fix (read of `ticketing/service.py`, `ticketing/db.py`)

| Defect | Change found in code | Judgement |
|---|---|---|
| DEF-01 (Medium) | `db.fetch_ticket` returns `None` when `ticket_id` is outside `[-2**63, 2**63-1]` (constants `_SQLITE_MIN/_SQLITE_MAX`) before any query. `service._not_found(ticket_id)` builds `NotFoundError("Ticket N was not found.")` and falls back to the generic `"Ticket was not found."` when `str(int)` raises `ValueError` (more than 4300 digits). `get_ticket` and `_load_editable` (used by `change_status`, `change_priority`, `set_resolution_note`) use it. | Satisfies AC-15 ("a not found message is shown, no error/crash") and AC-29 (error message, no data change). Type checks are unchanged: bool, float, str, None still give `ValidationError("Ticket ID must be a whole number.")`. Field validation still runs before the lookup. Not a storage failure, nothing logged. The fix sits in the data layer guard (no SQL change; still parameterized). |
| DEF-02 (Low) | `list_tickets`: a non-str creator gives `errors["creator"]`; text failing `_storable` gives `errors["creator"] = "<label> contains characters that cannot be stored."`; blank text means no filter. | Satisfies FR-08 robustness and matches `create_ticket`/`list_my_tickets` wording. Errors are collected with other filter errors. Blank-filter semantics unchanged. |
| DEF-03 (Low) | New `_storable(text)` = no `"\x00"` and UTF-8 encodable. `_check_text` calls it after the required/blank check and before the length check, so title, description, creator and the resolution note (both entry points) and the `list_my_tickets` name are covered. | Satisfies FR-02 (rejected with a message naming the field, nothing stored, no StorageError). Behaviour change: `"a\x00b"` and `"abc\x00"`, which cycle 0 stored, are now rejected too (consistent rule). Differs from `docs/validation-rules.md` line 60 (see C5). |

No SQL string was changed to use formatting; `test_code_rules.py` static checks still pass.

## C3. Retest of the 14 cycle 0 failing tests

Command and actual output (values of the NUL cases come from the 12-case parametrization; the 6 that failed in cycle 0 are the `'\x00'` and `'\x00abc'` ones):

```
.venv/bin/python -m pytest -v tests/test_service_read.py tests/test_service_update.py tests/test_service_create.py \
  -k "beyond_sqlite_integer_range or creator_filter_lone_surrogate or nul_character"
```

Earlier combined run of the same selection: `25 passed, 402 deselected in 0.20s` (14 previously failing + 11 previously passing). Per test:

| Cycle 0 failing test | Cycle 1 |
|---|---|
| `test_service_read.py::test_ac15_fr07_id_beyond_sqlite_integer_range_gives_clean_error[9223372036854775808]` | PASSED |
| `... [18446744073709551616]` | PASSED |
| `... [1180591620717411303424]` | PASSED |
| `... [-9223372036854775809]` | PASSED |
| `... [1000000000000000000000000000000]` | PASSED |
| `test_service_read.py::test_fr08_creator_filter_lone_surrogate_fails_cleanly` | PASSED |
| `test_service_update.py::test_ac29_fr09_id_beyond_sqlite_integer_range_gives_clean_error[9223372036854775808]` | PASSED |
| `... [1180591620717411303424]` | PASSED |
| `test_service_create.py::test_edge_fr02_nul_character_...[ '\x00'-title ]` | PASSED |
| `... ['\x00'-description]` | PASSED |
| `... ['\x00'-creator]` | PASSED |
| `... ['\x00abc'-title]` | PASSED |
| `... ['\x00abc'-description]` | PASSED |
| `... ['\x00abc'-creator]` | PASSED |

Real output of the NUL selection: `12 passed, 139 deselected in 0.10s`; of the other eight: `8 passed, 419 deselected in 0.16s`. The old NUL test accepts "stored or rejected with a field message" (written before the fix); the new tests pin the stricter behaviour, so the old test was not edited or weakened.

## C4. Full regression run, commands and actual output

All commands from `/home/labuser/Desktop/Practice/ClaudeCode_INC_MGMT_System`; run started 2026-10-24 09:48:31 UTC; Python 3.14.4, pytest 9.1.1, Ruff 0.17.2, Streamlit 1.66.1 (unchanged from cycle 0).

```
.venv/bin/python -m pytest -v
collected 879 items
...
============================= 879 passed in 23.71s =============================
exit=0

.venv/bin/ruff check .
All checks passed!
ruff_exit=0
```

Per-file results (counted from the `-v` output; 0 failed in every file):

| File | Passed |
|---|---|
| `tests/test_code_rules.py` | 77 |
| `tests/test_cycle1_regressions.py` (new) | 187 |
| `tests/test_db_layer.py` | 27 |
| `tests/test_persistence_integrity.py` | 27 |
| `tests/test_real_data_safety.py` | 8 |
| `tests/test_service_create.py` | 151 |
| `tests/test_service_dashboard.py` | 16 |
| `tests/test_service_read.py` | 107 |
| `tests/test_service_update.py` | 169 |
| `tests/test_ui_engineer.py` | 16 |
| `tests/test_ui_search.py` | 41 |
| `tests/test_ui_smoke.py` | 53 |
| **Total** | **879** |

AC reference check: `grep -rhoE "ac[0-9]{2}" tests | sort -u | wc -l` gives `73` (unchanged; the missing three are AC-49, 50, 53, manual only).

## C5. New regression tests (`tests/test_cycle1_regressions.py`, 187 cases in 30 functions)

DEF-01 (AC-15, AC-29, FR-07, FR-09):
- `test_ac15_ac29_fr07_fr09_out_of_range_id_is_not_found_for_every_operation` x11: 2**63, -2**63-1, 2**64, 2**70, 10**30, negatives, 10**4300, 10**5000 (5001 digits), 10**20000; all four operations raise exactly `NotFoundError`, short message, snapshot of all rows unchanged.
- `test_ac15_fr07_moderately_large_id_message_names_the_id` x4 (message `Ticket <id> was not found.`).
- `test_ac15_fr07_five_thousand_digit_id_message_is_generic_not_a_valueerror` (message `Ticket was not found.`).
- `test_ac15_ac29_fr07_fr09_in_range_unknown_id_boundaries_are_not_found` x5: 2**63-1, -2**63, 0, -1, 999999 (valid range but unknown), all four operations, message and data checked.
- `test_ac15_fr07_largest_storable_id_can_be_read_when_it_exists`: a row inserted with id 2**63-1 is returned (the guard does not over-reject the boundary); 2**63 is NotFound.
- `test_ac15_ac29_fr07_fr09_non_int_ids_are_still_validation_errors` x8: True, False, 1.0, 2.0**63, 1e30, inf, `"9"*30`, None for all four operations.
- `test_ac29_fr09_validation_errors_take_precedence_over_out_of_range_id`.
- `test_ac15_fr07_out_of_range_lookup_is_not_a_storage_failure_and_logs_nothing` (not StorageError; no WARNING/ERROR log).
- `test_ac15_fr07_service_still_works_after_out_of_range_lookups` (no lock/transaction left open; next ID is correct).
- `test_fr07_db_fetch_ticket_returns_none_outside_int64_and_row_inside` (db layer).

DEF-02 (FR-08, AC-19, FR-26):
- `test_fr08_ac19_creator_filter_with_unstorable_text_is_validation_error_on_creator` x5 (lone surrogates, mixed, padded); `test_fr08_creator_filter_containing_nul_is_validation_error_on_creator` x5; collected with an invalid status filter; service usable afterwards.
- Unchanged behaviour: blank creator filter means no filter x3; non-string creator filter x5.
- `test_ac66_fr26_my_tickets_rejects_unstorable_names` x7.
- `test_fr08_creator_filter_accepts_unicode_emoji_and_tabs` x6 (match, case-fold match, My tickets match).

DEF-03 (FR-02, AC-03, 05, 06, 36, 55):
- `test_ac06_fr02_nul_anywhere_is_rejected_with_validation_message_naming_the_field` x24: 8 NUL placements (alone, start, middle, end, padded, double) x title/description/creator; exactly that field keyed; no row; ID 1 not consumed.
- NUL in the resolution note via `set_resolution_note` and `change_status` x4; all three fields plus bad category collected; oversized text with NUL; lone surrogates per field x6; no ERROR log; row count unchanged after rejected NUL creates.
- Still accepted (x51 create and x17 note): newline, CRLF, tab, accented, CJK, Hebrew/Arabic, emoji, ZWJ sequence, combining mark, U+10FFFF, control chars \x01 \x1f \x7f, zero-width and non-breaking space, quotes/backslash/`%`/`_`, literal text `\x00` (backslash-x-0-0) in every text field and as a note; round-trip through a second `TicketService` on the same file; 100 emoji exactly at the title limit.
- UI (AppTest): `test_ac03_ac06_fr02_ui_form_with_nul_shows_named_error_and_creates_nothing` x9 (error text `<Label> contains characters that cannot be stored.`, no exception, no ticket) and `test_ac66_fr26_ui_my_tickets_name_with_unstorable_text_does_not_crash` x2.

## C6. Updated AC coverage (changed rows) and counts

| AC | FR | Cycle 0 | Cycle 1 evidence | Status |
|---|---|---|---|---|
| AC-15 | FR-07 | FAIL (DEF-01, 5 failed) | `-k ac15` over the whole suite: 58 passed (32 of them new, in `test_cycle1_regressions.py`) | **PASS (automated)** |
| AC-29 | FR-09 | FAIL (DEF-01, 2 failed) | `-k "ac29 or ac15_ac29"` over the whole suite: 36 passed (25 of them new) | **PASS (automated)** |
| AC-03, AC-05, AC-06 | FR-02 | PASS; DEF-03 note | NUL, surrogate, unicode and UI-form cases added; DEF-03 closed | PASS (automated) |
| AC-19 | FR-08 | PASS; DEF-02 note | creator-filter validation cases added; DEF-02 closed | PASS (automated) |
| AC-36 | FR-15 | PASS | note NUL/unicode cases added | PASS (automated) |
| AC-66 | FR-26 | PASS | unstorable names via service and UI | PASS (automated) |

All other AC rows (section 5 of the cycle 0 record below) are unchanged and were re-run: all their tests pass in the 879-test run. **Counts: 76 active ACs = 73 PASS (automated; several with a manual half pending) + 3 MANUAL ONLY (AC-49, AC-50, AC-53); 0 FAIL.** 5 retired ACs have no tests by design.

Test-harness limit (not a product defect): a lone surrogate cannot be sent through Streamlit's widget protocol (`UnicodeEncodeError` inside AppTest), so surrogate input is tested at the service level only. A browser cannot produce one either.

## C7. Remaining open items, doc drift and manual checklist

1. Manual checklist M-01 to M-14 (`docs/manual-test-checklist.md`) not yet executed by a human. Python 3.10 run (M-13) not possible here (3.14.4 only).
2. Doc drift for the architect (QA did not edit these):
   - `docs/validation-rules.md` line 60: "The only text rejected for its content is text that cannot be encoded as UTF-8". The build also rejects NUL anywhere in title, description, creator, resolution note and the creator filter. The rule text should add NUL (message `"{Label} contains characters that cannot be stored."`), or the architect/human decides to revert the build. Tests pin the build behaviour; `"a\x00b"` and `"abc\x00"` were stored in cycle 0 and are now rejected (a behaviour change; no real data affected: `data/tickets.db` untouched).
   - Design documents still say `app.py` / `ui/` and `streamlit run app.py`; as built it is `app/main.py` (`python -m streamlit run app/main.py`). Matrix and design cells still use the old names.
   - `docs/test-strategy.md` says 65 active ACs; the baseline is 76 (5 retired).
   - `README.md` line 48 says results are in `docs/test-report.md`; the primary location is `reports/test-report.md` (the docs file is a pointer).
   - `docs/interface-contracts.md` and `docs/validation-rules.md` do not mention the `Ticket was not found.` fallback for IDs over 4300 digits (cosmetic).
3. Assumption-dependent ACs (ASM-03, 06, 13, 19, 20, 21, 24, 25) still encode current values.
4. The Streamlit server was not started (see cycle 0 section 7).

## C8. Real-data safety evidence (cycle 1)

```
== BEFORE ==   (2026-10-24T09:48:31Z)
bd44ab5d1a09514e23f0603de8c383bef62c07a4bf83bc3d519aca21d4bc207e  data/tickets.db
mtime_ns=1792833802.842753400 size=12288
...(pytest 879 tests and ruff run here)...
== AFTER ==
bd44ab5d1a09514e23f0603de8c383bef62c07a4bf83bc3d519aca21d4bc207e  data/tickets.db
mtime_ns=1792833802.842753400 size=12288
```
Identical to the cycle 0 hash, mtime and size (also checked at 09:46:44 before the first retest and after the 8-test selection). The session fixture `_real_db_unchanged_for_whole_session` and the 8 tests in `test_real_data_safety.py` also passed. The file was not opened, modified or deleted by QA.

## C9. Files changed by QA in cycle 1

`tests/test_cycle1_regressions.py` (new), `reports/test-report.md`, `docs/test-report.md`, `docs/traceability-matrix.md` (Test(s) and Status cells of rows US-01, US-03, US-05, US-06, US-07, US-09 only). No production file was edited.

---

# Cycle 0 record (initial run, unchanged)

**QA cycle 0 (initial run).** Author: qa-engineer. Date: 2026-10-24. Baseline: requirements v3 (76 active ACs, 5 retired).

## 1. Summary

| Item | Result |
|---|---|
| Tests collected | 692 (293 test functions) |
| Passed | **678** |
| Failed | **14** (3 distinct defects: DEF-01, DEF-02, DEF-03) |
| Errors | 0 |
| Skipped / xfail | 0 / 0 (no test was skipped, xfailed, deleted or weakened) |
| Ruff (`ruff check .`) | All checks passed (exit 0) |
| Real data file `data/tickets.db` | SHA-256 and mtime identical before and after the run |
| Active ACs (76) | 71 PASS by automated tests; 2 FAIL (AC-15, AC-29, both DEF-01); 3 manual-only (AC-49, AC-50, AC-53, checklist items not yet executed). Several PASS ACs also have a manual half pending (see section 5). |
| Defects | DEF-01 Medium, DEF-02 Low, DEF-03 Low. No Critical or High defects. |

**Verdict: NOT READY FOR QA SIGN-OFF.** 14 tests fail because of 3 backend defects; they are left failing on purpose. The three defects are edge-case robustness problems (unhandled exception types or a generic storage message for odd input); none was reachable through normal UI use, and all main workflows, validation, persistence, dashboard, search and code rules passed. After the backend-developer fixes DEF-01..03, QA re-runs the full suite (cycle 1). Manual checklist items (`docs/manual-test-checklist.md`) are also still to be executed by a human.

## 2. Environment

| Item | Value |
|---|---|
| Date of run | 2026-10-24 (run started 09:40:24 UTC) |
| OS | Linux 7.0.0-1005-gcp |
| Python | 3.14.4 (project `.venv`) |
| pytest | 9.1.1 (pluggy 1.7.0, plugin anyio 4.15.1) |
| Streamlit | 1.66.1 (AppTest `streamlit.testing.v1` used for UI tests) |
| Ruff | 0.17.2 |
| Config | `pytest.ini`: `testpaths = tests`, `pythonpath = .`, `addopts = -ra` |
| Databases | Only temporary SQLite files under pytest `tmp_path` (and one throw-away session temp dir for the import-time guard). No network access; no package was installed. |
| Not available | Python 3.10 to 3.13 (only 3.14.4 installed), real browsers (see manual checklist) |

pytest header of the run:

```
============================= test session starts ==============================
platform linux -- Python 3.14.4, pytest-9.1.1, pluggy-1.7.0 -- /home/labuser/Desktop/Practice/ClaudeCode_INC_MGMT_System/.venv/bin/python
cachedir: .pytest_cache
rootdir: /home/labuser/Desktop/Practice/ClaudeCode_INC_MGMT_System
configfile: pytest.ini
testpaths: tests
plugins: anyio-4.15.1
collecting ... collected 692 items
```

## 3. Commands executed, with actual output

All commands were run from `/home/labuser/Desktop/Practice/ClaudeCode_INC_MGMT_System`.

### 3.1 Full test suite

```
.venv/bin/python -m pytest -v
```

Result (final lines of the real output; the complete `-v` log has 692 PASSED/FAILED lines, 678 PASSED and 14 FAILED, and is reproduced by re-running the command):

```

ticketing/db.py:117: OverflowError
=========================== short test summary info ============================
FAILED tests/test_service_create.py::test_edge_fr02_nul_character_is_stored_literally_or_rejected_with_validation_message['\\x00'-title]
FAILED tests/test_service_create.py::test_edge_fr02_nul_character_is_stored_literally_or_rejected_with_validation_message['\\x00'-description]
FAILED tests/test_service_create.py::test_edge_fr02_nul_character_is_stored_literally_or_rejected_with_validation_message['\\x00'-creator]
FAILED tests/test_service_create.py::test_edge_fr02_nul_character_is_stored_literally_or_rejected_with_validation_message['\\x00abc'-title]
FAILED tests/test_service_create.py::test_edge_fr02_nul_character_is_stored_literally_or_rejected_with_validation_message['\\x00abc'-description]
FAILED tests/test_service_create.py::test_edge_fr02_nul_character_is_stored_literally_or_rejected_with_validation_message['\\x00abc'-creator]
FAILED tests/test_service_read.py::test_ac15_fr07_id_beyond_sqlite_integer_range_gives_clean_error[9223372036854775808]
FAILED tests/test_service_read.py::test_ac15_fr07_id_beyond_sqlite_integer_range_gives_clean_error[18446744073709551616]
FAILED tests/test_service_read.py::test_ac15_fr07_id_beyond_sqlite_integer_range_gives_clean_error[1180591620717411303424]
FAILED tests/test_service_read.py::test_ac15_fr07_id_beyond_sqlite_integer_range_gives_clean_error[-9223372036854775809]
FAILED tests/test_service_read.py::test_ac15_fr07_id_beyond_sqlite_integer_range_gives_clean_error[1000000000000000000000000000000]
FAILED tests/test_service_read.py::test_fr08_creator_filter_lone_surrogate_fails_cleanly
FAILED tests/test_service_update.py::test_ac29_fr09_id_beyond_sqlite_integer_range_gives_clean_error[9223372036854775808]
FAILED tests/test_service_update.py::test_ac29_fr09_id_beyond_sqlite_integer_range_gives_clean_error[1180591620717411303424]
======================= 14 failed, 678 passed in 21.95s ========================
```

Per-file results (counted from the same `-v` output):

| File | Passed | Failed |
|---|---|---|
| `tests/test_code_rules.py` | 77 | 0 |
| `tests/test_db_layer.py` | 27 | 0 |
| `tests/test_persistence_integrity.py` | 27 | 0 |
| `tests/test_real_data_safety.py` | 8 | 0 |
| `tests/test_service_create.py` | 145 | 6 |
| `tests/test_service_dashboard.py` | 16 | 0 |
| `tests/test_service_read.py` | 101 | 6 |
| `tests/test_service_update.py` | 167 | 2 |
| `tests/test_ui_engineer.py` | 16 | 0 |
| `tests/test_ui_search.py` | 41 | 0 |
| `tests/test_ui_smoke.py` | 53 | 0 |
| **Total** | **678** | **14** |

Raw failure excerpts (real output) are in section 8 (Defects).

### 3.2 Lint

```
.venv/bin/ruff check .
All checks passed!
```
Exit code 0. Findings that occurred during development of the tests (import order, E501, unused import) were fixed in `tests/` only; `ruff format --check tests` reports `15 files already formatted`. No finding was reported in production files. The same check also runs inside the suite as `test_ac70_nfr11_ruff_reports_no_errors_with_project_configuration` (passed).

### 3.3 AC reference check (test-strategy section 4)

```
grep -rhoE "ac[0-9]{2}" tests | sort -u | wc -l
73
```
73 distinct AC IDs are referenced by test names. The 76 active ACs minus these 73 are exactly AC-49, AC-50, AC-53, which are manual-only (checklist M-01, M-02, M-03). (AC-57, 58, 68, 69 appear in tests for their automatable parts and also have manual items.)

### 3.4 AC-54 timing record (service level, 1,000 tickets)

```
.venv/bin/python -m pytest tests/test_persistence_integrity.py -k ac54 -s -q
AC-54 timing: list=0.0081s dashboard=0.0015s my=0.0013s
1 passed, 26 deselected
```
Limit is 2 seconds each. The UI timing half is manual (M-04).

### 3.5 Real-data safety (hash and mtime of `data/tickets.db`)

```
== BEFORE ==
2026-10-24T09:40:24Z
bd44ab5d1a09514e23f0603de8c383bef62c07a4bf83bc3d519aca21d4bc207e  data/tickets.db
mtime_ns=1792833802.842753400 size=12288
2026-10-24 09:23:22.842753311 +0000
...(pytest and ruff run here)...
== AFTER ==
bd44ab5d1a09514e23f0603de8c383bef62c07a4bf83bc3d519aca21d4bc207e  data/tickets.db
mtime_ns=1792833802.842753400 size=12288
2026-10-24 09:23:22.842753311 +0000
```
SHA-256, size and modification time (including nanoseconds) are identical before and after the full run: `data/tickets.db` was not touched. The file already existed before QA started (created 09:23, git-ignored `data/`); it was not opened, read by a test, modified or deleted.

## 4. Test case list (grouped)

Naming: `test_<ac id>_<fr id>_<what>`; the first docstring line repeats the IDs as `AC-xx / FR-xx: ...`. `xN` is the number of parametrized cases.

### `tests/test_code_rules.py` - L4 static and code-rule checks (AC-45, 56-58, 68-70, 81) (77 cases in 29 functions; 77 passed, 0 failed)

- `test_code_rules_sources_were_found`
- `test_ac57_nfr08_ui_does_not_import_sqlite3_or_the_db_layer` x6
- `test_ac57_nfr08_ui_contains_no_sql_keywords_in_string_literals` x6
- `test_ac57_nfr08_ui_never_calls_execute_or_cursor` x6
- `test_ac57_nfr08_sql_only_executed_in_db_layer`
- `test_ac57_nfr08_db_statements_are_static_with_question_mark_placeholders`
- `test_ac57_nfr08_db_module_builds_no_sql_with_fstrings_or_format_or_percent`
- `test_ac57_nfr08_ddl_is_generated_only_from_config_constants`
- `test_ac57_nfr08_service_imports_sqlite3_only_for_error_handling`
- `test_ac57_nfr08_ticketing_does_not_import_streamlit` x5
- `test_ac57_ic1_service_has_no_role_concept`
- `test_ac81_fr27_service_offers_no_search_operation`
- `test_ac81_fr27_search_runs_in_ui_layer_on_already_returned_tickets`
- `test_ac58_nfr09_no_network_or_cloud_imports` x11
- `test_ac58_nfr09_no_urls_in_application_string_literals` x11
- `test_ac58_nfr09_streamlit_usage_statistics_are_disabled_and_server_is_local`
- `test_ac58_nfr09_no_secret_like_strings_in_source_config_and_readme`
- `test_ac58_nfr09_no_env_key_or_credential_files_in_repository`
- `test_ac45_fr21_demo_notice_text_is_present_and_clear`
- `test_ac45_fr21_main_renders_notice_before_any_role_view`
- `test_ac45_ac68_fr21_ui_strings_make_no_login_or_security_claim` x6
- `test_ac45_fr21_login_wording_only_appears_as_the_explicit_not_a_login_disclaimer`
- `test_ic1_backend_docstrings_and_messages_avoid_security_words` x5
- `test_ac69_nfr10_python_streamlit_sqlite_pytest_baseline`
- `test_ac69_nfr10_entry_point_is_app_main_py_and_readme_states_launch_command`
- `test_ac68_nfr12_readme_discloses_demo_roles_and_makes_no_security_claim`
- `test_ac69_nfr10_readme_documents_pytest_and_ruff_commands`
- `test_ac70_nfr11_ruff_reports_no_errors_with_project_configuration`
- `test_ac56_nfr07_meta_tests_run_without_a_browser_and_conftest_guards_exist`

### `tests/test_db_layer.py` - L1 data layer (schema, CHECKs, binding, transactions) (27 cases in 16 functions; 27 passed, 0 failed)

- `test_ac47_nfr01_init_schema_is_idempotent_and_creates_parent_directory`
- `test_nfr06_schema_columns_match_baseline_bl06`
- `test_nfr06_check_constraints_reject_bad_rows_defence_in_depth` x12
- `test_ac09_fr04_ids_increase_and_are_not_reused`
- `test_ac06_nfr08_values_with_sql_text_roundtrip_unchanged`
- `test_fr08_select_tickets_filters_and_combine_with_and`
- `test_fr08_casefold_function_matches_non_ascii_names`
- `test_fr08_creator_key_is_not_a_wildcard_pattern`
- `test_fr13_update_ticket_changes_only_given_fields_and_updated_at`
- `test_nfr06_update_of_unknown_id_affects_zero_rows`
- `test_fr16_count_by_returns_only_present_values_and_rejects_unknown_columns`
- `test_nfr06_write_session_rolls_back_on_exception`
- `test_nfr06_write_session_commits_on_success_and_is_visible_to_new_connection`
- `test_nfr06_failed_multi_statement_session_is_atomic`
- `test_nfr08_get_db_path_uses_env_var_then_default`
- `test_ac14_fr07_fetch_ticket_returns_all_ten_fields`

### `tests/test_persistence_integrity.py` - Persistence, integrity, StorageError translation, timing (AC-47, 48, 54, 55, 56) (27 cases in 20 functions; 27 passed, 0 failed)

- `test_ac47_nfr01_new_service_on_same_file_sees_every_field_and_dashboard`
- `test_ac47_nfr01_data_survives_updates_across_restarts`
- `test_ac48_nfr01_data_visible_after_connection_is_closed_and_reopened`
- `test_ac47_ac06_special_characters_survive_restart` x8
- `test_ac47_nfr01_schema_creation_is_idempotent`
- `test_ac56_nfr07_database_file_is_created_inside_tmp_path_only`
- `test_ac56_nfr07_str_path_and_path_object_are_both_accepted`
- `test_ac56_nfr07_two_databases_do_not_share_data`
- `test_ac55_nfr06_rejected_operations_leave_snapshot_identical`
- `test_ac55_nfr06_failed_status_change_with_note_does_not_partially_apply`
- `test_ac55_nfr06_storage_error_during_insert_leaves_no_row`
- `test_ac55_nfr06_storage_error_during_update_rolls_back`
- `test_nfr06_dropped_table_is_translated_to_storage_error`
- `test_nfr06_directory_as_database_path_is_translated_to_storage_error`
- `test_nfr06_non_database_file_is_translated_to_storage_error`
- `test_nfr06_parent_path_is_a_file_is_translated_to_storage_error`
- `test_nfr06_storage_error_message_and_log_do_not_leak_ticket_text`
- `test_nfr06_validation_errors_are_not_logged_as_storage_failures`
- `test_ac54_nfr05_list_and_dashboard_with_1000_tickets_load_within_2_seconds`
- `test_ac55_nfr06_raw_rows_helper_matches_service_view`

### `tests/test_real_data_safety.py` - Real-data safety guard tests (AC-56) (8 cases in 8 functions; 8 passed, 0 failed)

- `test_ac56_nfr07_env_var_points_to_a_tmp_path_not_the_real_db`
- `test_ac56_nfr07_service_fixture_uses_explicit_tmp_database`
- `test_ac56_nfr07_default_constructor_never_touches_the_real_database`
- `test_ac56_nfr07_guard_refuses_connections_to_the_real_database`
- `test_ac56_nfr07_guard_also_blocks_relative_and_dotdot_spellings_of_real_path`
- `test_ac56_nfr07_blank_env_var_would_fall_back_to_default_but_is_never_connected`
- `test_ac56_nfr07_real_database_file_is_unchanged_by_a_service_workout`
- `test_ac56_nfr07_default_db_path_is_inside_repo_data_directory`

### `tests/test_service_create.py` - L2 creation and validation (AC-01..11, 33, 67) (151 cases in 38 functions; 145 passed, 6 failed)

- `test_ac01_fr01_valid_ticket_is_created_and_listed`
- `test_ac02_fr01_fr07_stored_values_equal_input`
- `test_ac02_fr02_text_fields_are_trimmed`
- `test_ac11_fr05_new_ticket_status_is_open`
- `test_ac33_fr13_new_ticket_updated_at_equals_created_at`
- `test_ac09_fr04_ids_increase_and_created_at_not_earlier`
- `test_ac09_fr04_ids_are_never_reused_after_deletion`
- `test_ac09_fr04_failed_create_does_not_consume_or_leave_rows`
- `test_ac10_fr04_asm13_identical_submissions_create_two_tickets`
- `test_ac10_fr04_many_repeated_creates_get_unique_ids`
- `test_ac10_fr04_concurrent_creates_from_threads_have_unique_ids`
- `test_ac03_fr02_empty_required_text_is_rejected_with_field_message` x12
- `test_ac04_fr02_whitespace_only_text_counts_as_empty` x18
- `test_ac03_fr02_non_string_text_is_rejected` x18
- `test_ac03_fr02_missing_arguments_raise_type_error`
- `test_ac03_fr02_all_errors_are_collected_in_one_validation_error`
- `test_ac03_fr02_two_invalid_fields_only_reports_those_two`
- `test_ac05_fr02_exactly_at_limit_is_accepted` x3
- `test_ac05_fr02_one_over_limit_is_rejected_with_limit_in_message` x3
- `test_ac05_fr02_surrounding_whitespace_does_not_count_toward_limit` x3
- `test_ac05_fr02_limit_counts_characters_not_bytes` x3
- `test_edge_fr02_hugely_oversized_input_is_rejected_cleanly` x3
- `test_ac06_fr02_special_characters_roundtrip_literally` x16
- `test_ac06_fr02_control_and_invisible_characters_roundtrip` x4
- `test_ac06_fr02_description_keeps_internal_line_breaks`
- `test_ac06_nfr08_sql_injection_text_does_not_damage_table`
- `test_edge_fr02_lone_surrogate_is_rejected_with_cannot_be_stored`
- `test_edge_fr02_lone_surrogate_in_each_text_field` x3
- `test_edge_fr02_nul_character_is_stored_literally_or_rejected_with_validation_message` x12 **[6 FAILED]**
- `test_ac07_fr03_priority_options_and_default_are_as_specified`
- `test_ac07_fr03_every_listed_priority_is_accepted` x4
- `test_ac08_fr03_invalid_priority_is_rejected` x12
- `test_ac67_fr25_category_options_and_default_are_as_specified`
- `test_ac67_fr25_every_listed_category_is_accepted` x5
- `test_ac67_fr25_invalid_category_is_rejected` x10
- `test_ac67_fr25_category_cannot_be_changed_after_creation`
- `test_ac01_fr01_create_has_no_way_to_set_status_or_id`
- `test_ac55_nfr06_rejected_create_leaves_database_identical`

### `tests/test_service_dashboard.py` - L2 dashboard (AC-37, 39..43, 59, 65) (16 cases in 16 functions; 16 passed, 0 failed)

- `test_ac42_fr20_fr24_empty_database_is_zero_filled_without_error`
- `test_ac41_ac65_fr19_fr24_keys_are_exactly_the_configured_lists_in_order`
- `test_ac37_fr16_total_equals_number_of_tickets`
- `test_ac39_ac59_fr18_fr23_status_counts_match_actual`
- `test_ac41_fr19_priority_counts_match_actual`
- `test_ac65_fr24_category_counts_match_actual`
- `test_ac40_ac41_ac65_invariants_hold_on_populated_data`
- `test_ac41_fr19_zero_levels_are_shown_when_other_levels_have_tickets`
- `test_ac43_fr20_dashboard_reflects_create_without_restart`
- `test_ac43_fr20_dashboard_reflects_status_change`
- `test_ac43_fr20_dashboard_reflects_priority_change_and_total_is_stable`
- `test_ac43_fr20_rejected_updates_do_not_change_dashboard`
- `test_ac59_fr23_closed_count_is_visible_and_counts_only_closed`
- `test_ac40_fr16_dashboard_has_no_pending_figure`
- `test_ac42_fr20_dashboard_is_read_only`
- `test_ac40_ac41_ac65_invariants_hold_for_every_prefix_of_a_mixed_sequence`

### `tests/test_service_read.py` - L2 retrieval, filters, My tickets (AC-02, 12..20, 60, 66) (107 cases in 37 functions; 101 passed, 6 failed)

- `test_ac14_fr07_details_contain_all_ten_fields`
- `test_ac15_fr07_unknown_id_raises_not_found` x8
- `test_ac15_fr07_id_beyond_sqlite_integer_range_gives_clean_error` x5 **[5 FAILED]**
- `test_ac15_fr07_non_integer_id_is_validation_error` x11
- `test_ac29_fr09_non_integer_id_rejected_by_every_update_operation` x4
- `test_ac15_fr07_sql_injection_looking_id_string_is_not_executed`
- `test_ac13_fr06_empty_database_lists_nothing_without_error`
- `test_ac12_fr06_list_is_newest_first_with_all_columns`
- `test_ac12_fr06_newest_first_is_by_id_even_with_identical_timestamps`
- `test_ac16_fr08_filter_by_status_only_returns_that_status`
- `test_ac16_fr08_each_status_filter_matches_exactly` x4
- `test_ac17_fr08_filter_by_priority_only_returns_that_priority`
- `test_ac17_fr08_each_priority_filter_matches_exactly` x4
- `test_ac60_fr08_filter_by_category`
- `test_ac60_fr08_each_category_filter_matches_exactly` x5
- `test_ac18_fr08_status_and_priority_combine_with_and`
- `test_ac18_fr08_all_four_filters_combine`
- `test_ac19_fr08_creator_filter_is_case_insensitive_and_trimmed`
- `test_ac19_fr08_creator_filter_is_exact_not_substring`
- `test_ac19_fr08_creator_filter_uses_unicode_casefold`
- `test_ac20_fr08_filter_combination_with_no_match_returns_empty_list`
- `test_fr08_blank_or_none_filter_means_no_filter` x16
- `test_fr08_status_filter_value_is_trimmed`
- `test_fr08_invalid_filter_value_is_validation_error` x11
- `test_fr08_non_string_creator_filter_is_validation_error`
- `test_fr08_several_invalid_filters_are_collected`
- `test_fr08_nfr08_injection_text_in_creator_filter_is_literal` x5
- `test_fr08_nfr08_injection_text_in_enum_filters_is_validation_error` x3
- `test_fr08_creator_filter_lone_surrogate_fails_cleanly` **[1 FAILED]**
- `test_fr08_filtering_does_not_modify_data`
- `test_ac66_fr26_my_tickets_returns_only_own_tickets_trimmed_case_insensitive`
- `test_ac66_fr26_my_tickets_exposes_status_and_resolution_note`
- `test_ac66_fr26_name_without_tickets_returns_empty_list`
- `test_ac66_fr26_blank_or_invalid_name_is_rejected_and_never_means_all` x6
- `test_ac66_fr26_my_tickets_wildcards_and_injection_are_literal`
- `test_ac66_fr26_my_tickets_name_over_limit_is_rejected`
- `test_ac66_fr26_my_tickets_newest_first`

### `tests/test_service_update.py` - L2 workflow, priority, note, updated_at (AC-21..31, 33, 36, 61..64) (169 cases in 48 functions; 167 passed, 2 failed)

- `test_ac21_fr10_config_transition_table_matches_approved_table`
- `test_ac21_ac22_ac23_ac24_ac61_fr10_every_allowed_transition_succeeds` x5
- `test_ac21_fr10_fr13_open_to_in_progress_refreshes_updated_at`
- `test_ac22_fr15_resolved_with_note_supplied_in_same_action`
- `test_ac22_fr15_resolved_with_existing_stored_note`
- `test_ac22_fr15_note_in_change_status_replaces_stored_note`
- `test_ac22_fr15_blank_note_in_change_status_keeps_stored_note` x4
- `test_ac22_fr15_note_may_accompany_any_allowed_transition`
- `test_ac23_fr10_reopen_resolved_to_in_progress_retains_note`
- `test_ac24_fr10_in_progress_back_to_open`
- `test_ac23_ac22_fr10_full_reopen_path_open_to_closed_and_back_down`
- `test_ac25_ac26_ac27_ac62_ac63_fr10_every_disallowed_pair_is_rejected_unchanged` x22
- `test_ac25_fr10_open_to_resolved_message_names_allowed_target`
- `test_ac25_fr10_open_to_resolved_without_note_is_state_error_not_note_error`
- `test_ac26_fr10_resolved_to_open_message`
- `test_ac27_fr10_same_status_message` x3
- `test_ac63_fr10_open_or_in_progress_straight_to_closed_rejected` x2
- `test_ac28_fr09_invalid_status_value_is_validation_error_and_ticket_unchanged` x33
- `test_ac28_fr09_multiple_invalid_inputs_are_collected`
- `test_ac29_fr09_unknown_id_raises_not_found_for_every_update` x4
- `test_ac29_fr09_id_beyond_sqlite_integer_range_gives_clean_error` x2 **[2 FAILED]**
- `test_ac64_fr10_fr15_resolved_without_note_is_rejected_naming_the_note` x4
- `test_ac30_fr11_priority_change_visible_in_details_list_and_dashboard`
- `test_ac30_fr11_every_listed_priority_is_reachable` x3
- `test_ac31_fr11_same_priority_rejected_unchanged`
- `test_ac31_fr11_invalid_priority_rejected_unchanged` x10
- `test_ac30_fr11_priority_can_change_on_every_non_closed_status` x3
- `test_ac61_fr10_resolved_to_closed_refreshes_updated_at`
- `test_ac62_fr10_closed_ticket_rejects_every_status_change` x4
- `test_ac62_fr11_closed_ticket_rejects_every_priority_change` x4
- `test_ac62_fr15_closed_ticket_rejects_note_change`
- `test_ac62_fr10_closed_check_precedes_value_checks_only_for_valid_values`
- `test_ac36_fr15_note_within_limit_is_saved` x4
- `test_ac36_fr15_note_1001_chars_rejected_unchanged`
- `test_ac36_fr15_blank_or_invalid_note_rejected_unchanged` x6
- `test_ac36_fr15_note_over_limit_in_change_status_is_rejected`
- `test_ac36_fr15_note_special_characters_roundtrip_literally` x16
- `test_ac36_fr15_note_is_trimmed_and_keeps_line_breaks`
- `test_ac36_fr15_note_replaces_previous_note`
- `test_ac36_fr15_note_allowed_on_every_non_closed_status` x3
- `test_ac36_fr15_unicode_note_at_limit`
- `test_ac36_fr15_lone_surrogate_note_rejected`
- `test_ac33_fr13_updated_at_changes_on_each_successful_update_type`
- `test_ac33_fr13_updated_at_unchanged_after_each_kind_of_rejected_update`
- `test_ac33_fr13_update_does_not_alter_other_tickets`
- `test_ac21_fr10_allowed_next_statuses_equals_transition_table` x4
- `test_ac28_fr10_allowed_next_statuses_unknown_is_empty` x5
- `test_ac62_fr10_closed_has_no_next_statuses`

### `tests/test_ui_engineer.py` - L3 AppTest Engineer update forms (16 cases in 16 functions; 16 passed, 0 failed)

- `test_ac21_ac33_fr10_open_to_in_progress_via_form`
- `test_ac24_ac25_fr10_status_dropdown_offers_only_allowed_targets`
- `test_ac64_fr10_fr15_resolved_without_note_shows_resolution_note_error`
- `test_ac22_fr15_resolved_with_note_typed_in_the_same_form`
- `test_ac23_ac61_fr10_reopen_and_close_via_form`
- `test_ac36_fr15_save_note_only_replaces_note_and_keeps_status`
- `test_ac36_fr15_save_blank_note_shows_error_and_changes_nothing`
- `test_ac36_fr15_over_long_note_is_rejected_with_limit_message`
- `test_ac30_fr11_change_priority_via_form_updates_details_list_and_dashboard`
- `test_ac31_fr11_same_priority_submission_shows_message_and_changes_nothing`
- `test_ac62_fr10_closed_ticket_is_read_only_in_the_engineer_view`
- `test_ac44_ac62_selecting_another_ticket_switches_the_forms`
- `test_ac43_fr20_dashboard_reflects_status_change_made_in_engineer_view`
- `test_ac55_nfr06_rejected_ui_operations_leave_stored_data_unchanged`
- `test_ac29_ac15_fr09_fr07_ui_only_offers_existing_ticket_ids`
- `test_fr06_special_characters_in_titles_do_not_break_the_selector_or_details`

### `tests/test_ui_search.py` - L3 AppTest + unit FR-27 search (AC-71..81) (41 cases in 27 functions; 41 passed, 0 failed)

- `test_ac71_ac72_fr27_search_tickets_function_is_case_insensitive_substring_and_keeps_order`
- `test_ac76_fr27_empty_or_whitespace_query_returns_the_same_list` x4
- `test_ac77_fr27_search_tickets_does_not_modify_its_input_and_treats_text_literally`
- `test_ac74_fr27_search_matches_id_text_substring`
- `test_ac71_fr27_engineer_search_title_substring_lists_only_matching_ticket`
- `test_ac71_fr27_engineer_search_keeps_newest_first_order`
- `test_ac72_fr27_engineer_search_is_case_insensitive` x3
- `test_ac73_fr27_engineer_search_covers_description_and_creator_only`
- `test_ac74_fr27_engineer_search_by_ticket_id_text`
- `test_ac75_fr27_fr08_search_combines_with_filters_and_clearing_restores`
- `test_ac75_fr27_search_combines_with_each_other_filter`
- `test_ac76_fr27_engineer_empty_or_blank_search_shows_full_list_without_messages` x3
- `test_ac77_fr27_nfr08_special_characters_are_matched_literally` x6
- `test_ac77_fr27_nfr08_sql_looking_search_matches_nothing_and_changes_nothing`
- `test_ac77_fr27_percent_does_not_match_everything`
- `test_ac78_fr27_no_match_shows_message_and_clearing_restores_list`
- `test_ac78_fr27_overlong_search_text_simply_matches_nothing`
- `test_ac78_fr27_search_on_empty_database_shows_no_tickets_not_an_error`
- `test_ac72_fr27_search_handles_unicode_text` x3
- `test_ac81_fr27_search_does_not_change_stored_data`
- `test_ac79_fr27_fr26_employee_search_never_shows_other_peoples_tickets`
- `test_ac79_fr27_fr26_employee_search_matching_every_ticket_still_only_lists_own`
- `test_ac80_fr27_fr26_employee_messages_for_no_match_no_tickets_and_cleared_search`
- `test_ac71_ac72_fr27_employee_search_title_case_insensitive`
- `test_ac76_fr27_employee_blank_search_shows_all_own_tickets`
- `test_ac77_fr27_employee_search_special_characters_literal`
- `test_ac81_fr27_employee_search_leaves_stored_data_unchanged`

### `tests/test_ui_smoke.py` - L3 AppTest smoke: roles, notice, create form, My tickets, dashboard, filters (53 cases in 38 functions; 53 passed, 0 failed)

- `test_ac44_fr21_app_starts_without_exception`
- `test_ac45_fr21_nfr12_demo_notice_is_visible_in_every_role` x3
- `test_ac44_fr21_role_selector_options_and_label`
- `test_ac44_fr21_employee_screen_has_form_and_my_tickets_but_no_update_controls`
- `test_ac44_fr21_engineer_screen_has_filters_search_and_update_controls`
- `test_ac44_fr21_manager_screen_is_dashboard_only`
- `test_ac44_fr21_switching_roles_back_and_forth_keeps_app_healthy`
- `test_ac07_ac67_fr03_fr25_form_options_and_defaults`
- `test_ac51_nfr03_required_fields_are_labelled_and_marked`
- `test_ac01_fr01_submit_valid_ticket_shows_id_and_ticket_is_stored`
- `test_ac01_fr01_created_ticket_appears_in_engineer_list`
- `test_ac01_fr01_form_is_reset_with_fresh_widgets_after_success`
- `test_ac01_ac09_two_submissions_create_two_tickets_with_increasing_ids`
- `test_ac03_ac52_fr02_empty_field_shows_named_error_and_keeps_other_values` x3
- `test_ac03_ac52_fr02_all_empty_reports_every_missing_field`
- `test_ac04_fr02_whitespace_only_title_is_rejected_in_the_form`
- `test_ac05_fr02_over_limit_title_shows_limit_message_and_widget_has_no_max_chars`
- `test_ac05_fr02_exactly_at_limit_is_created_through_the_form`
- `test_ac06_fr02_special_characters_are_created_and_shown_literally` x12
- `test_ac06_fr02_multiline_description_roundtrips_in_details`
- `test_ac06_nfr08_sql_injection_text_in_form_leaves_table_and_other_tickets_intact`
- `test_ac66_fr26_my_tickets_asks_for_a_name_first`
- `test_ac66_fr26_my_tickets_lists_only_own_tickets_case_and_space_insensitive`
- `test_ac66_fr07_fr26_my_tickets_details_show_status_and_resolution_note`
- `test_ac66_fr26_unknown_name_shows_no_tickets_message`
- `test_ac66_fr26_employee_view_has_no_update_controls_even_with_a_name_entered`
- `test_ac66_fr26_my_tickets_disclaimer_says_convenience_not_privacy`
- `test_ac47_ac48_nfr01_second_app_session_shows_tickets_created_by_the_first`
- `test_ac42_fr20_fr24_manager_dashboard_on_empty_database_shows_zeros`
- `test_ac37_ac39_ac40_ac59_fr16_fr18_fr23_manager_metrics_match_data`
- `test_ac41_ac65_manager_shows_priority_and_category_sections_with_charts`
- `test_ac43_fr20_manager_refresh_shows_data_created_after_first_load`
- `test_ac43_fr20_dashboard_reflects_a_ticket_raised_in_the_employee_view`
- `test_ac13_fr06_engineer_view_on_empty_database_shows_no_tickets_message`
- `test_ac12_fr06_engineer_table_columns_and_newest_first`
- `test_ac14_fr07_engineer_details_show_all_fields`
- `test_ac16_ac17_ac18_ac19_ac20_ac60_fr08_engineer_filters_and_no_match_message`
- `test_ac58_nfr09_app_makes_no_outbound_network_connection_during_a_full_walkthrough`


## 5. Acceptance-criteria coverage (all active AC-01..AC-81)

Legend: PASS (automated) = at least one automated test names the AC and all of them passed. "manual M-xx pending" = a checklist item exists for a part that automation cannot show and has not been executed yet. The "Tests" column shows case counts and up to two test function names (prefix `test_` omitted); the full list is in section 4.

| AC | FR / NFR | Tests | Status |
|---|---|---|---|
| AC-01 | FR-01 | 6 passed: `ac01_fr01_valid_ticket_is_created_and_listed`, `ac01_fr01_create_has_no_way_to_set_status_or_id` (+4 more functions) | PASS (automated) |
| AC-02 | FR-01, FR-07 | 2 passed: `ac02_fr01_fr07_stored_values_equal_input`, `ac02_fr02_text_fields_are_trimmed` | PASS (automated) |
| AC-03 | FR-02 | 37 passed: `ac03_fr02_empty_required_text_is_rejected_with_field_message`, `ac03_fr02_non_string_text_is_rejected` (+5 more functions) | PASS (automated) |
| AC-04 | FR-02 | 19 passed: `ac04_fr02_whitespace_only_text_counts_as_empty`, `ac04_fr02_whitespace_only_title_is_rejected_in_the_form` | PASS (automated) |
| AC-05 | FR-02 | 14 passed: `ac05_fr02_exactly_at_limit_is_accepted`, `ac05_fr02_one_over_limit_is_rejected_with_limit_in_message` (+4 more functions) | PASS (automated) |
| AC-06 | FR-02 | 45 passed: `ac06_nfr08_values_with_sql_text_roundtrip_unchanged`, `ac47_ac06_special_characters_survive_restart` (+7 more functions) | PASS (automated); note: DEF-03 affects FR-02 robustness for NUL text (not in the AC list of special characters) |
| AC-07 | FR-03 | 6 passed: `ac07_fr03_priority_options_and_default_are_as_specified`, `ac07_fr03_every_listed_priority_is_accepted` (+1 more functions) | PASS (automated) |
| AC-08 | FR-03 | 12 passed: `ac08_fr03_invalid_priority_is_rejected` | PASS (automated) |
| AC-09 | FR-04 | 5 passed: `ac09_fr04_ids_increase_and_are_not_reused`, `ac09_fr04_ids_increase_and_created_at_not_earlier` (+3 more functions) | PASS (automated) |
| AC-10 | FR-04 (ASM-13) | 3 passed: `ac10_fr04_asm13_identical_submissions_create_two_tickets`, `ac10_fr04_many_repeated_creates_get_unique_ids` (+1 more functions) | PASS (automated) |
| AC-11 | FR-05 | 1 passed: `ac11_fr05_new_ticket_status_is_open` | PASS (automated) |
| AC-12 | FR-06 | 3 passed: `ac12_fr06_list_is_newest_first_with_all_columns`, `ac12_fr06_newest_first_is_by_id_even_with_identical_timestamps` (+1 more functions) | PASS (automated) |
| AC-13 | FR-06 | 2 passed: `ac13_fr06_empty_database_lists_nothing_without_error`, `ac13_fr06_engineer_view_on_empty_database_shows_no_tickets_message` | PASS (automated) |
| AC-14 | FR-07 | 3 passed: `ac14_fr07_fetch_ticket_returns_all_ten_fields`, `ac14_fr07_details_contain_all_ten_fields` (+1 more functions) | PASS (automated) |
| AC-15 | FR-07 | 21 passed, 5 failed: `ac15_fr07_unknown_id_raises_not_found`, `ac15_fr07_id_beyond_sqlite_integer_range_gives_clean_error` (+3 more functions) | **FAIL** (DEF-01: raw OverflowError for ticket ID outside SQLite range) |
| AC-16 | FR-08 | 6 passed: `ac16_fr08_filter_by_status_only_returns_that_status`, `ac16_fr08_each_status_filter_matches_exactly` (+1 more functions) | PASS (automated) |
| AC-17 | FR-08 | 6 passed: `ac17_fr08_filter_by_priority_only_returns_that_priority`, `ac17_fr08_each_priority_filter_matches_exactly` (+1 more functions) | PASS (automated) |
| AC-18 | FR-08 | 3 passed: `ac18_fr08_status_and_priority_combine_with_and`, `ac18_fr08_all_four_filters_combine` (+1 more functions) | PASS (automated) |
| AC-19 | FR-08 | 4 passed: `ac19_fr08_creator_filter_is_case_insensitive_and_trimmed`, `ac19_fr08_creator_filter_is_exact_not_substring` (+2 more functions) | PASS (automated); note: DEF-02 affects FR-08 creator-filter robustness (not the AC text) |
| AC-20 | FR-08 | 2 passed: `ac20_fr08_filter_combination_with_no_match_returns_empty_list`, `ac16_ac17_ac18_ac19_ac20_ac60_fr08_engineer_filters_and_no_match_message` | PASS (automated) |
| AC-21 | FR-09, FR-10, FR-13 | 12 passed: `ac21_fr10_config_transition_table_matches_approved_table`, `ac21_ac22_ac23_ac24_ac61_fr10_every_allowed_transition_succeeds` (+3 more functions) | PASS (automated) |
| AC-22 | FR-09, FR-10, FR-15 | 15 passed: `ac21_ac22_ac23_ac24_ac61_fr10_every_allowed_transition_succeeds`, `ac22_fr15_resolved_with_note_supplied_in_same_action` (+6 more functions) | PASS (automated) |
| AC-23 | FR-10 | 8 passed: `ac21_ac22_ac23_ac24_ac61_fr10_every_allowed_transition_succeeds`, `ac23_fr10_reopen_resolved_to_in_progress_retains_note` (+2 more functions) | PASS (automated) |
| AC-24 | FR-10 | 7 passed: `ac21_ac22_ac23_ac24_ac61_fr10_every_allowed_transition_succeeds`, `ac24_fr10_in_progress_back_to_open` (+1 more functions) | PASS (automated) |
| AC-25 | FR-10 | 25 passed: `ac25_ac26_ac27_ac62_ac63_fr10_every_disallowed_pair_is_rejected_unchanged`, `ac25_fr10_open_to_resolved_message_names_allowed_target` (+2 more functions) | PASS (automated) |
| AC-26 | FR-10 | 23 passed: `ac25_ac26_ac27_ac62_ac63_fr10_every_disallowed_pair_is_rejected_unchanged`, `ac26_fr10_resolved_to_open_message` | PASS (automated) |
| AC-27 | FR-10 | 25 passed: `ac25_ac26_ac27_ac62_ac63_fr10_every_disallowed_pair_is_rejected_unchanged`, `ac27_fr10_same_status_message` | PASS (automated) |
| AC-28 | FR-09 | 39 passed: `ac28_fr09_invalid_status_value_is_validation_error_and_ticket_unchanged`, `ac28_fr09_multiple_invalid_inputs_are_collected` (+1 more functions) | PASS (automated) |
| AC-29 | FR-09 | 9 passed, 2 failed: `ac29_fr09_non_integer_id_rejected_by_every_update_operation`, `ac29_fr09_unknown_id_raises_not_found_for_every_update` (+2 more functions) | **FAIL** (DEF-01: raw OverflowError for ticket ID outside SQLite range) |
| AC-30 | FR-11 | 8 passed: `ac30_fr11_priority_change_visible_in_details_list_and_dashboard`, `ac30_fr11_every_listed_priority_is_reachable` (+2 more functions) | PASS (automated) |
| AC-31 | FR-11 | 12 passed: `ac31_fr11_same_priority_rejected_unchanged`, `ac31_fr11_invalid_priority_rejected_unchanged` (+1 more functions) | PASS (automated) |
| AC-32 | FR-12 (retired) | - | RETIRED (no requirement, no tests) |
| AC-33 | FR-13 | 5 passed: `ac33_fr13_new_ticket_updated_at_equals_created_at`, `ac33_fr13_updated_at_changes_on_each_successful_update_type` (+3 more functions) | PASS (automated) |
| AC-34 | FR-14 (retired) | - | RETIRED (no requirement, no tests) |
| AC-35 | FR-14 (retired) | - | RETIRED (no requirement, no tests) |
| AC-36 | FR-15 | 38 passed: `ac36_fr15_note_within_limit_is_saved`, `ac36_fr15_note_1001_chars_rejected_unchanged` (+11 more functions) | PASS (automated) |
| AC-37 | FR-16 | 2 passed: `ac37_fr16_total_equals_number_of_tickets`, `ac37_ac39_ac40_ac59_fr16_fr18_fr23_manager_metrics_match_data` | PASS (automated) |
| AC-38 | FR-17 (retired) | - | RETIRED (no requirement, no tests) |
| AC-39 | FR-18 | 2 passed: `ac39_ac59_fr18_fr23_status_counts_match_actual`, `ac37_ac39_ac40_ac59_fr16_fr18_fr23_manager_metrics_match_data` | PASS (automated) |
| AC-40 | FR-16, FR-18, FR-23 | 4 passed: `ac40_ac41_ac65_invariants_hold_on_populated_data`, `ac40_fr16_dashboard_has_no_pending_figure` (+2 more functions) | PASS (automated) |
| AC-41 | FR-19 | 6 passed: `ac41_ac65_fr19_fr24_keys_are_exactly_the_configured_lists_in_order`, `ac41_fr19_priority_counts_match_actual` (+4 more functions) | PASS (automated) |
| AC-42 | FR-20, FR-24 | 3 passed: `ac42_fr20_fr24_empty_database_is_zero_filled_without_error`, `ac42_fr20_dashboard_is_read_only` (+1 more functions) | PASS (automated) |
| AC-43 | FR-20 | 7 passed: `ac43_fr20_dashboard_reflects_create_without_restart`, `ac43_fr20_dashboard_reflects_status_change` (+5 more functions) | PASS (automated) |
| AC-44 | FR-21 | 7 passed: `ac44_ac62_selecting_another_ticket_switches_the_forms`, `ac44_fr21_app_starts_without_exception` (+5 more functions) | PASS (automated) + manual M-06 (visual part) pending |
| AC-45 | FR-21, NFR-12 | 12 passed: `ac45_fr21_demo_notice_text_is_present_and_clear`, `ac45_fr21_main_renders_notice_before_any_role_view` (+3 more functions) | PASS (automated) + manual M-07 (visual part) pending |
| AC-46 | FR-22 (retired) | - | RETIRED (no requirement, no tests) |
| AC-47 | NFR-01 | 13 passed: `ac47_nfr01_init_schema_is_idempotent_and_creates_parent_directory`, `ac47_nfr01_new_service_on_same_file_sees_every_field_and_dashboard` (+4 more functions) | PASS (automated) + manual M-05 (real restart) pending |
| AC-48 | NFR-01 | 2 passed: `ac48_nfr01_data_visible_after_connection_is_closed_and_reopened`, `ac47_ac48_nfr01_second_app_session_shows_tickets_created_by_the_first` | PASS (automated) + manual M-05 (browser refresh/reopen) pending |
| AC-49 | NFR-02 | 0: none (cannot be automated: real browser / human judgement) | MANUAL ONLY - checklist M-01, not yet executed |
| AC-50 | NFR-03 | 0: none (cannot be automated: real browser / human judgement) | MANUAL ONLY - checklist M-02, not yet executed |
| AC-51 | NFR-03 | 1 passed: `ac51_nfr03_required_fields_are_labelled_and_marked` | PASS (automated) + manual M-08 (visual part) pending |
| AC-52 | NFR-03 | 4 passed: `ac03_ac52_fr02_empty_field_shows_named_error_and_keeps_other_values`, `ac03_ac52_fr02_all_empty_reports_every_missing_field` | PASS (automated) + manual M-09 (browser) pending |
| AC-53 | NFR-04 | 0: none (cannot be automated: real browser / human judgement) | MANUAL ONLY - checklist M-03, not yet executed |
| AC-54 | NFR-05 | 1 passed: `ac54_nfr05_list_and_dashboard_with_1000_tickets_load_within_2_seconds` | PASS (automated) + manual M-04 (UI timing half) pending |
| AC-55 | NFR-06 | 7 passed: `ac55_nfr06_rejected_operations_leave_snapshot_identical`, `ac55_nfr06_failed_status_change_with_note_does_not_partially_apply` (+5 more functions) | PASS (automated) |
| AC-56 | NFR-07 | 12 passed: `ac56_nfr07_meta_tests_run_without_a_browser_and_conftest_guards_exist`, `ac56_nfr07_database_file_is_created_inside_tmp_path_only` (+10 more functions) | PASS (automated) |
| AC-57 | NFR-08 | 29 passed: `ac57_nfr08_ui_does_not_import_sqlite3_or_the_db_layer`, `ac57_nfr08_ui_contains_no_sql_keywords_in_string_literals` (+8 more functions) | PASS (automated) + manual M-10 (review part) pending |
| AC-58 | NFR-09 | 26 passed: `ac58_nfr09_no_network_or_cloud_imports`, `ac58_nfr09_no_urls_in_application_string_literals` (+4 more functions) | PASS (automated) + manual M-11 (network monitor) pending |
| AC-59 | FR-23 | 3 passed: `ac39_ac59_fr18_fr23_status_counts_match_actual`, `ac59_fr23_closed_count_is_visible_and_counts_only_closed` (+1 more functions) | PASS (automated) |
| AC-60 | FR-08 | 7 passed: `ac60_fr08_filter_by_category`, `ac60_fr08_each_category_filter_matches_exactly` (+1 more functions) | PASS (automated) |
| AC-61 | FR-09, FR-10 | 7 passed: `ac21_ac22_ac23_ac24_ac61_fr10_every_allowed_transition_succeeds`, `ac61_fr10_resolved_to_closed_refreshes_updated_at` (+1 more functions) | PASS (automated) |
| AC-62 | FR-10, FR-11, FR-15 | 35 passed: `ac25_ac26_ac27_ac62_ac63_fr10_every_disallowed_pair_is_rejected_unchanged`, `ac62_fr10_closed_ticket_rejects_every_status_change` (+6 more functions) | PASS (automated) |
| AC-63 | FR-10 | 24 passed: `ac25_ac26_ac27_ac62_ac63_fr10_every_disallowed_pair_is_rejected_unchanged`, `ac63_fr10_open_or_in_progress_straight_to_closed_rejected` | PASS (automated) |
| AC-64 | FR-10, FR-15 | 5 passed: `ac64_fr10_fr15_resolved_without_note_is_rejected_naming_the_note`, `ac64_fr10_fr15_resolved_without_note_shows_resolution_note_error` | PASS (automated) |
| AC-65 | FR-24 | 5 passed: `ac41_ac65_fr19_fr24_keys_are_exactly_the_configured_lists_in_order`, `ac65_fr24_category_counts_match_actual` (+3 more functions) | PASS (automated) |
| AC-66 | FR-26, FR-07 | 18 passed: `ac66_fr26_my_tickets_returns_only_own_tickets_trimmed_case_insensitive`, `ac66_fr26_my_tickets_exposes_status_and_resolution_note` (+11 more functions) | PASS (automated) |
| AC-67 | FR-25, FR-02 | 18 passed: `ac67_fr25_category_options_and_default_are_as_specified`, `ac67_fr25_every_listed_category_is_accepted` (+3 more functions) | PASS (automated) |
| AC-68 | NFR-12 | 7 passed: `ac45_ac68_fr21_ui_strings_make_no_login_or_security_claim`, `ac68_nfr12_readme_discloses_demo_roles_and_makes_no_security_claim` | PASS (automated) + manual M-12 (reading) pending |
| AC-69 | NFR-10 | 3 passed: `ac69_nfr10_python_streamlit_sqlite_pytest_baseline`, `ac69_nfr10_entry_point_is_app_main_py_and_readme_states_launch_command` (+1 more functions) | PASS (automated) + manual M-13 (Python 3.10 run) pending |
| AC-70 | NFR-11 | 1 passed: `ac70_nfr11_ruff_reports_no_errors_with_project_configuration` | PASS (automated) |
| AC-71 | FR-27 | 4 passed: `ac71_ac72_fr27_search_tickets_function_is_case_insensitive_substring_and_keeps_order`, `ac71_fr27_engineer_search_title_substring_lists_only_matching_ticket` (+2 more functions) | PASS (automated) |
| AC-72 | FR-27 | 8 passed: `ac71_ac72_fr27_search_tickets_function_is_case_insensitive_substring_and_keeps_order`, `ac72_fr27_engineer_search_is_case_insensitive` (+2 more functions) | PASS (automated) |
| AC-73 | FR-27 | 1 passed: `ac73_fr27_engineer_search_covers_description_and_creator_only` | PASS (automated) |
| AC-74 | FR-27 | 2 passed: `ac74_fr27_search_matches_id_text_substring`, `ac74_fr27_engineer_search_by_ticket_id_text` | PASS (automated) |
| AC-75 | FR-27, FR-08 | 2 passed: `ac75_fr27_fr08_search_combines_with_filters_and_clearing_restores`, `ac75_fr27_search_combines_with_each_other_filter` | PASS (automated) |
| AC-76 | FR-27 | 8 passed: `ac76_fr27_empty_or_whitespace_query_returns_the_same_list`, `ac76_fr27_engineer_empty_or_blank_search_shows_full_list_without_messages` (+1 more functions) | PASS (automated) |
| AC-77 | FR-27, NFR-08 | 10 passed: `ac77_fr27_search_tickets_does_not_modify_its_input_and_treats_text_literally`, `ac77_fr27_nfr08_special_characters_are_matched_literally` (+3 more functions) | PASS (automated) |
| AC-78 | FR-27 | 3 passed: `ac78_fr27_no_match_shows_message_and_clearing_restores_list`, `ac78_fr27_overlong_search_text_simply_matches_nothing` (+1 more functions) | PASS (automated) |
| AC-79 | FR-27, FR-26 | 2 passed: `ac79_fr27_fr26_employee_search_never_shows_other_peoples_tickets`, `ac79_fr27_fr26_employee_search_matching_every_ticket_still_only_lists_own` | PASS (automated) |
| AC-80 | FR-27, FR-26 | 1 passed: `ac80_fr27_fr26_employee_messages_for_no_match_no_tickets_and_cleared_search` | PASS (automated) |
| AC-81 | FR-27 | 4 passed: `ac81_fr27_service_offers_no_search_operation`, `ac81_fr27_search_runs_in_ui_layer_on_already_returned_tickets` (+2 more functions) | PASS (automated) + manual M-14 (inspection) pending |

Counts: 76 active ACs = 71 PASS + 2 FAIL + 3 MANUAL ONLY; 5 retired (AC-32, 34, 35, 38, 46) have no tests by design.

Service-level-only ACs (as the requirements state): AC-15 and AC-29 (unknown ticket ID). Their UI side is covered by `test_ac29_ac15_fr09_fr07_ui_only_offers_existing_ticket_ids`.

Requirement view: every active FR and NFR is reached by at least one passing automated AC test except NFR-02 (AC-49, manual only), NFR-03 usability measure (AC-50, manual only), NFR-04 (AC-53, manual only). FR-07 and FR-09 have all but their "unknown huge ticket ID" robustness cases passing (DEF-01).

## 6. Edge-case coverage (CLAUDE.md section 7 list)

| Edge case | Where tested |
|---|---|
| Invalid / empty / whitespace / None input | `test_service_create.py` (AC-03, AC-04 parametrized over creator, title, description and 4 + 6 bad values), update and filter tests |
| Oversized input | exactly-at-limit and limit+1 for creator/title/description/note; 1 MB values; emoji counted as characters; 5,000-character search |
| Special characters | `SPECIAL_TEXTS` (16 samples) round-trip for create, note, restart and UI; SQL-injection strings in title/description/creator/filters/search/ticket ID; control chars; unicode; emoji; newlines/tabs |
| Invalid status/priority/category/filters | all 4x4 transition pairs, bad values incl. wrong case, None, non-str; bool/str/float/None ticket IDs |
| Invalid transitions | 5 allowed + 11 rejected pairs, each with and without a note; Closed read-only for status/priority/note; Resolved without note; reopen path |
| Duplicates | identical creates, 60 repeated creates, 6 concurrent threads x 5 creates (unique IDs) |
| Persistence across reconnects | new `TicketService` on same file after create/update; idempotent schema; restart through the UI |
| Rejected operations leave data unchanged | `snapshot` of all rows compared after 21 rejected calls (AC-55) plus per-test checks of `updated_at` |
| StorageError translation | dropped table, directory as DB path, garbage file, DB path below a file, forced `sqlite3.Error` in insert/update (rollback), no ticket text in message/log |
| Real-data safety | autouse env guard, `db.connect` guard, session hash check, 8 guard tests |

## 7. Not testable here / manual items

See `docs/manual-test-checklist.md` (M-01 to M-14; none executed yet): real browsers (AC-49), first-time-user timing (AC-50), scope review (AC-53), UI timing with 1,000 tickets (AC-54 UI half), real server restart and browser refresh (AC-47, AC-48), visual checks (AC-44, AC-45, AC-51, AC-52), human code/doc review (AC-57, AC-68, AC-81), OS-level network monitoring (AC-58), Python 3.10 run (AC-69; only 3.14.4 is installed). The Streamlit server itself was deliberately not started (it would be a long-running local network service and could open `data/tickets.db`); AppTest runs the real `app/main.py` script instead, against temp databases.

## 8. Defects

| ID | Severity | Summary | FR / AC | Failing tests | Owner |
|---|---|---|---|---|---|
| DEF-01 | Medium | A ticket ID outside SQLite's 64-bit integer range makes `get_ticket`, `change_status`, `change_priority`, `set_resolution_note` raise a raw `OverflowError` instead of a `TicketError` | FR-07, FR-09, FR-11, FR-15; AC-15, AC-29; IC section 5 (every failed call yields a documented outcome), NFR-06 | 7 | backend-developer: `ticketing/service.py` (`_check_ticket_id`, `_load_editable`) / `ticketing/db.py` `fetch_ticket` |
| DEF-02 | Low | `list_tickets(creator=<text with lone surrogate>)` raises a raw `UnicodeEncodeError` | FR-08 (AC-19 robustness), VR section 5 | 1 | backend-developer: `ticketing/service.py` `list_tickets` |
| DEF-03 | Low | Title/description/creator that start with a NUL character (`"\x00"`, `"\x00abc"`) are rejected with the generic `StorageError` message "The ticket data could not be read or saved. Please try again." instead of a validation message naming the field; `"a\x00b"` and `"abc\x00"` are stored fine (inconsistent) | FR-02 (AC-03..06 robustness), VR section 5 | 6 | backend-developer: `ticketing/service.py` `_check_text` (DB CHECK `length(trim(...)) > 0` in `ticketing/db.py` fails because SQLite `length()` stops at NUL) |

### DEF-01 (Medium) - raw OverflowError for out-of-range ticket ID

- Tests: `test_service_read.py::test_ac15_fr07_id_beyond_sqlite_integer_range_gives_clean_error[...]` (5 cases: 2**63, 2**64, 2**70, -2**63-1, 10**30) and `test_service_update.py::test_ac29_fr09_id_beyond_sqlite_integer_range_gives_clean_error[...]` (2 cases: 2**63, 2**70).
- Steps: `svc = TicketService(db_path=<tmp>); svc.get_ticket(2**63)` (also `change_status(2**63, "In Progress")`, `change_priority(2**63, "Low")`, `set_resolution_note(2**63, "n")`).
- Expected (AC-15 "a not found message is shown and no error/crash occurs"; AC-29 "an error message is shown and no data changes"; IC section 5): a `TicketError` subclass, for example `NotFoundError("Ticket 9223372036854775808 was not found.")`.
- Actual: unhandled `OverflowError`, not caught by `_storage_guard` (which only handles `sqlite3.Error` and `OSError`). Raw output:

```
ticketing/service.py:256: in change_status
    current = self._load_editable(conn, ticket_id)
ticketing/service.py:325: in _load_editable
    current = db.fetch_ticket(conn, ticket_id)
ticketing/db.py:117: in fetch_ticket
    row = conn.execute(
E       OverflowError: Python int too large to convert to SQLite INTEGER
```
- Not reachable from the UI (the selector offers only existing IDs), hence Medium and not High. IDs up to 2**63-1 and down to -2**63 already return `NotFoundError` correctly (passing tests).
- Suggested fix direction (for the owner to decide): treat ints outside the SQLite range as not found before querying.

### DEF-02 (Low) - lone surrogate in creator filter

- Test: `test_service_read.py::test_fr08_creator_filter_lone_surrogate_fails_cleanly`.
- Steps: `svc.list_tickets(creator="\ud800")`.
- Expected: `[]` or a `ValidationError` ("... contains characters that cannot be stored."), as `create_ticket` and `list_my_tickets` already do.
- Actual (raw):
```
ticketing/db.py:134: UnicodeEncodeError
E       UnicodeEncodeError: 'utf-8' codec can't encode character '\ud800' in position 0: surrogates not allowed
```
- The creator filter skips the UTF-8 encodability check that `_check_text` applies elsewhere. Unlikely to be produced from a browser.

### DEF-03 (Low) - NUL character at the start of text

- Tests: `test_service_create.py::test_edge_fr02_nul_character_is_stored_literally_or_rejected_with_validation_message[...]`, 6 failing cases: values `"\x00"` and `"\x00abc"` for each of title, description, creator (the cases `"a\x00b"` and `"abc\x00"` pass).
- Steps: `svc.create_ticket("c", "\x00abc", "d", "Other", "Low")`.
- Expected (FR-02: invalid input is rejected with a message naming the field and no ticket is created; or the text is stored literally): `ValidationError` naming the field, or success.
- Actual (raw):
```
sqlite3.IntegrityError: CHECK constraint failed: length(trim(title)) > 0
ticketing.models.StorageError: The ticket data could not be read or saved. Please try again.
ERROR    ticketing:service.py:137 Storage failure in create_ticket (ticket n/a): IntegrityError
```
- No ticket is created (data intact), so this is a message-quality problem only. Plain-text inputs from a browser rarely contain NUL.

## 9. Fixes applied

None yet (cycle 0). No production file was edited by QA. Fixes are to be made by the backend-developer via the orchestrator; QA then re-runs the full suite and the hash check and records cycle 1 here.

Test-side corrections made during test authoring (test bugs, not production bugs): AppTest reports an unset `max_chars` as 0 (assertion adjusted to `in (None, 0)`); two widgets share the label "Resolution note" in the engineer details (selector changed to the widget key); the UI tests read the UI database via a dedicated `ui_snapshot` fixture; one expectation in a pure-function search test was corrected after review. None of these hid a production failure.

## 10. Remaining problems and risks

1. DEF-01, DEF-02, DEF-03 open (section 8).
2. Manual checklist M-01..M-14 not yet executed (browsers, usability, scope, UI timing, real restart, network monitoring, Python 3.10).
3. The suite runs on Python 3.14.4 only; the NFR-10 baseline (Python 3.10+) is unverified.
4. Several ACs depend on unapproved assumptions (ASM-03, 06, 13, 19, 20, 21, 24, 25); the tests encode the current values (limits 100/100/2000/1000, transition table, category list). If the human changes an assumption, the matching tests and `config.py` change together.
5. `data/tickets.db` pre-existed before this QA run (created by a developer run); its contents were not inspected. The README says it is git-ignored.

## 11. Real-data safety evidence (task 11)

Layers in `tests/conftest.py`:
1. At import time `TICKET_DB_PATH` is set to a throw-away temp directory, so code run during collection cannot fall back to `data/tickets.db`.
2. Autouse `guard_default_db` points `TICKET_DB_PATH` to the per-test `tmp_path`.
3. The same fixture wraps `ticketing.db.connect` and raises `AssertionError` if any code opens the real default database (even through `..` path spellings or a blank env var).
4. Session-scoped autouse fixture hashes `data/tickets.db` before and after the run and fails at teardown if the content changed.
5. Every service fixture (`service`, `ui_service`, `new_app`) is bound to an explicit tmp_path database.

Automated guard tests: `tests/test_real_data_safety.py` (8 tests, all passed): env var under `tmp_path`, explicit tmp DB for fixtures, `TicketService()` without arguments stays in tmp, guard refuses the real path (including relative spellings and blank env), real file unchanged after a service workout, default path location and `.gitignore` entry.

Manual evidence: the before/after hash and mtime in section 3.5 are identical (SHA-256 `bd44ab5d1a09514e23f0603de8c383bef62c07a4bf83bc3d519aca21d4bc207e`, mtime 2026-10-24 09:23:22.842753311 UTC, size 12288).

## 12. Observations on documents and code (not defects)

- Design documents still say `app.py` / `ui/` and `streamlit run app.py`; the as-built entry point is `app/main.py` with `python -m streamlit run app/main.py`. `docs/test-strategy.md` still says 65 active ACs (now 76) and `test_ui_smoke.py` references `app.py`. The tests use the as-built paths. (Owner: solution-architect.)
- `README.md` says test evidence is in `docs/test-report.md`; the human-specified location is `reports/test-report.md`; `docs/test-report.md` is a pointer.
- `docs/validation-rules.md` section 3 lists no filter-trimming or case rule; the build-time rules (filters trimmed, status/priority/category filters case-sensitive, creator filter case-insensitive, same-status message "Ticket N is already X.", note supplied to `change_status` replaces the stored note, blank keeps it, several invalid inputs collected into one `ValidationError`) are tested as described in the brief.
- On a Closed ticket, setting status to Closed again returns "Ticket N is Closed and cannot be changed." rather than "already Closed" (read-only check runs first, as IC section 5.2 orders it). Consistent with the IC; noted only because AC-27 says "any status".
- The Employee "no tickets" message is "No tickets found for that name." and the Engineer one is "No tickets yet."; the ACs only say "a no-tickets message", so the tests pin the current wording (`tests/ui_helpers.py`).
- Search matches the ticket ID as decimal text, so searching `#12` matches nothing; this follows ASM-25(b).

## 13. Retest procedure for cycle 1

```
sha256sum data/tickets.db; stat -c 'mtime_ns=%.9Y size=%s' data/tickets.db
.venv/bin/python -m pytest -v
.venv/bin/ruff check .
sha256sum data/tickets.db; stat -c 'mtime_ns=%.9Y size=%s' data/tickets.db
```
Expected after fixes: 692 passed, 0 failed.

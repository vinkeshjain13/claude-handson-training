# Implementation Plan

Status: DESIGN v1 (awaiting approval). Author: solution-architect, 2026-10-24. No application code may be written until the human approves the requirements (including the pending assumptions) and this design (CLAUDE.md sections 5 and 8). The orchestrator delegates each task below to the named agent with a self-contained brief (FR/AC IDs, input docs, allowed files, report format).

Reminder (BL-10, NFR-12): roles are a DEMO selector, not authentication or authorization. No task may add a security claim.

## 1. Work breakdown

| ID | Task | Owner | FR / AC covered | Inputs | Outputs | Definition of done |
|---|---|---|---|---|---|---|
| T00 | Human approval of requirements assumptions and this design (gate G1) | human via orchestrator | all | all docs | decisions on ASM-02..04, 06, 13, 15..24, OQ-04, 05, 16..20 and on Q1..Q3 (ARCH section 10) | written approval or requested changes recorded by the orchestrator |
| T01 | Repository housekeeping: `.gitignore` (`data/`, `__pycache__/`, `.pytest_cache/`, `.ruff_cache/`, `.venv/`), `requirements.txt` (section 5 of ARCH), `ruff.toml` (TS section 8), `.streamlit/config.toml` (localhost, telemetry off; if Q2 approved). Ask the human before installing packages. | orchestrator | NFR-09, NFR-10, NFR-11, AC-58, AC-69 | ARCH sections 3, 5; TS section 8 | the four files; virtual environment created and packages installed only after approval | files exist; `python -c "import streamlit, pytest"` and `ruff --version` succeed; Streamlit version recorded in the report |
| T02 | Contract skeleton: `ticketing/__init__.py`, `ticketing/config.py` (full), `ticketing/models.py` (full), `ticketing/service.py` with the class and every method signature, docstrings, `raise NotImplementedError` | backend-developer | all (shapes only) | IC sections 2..5 | importable package matching the contract names exactly | `python -c "from ticketing.service import TicketService; from ticketing.models import Ticket, DashboardStats, ValidationError"` works; `ruff check ticketing` clean; names, parameters and return annotations equal IC |
| T03 | Data layer: `ticketing/db.py` per DM sections 2 and 9 | backend-developer | FR-04, 05, 06, 08, 13, 16..20, 23, 24, 26; NFR-01, NFR-06, NFR-08; AC-47, 48, 55, 57 | DM | `db.py` | all functions exist with the DM signatures; all SQL static with `?` placeholders; schema creation works on a new file; developer reports a manual smoke run (insert, select, update, count, rollback) with output; Ruff clean |
| T04 | Service layer implementation of S1..S9 | backend-developer | FR-01..03, 05, 07, 09..11, 13, 15, 16, 18..20, 23..26; AC-01..11, 12..31, 33, 36, 37..43, 59, 61..67 | IC, VR, T03 | `ticketing/service.py` | every method follows IC section 5 incl. order of checks (5.2) and error classes; no role parameter; no SQL; all limits/lists from config; developer reports a smoke run; Ruff clean |
| T05 | UI shell and shared helpers plus Employee view: `app.py`, `ui/__init__.py`, `ui/common.py`, `ui/employee_view.py` | frontend-developer | FR-01..03, 05, 06, 07, 21, 25, 26; NFR-03; AC-01..11, 44, 45, 51, 52, 66, 67 | UI, IC, T02 (T04 for live data) | the four files | UI section 3 and 4 satisfied, widget keys as specified; DEMO notice visible; no SQL or `sqlite3` import; user text rendered literally; `streamlit run app.py` starts; Ruff clean |
| T06 | Manager view `ui/manager_view.py` | frontend-developer | FR-16, 18..20, 23, 24; AC-37..43, 59, 65 | UI section 6, IC S8, T02 (T04 for live) | one file | numbers and charts match `DashboardStats`; empty DB shows zeros with no error; Ruff clean |
| T07 | Engineer view `ui/engineer_view.py` | frontend-developer | FR-06..11, 13, 15; AC-12..31, 33, 36, 60..64 | UI section 5, IC S3, S5..S7, S9, T04 | one file | filters, table, details and three update forms behave as specified; closed tickets read-only; service messages displayed; Ruff clean |
| T08 | Test scaffolding and data-layer tests: `pytest.ini`, `tests/conftest.py`, `tests/test_db_layer.py` | qa-engineer | NFR-06, 07, 08; AC-55, 56 | TS sections 2, 3, 6; DM; T02 (write), T03 (run) | files | fixtures per TS section 3; tests run against T03 and pass or produce defect reports |
| T09 | Service-layer tests: `test_service_create.py`, `test_service_read.py`, `test_service_update.py`, `test_service_dashboard.py`, `test_persistence_integrity.py` | qa-engineer | all functional AC listed in TS section 10 | IC, VR, TS; T02 (write), T04 (run) | test files | every mapped AC has at least one test named per TS section 4; suite runs; failures reported as defects to the orchestrator, not "fixed" in production code |
| T10 | Static and UI-smoke tests and manual checklist: `test_code_rules.py`, `test_ui_smoke.py`, `docs/manual-test-checklist.md` | qa-engineer | AC-44, 45, 49..54, 57, 58, 68, 69; UI parts of AC-01, 07, 13, 41, 42, 51, 52, 66, 67 | UI keys, TS sections 5, 6, 10; T05..T07 (run) | files | items for every manual AC with steps and pass criteria; AppTest checks that are not feasible are moved to the checklist with a reason |
| T11 | `README.md` (content spec in section 4) | orchestrator (proposed; Q1) | NFR-12, AC-68; AC-69 | section 4 | `README.md` | contains the demo-role disclosure near the top, run/test/lint commands that were actually executed, no security claim |
| T12 | Integration check (gate G2 = CLAUDE.md checkpoint 4): orchestrator starts the app, confirms files exist, runs `ruff check .` and `python -m pytest`, reviews developer claims against real output | orchestrator | all | T04..T11 | progress summary | files present per ownership table; commands run by the orchestrator; human approves moving to QA sign-off |
| T13 | QA execution and report: run full suite and manual checklist, `ruff check .`; write `docs/test-report.md` and update the Tests/Status columns | qa-engineer | all AC | T12 | `docs/test-report.md`, checklist results | commands and raw output recorded; every active AC has a result; defects listed with evidence |
| T14 | Security review (parallel with T13; reads code only) | security-reviewer | NFR-08, NFR-09, NFR-12, AC-57, 58, 68; FR-21 disclosure | code, docs | `docs/security-review.md` | severity-rated findings; confirms SQL parameterization, no secrets, the demo disclosure; makes no claim that the demo selector is secure |
| T15 | Defect fixing: route each defect to the file owner (backend, frontend, or orchestrator for config files); contract changes go back to the architect | owners | per defect | T13, T14 | fixes | fix noted per defect; no contract change without architect (and, if material, human) approval |
| T16 | Re-verification by QA and security of every fix; update report | qa-engineer, security-reviewer | per defect | T15 | updated reports | retest output recorded before any item is called fixed |
| T17 | Traceability and handover (gate G4 = checkpoint 6): orchestrator completes the "Implementing file(s)" column; QA completes Tests/Status; final gaps/orphans report | orchestrator, qa-engineer | all | T13..T16 | updated `docs/traceability-matrix.md`, handover summary | no active FR/NFR/AC without a test or manual evidence; no orphan code or test |

## 2. Dependency graph and parallel groups

```
T00 (human approval, G1)
  |
  +--> T01 (orchestrator housekeeping) --------------------------------+
  |                                                                    |
  +--> T02 (contract skeleton: config, models, service stubs)          |
          |                                                            |
          +--> T03 (db.py) --> T04 (service impl) ----+                |
          |                                           |                |
          +--> T05 (app shell + Employee) --> T06 (Manager) --> T07 (Engineer; best run after T04)
          |                                           |
          +--> T08/T09 (QA writes tests from contract; run after T03/T04)
                                                      |
                      T05..T07 done --> T10 (QA smoke/static/manual) , T11 (README)
                                                      |
                              T04..T11 done --> T12 (integration, G2: human approval)
                                                      |
                                       T13 (QA run)  ||  T14 (security review)
                                                      |
                                           T15 -> T16 -> (G3: human approval of QA/security results)
                                                      |
                                                    T17 (G4 final handover)
```

Parallel groups (different files, no shared edits):

| Group | Tasks that may run concurrently | Why safe |
|---|---|---|
| A | T01 and T02 | housekeeping files vs `ticketing/` files |
| B | T03 then T04 (backend, sequential) in parallel with T05 -> T06 -> T07 (frontend) and T08/T09 (QA writing tests) | disjoint files; frontend and QA work against the T02 skeleton and the contracts |
| C | T10 and T11 | QA files vs README |
| D | T13 and T14 | QA writes its report and tests; security writes only `docs/security-review.md`; both read code only |

Serial constraints: T03 before T04; T04 before running anything meaningful in T05..T09; T12 after all implementation; T15 after T13/T14.

What the frontend can start on contract only: everything in T05..T07 can be written against the T02 skeleton (names, signatures, `Ticket`, `DashboardStats`, errors, `config` constants) because the contract fixes all shapes. The frontend cannot run end-to-end until T04 lands; until then it checks that `streamlit run app.py` starts and renders the shell. No fake/stub service is built (it would be an extra file and a second source of truth); the real service arrives quickly because T03/T04 are small.

Integration points to verify at T12: (1) `config` names imported by UI exist; (2) `TicketService()` construction from `app.py` with `TICKET_DB_PATH` honoured; (3) error classes caught by `show_error`; (4) `allowed_next_statuses` output matches what the engineer sees; (5) widget keys in `ui-design.md` match the keys used by `test_ui_smoke.py`.

## 3. File ownership (two agents never edit the same file)

| Path | Owner | Notes |
|---|---|---|
| `ticketing/__init__.py`, `config.py`, `models.py`, `db.py`, `service.py` | backend-developer | contract names fixed by IC; UI change requests go through the orchestrator |
| `app.py`, `ui/__init__.py`, `ui/common.py`, `ui/employee_view.py`, `ui/engineer_view.py`, `ui/manager_view.py` | frontend-developer | no SQL |
| `tests/**`, `pytest.ini` | qa-engineer | never production code |
| `docs/test-report.md`, `docs/manual-test-checklist.md` | qa-engineer | evidence |
| `docs/security-review.md` | security-reviewer | only this file |
| `docs/architecture.md`, `data-model.md`, `interface-contracts.md`, `validation-rules.md`, `ui-design.md`, `test-strategy.md`, `implementation-plan.md`; "Design element" column of `docs/traceability-matrix.md` | solution-architect | contract changes |
| `docs/requirements-analysis.md`, `docs/client-requirements.md`; columns 1-3 of the matrix | requirements-analyst | |
| `requirements.txt`, `ruff.toml`, `.gitignore`, `.streamlit/config.toml`, `README.md`, `CLAUDE.md`, `.claude/**` | orchestrator | `README.md` is a proposal (Q1); `requirements.txt` only after approval; packages installed only after the human agrees |
| Matrix column "Implementing file(s)" | orchestrator (from developers' reports, verified against files) | the developers write no docs; proposed to avoid a second writer |
| Matrix columns "Test(s)" and "Status" | qa-engineer | |
| `data/` | runtime only, git-ignored | never committed, never edited by hand |

Split files by owner on purpose: `pytest.ini` (qa-engineer) and `ruff.toml` (orchestrator) are separate files rather than one `pyproject.toml`, so no file has two owners.

Flag for the orchestrator/human (Q1): the architect and analyst may only write Markdown under `docs/`, so `README.md` (repository root) needs an owner. Recommendation: orchestrator writes it from the spec in section 4 because it is housekeeping and contains no design decisions. Alternative if the human prefers strict separation: add a `docs/user-guide.md` written by the solution-architect on request and keep `README.md` as a three-line pointer.

## 4. README content specification (NFR-12, AC-68)

1. Title and one-sentence purpose.
2. Section "DEMO ONLY: roles are not security" (first section): the Employee/Support Engineer/Manager selector is a demonstration switch, not authentication or authorization; anyone can select any role; no security, privacy or access-control claim; do not enter confidential information; creator names are free text and "My tickets" is a convenience filter.
3. Requirements: Python 3.10+, packages from `requirements.txt` (installation steps for a virtual environment).
4. Run: `streamlit run app.py` (localhost only), where the database lives (`data/tickets.db`, `TICKET_DB_PATH` override), how to reset (delete the file; also required after changing the category/status/priority lists).
5. Test and lint commands: `python -m pytest -v`, `ruff check .`.
6. Project layout (copy of ARCH section 6 table, short).
7. Known limitations: single local file, no backup, no authentication, no ticket deletion, no history.
8. Links to the docs in `docs/`.

## 5. Recommended order and approval gates

| Order | Step | Gate (CLAUDE.md section 8) |
|---|---|---|
| 1 | Agent setup verified | checkpoint 1 (done before this design) |
| 2 | Requirements and assumptions approved | checkpoint 2 |
| 3 | This design, contracts and plan approved (T00) | checkpoint 3 (G1) |
| 4 | T01, T02 in parallel | ask before installing packages |
| 5 | T03 -> T04 || T05 -> T06 -> T07 || T08 -> T09 | |
| 6 | T10, T11 | |
| 7 | T12 integration | checkpoint 4 (G2): human approves before QA sign-off |
| 8 | T13 || T14, then T15, T16 | checkpoint 5 (G3): human approves QA and security results; also before any scope change |
| 9 | T17 handover | checkpoint 6 (G4) |

## 6. Risks specific to the plan

| Risk | Mitigation |
|---|---|
| Streamlit API differences by version (`use_container_width` vs newer width options, `AppTest` behaviour) | Orchestrator records the installed version in T01; frontend uses the documented API for that version; QA falls back to the manual checklist for flaky UI tests |
| Pending assumptions change after coding starts | Rules are in `config.py` (ARCH section 9); contract changes go back to the architect |
| UI re-implements rules (for example transition logic) | Contract checklist in IC section 9; `allowed_next_statuses` exists to prevent it; security-reviewer and QA static scan check it |
| README has no clear owner | Q1 decision before T11 |
| Test report evidence missing | QA task T13 definition of done requires raw command output |
| Scope creep (search, pagination, history) | NFR-04; UI section 9 and ARCH section 11 list exclusions; changes need human approval |

## 7. Contract change procedure

Any change to `docs/interface-contracts.md`, `docs/data-model.md`, `docs/validation-rules.md` or widget keys in `docs/ui-design.md` is requested through the orchestrator, edited only by the solution-architect, announced to the affected developers and QA, and approved by the human when material (CLAUDE.md section 5).

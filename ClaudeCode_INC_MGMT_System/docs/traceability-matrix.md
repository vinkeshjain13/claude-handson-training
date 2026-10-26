# Requirements Traceability Matrix

Status: BASELINE v3 (MVP scope approved by the human; v3 adds the human-directed FR-27 listing search, BL-11, and the launch-command decision BL-12; remaining assumptions in `docs/requirements-analysis.md` section 7 still pending approval). "Design element" column filled by solution-architect (design v1, awaiting approval; see legend in section 7); rows added in v3 (US-22) are TBD until the architect fills them.
Owner of columns 1-3 (user story, FR/NFR, AC): requirements-analyst. Later columns are owned by later agents and stay "TBD" until then.
Definitions: `docs/requirements-analysis.md`. Client text: `docs/client-requirements.md`.
RETIRED IDs keep their number and have no mapping; they are listed in section 5 and must not be reused.

## 1. User story -> FR/NFR -> AC

| User story | FR / NFR | Acceptance criteria | Design element | Implementing file(s) | Test(s) | Status |
|---|---|---|---|---|---|---|
| US-01 Employee raises ticket | FR-01, FR-02, FR-04, FR-05, FR-13 | AC-01, AC-02, AC-03, AC-04, AC-05, AC-06, AC-09, AC-10, AC-11, AC-33 | service.create_ticket (IC S1, 5.3); db.insert_ticket; tickets table (DM s2-3, s5, s6); ui/employee_view "Raise a ticket" form; VR s2 | TBD | `test_service_create.py` (AC-01..06, 09..11, 33), `test_ui_smoke.py` (AC-01, 03..06 UI), `test_cycle1_regressions.py` (AC-03, 05, 06 NUL/surrogate/unicode text, UI form) | QA cycle 0: PASS; DEF-03 (Low) open on FR-02 edge (NUL text). QA cycle 1: DEF-03 fixed and retested, PASS (NUL now rejected with a field message; see doc drift in reports/test-report.md Cycle 1 section C7) |
| US-02 Employee chooses priority | FR-03 | AC-07, AC-08 | config.PRIORITIES, DEFAULT_PRIORITY; create_ticket priority validation (VR s2); employee form priority selectbox (UI s4) | TBD | `test_service_create.py` (AC-07, 08), `test_ui_smoke.py` (AC-07) | QA cycle 0: PASS |
| US-03 Employee sees own tickets and status | FR-06, FR-07, FR-26 | AC-12, AC-13, AC-14, AC-15, AC-66 | service.list_my_tickets, get_ticket (IC S2, S4); db.select_tickets, fetch_ticket; ui/employee_view "My tickets"; ui/common.ticket_rows, render_ticket_details | TBD | `test_service_read.py` (AC-12..15, 66), `test_ui_smoke.py` (AC-12..14, 66), `test_cycle1_regressions.py` (AC-15, 66) | QA cycle 0: AC-15 FAIL (DEF-01); others PASS. QA cycle 1: AC-15 PASS (DEF-01 fixed and retested) |
| US-04 Employee gets clear error messages | FR-02, NFR-03 | AC-03, AC-04, AC-05, AC-51, AC-52, AC-67 | ValidationError and message policy (IC s4); VR s2, s4; ui/common.show_error; non-clearing form, required marks (UI s4, s8) | TBD | `test_service_create.py` (AC-03..05, 67), `test_ui_smoke.py` (AC-03..05, 51, 52, 67) | QA cycle 0: PASS; manual M-08, M-09 pending |
| US-05 Engineer views and filters tickets | FR-06, FR-07, FR-08 | AC-12, AC-13, AC-14, AC-15, AC-16, AC-17, AC-18, AC-19, AC-20, AC-60 | service.list_tickets, get_ticket (IC S3, S2); db.select_tickets (static WHERE pattern); ui/engineer_view filters, table, details (UI s5) | TBD | `test_service_read.py` (AC-12..20, 60), `test_ui_smoke.py`, `test_ui_search.py`, `test_cycle1_regressions.py` (AC-15, 19) | QA cycle 0: AC-15 FAIL (DEF-01); DEF-02 (Low) on FR-08 edge; others PASS. QA cycle 1: AC-15 PASS (DEF-01), DEF-02 fixed and retested, PASS |
| US-06 Engineer updates status | FR-09, FR-10, FR-13 | AC-21, AC-22, AC-23, AC-24, AC-25, AC-26, AC-27, AC-28, AC-29, AC-33, AC-61, AC-62, AC-63, AC-64 | service.change_status, allowed_next_statuses (IC S5, S9, 5.2, s6); config.TRANSITIONS, READ_ONLY_STATUSES; db.update_ticket; ui/engineer_view status form | TBD | `test_service_update.py` (AC-21..29, 33, 61..64), `test_ui_engineer.py`, `test_cycle1_regressions.py` (AC-29) | QA cycle 0: AC-29 FAIL (DEF-01); others PASS. QA cycle 1: AC-29 PASS (DEF-01 fixed and retested) |
| US-07 Engineer changes priority | FR-11 | AC-30, AC-31, AC-62 | service.change_priority (IC S6); db.update_ticket; ui/engineer_view priority form | TBD | `test_service_update.py` (AC-30, 31, 62), `test_ui_engineer.py`, `test_cycle1_regressions.py` (huge ticket ID) | QA cycle 0: PASS. QA cycle 1: PASS |
| US-08 (RETIRED) | FR-12 retired | AC-32 retired | - | - | - | Retired |
| US-09 Engineer adds resolution note | FR-15 | AC-22, AC-36, AC-62, AC-64 | service.set_resolution_note (IC S7), change_status note parameter; config.RESOLVED_REQUIRES_NOTE, LIMITS; ui/engineer_view status form | TBD | `test_service_update.py` (AC-22, 36, 62, 64), `test_ui_engineer.py`, `test_cycle1_regressions.py` (AC-36 NUL/unicode note, huge ticket ID) | QA cycle 0: PASS. QA cycle 1: PASS |
| US-10 (RETIRED) | FR-22 retired | AC-46 retired | - | - | - | Retired |
| US-11 Manager sees total tickets | FR-16 | AC-37, AC-40 | service.get_dashboard_stats (IC S8); db.count_all; ui/manager_view metrics | TBD | `test_service_dashboard.py` (AC-37, 40), `test_ui_smoke.py` | QA cycle 0: PASS |
| US-12 Manager sees status counts | FR-18, FR-23 | AC-39, AC-40, AC-59 | DashboardStats.by_status (IC s3); db.count_by("status"); ui/manager_view status metrics | TBD | `test_service_dashboard.py` (AC-39, 40, 59), `test_ui_smoke.py` | QA cycle 0: PASS |
| US-13 Manager sees priority breakdown | FR-19 | AC-41 | DashboardStats.by_priority zero-filled (IC s3, 5.4); ui/manager_view priority metrics and chart | TBD | `test_service_dashboard.py` (AC-41), `test_ui_smoke.py` | QA cycle 0: PASS |
| US-14 Manager dashboard current and empty-safe | FR-20 | AC-42, AC-43 | zero-filled stats on empty DB (IC 5.4); stats read on every rerun; ui/manager_view Refresh (UI s6) | TBD | `test_service_dashboard.py` (AC-42, 43), `test_ui_smoke.py`, `test_ui_engineer.py` | QA cycle 0: PASS |
| US-15 Any user picks a role view | FR-21 | AC-44, AC-45 | app.py sidebar radio and ROLE_VIEWS; DEMO_NOTICE rendered before role content (UI s1, s2); IC s1 | TBD | `test_ui_smoke.py` (AC-44, 45), `test_code_rules.py` (AC-45) | QA cycle 0: PASS; manual M-06, M-07 (visual) pending |
| US-16 Data persists | NFR-01 | AC-47, AC-48 | db.init_schema, per-operation connections, data/tickets.db (ARCH s4; DM s8) | TBD | `test_persistence_integrity.py` (AC-47, 48), `test_db_layer.py`, `test_ui_smoke.py` | QA cycle 0: PASS; manual M-05 (real restart) pending |
| US-17 Works in a browser | NFR-02 | AC-49 | Streamlit app run with `streamlit run app.py` on localhost (ARCH s3); UI s10 | TBD | Manual only: `docs/manual-test-checklist.md` M-01 (AC-49) | Manual - not yet executed |
| US-18 Simple and easy to use | NFR-03, NFR-04 | AC-50, AC-51, AC-52, AC-53 | UI s8 (labels, required marks, messages, retained input); ARCH s1, s11 and UI s9 (scope exclusions) | TBD | `test_ui_smoke.py` (AC-51, 52); manual M-02 (AC-50), M-03 (AC-53), M-08, M-09 | AC-51, 52 PASS (cycle 0); AC-50, 53 manual - not yet executed |
| US-19 Manager sees category breakdown | FR-24 | AC-42, AC-65 | DashboardStats.by_category zero-filled; db.count_by("category"); ui/manager_view category metrics and chart | TBD | `test_service_dashboard.py` (AC-42, 65), `test_ui_smoke.py` | QA cycle 0: PASS |
| US-20 Employee chooses category | FR-25 | AC-67 | config.CATEGORIES, DEFAULT_CATEGORY; create_ticket category validation; tickets.category CHECK (DM s2); employee form category selectbox | TBD | `test_service_create.py` (AC-67), `test_ui_smoke.py` (AC-67) | QA cycle 0: PASS |
| US-21 Demo roles clearly disclosed | FR-21, NFR-12 | AC-45, AC-68 | ui/common.DEMO_NOTICE shown by app.py on every screen; ARCH s0; IC s1 (service has no roles); README content spec (IP s4) | TBD | `test_code_rules.py` (AC-45, 68), `test_ui_smoke.py` (AC-45) | QA cycle 0: PASS; manual M-12 pending |
| US-22 Engineer or employee searches the ticket list | FR-27 (with FR-08, FR-26) | AC-71, AC-72, AC-73, AC-74, AC-75, AC-76, AC-77, AC-78, AC-79, AC-80, AC-81 | TBD | TBD | `test_ui_search.py` (AC-71..81), `test_code_rules.py` (AC-81) | QA cycle 0: PASS |
| (no user story; cross-cutting) | NFR-05 | AC-54 | no index and ORDER BY id DESC (DM s7, ARCH D7, D9); timing test (TS s6) | TBD | `test_persistence_integrity.py` (AC-54 service timing) | QA cycle 0: PASS (service); manual M-04 (UI timing) pending |
| (no user story; cross-cutting) | NFR-06 | AC-55 | db.session transaction, validate-before-write, StorageError (DM s9; IC s4, 5.2; VR s6) | TBD | `test_persistence_integrity.py` (AC-55), `test_db_layer.py`, `test_ui_engineer.py` | QA cycle 0: PASS |
| (no user story; project rule) | NFR-07 | AC-56 | TicketService(db_path, clock) injection; tmp_path fixtures and env guard (ARCH s4; TS s3) | TBD | `test_real_data_safety.py`, `test_code_rules.py` (AC-56), `conftest.py` | QA cycle 0: PASS |
| (no user story; project rule) | NFR-08 | AC-57 | static parameterized SQL, import rules (ARCH s2, s7; DM s9); Ruff S608; static scan (TS s6) | TBD | `test_code_rules.py` (AC-57), `test_db_layer.py`, `test_ui_search.py` (AC-77) | QA cycle 0: PASS; manual M-10 (review) pending |
| (no user story; project rule) | NFR-09 | AC-58 | local-only launch, telemetry off, no network, no secrets, git-ignored data/ (ARCH s3, s7) | TBD | `test_code_rules.py` (AC-58), `test_ui_smoke.py` (AC-58) | QA cycle 0: PASS; manual M-11 pending |
| (no user story; approved tech baseline) | NFR-10 | AC-69 | dependency list and Python 3.10+ (ARCH s5) | TBD | `test_code_rules.py` (AC-69) | QA cycle 0: PASS (Python 3.14.4 only); manual M-13 pending |
| (no user story; approved tech baseline) | NFR-11 | AC-70 | ruff.toml specification and `ruff check .` command (TS s8) | TBD | `test_code_rules.py` (AC-70), `ruff check .` | QA cycle 0: PASS |

## 2. Requirement -> AC coverage (FR/NFR without AC check)

| Requirement | Priority | Covered by | User story | Gap? |
|---|---|---|---|---|
| FR-01 | Must | AC-01, AC-02 | US-01 | No |
| FR-02 | Must | AC-03, AC-04, AC-05, AC-06, AC-67 | US-01, US-04 | No |
| FR-03 | Must | AC-07, AC-08 | US-02 | No |
| FR-04 | Must | AC-09, AC-10 | US-01 | No |
| FR-05 | Must | AC-11 | US-01 | No |
| FR-06 | Must | AC-12, AC-13 | US-03, US-05 | No |
| FR-07 | Must | AC-02, AC-14, AC-15, AC-66 | US-03, US-05 | No |
| FR-08 | Should | AC-16, AC-17, AC-18, AC-19, AC-20, AC-60, AC-75 | US-05, US-22 | No |
| FR-09 | Must | AC-21, AC-22, AC-28, AC-29, AC-61 | US-06 | No |
| FR-10 | Must | AC-21 to AC-27, AC-61, AC-62, AC-63, AC-64 | US-06 | No |
| FR-11 | Must | AC-30, AC-31, AC-62 | US-07 | No |
| FR-12 | RETIRED | - | US-08 retired | n/a |
| FR-13 | Must | AC-21, AC-33 | US-01, US-06 | No |
| FR-14 | RETIRED | - | - | n/a |
| FR-15 | Must | AC-22, AC-36, AC-62, AC-64 | US-09 | No |
| FR-16 | Must | AC-37, AC-40 | US-11 | No |
| FR-17 | RETIRED | - | - | n/a |
| FR-18 | Must | AC-39, AC-40 | US-12 | No |
| FR-19 | Must | AC-41 | US-13 | No |
| FR-20 | Must | AC-42, AC-43 | US-14 | No |
| FR-21 | Must | AC-44, AC-45 | US-15, US-21 | No |
| FR-22 | RETIRED | - | US-10 retired | n/a |
| FR-23 | Must | AC-40, AC-59 | US-12 | No |
| FR-24 | Must | AC-42, AC-65 | US-19 | No |
| FR-25 | Must | AC-67 | US-20 | No |
| FR-26 | Must | AC-66, AC-79, AC-80 | US-03, US-22 | No |
| FR-27 | Should | AC-71, AC-72, AC-73, AC-74, AC-75, AC-76, AC-77, AC-78, AC-79, AC-80, AC-81 | US-22 | No |
| NFR-01 | Must | AC-47, AC-48 | US-16 | No |
| NFR-02 | Must | AC-49 | US-17 | No |
| NFR-03 | Must | AC-50, AC-51, AC-52 | US-04, US-18 | No |
| NFR-04 | Should | AC-53 | US-18 | No |
| NFR-05 | Should | AC-54 | none | No AC gap; no user story |
| NFR-06 | Must | AC-55 | none | No AC gap; no user story |
| NFR-07 | Should | AC-56 | none | No AC gap; no user story |
| NFR-08 | Should | AC-57, AC-77 | none | No AC gap; no user story |
| NFR-09 | Must | AC-58 | none | No AC gap; no user story |
| NFR-10 | Must | AC-69 | none | No AC gap; no user story |
| NFR-11 | Should | AC-70 | none | No AC gap; no user story |
| NFR-12 | Must | AC-45, AC-68 | US-21 | No |

## 3. AC -> requirement check (AC without FR/NFR)

Every active AC links to at least one FR/NFR (see "Verifies" column in section 10 of `docs/requirements-analysis.md`). Multi-linked ACs: AC-02 (FR-01, FR-07), AC-21 (FR-09, FR-10, FR-13), AC-22 (FR-09, FR-10, FR-15), AC-40 (FR-16, FR-18, FR-23), AC-42 (FR-20, FR-24), AC-45 (FR-21, NFR-12), AC-61 (FR-09, FR-10), AC-62 (FR-10, FR-11, FR-15), AC-64 (FR-10, FR-15), AC-66 (FR-26, FR-07), AC-67 (FR-25, FR-02), AC-75 (FR-27, FR-08), AC-77 (FR-27, NFR-08), AC-79 (FR-27, FR-26), AC-80 (FR-27, FR-26).

New ACs in v3 (all verify FR-27, story US-22): AC-71 (title substring, order kept), AC-72 (case-insensitive), AC-73 (description and creator matched; other fields not searched), AC-74 (ID match), AC-75 (AND with filters), AC-76 (empty or whitespace-only search), AC-77 (special and SQL-looking text matched literally), AC-78 (no-match message), AC-79 (Employee search limited to own tickets), AC-80 (Employee messages), AC-81 (no new backend capability, data unchanged).

## 4. Gaps and orphans report

| Check | Result |
|---|---|
| Active FR without AC | None (23 active FRs) |
| Active NFR without AC | None (12 NFRs) |
| Active AC without FR/NFR | None (76 active ACs) |
| Active user story without FR/NFR | None (20 active stories) |
| ACs pointing at a retired FR | None (retired ACs are listed in section 5 and are empty) |
| Active FR/NFR without user story | NFR-05, NFR-06, NFR-07, NFR-08, NFR-09, NFR-10, NFR-11 (cross-cutting or project/approved baseline rules; informational, not defects) |
| ACs verified by manual or document evidence rather than pytest | AC-49, AC-50, AC-53, AC-54 (timing may be scripted), AC-57, AC-58, AC-68, AC-69, AC-70 (Ruff run), UI parts of AC-44, AC-45, AC-51, AC-52. AC-81 is a static check or inspection with recorded evidence. QA should record evidence for each. |
| ACs verified at service level only | AC-15 and AC-29 (unknown ticket ID): the UI offers only existing ticket IDs, so the case cannot be produced from the UI. |
| Requirements from `CLAUDE.md`, not client | NFR-07, NFR-08, NFR-09 (and edge-case wording of FR-10); labelled [P] |
| Requirements from the approved baseline rather than client text | FR-21, FR-23 to FR-26, NFR-10, NFR-11, NFR-12; FR-27 (human-directed addition BL-11 at implementation start); launch command in NFR-10 (BL-12) |
| Client wording changed by the baseline | "pending issues" (client) is replaced by four status counts (BL-05); no pending figure (ASM-22, confirm) |
| ACs whose wording depends on unapproved assumptions | AC-05 (ASM-03); AC-07/08/30/31 (ASM-04, ASM-24); AC-21 to AC-29, AC-61 to AC-64 (ASM-06, ASM-20, ASM-21); AC-36, AC-64 (ASM-21); AC-66 (ASM-23); AC-67 (ASM-19); AC-10 (ASM-13); AC-44 (ASM-18); AC-49 (ASM-12); AC-50 (ASM-17); AC-54 (ASM-11); AC-71 to AC-80 (ASM-25) |
| ASM-20 softened (v3) | "Only engineers set Closed" is UI placement (the Closed control is shown only in the Support Engineer view); the service has no roles and cannot enforce it; not access control. Affects AC-61, AC-62, AC-63 wording only as a note; no AC claims enforcement. |
| Items that need human approval before design | Blocking: OQ-04, OQ-05, OQ-16, OQ-17. Others: OQ-09 to OQ-13, OQ-18 to OQ-21 |
| Design coverage (architect, design v1) | Every active FR/NFR/AC has a design element (section 1 column "Design element"; `docs/architecture.md` section 11). AC-15 and AC-29 are verifiable only at service level because the UI offers existing IDs only. Design elements without a direct requirement: `StorageError`/logging (supports NFR-06), `allowed_next_statuses` (supports FR-09/FR-10), `clock` injection (supports FR-13, NFR-07), `.streamlit/config.toml` (supports NFR-09, needs approval). |
| Design coverage gap (v3, for the architect) | FR-27, US-22 and AC-71 to AC-81 have no design element yet (design element "TBD"). The v1 statement above predates FR-27. |
| Design elements predating BL-12 (for the architect) | Design element cells of US-15, US-17 and US-21 and the design documents (`architecture.md`, `ui-design.md`, `interface-contracts.md`, `test-strategy.md`, `implementation-plan.md`) refer to `app.py` and `streamlit run app.py`. The human-specified entry point is `app/main.py` with `python -m streamlit run app/main.py` (BL-12; NFR-10, AC-69). These cells were left unchanged by the requirements-analyst because the architect owns that column. |

## 5. Retired IDs (no mapping, do not reuse)

| Type | IDs | Reason |
|---|---|---|
| FR | FR-12 | Title/description editing not in approved scope |
| FR | FR-14 | Status history dropped (ASM-09) |
| FR | FR-17 | "Pending" figure replaced by four status counts (BL-05) |
| FR | FR-22 | Assignee not in approved scope |
| User story | US-08, US-10 | Linked only to retired FR-12, FR-22 |
| AC | AC-32, AC-34, AC-35, AC-38, AC-46 | Linked only to retired FRs |
| Risk | RISK-03 | Pending definition no longer applies |
| Assumption | ASM-01, ASM-05 | Superseded by the approved baseline |

## 6. Totals

| Item | Active | Retired | Total IDs |
|---|---|---|---|
| Functional requirements | 23 | 4 | 27 |
| Non-functional requirements | 12 | 0 | 12 |
| User stories | 20 | 2 | 22 |
| Acceptance criteria | 76 | 5 | 81 |

## 7. Legend for the "Design element" column (solution-architect)

| Abbreviation | Document |
|---|---|
| ARCH s# | `docs/architecture.md` section # (D# = key decision) |
| DM s# | `docs/data-model.md` section # |
| IC s#, S# | `docs/interface-contracts.md` section #, service operation S1..S9 |
| VR s# | `docs/validation-rules.md` section # |
| UI s# | `docs/ui-design.md` section # |
| TS s# | `docs/test-strategy.md` section # |
| IP s# | `docs/implementation-plan.md` section # |
| module.function | planned code element: `ticketing/service.py`, `ticketing/db.py`, `ticketing/config.py`, `ui/*` (see ARCH s6 for paths) |

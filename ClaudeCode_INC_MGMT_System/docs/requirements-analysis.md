# Requirements Analysis - IT Support Ticket Management System

Status: BASELINE v3 (v2 plus the human-directed changes BL-11 and BL-12 made at implementation start; see section 11). The MVP scope in section 0.2 is APPROVED by the human. Items tagged [A] and listed in section 7 are still ASSUMPTIONS that need human approval.
Author: requirements-analyst. Date: 2026-10-24.
Input: `docs/client-requirements.md` (verbatim client text, unchanged) plus the human-approved MVP scope (section 0.2).
Scope: local classroom MVP. No design, schema or code decisions are made here.

## 0. How to read this document

| Tag | Meaning |
|---|---|
| **[E]** | Explicitly stated by the client (quoted phrase given). |
| **[B]** | Part of the human-approved MVP baseline (section 0.2). Final unless the human changes it. |
| **[I]** | Inferred by the analyst as a necessary consequence of client wording or the baseline. |
| **[A]** | Assumption by the analyst. REQUIRES HUMAN APPROVAL (section 7). |
| **[P]** | Project-level rule from `CLAUDE.md`. Not stated by the client. |

Priority terms: Must = needed for the approved scope; Should = strongly implied or improves testability.

Retired IDs: an ID marked RETIRED is kept in the tables so numbering stays stable. It has no requirement and no tests. Do not reuse retired IDs.

### 0.1 Important statement on security and access control

The client never mentioned login, authentication, authorization, encryption, audit trail, privacy, confidentiality or compliance. Nothing in this document requires or promises any of these.

The Employee / Support Engineer / Manager views are chosen with a clearly labelled **DEMO role selector**. It is NOT real authentication and NOT authorization. Anyone who can open the application can pick any role and do anything that role's screens offer. This must be disclosed in the documentation (NFR-12) and visibly in the UI (FR-21). No security guarantee of any kind is claimed. Input validation and parameterized SQL (NFR-08) are code-quality rules from `CLAUDE.md`, not security guarantees.

### 0.2 Approved MVP baseline (human decision, supersedes earlier draft defaults)

| ID | Approved decision |
|---|---|
| BL-01 | Python 3.10+; Streamlit UI; SQLite via built-in `sqlite3`; pytest for tests; Ruff for linting. No cloud, external APIs or deployment. |
| BL-02 | Three views: Employee, Support Engineer, Manager. |
| BL-03 | Employee: create tickets and view ticket status. |
| BL-04 | Support Engineer: inspect tickets, change priority and status, add resolution notes. |
| BL-05 | Manager dashboard: total, open, in-progress, resolved and closed counts, plus priority breakdown and category breakdown. |
| BL-06 | Ticket fields: ID, title, description, category, priority, status, creator, created_at, updated_at, resolution_note. |
| BL-07 | Status values: Open, In Progress, Resolved, Closed. |
| BL-08 | Priority values: Low, Medium, High, Critical. |
| BL-09 | Tickets persist in a local SQLite database. |
| BL-10 | Roles are a DEMO role selector, not authentication or authorization; disclosed in documentation and visibly in the UI; no security guarantee claimed. |
| BL-11 | Listing search is added to the approved scope (FR-27): a case-insensitive text search over ticket ID, title, description and creator on the Support Engineer ticket list and the Employee "My tickets" list. Human-directed addition at implementation start. |
| BL-12 | The application entry point is `app/main.py` and the launch command is `python -m streamlit run app/main.py`. Human-specified at implementation start. |

## 1. Client statement breakdown

| Ref | Client phrase | What it gives us |
|---|---|---|
| P1 | "a simple IT Support Ticket Management System" | Small scope |
| P2 | "Employees should be able to raise support tickets with details of their issues" | Ticket creation |
| P3 | "assign priorities" | Tickets carry a priority |
| P4 | "track progress" | Tickets carry a status that can be followed |
| P5 | "Support engineers should be able to view and update tickets" | Engineers inspect and update |
| P6 | "managers should see a dashboard showing total tickets, pending issues, resolved tickets, and ticket priorities" | Dashboard. The approved baseline (BL-05) shows the four status counts instead of a combined "pending" figure, and adds a category breakdown. |
| P7 | "easy to use" | Usability expectation |
| P8 | "store information permanently" | Data survives restarts |
| P9 | "work from a web browser" | Browser-based access (Streamlit, local) |

## 2. Functional requirements

"Depends on" lists assumptions (section 7) that must be approved for the requirement to be final. A dash means fully covered by the approved baseline.

| ID | Requirement | Priority | Basis | Type | Depends on |
|---|---|---|---|---|---|
| FR-01 | The system shall let an Employee create a support ticket by submitting creator name, title, description, category and priority. | Must | P2; BL-03, BL-06 | E / B | ASM-02, ASM-03 |
| FR-02 | The system shall validate ticket input: creator name, title and description must be non-empty after trimming surrounding whitespace; fields must not exceed their maximum lengths; category and priority must come from their fixed lists. Invalid input is rejected with a message naming the field and no ticket is created. Special characters (quotes, semicolons, angle brackets, unicode, line breaks in the description) are accepted and stored/displayed literally. | Must | P2; limits are analyst choices | I / A | ASM-03, ASM-16, ASM-19 |
| FR-03 | The system shall let the user choose a priority from the fixed list Low, Medium, High, Critical when raising a ticket (default Medium). | Must | P3; BL-08 | E / B | ASM-04 |
| FR-04 | The system shall give each ticket a unique ID that is never reused and record its created_at date/time. | Must | P4; BL-06 | I / B | ASM-15 |
| FR-05 | A newly created ticket shall have status "Open". | Must | P4; BL-07 | I / B | - |
| FR-06 | The system shall show a ticket list with at least ID, title, creator, category, priority, status and created_at, newest first. | Must | P5; BL-04 | E / I | - |
| FR-07 | The system shall show the full details of one ticket: ID, title, description, category, priority, status, creator, created_at, updated_at and resolution_note (shown as empty when none). | Must | P5; BL-04, BL-06 | E / B | - |
| FR-08 | The Support Engineer view shall let the user filter the ticket list by status, priority, category and creator name (filters combine with AND). | Should | P5; supports "inspect tickets" | I | - |
| FR-09 | A Support Engineer shall be able to change a ticket's status to one of Open, In Progress, Resolved, Closed, subject to FR-10. | Must | P5; BL-04, BL-07 | E / B | ASM-20 |
| FR-10 | The system shall enforce the status workflow in section 5.2: only allowed transitions are accepted; any other change (including to the same status, to an unknown status, or from Closed) is rejected with a message and leaves the ticket unchanged. Setting Resolved requires a non-empty resolution note (FR-15). | Must | P4; `CLAUDE.md` edge case "invalid status transitions" | I / P / A | ASM-06, ASM-20, ASM-21 |
| FR-11 | A Support Engineer shall be able to change a ticket's priority to a value from the fixed list. A change to the same value, to an unlisted value, or on a Closed ticket is rejected and leaves the ticket unchanged. | Must | P3, P5; BL-04 | E / B | ASM-20 |
| FR-12 | RETIRED (superseded). Edit title/description was a Could item and is not in the approved scope (BL-04). | - | - | - | - |
| FR-13 | The system shall maintain updated_at: equal to created_at on creation, changed to the current time on every successful update (status, priority, resolution note), unchanged on a rejected update. | Must | P4; BL-06 | I / B | ASM-15 |
| FR-14 | RETIRED (out of scope). Status history was a Should item and is dropped from the MVP (ASM-09, OQ-13). | - | - | - | - |
| FR-15 | A Support Engineer shall be able to add or replace a ticket's resolution note (1-1000 characters after trimming), shown in ticket details. Notes cannot be changed on a Closed ticket. (Changed: was "progress note", Could.) | Must | BL-04 "add resolution notes"; BL-06 | B / A | ASM-03, ASM-21 |
| FR-16 | The dashboard shall show the total number of tickets. | Must | P6; BL-05 | E / B | - |
| FR-17 | RETIRED (superseded). The combined "pending" figure is replaced by the four status counts (FR-18, FR-23). See ASM-22. | - | - | - | - |
| FR-18 | The dashboard shall show the number of Resolved tickets. | Must | P6; BL-05 | E / B | - |
| FR-19 | The dashboard shall show the number of tickets per priority (Low, Medium, High, Critical), including levels with zero tickets. | Must | P6; BL-05 | E / B | ASM-10 |
| FR-20 | The dashboard shall work when there are no tickets (every figure 0, no error) and shall reflect current stored data each time it is loaded or refreshed. | Must | P6, P8; BL-05 | I / B | ASM-10 |
| FR-21 | The application shall offer a role selector (Employee, Support Engineer, Manager) that shows the screens for that role (section 5.1) and shall display, on every screen, a visible notice that the selector is a DEMO and not authentication or access control. | Must | BL-02, BL-10 | B | ASM-18 |
| FR-22 | RETIRED (out of scope). Assignee was a Could item; assignment is not in the approved scope. | - | - | - | - |
| FR-23 | The dashboard shall show the number of Open, In Progress and Closed tickets. | Must | BL-05 | B | - |
| FR-24 | The dashboard shall show the number of tickets per category, including categories with zero tickets. | Must | BL-05 | B | ASM-19, ASM-10 |
| FR-25 | The system shall let the user choose a category from a fixed list when raising a ticket. Suggested list: Hardware, Software, Network, Account Access, Other (default Other). Category cannot be changed after creation. | Must | BL-06 (category field) | B / A | ASM-19 |
| FR-26 | The Employee view shall show a "My tickets" list: after the employee enters their name, the list shows only tickets whose creator matches (case-insensitive, exact, after trimming), with status and details per FR-06/FR-07. This is a convenience, not privacy (anyone can type any name). | Must | BL-03 "view ticket status" | B / A | ASM-02, ASM-23 |
| FR-27 | The Support Engineer ticket list and the Employee "My tickets" list shall each provide a text search. The search is case-insensitive and matches a ticket when the search text appears anywhere in the ticket's ID, title, description or creator. It combines (AND) with the filters already applied to that list: in the Support Engineer view the FR-08 filters (status, priority, category, creator); in the Employee view the own-tickets name match of FR-26 (so an employee can only find their own tickets). An empty search (or one containing only whitespace, ASM-25) applies no search. Special characters (for example `%`, `_`, quotes, semicolons, backslashes, angle brackets and SQL-looking text) are matched literally and have no wildcard or command meaning. When nothing matches, the existing "no matching tickets" message is shown. The search is performed on the tickets already returned by the service; it adds no new backend capability. | Should | BL-11 (human-directed addition at implementation start) | B / A | ASM-25 |

Counts: 27 FR IDs = 23 active (Must 21, Should 2) + 4 RETIRED (FR-12, FR-14, FR-17, FR-22).

## 3. Non-functional requirements

| ID | Requirement | Priority | Basis |
|---|---|---|---|
| NFR-01 | Persistence: all tickets and their fields (including category, resolution note, status, priority, timestamps) shall survive stopping and restarting the application and closing/reopening a browser session, using the local SQLite file. No backup/retention is promised (ASM-14). | Must | P8; BL-09 |
| NFR-02 | Browser access: all user functions shall be usable from a standard desktop web browser (latest Chrome, Firefox, Edge) on a local address, with no client software installed. | Must | P9; browser list is ASM-12 |
| NFR-03 | Usability: a first-time user shall be able to raise a ticket without instructions in about 2 minutes; fields are labelled and required fields marked; validation messages are plain language and name the field; the form keeps the user's input after a validation error. | Must | P7; measures are ASM-17 |
| NFR-04 | Simplicity: the MVP shall contain only the approved features; nothing from the out-of-scope list (section 9) is built unless the human approves. | Should | P1 |
| NFR-05 | Performance: with up to 1,000 tickets on a typical local machine, the ticket list and dashboard shall load in 2 seconds or less. | Should | ASM-11 |
| NFR-06 | Data integrity: a rejected or failed operation shall leave stored data unchanged (no partial tickets, no partial updates). | Must | Supports P8 |
| NFR-07 | Testability: business rules (validation, status workflow, dashboard counts) shall be verifiable by automated pytest tests without a browser, using an isolated temporary database and no real data. | Should | `CLAUDE.md` section 7; BL-01 |
| NFR-08 | Code-quality rule: all database access uses parameterized queries and the UI layer contains no SQL. This is NOT a security guarantee. | Should | `CLAUDE.md` section 7 |
| NFR-09 | Local-only: development and running are local; no cloud/external hosting, remote database or external API; the running application makes no external network calls and sends no usage telemetry (Streamlit usage statistics are disabled in the local configuration); no secrets or real customer data in the repository. | Must | `CLAUDE.md` section 10; BL-01; telemetry/network wording from human instruction at implementation start |
| NFR-10 | Technology baseline: Python 3.10 or later; Streamlit for the UI; built-in `sqlite3` for persistence; pytest for tests. The application entry point is `app/main.py`, launched with `python -m streamlit run app/main.py`. | Must | BL-01; BL-12 |
| NFR-11 | Lint quality: the project source and tests pass Ruff with no errors using the project's Ruff configuration. | Should | BL-01 |
| NFR-12 | Demo-role disclosure: the project documentation (user-facing README/guide and design docs) shall state that roles are a demo selector, not authentication or authorization, and shall make no security claim. | Must | BL-10 |

Counts: 12 NFRs (Must 7, Should 5). Deliberately NOT included: authentication, authorization, encryption, audit logging, privacy/compliance, uptime, backup/DR, accessibility standards, localization.

## 4. User stories

| ID | Story | Priority | Links |
|---|---|---|---|
| US-01 | As an employee, I want to raise a ticket with my name, title, description, category and priority, so that IT support knows what is wrong. | Must | FR-01, FR-02, FR-04, FR-05, FR-13 |
| US-02 | As an employee, I want to choose a priority for my ticket, so that urgent problems are visible. | Must | FR-03 |
| US-03 | As an employee, I want to see my tickets and their current status and resolution, so that I can track progress without asking IT. | Must | FR-06, FR-07, FR-26 |
| US-04 | As an employee, I want clear messages when my input is invalid, so that I can fix it and resubmit quickly. | Must | FR-02, NFR-03 |
| US-05 | As a support engineer, I want to view all tickets and filter them by status, priority, category and creator, so that I can decide what to work on. | Must | FR-06, FR-07, FR-08 |
| US-06 | As a support engineer, I want to move a ticket through Open, In Progress, Resolved and Closed, so that progress is visible to everyone. | Must | FR-09, FR-10, FR-13 |
| US-07 | As a support engineer, I want to change a ticket's priority, so that it reflects its real urgency. | Must | FR-11 |
| US-08 | RETIRED. Engineer edits title/description (Could); out of scope. | - | FR-12 retired |
| US-09 | As a support engineer, I want to add a resolution note to a ticket, so that the requester and others can see how it was resolved. (Changed from "progress note".) | Must | FR-15 |
| US-10 | RETIRED. Engineer records assignee (Could); out of scope. | - | FR-22 retired |
| US-11 | As a manager, I want to see the total number of tickets, so that I understand workload size. | Must | FR-16 |
| US-12 | As a manager, I want to see how many tickets are Open, In Progress, Resolved and Closed, so that I can judge progress. (Changed from "pending and resolved".) | Must | FR-18, FR-23 |
| US-13 | As a manager, I want to see how many tickets exist at each priority, so that I can see how much urgent work there is. | Must | FR-19 |
| US-14 | As a manager, I want the dashboard to show current data and handle having no tickets, so that I can trust it and always open it. | Must | FR-20 |
| US-15 | As any user, I want to pick my role and see the screens for it, so that I am not shown controls I do not need. | Must | FR-21 |
| US-16 | As any user, I want my tickets to still be there after the application is restarted, so that no information is lost. | Must | NFR-01 |
| US-17 | As any user, I want to use the system from my web browser, so that I need not install anything. | Must | NFR-02 |
| US-18 | As any user, I want the system to be simple and easy to use, so that I need no training. | Must | NFR-03, NFR-04 |
| US-19 | As a manager, I want to see how many tickets exist in each category, so that I can see where problems concentrate. | Must | FR-24 |
| US-20 | As an employee, I want to pick a category for my ticket, so that it reaches the right kind of help. | Must | FR-25 |
| US-21 | As a reviewer of this system, I want it clearly disclosed that roles are a demo selector and not security, so that nobody assumes access control exists. | Must | FR-21, NFR-12 |
| US-22 | As a support engineer or an employee, I want to type a word or a ticket number into a search box on my ticket list and have it combine with the filters I already use, so that I can find a particular ticket without scrolling through the whole list. | Should | FR-27 (with FR-08, FR-26) |

Counts: 22 story IDs = 20 active + 2 RETIRED (US-08, US-10). Cross-cutting NFR-05 to NFR-11 have no dedicated story (see matrix).

## 5. Roles, workflow, validation, edge cases

### 5.1 Roles and capabilities (DEMO selector; NO access control, see 0.1)

| Capability | Employee | Support Engineer | Manager |
|---|---|---|---|
| Raise ticket | Yes | No | No |
| View ticket list / details | Own tickets only, by entered name (ASM-23) | All tickets | No (dashboard only; ASM-18) |
| Filter list | No | Yes (status, priority, category, creator) | No |
| Search list (FR-27) | Yes (within own tickets only) | Yes (within the filtered list) | No |
| Change status | No | Yes | No |
| Change priority | No | Yes | No |
| Add/replace resolution note | No (read only) | Yes | No |
| Dashboard | No | No | Yes |

"No" means "the screen does not show the control", not "the action is prevented". Anyone can switch role. In particular, the Closed control is shown only in the Support Engineer view (ASM-20); this is UI placement, not access control, and the service layer has no roles.

### 5.2 Status workflow (proposed; ASM-06, ASM-20, ASM-21)

Statuses: Open, In Progress, Resolved, Closed. New tickets are Open. Closed is final. No delete in the MVP. The Closed control is shown only in the Support Engineer view (ASM-20); this is UI placement, not access control, and the service layer has no roles and cannot enforce who sets Closed.

| From \ To | Open | In Progress | Resolved | Closed |
|---|---|---|---|---|
| Open | rejected (same) | allowed | rejected | rejected |
| In Progress | allowed (put back) | rejected (same) | allowed (needs resolution note) | rejected |
| Resolved | rejected | allowed (reopen) | rejected (same) | allowed |
| Closed | rejected | rejected | rejected | rejected (same) |

Closed tickets are read-only: status, priority and resolution note cannot change.

### 5.3 Validation rules (limits are assumptions, ASM-03 / ASM-16)

| Field | Required | Rule |
|---|---|---|
| Creator | Yes | 1-100 characters after trimming |
| Title | Yes | 1-100 characters after trimming |
| Description | Yes | 1-2000 characters after trimming; line breaks allowed |
| Category | Yes | Exactly one value of the fixed list (ASM-19); default Other |
| Priority | Yes | Exactly one of Low, Medium, High, Critical; default Medium |
| Status (on update) | Yes | Exactly one of Open, In Progress, Resolved, Closed; must be an allowed transition |
| Resolution note | Yes when setting Resolved; otherwise optional | 1-1000 characters after trimming; line breaks allowed |
| Search text (FR-27) | No | Any text; trimmed; empty or whitespace-only means no search; matched literally (no wildcard or pattern meaning); no length limit is enforced and an overlong term simply matches nothing (ASM-25); never an error |

Whitespace-only counts as empty. Text is stored and shown literally. ID, created_at and updated_at are system-set and never user-entered.

### 5.4 Edge cases to be covered by acceptance criteria

Empty and whitespace-only input; exactly-at-limit and one-over-limit lengths; special characters, unicode, SQL-like text and markup; invalid priority/status/category value; invalid, same-status, skip-ahead and from-Closed transitions; Resolved without a note; unknown ticket ID; identical duplicate submissions; persistence across restart and reconnect; empty database (lists and dashboard); dashboard consistency (status counts sum = priority counts sum = category counts sum = total); filters with no matches; employee name with different case or surrounding spaces; rejected operations leaving data unchanged. Search (FR-27): empty and whitespace-only search; different letter case; ID search including partial ID text; search matching a different field than the title; `%`, `_`, quotes, backslash and SQL-looking text; search combined with each filter; no match; employee searching for text that exists only in another person's ticket; search leaving stored data unchanged.

## 6. Ambiguities, gaps and risks

### 6.1 Ambiguities and gaps

Status: Resolved = settled by the approved baseline or human instruction (a "Resolved (...; ... open)" row still has a residual assumption but is counted as resolved); Open = still needs a human decision (default shown).

| ID | Ambiguity / gap | Status | Resolution or proposed default |
|---|---|---|---|
| AMB-01 | "simple" vs "enterprise-style" in `CLAUDE.md` | Resolved | Human directed a small classroom MVP (BL scope). OQ-15 closed. |
| AMB-02 | "easy to use" not measurable | Open (confirm) | ASM-17 |
| AMB-03 | Which fields are required | Resolved (fields); limits open | BL-06; limits ASM-03 |
| AMB-04 | Who sets priority, what scale | Resolved (scale, engineer change); open (employee sets at creation) | BL-04, BL-08; ASM-04 |
| AMB-05 | "track progress": history/comments? | Resolved by default | Status plus resolution note only; history dropped (ASM-09, confirm) |
| AMB-06 | Which statuses are "pending" | Resolved | BL-05: dashboard shows the four status counts; no "pending" figure (ASM-22, confirm) |
| AMB-07 | "resolved" vs "closed"; reopen | Resolved (Closed exists, BL-07); open (rules) | ASM-06, ASM-20 |
| AMB-08 | Which fields engineers may update | Resolved | Status, priority, resolution note (BL-04) |
| AMB-09 | Login / role enforcement | Resolved | BL-10 demo selector, disclosed |
| AMB-10 | Assignment of tickets | Resolved | Not in approved scope; out of scope |
| AMB-11 | Categories | Resolved (in scope, BL-06); list open | ASM-19 |
| AMB-12 | Attachments | Resolved | Out of scope |
| AMB-13 | Notifications | Resolved | Out of scope |
| AMB-14 | Volume and concurrent users | Open | ASM-11 |
| AMB-15 | Browsers; local vs network | Open | ASM-12 |
| AMB-16 | Priority counts: all or pending only | Resolved | All tickets (BL-05, ASM-10) |
| AMB-17 | Employees see own or all tickets | Open (flag) | Own tickets by entered name; ASM-23 |
| AMB-18 | Delete/cancel tickets | Resolved by default | No delete; Closed is the final state |
| AMB-19 | Duplicate tickets | Open | Allowed (ASM-13) |
| AMB-20 | Dashboard time scope | Resolved | All-time current snapshot (ASM-10) |
| AMB-21 | "permanently": backup/retention | Open | Local file only (ASM-14) |
| AMB-22 | Date/time zone and format | Open (confirm) | ASM-15 |
| AMB-23 | Sensitive content in tickets | Resolved by disclosure | No protection promised; UI/doc notice (FR-21, NFR-12) |
| AMB-24 | Who sets Closed; can Closed be reopened | Open | Closed control shown only in the Support Engineer view (UI placement, not access control; the service has no roles); Closed is final (ASM-20) |
| AMB-25 | Is a resolution note mandatory for Resolved | Open | Yes (ASM-21) |
| AMB-26 | Listing search: which fields, how ID is matched, whitespace handling, behaviour for employees | Resolved (scope and fields, BL-11); matching details open | ID, title, description, creator; details in ASM-25, OQ-21 |

Counts: 26 ambiguities; 17 resolved by the baseline or human instruction (some with residual assumptions), 9 still open (AMB-02, 14, 15, 17, 19, 21, 22, 24, 25). Correction: the v2 line said "25 ambiguities; 15 resolved, 10 open"; counting the rows of AMB-01 to AMB-25 gives 16 resolved and 9 open, and adding AMB-26 gives 17 resolved and 9 open.

### 6.2 Risks

| ID | Risk | Impact | Mitigation |
|---|---|---|---|
| RISK-01 | No access control: anyone can switch role and change any ticket; creator names cannot be trusted. | High | Accepted by BL-10; FR-21 and NFR-12 disclosure; no security claims. |
| RISK-02 | Scope creep (attachments, notifications, assignment, history). | Medium | Out of scope list (section 9); changes need human approval. |
| RISK-03 | RETIRED. Wrong "pending" definition; superseded because there is no pending figure. | - | - |
| RISK-04 | Free-text creator names mean variants/typos; employees may not find their tickets. | Medium | Case-insensitive, trimmed exact match (FR-26); documented limitation. |
| RISK-05 | "Permanent" storage is one local file; deleting it loses all data. | Medium | State the limitation (ASM-14). |
| RISK-06 | Several browser sessions writing at once may conflict. | Low | Small expectations (ASM-11); NFR-06. |
| RISK-07 | Repeated clicks/reruns may create duplicate tickets. | Medium | AC-10 documents behaviour (ASM-13). |
| RISK-08 | Priority inflation makes the breakdown meaningless. | Low | Note for client. |
| RISK-09 | Unapproved assumptions drive several ACs. | Medium | Resolve section 8 before design. |
| RISK-10 | Ticket text may hold sensitive data stored unprotected. | Medium | Disclosure only; no protection promised. |
| RISK-11 | The demo role selector is mistaken for security (e.g. a manager or employee believes data is restricted). | High | Visible UI notice on every screen (FR-21), documentation (NFR-12), AC-45 and AC-68. |
| RISK-12 | "My tickets" view (FR-26) is read as privacy, but any name can be typed. | Medium | Described as convenience in UI and docs (ASM-23). |
| RISK-13 | Search text is passed into code or SQL unsafely, or wildcard characters (`%`, `_`) change the result. | Medium | Literal matching required by FR-27 and AC-77; search runs on rows already returned by the service (no new SQL); NFR-08 still applies. |

Counts: 13 risk IDs (12 active, 1 RETIRED).

## 7. Assumptions

Section 0.2 items are approved. The assumptions below are not. Status: SUPERSEDED = replaced by the baseline; REVISED = changed by the baseline and still needs approval; PENDING = needs approval as written.

| ID | Assumption | Status | Suggested default | Alternatives |
|---|---|---|---|---|
| ASM-01 | No authentication; role selector only. | SUPERSEDED by BL-10 (approved) | - | - |
| ASM-02 | Creators identify themselves by typing a name; free text, trimmed, case-insensitive match. No employee directory. | PENDING | Free-text name | Seeded name dropdown |
| ASM-03 | Length limits: creator 100, title 100, description 2000, resolution note 1000 characters. | PENDING (fields approved by BL-06) | As stated | Other limits |
| ASM-04 | The employee chooses priority at creation (default Medium); only engineers change it later. | REVISED (scale approved BL-08; engineer change approved BL-04) | As stated | Employee cannot set priority |
| ASM-05 | Statuses Open/In Progress/Resolved and "pending" = Open + In Progress. | SUPERSEDED by BL-07 and BL-05 | - | - |
| ASM-06 | Allowed transitions as in section 5.2: Open to In Progress; In Progress to Open; In Progress to Resolved; Resolved to In Progress (reopen); Resolved to Closed. All others rejected. Closed is final. | REVISED, PENDING | As stated | Allow Open to Resolved; allow reopen of Closed |
| ASM-07 | Out of scope: attachments, notifications/email, SLAs/due dates, comment threads, reports beyond the dashboard, ticket delete, bulk actions, import/export, free-text search (except the listing search of FR-27, added by BL-11), title/description editing, assignee, status history. | REVISED (categories now in scope; listing search now in scope by BL-11) | Out of scope | Pull items in individually |
| ASM-08 | Assignment of tickets to engineers is not built. | Resolved by omission from BL-04 (confirm) | Not built | Free-text assignee |
| ASM-09 | Status history and progress notes are dropped from the MVP (FR-14 and the old FR-15 note retired). | REVISED, PENDING | Dropped; keeps the demo small | Re-add FR-14 as a Should |
| ASM-10 | Dashboard figures are all-time current counts across ALL tickets; no date range. | Largely resolved by BL-05 (confirm) | As stated | Date filter |
| ASM-11 | Up to about 1,000 tickets and 5 concurrent users on one local machine. | PENDING | As stated | Other figures |
| ASM-12 | Latest desktop Chrome, Firefox, Edge on a local address; not exposed to other machines. | PENDING | As stated | LAN access (needs approval) |
| ASM-13 | Duplicates are not blocked; identical submissions create separate tickets. | PENDING | Allow | Warn or block |
| ASM-14 | "Permanently" = local file persistence only; no backup, retention or deletion tooling. | PENDING | As stated | Manual export |
| ASM-15 | Timestamps use the local system clock, displayed as `YYYY-MM-DD HH:MM`. | PENDING | As stated | UTC |
| ASM-16 | Text is trimmed; whitespace-only counts as empty; special characters and unicode accepted and shown literally. | PENDING | As stated | Restrict characters |
| ASM-17 | "Easy to use" is judged by a manual walk-through: first-time user raises a ticket in about 2 minutes with no instructions. | PENDING | As stated | Formal usability test |
| ASM-18 | Capability split in 5.1: Employee raises tickets and sees own; Engineer sees all, filters and updates; Manager sees the dashboard only (the earlier read-only list for managers is dropped). Enforced only by which controls are shown. | REVISED, PENDING | As in 5.1 | Manager also gets a read-only list |
| ASM-19 | Category is a small fixed list, required at creation, default Other, not changeable later: Hardware, Software, Network, Account Access, Other. | NEW, PENDING | As stated | Different list; engineer may recategorise |
| ASM-20 | "Only engineers set Closed" is a UI placement, not a rule that is enforced: the Closed control is shown only in the Support Engineer view (employees only create and view, BL-03). The service layer has no roles and cannot enforce who sets Closed; this is not access control (see 0.1). Closed is reachable only from Resolved, is final and read-only. No reopen of Closed. | NEW, PENDING (softened in v3) | As stated | Employee confirms closure; allow reopen of Closed |
| ASM-21 | A non-empty resolution note is required to set Resolved. The note may be added or replaced by an engineer on any non-Closed ticket. Notes are retained when a ticket is reopened. | NEW, PENDING | As stated | Note optional |
| ASM-22 | "Pending" has no dashboard meaning. The dashboard shows the four status counts instead; if the client still wants a pending figure, it equals Open + In Progress. | NEW, PENDING | No pending figure | Add derived pending figure |
| ASM-23 | Employees see only tickets whose creator matches the name they enter (case-insensitive, exact). This is a convenience, not privacy. | NEW, PENDING (flagged) | Own tickets by entered name | Employees see all tickets (simpler) |
| ASM-24 | Same-value priority change (and same-status change) is rejected as "no change". | NEW, PENDING | Reject | Treat as silent no-op |
| ASM-25 | Listing search details (FR-27) not fixed by BL-11: (a) the search text is trimmed and an empty or whitespace-only text means no search; (b) the text is matched as one literal phrase (not split into words) as a substring of the ticket ID's decimal text, the title, the description or the creator, so "12" matches IDs 12, 112 and 120, and "#12" matches only text that really contains "#12"; (c) category, status, priority and resolution note are not searched; (d) case-insensitivity uses Python Unicode case folding; (e) in the Employee view the message is "no matching tickets" when the entered name has tickets but none match, and the existing "no tickets" message of AC-66 when the name has no tickets at all; (f) the search runs in the UI layer on the list returned by the service, which is why FR-27 adds no service capability; (g) no maximum search length. | NEW, PENDING | As stated | ID matches only exactly; search also covers category/resolution note; multi-word terms matched word by word |

Counts: 25 assumption IDs: 2 SUPERSEDED (ASM-01, ASM-05), 1 resolved by omission (ASM-08), 22 needing approval.

## 8. Open questions for the human

Blocking = answer needed before design starts. Resolved questions are kept for traceability.

| ID | Question | State | Suggested default |
|---|---|---|---|
| OQ-01 | Real authentication required? | RESOLVED by BL-10 (demo selector) | - |
| OQ-02 | Who sets priority; which scale? | RESOLVED (BL-04, BL-08); residual in ASM-04 | - |
| OQ-03 | Which statuses; meaning of "pending"? | RESOLVED (BL-07, BL-05); see OQ-20 | - |
| OQ-04 | Allowed status transitions, including Resolved to Closed and any reopen? | **Open, blocking** | ASM-06 |
| OQ-05 | Do employees see only their own tickets or all? | **Open, blocking (flagged)** | Own, by entered name (ASM-23) |
| OQ-06 | Ticket assignment? | RESOLVED by omission (ASM-08) | Not built |
| OQ-07 | Categories, attachments, notifications? | RESOLVED: categories in (BL-06); attachments and notifications out. List is OQ-16. | - |
| OQ-08 | Dashboard priority counts: all or pending only; date range? | RESOLVED (BL-05, ASM-10) | - |
| OQ-09 | Volume and concurrent users? | Open | 1,000 / 5 (ASM-11) |
| OQ-10 | Local-only access; which browsers? | Open | Local; Chrome/Firefox/Edge (ASM-12) |
| OQ-11 | Duplicates blocked, warned, or allowed? | Open | Allowed (ASM-13) |
| OQ-12 | Meaning of "permanently" for backup/retention? | Open | Local file only (ASM-14) |
| OQ-13 | Is status history needed? | Open (confirm drop) | Dropped (ASM-09) |
| OQ-14 | Sensitive ticket content? | RESOLVED by disclosure | No protection promised |
| OQ-15 | "simple" vs "enterprise-style"? | RESOLVED (human: keep it small) | - |
| OQ-16 | What is the category list? | **Open, blocking** | Hardware, Software, Network, Account Access, Other (ASM-19) |
| OQ-17 | Who sets Closed (engineer or employee)? | **Open, blocking** | Closed control shown in the Support Engineer view only (ASM-20); UI placement, not access control |
| OQ-18 | Are the length limits acceptable? | Open | 100/100/2000/1000 (ASM-03) |
| OQ-19 | Is a resolution note mandatory to set Resolved? | Open | Yes (ASM-21) |
| OQ-20 | Does "pending" still need a dashboard figure? | Open (confirm) | No (ASM-22) |
| OQ-21 | Listing search details (FR-27): is the ID matched as a substring ("12" also finds 112) or exactly; should whitespace-only text mean no search; are other fields (category, resolution note) searched? | Open (not blocking) | Substring on ID; whitespace-only = no search; ID, title, description, creator only (ASM-25) |

Counts: 21 questions; 8 resolved (OQ-01, 02, 03, 06, 07, 08, 14, 15); 13 open, of which 4 blocking (OQ-04, OQ-05, OQ-16, OQ-17).

## 9. Out of scope

Authentication, authorization enforcement, encryption, audit logging, privacy/compliance features; attachments; notifications/email; SLA/due dates; comment threads; status history; assignee/assignment; editing title, description or category after creation; ticket deletion; bulk actions; import/export; free-text search other than the listing search in FR-27 (so no search on the Manager view, no search of resolution notes or category, no saved searches, no full-text index, no new backend search capability); reports beyond the dashboard in BL-05; a combined "pending" figure (ASM-22); manager ticket list; multi-language; mobile-specific UI; cloud deployment or external hosting; external APIs or integrations.

## 10. Acceptance criteria

Convention: AC IDs are stable. RETIRED ACs keep their number with no content. Each AC names the FR/NFR it verifies. Every AC depends on the assumptions in its FR/NFR rows; if an assumption is rejected the AC must be revised. Per `CLAUDE.md`, each AC needs at least one pytest test, except those that are manual or document checks (AC-49, AC-50, AC-53, AC-54 timing record, AC-57, AC-58, AC-68, AC-69 and the UI parts of AC-44, AC-45, AC-51, AC-52), which need recorded evidence instead. AC-81 is verified by a static check or inspection with recorded evidence. AC-15 and AC-29 (unknown ticket ID) are verified at service level only, because the UI offers only existing ticket IDs and the case cannot be produced from the UI.

### 10.1 Raising tickets (FR-01 to FR-05, FR-25)

| ID | Verifies | Criterion |
|---|---|---|
| AC-01 | FR-01 | **Given** the raise-ticket form, **when** I enter a valid creator name, title, description, category and priority and submit, **then** a ticket is created, I see a confirmation showing its ID, and the ticket appears in the engineer ticket list. |
| AC-02 | FR-01, FR-07 | **Given** a ticket created with specific values, **when** I open its details, **then** creator, title, description, category and priority equal what I entered (after whitespace trimming). |
| AC-03 | FR-02 | **Given** the form, **when** I submit with any one of creator name, title or description empty, **then** no ticket is created, the total ticket count is unchanged, and a message names the missing field. |
| AC-04 | FR-02 | **Given** the form, **when** a required text field contains only spaces/tabs, **then** it is treated as empty and rejected as in AC-03. |
| AC-05 | FR-02 | **Given** the form, **when** creator or title is 101 characters or description is 2001 characters, **then** the submission is rejected with a message stating the limit; **and when** they are exactly 100 / 100 / 2000 characters, **then** the ticket is created. |
| AC-06 | FR-02 | **Given** the form, **when** I submit text containing quotes, semicolons, angle brackets/markup, SQL-like text, unicode/emoji and line breaks (description), **then** the ticket is created without error, the text is displayed exactly as typed, and all other tickets are unchanged. |
| AC-07 | FR-03 | **Given** the form, **when** I open the priority control, **then** the options are exactly Low, Medium, High, Critical, with Medium preselected. |
| AC-08 | FR-03 | **Given** a request to create a ticket with a priority outside the list (e.g. "Urgent", empty), **when** it is submitted, **then** it is rejected and no ticket is created. |
| AC-09 | FR-04 | **Given** two tickets created one after the other, **when** I view them, **then** their IDs differ, the second ID is greater than the first, each shows created_at, and the second is not earlier than the first. |
| AC-10 | FR-04 (ASM-13) | **Given** I submit two tickets with identical content, **when** both succeed, **then** two separate tickets with distinct IDs exist. |
| AC-11 | FR-05 | **Given** a newly created ticket, **when** I view it, **then** its status is Open. |
| AC-67 | FR-25, FR-02 | **Given** the form, **when** I open the category control, **then** the options are exactly the approved category list (suggested: Hardware, Software, Network, Account Access, Other) with Other preselected; **and when** a category outside the list (e.g. "Printers", empty) is submitted, **then** it is rejected and no ticket is created. |

### 10.2 Viewing, filtering and searching (FR-06 to FR-08, FR-26, FR-27)

| ID | Verifies | Criterion |
|---|---|---|
| AC-12 | FR-06 | **Given** at least three tickets, **when** I open the engineer list, **then** every ticket shows ID, title, creator, category, priority, status and created_at, ordered newest first. |
| AC-13 | FR-06 | **Given** no tickets exist, **when** I open the list, **then** a "no tickets" message is shown and no error occurs. |
| AC-14 | FR-07 | **Given** an existing ticket, **when** I open its details, **then** I see ID, title, creator, description, category, priority, status, created_at, updated_at and resolution_note (empty if none). |
| AC-15 | FR-07 | **Given** a ticket ID that does not exist, **when** details are requested, **then** a "not found" message is shown and no error/crash occurs. Verified at service level only: the UI offers only existing ticket IDs, so the case cannot be produced from the UI. |
| AC-16 | FR-08 | **Given** tickets in several statuses, **when** I filter by status Open, **then** only Open tickets are listed. |
| AC-17 | FR-08 | **Given** tickets in several priorities, **when** I filter by priority High, **then** only High tickets are listed. |
| AC-18 | FR-08 | **Given** a mix of tickets, **when** I filter by status and priority together, **then** only tickets matching both are listed. |
| AC-19 | FR-08 | **Given** tickets from several creators, **when** I filter by creator name (case-insensitive, exact), **then** only that creator's tickets are listed. |
| AC-20 | FR-08 | **Given** a filter combination that matches nothing, **when** applied, **then** a "no matching tickets" message is shown and no error occurs. |
| AC-60 | FR-08 | **Given** tickets in several categories, **when** I filter by category Network, **then** only Network tickets are listed; **and when** combined with a status filter, **then** only tickets matching both are listed. |
| AC-66 | FR-26, FR-07 | **Given** tickets from creators "Ann" and "Bob", **when** in the Employee view I enter " ann " as my name, **then** only Ann's tickets are listed, each with status and resolution note visible; **and when** I enter a name with no tickets, **then** a "no tickets" message is shown; **and** the Employee view shows no controls to change status, priority or notes. |
| AC-71 | FR-27 | **Given** engineer-view tickets titled "Printer jam" and "VPN down" (neither description nor creator contains "print"), **when** I search "print", **then** only "Printer jam" is listed (substring match on the title), the list shows the same columns as FR-06, and the order stays newest first. |
| AC-72 | FR-27 | **Given** a ticket titled "Printer jam", **when** I search "PRINTER", "printer" and "pRiNtEr" in turn, **then** each search lists exactly the same tickets, including "Printer jam". |
| AC-73 | FR-27 | **Given** one ticket whose description contains "toner" only there, one whose creator is "Marlene" only there, and one whose category, status, priority or resolution note (but none of ID, title, description, creator) contains the term "Network", **when** I search "toner", "marlene" and "Network" in turn, **then** the first two searches list the description ticket and the creator ticket respectively, and the "Network" search does not list the ticket that matches only on category, status, priority or resolution note. |
| AC-74 | FR-27 | **Given** tickets with IDs 2, 5 and 12, **when** I search "12", **then** only ticket 12 is listed; **and when** I search "2", **then** tickets 2 and 12 are listed (substring of the ID text, ASM-25). |
| AC-75 | FR-27, FR-08 | **Given** Open and Resolved tickets that both contain "VPN" in the title, **when** I filter status Open and search "vpn", **then** only Open tickets containing "VPN" are listed; **and when** I clear the search, **then** all Open tickets are listed again (filter unchanged). |
| AC-76 | FR-27 | **Given** any set of tickets, **when** the search text is empty, **then** the list equals the list shown with no search; **and when** it contains only spaces, **then** the same list is shown and no error or no-match message appears. |
| AC-77 | FR-27, NFR-08 | **Given** tickets whose text contains literally `100%`, `a_c`, `it's`, `say "hi"`, `back\slash`, `<b>x</b>` and a ticket titled `abc`, **when** I search `%`, `a_c`, `'`, `"hi"`, `\`, `<b>` and `' OR 1=1 --` in turn, **then** each search lists only tickets that really contain that exact text (`%` does not match everything; `a_c` does not match `abc`; the last term matches nothing unless a ticket contains it), no error occurs, and the stored tickets are unchanged afterwards. |
| AC-78 | FR-27 | **Given** tickets exist, **when** I search for text found in no ticket (alone, or combined with filters), **then** the existing "no matching tickets" message is shown, no error occurs, and clearing the search shows the list again. |
| AC-79 | FR-27, FR-26 | **Given** tickets from "Ann" and "Bob", where the word "firewall" appears only in Bob's ticket, **when** in the Employee view I enter "Ann" and search "firewall", **then** no ticket is listed and Bob's ticket is never shown; **and when** I search a word that appears in Ann's ticket, **then** only Ann's matching tickets are listed (search combines with the own-tickets name match). |
| AC-80 | FR-27, FR-26 | **Given** the Employee view, **when** the entered name has tickets but none match the search, **then** the "no matching tickets" message is shown; **and when** the entered name has no tickets at all, **then** the "no tickets" message of AC-66 is shown; **and when** the search is cleared, **then** the employee's tickets are listed again. |
| AC-81 | FR-27 | **Given** the code base and a snapshot of stored data, **when** the search is used (including with special characters) and the code is inspected, **then** the service interface offers no search operation (no new backend capability), the search is applied to tickets already returned by the service, no SQL is built from the search text, and the stored data after searching is identical to the snapshot. |

### 10.3 Updating tickets (FR-09 to FR-15)

| ID | Verifies | Criterion |
|---|---|---|
| AC-21 | FR-09, FR-10, FR-13 | **Given** an Open ticket, **when** an engineer sets it to In Progress, **then** its status is In Progress and updated_at is refreshed. |
| AC-22 | FR-09, FR-10, FR-15 | **Given** an In Progress ticket with a resolution note (existing or supplied in the same action), **when** set to Resolved, **then** its status is Resolved. |
| AC-23 | FR-10 | **Given** a Resolved ticket, **when** set to In Progress (reopen), **then** its status is In Progress and its resolution note is retained. |
| AC-24 | FR-10 | **Given** an In Progress ticket, **when** set to Open, **then** its status is Open. |
| AC-25 | FR-10 | **Given** an Open ticket, **when** set directly to Resolved, **then** the change is rejected with a message, and status and updated_at are unchanged. |
| AC-26 | FR-10 | **Given** a Resolved ticket, **when** set to Open, **then** the change is rejected and the ticket is unchanged. |
| AC-27 | FR-10 | **Given** a ticket in any status, **when** set to the status it already has, **then** the change is rejected and the ticket is unchanged. |
| AC-28 | FR-09 | **Given** a ticket, **when** a status value outside Open/In Progress/Resolved/Closed is submitted (e.g. "Pending", empty), **then** it is rejected and the ticket is unchanged. |
| AC-29 | FR-09 | **Given** a ticket ID that does not exist, **when** a status change is submitted, **then** an error message is shown and no data changes. Verified at service level only: the UI offers only existing ticket IDs, so the case cannot be produced from the UI. |
| AC-30 | FR-11 | **Given** a ticket with priority High, **when** an engineer changes it to Low, **then** the details, the list and the dashboard priority counts show Low. |
| AC-31 | FR-11 | **Given** a ticket, **when** a priority outside the list, or the same priority it already has, is submitted, **then** it is rejected and the ticket (including updated_at) is unchanged. |
| AC-32 | FR-12 (RETIRED) | RETIRED. Title/description editing is out of scope. |
| AC-33 | FR-13 | **Given** a new ticket, **then** updated_at equals created_at; **and given** any ticket, **when** a status, priority or resolution-note update succeeds, **then** updated_at is not earlier than before and shows the new time; **and when** an update is rejected, **then** updated_at is unchanged. |
| AC-34 | FR-14 (RETIRED) | RETIRED. Status history is out of scope. |
| AC-35 | FR-14 (RETIRED) | RETIRED. Status history is out of scope. |
| AC-36 | FR-15 | **Given** a non-Closed ticket, **when** an engineer adds or replaces a resolution note of 1-1000 characters (including special characters and line breaks), **then** it is saved, shown exactly as typed in ticket details, and updated_at is refreshed; **and when** the note is empty, whitespace-only or 1001 characters, **then** it is rejected and the ticket is unchanged. |
| AC-61 | FR-09, FR-10 | **Given** a Resolved ticket, **when** an engineer sets it to Closed, **then** its status is Closed and updated_at is refreshed. Note (ASM-20): the Closed control is shown only in the Support Engineer view (UI placement, not access control); the service layer has no roles and does not check who closes a ticket. |
| AC-62 | FR-10, FR-11, FR-15 | **Given** a Closed ticket, **when** any status change, priority change or resolution-note change is submitted, **then** each is rejected with a message and the ticket is unchanged. |
| AC-63 | FR-10 | **Given** an Open or In Progress ticket, **when** set directly to Closed, **then** the change is rejected and the ticket is unchanged. |
| AC-64 | FR-10, FR-15 | **Given** an In Progress ticket with no resolution note, **when** set to Resolved without supplying a note, **then** the change is rejected with a message naming the resolution note, and status and updated_at are unchanged. |

### 10.4 Dashboard (FR-16 to FR-20, FR-23, FR-24)

| ID | Verifies | Criterion |
|---|---|---|
| AC-37 | FR-16 | **Given** N tickets exist, **when** the manager opens the dashboard, **then** total tickets equals N. |
| AC-38 | FR-17 (RETIRED) | RETIRED. No "pending" figure. |
| AC-39 | FR-18 | **Given** tickets in several statuses, **when** the dashboard is opened, **then** resolved equals the number of Resolved tickets. |
| AC-40 | FR-16, FR-18, FR-23 | **Given** any set of tickets, **when** the dashboard is opened, **then** open + in-progress + resolved + closed = total. |
| AC-41 | FR-19 | **Given** tickets of mixed priorities, **when** the dashboard is opened, **then** it shows a numeric count for each of Low, Medium, High, Critical (including 0) and the four counts sum to total. A chart may accompany but the numbers must be visible. |
| AC-42 | FR-20, FR-24 | **Given** no tickets, **when** the dashboard is opened, **then** total and all four status counts show 0, all four priorities show 0, every category shows 0, and no error occurs. |
| AC-43 | FR-20 | **Given** the dashboard was viewed, **when** a ticket is created or its status/priority changed and the dashboard is reloaded or refreshed, **then** the figures reflect the change without restarting the application. |
| AC-59 | FR-23 | **Given** tickets in each of Open, In Progress and Closed (and others), **when** the dashboard is opened, **then** the Open, In Progress and Closed counts each equal the number of tickets in that status. |
| AC-65 | FR-24 | **Given** tickets across several categories, **when** the dashboard is opened, **then** it shows a numeric count for every category in the list (including 0) and the category counts sum to total. A chart may accompany but the numbers must be visible. |

### 10.5 Roles and disclosure (FR-21)

| ID | Verifies | Criterion |
|---|---|---|
| AC-44 | FR-21 | **Given** the application is open, **when** I choose Employee, Support Engineer or Manager, **then** I see respectively: raise ticket plus "My tickets"; ticket list with filters and status/priority/resolution-note controls; dashboard only. |
| AC-45 | FR-21, NFR-12 | **Given** the application is open in any role, **when** I look at any screen, **then** a visible notice labels the role selector as a DEMO and states it is not authentication or access control and offers no security. |
| AC-46 | FR-22 (RETIRED) | RETIRED. Assignee is out of scope. |

### 10.6 Non-functional (NFR-01 to NFR-12)

| ID | Verifies | Criterion |
|---|---|---|
| AC-47 | NFR-01 | **Given** several tickets with changed statuses/priorities and resolution notes, **when** the application is stopped and started again, **then** every ticket and field is still present and the dashboard figures are the same. |
| AC-48 | NFR-01 | **Given** stored tickets, **when** I refresh the browser, close and reopen it, or the data connection is closed and reopened, **then** the same tickets are shown. |
| AC-49 | NFR-02 | **Given** the application is running locally (started with the BL-12 command), **when** I open its local address in the latest Chrome, Firefox and Edge, **then** raising a ticket, updating a ticket and viewing the dashboard complete without installing client software. |
| AC-50 | NFR-03 | **Given** a first-time user and no instructions, **when** asked to raise a ticket, **then** they succeed in about 2 minutes or less (manual walk-through, result recorded). |
| AC-51 | NFR-03 | **Given** any form, **when** I view it and trigger a validation error, **then** all fields are labelled, required fields are marked, and the message is plain language naming the field. |
| AC-52 | NFR-03 | **Given** a validation error on the raise-ticket form, **when** the error is shown, **then** the values I typed in the other fields are still present. |
| AC-53 | NFR-04 | **Given** the finished application, **when** I review its screens, **then** it contains no feature from the out-of-scope list in section 9 (no attachments, notifications, SLAs, delete, history, assignee). |
| AC-54 | NFR-05 | **Given** 1,000 tickets stored, **when** I open the ticket list and the dashboard on a local machine, **then** each loads in 2 seconds or less (measured and recorded). |
| AC-55 | NFR-06 | **Given** a snapshot of stored data, **when** I perform rejected operations (invalid create, invalid transition, unknown ID, invalid priority/category), **then** the data afterwards is identical to the snapshot. |
| AC-56 | NFR-07 | **Given** a clean isolated temporary database, **when** automated tests exercise creation, validation, workflow and dashboard counts, **then** they run without a browser and without touching real data. |
| AC-57 | NFR-08 | **Given** the code base, **when** inspected, **then** every database statement is parameterized and no SQL appears in the UI layer. (Code-quality rule; not a security guarantee.) |
| AC-58 | NFR-09 | **Given** the repository and running application, **when** inspected, **then** no cloud/external service, external API or remote database is configured or contacted, and no secrets or real customer data are present; **and** the application makes no external network calls and sends no usage telemetry (Streamlit usage statistics are disabled in the project's local Streamlit configuration, and a code and configuration inspection plus a run with outbound network blocked or monitored shows no outbound connection; evidence recorded). |
| AC-68 | NFR-12 | **Given** the project documentation (README/user guide and design docs), **when** I read it, **then** it states that roles are a demo selector and not authentication or authorization, and contains no claim of security, access control or privacy. |
| AC-69 | NFR-10 | **Given** the project, **when** inspected and run, **then** it runs on Python 3.10 or later, the UI is Streamlit, persistence uses the built-in `sqlite3` module, and tests run under pytest; **and** the application entry point is `app/main.py`, the application starts with `python -m streamlit run app/main.py` (BL-12), and the README states this launch command. |
| AC-70 | NFR-11 | **Given** the project source and tests, **when** Ruff is run with the project configuration, **then** it reports no errors (command and output recorded). |

Counts: 81 AC IDs = 76 active + 5 RETIRED (AC-32, AC-34, AC-35, AC-38, AC-46). AC-71 to AC-81 are new in v3 (FR-27). Typo fix: AC-20 now reads "a 'no matching tickets' message".

## 11. Change log

### 11.1 Draft (v1) to baseline v2

| Change | IDs |
|---|---|
| Added FR | FR-23 (Open/In Progress/Closed counts), FR-24 (category breakdown), FR-25 (category list), FR-26 (employee "My tickets") |
| Changed FR | FR-01, 02, 03, 06, 07, 08, 09, 10, 11, 13, 15 (now resolution note), 18, 19, 20, 21 (now Must, visible demo notice) |
| Retired FR | FR-12, FR-14, FR-17, FR-22 |
| Added NFR | NFR-10 (tech baseline), NFR-11 (Ruff), NFR-12 (demo-role disclosure) |
| Changed NFR | NFR-01 (no history), NFR-04 (scope list), NFR-07, NFR-09 |
| Added stories | US-19, US-20, US-21 |
| Changed stories | US-01, 03, 04, 05, 06, 07, 09 (resolution note), 12, 15 |
| Retired stories | US-08, US-10 |
| Added AC | AC-59 to AC-70 |
| Changed AC | AC-01 to AC-07, 12, 14, 19, 20 (typo fixed), 21 to 28, 30, 31, 33, 36, 39 to 45, 47, 53, 55 |
| Retired AC | AC-32, AC-34, AC-35, AC-38, AC-46 |
| Retired risk | RISK-03; added RISK-11, RISK-12 |
| Superseded assumptions | ASM-01 (by BL-10), ASM-05 (by BL-07/BL-05); new ASM-19 to ASM-24 |

### 11.2 Baseline v2 to v3 (human-directed changes at implementation start)

| Change | IDs |
|---|---|
| Added baseline decisions | BL-11 (listing search, human-directed addition to the approved scope), BL-12 (entry point `app/main.py`, launch command `python -m streamlit run app/main.py`) |
| Added FR | FR-27 (listing search, Should) |
| Added story | US-22 |
| Added AC | AC-71 to AC-81 (search; AC-81 is an inspection/static check) |
| Added assumption, question, ambiguity, risk | ASM-25, OQ-21, AMB-26, RISK-13 |
| Changed NFR | NFR-09 (no external network calls, no usage telemetry; Streamlit usage statistics disabled in local config), NFR-10 (entry point and launch command, BL-12) |
| Changed AC | AC-49 (started with BL-12 command), AC-58 (no network calls, no telemetry), AC-69 (entry point and launch command, README states it), AC-15 and AC-29 (marked verified at service level only; UI offers only existing IDs), AC-61 (note on ASM-20) |
| Softened assumption | ASM-20: "only engineers set Closed" is a UI placement (Closed control shown only in the Support Engineer view); the service layer has no roles and cannot enforce it; not access control. Related wording updated in sections 5.1, 5.2, AMB-24 and OQ-17. |
| Scope text updated | ASM-07 and section 9 (listing search of FR-27 is no longer out of scope; other free-text search remains out) |
| Corrected | Section 6.1 count line: true values are 16 resolved and 9 open for AMB-01 to AMB-25 (the v2 line said 15 and 10); with AMB-26 the line now reads 17 resolved, 9 open |

## 12. Hand-off notes

- Design may start only after the human approves the remaining assumptions (section 7), in particular the four blocking questions OQ-04, OQ-05, OQ-16, OQ-17.
- The traceability matrix is in `docs/traceability-matrix.md`.
- If a pending assumption is rejected, revise the linked FR/AC rows listed in the matrix before design.
- v3 note for the solution-architect: FR-27, US-22 and AC-71 to AC-81 have no design element yet; design documents and the matrix "Design element" column that mention `app.py` or `streamlit run app.py` predate BL-12 (entry point `app/main.py`, command `python -m streamlit run app/main.py`) and need updating by the architect.

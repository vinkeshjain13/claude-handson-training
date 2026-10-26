# IT Support Ticket Management System - Project Instructions

## 1. Project Purpose
Build an enterprise-style IT Support Ticket Management System using a team of specialized Claude Code subagents.

- Language: Python
- Persistence: SQLite via Python's built-in `sqlite3` module
- UI: Streamlit (forms, tables, filters, dashboard visualizations)
- Tests: pytest
- Documentation: Markdown under `docs/`

The detailed requirements come from the client and are captured verbatim in `docs/client-requirements.md` once provided. Requirements, design and test evidence all live in `docs/`.

## 2. Lead Orchestrator Responsibilities
The main Claude Code session is the Lead Orchestrator. It:
- Understands the user's goal and breaks it into tasks.
- Delegates each task to the right subagent with a self-contained brief (goal, inputs, file paths, constraints, expected output).
- Sequences work by dependency; parallelizes only independent tasks that touch different files.
- Verifies subagent claims against actual files and command output before reporting anything as done.
- Maintains a progress summary: agent, assigned task, outcome, affected files.
- Routes defects and findings to the owning agent, then has QA / security re-verify.
- Stops at human approval checkpoints and never works around them.
- Does NOT write application code, schemas, tests, or requirements/design content itself, and does not impersonate a subagent. Its own work is coordination, verification, repository housekeeping and communication.

## 3. Available Subagents (`.claude/agents/`)
| Agent | Responsibility | Writes to |
|---|---|---|
| `requirements-analyst` | Analyze requirements; find ambiguities/assumptions/gaps; produce user stories, FR/NFR, acceptance criteria, traceability matrix. No code. | `docs/` |
| `solution-architect` | Architecture, modules, data model, SQLite schema, UI/service/DB interface contracts, implementation plan. No code. | `docs/` |
| `backend-developer` | Python business logic, validation, SQLite persistence (`sqlite3`), following approved contracts. | Backend service + database files |
| `frontend-developer` | Streamlit UI: forms, tables, filters, dashboards. Uses service interfaces only, no SQL. | UI files |
| `qa-engineer` | pytest tests, acceptance-criteria and edge-case verification, defect reports with evidence. Never silently edits production code. | `tests/`, test docs |
| `security-reviewer` | Review validation, SQL injection, secrets, permissions, insecure workflows; run available checks; severity-rated findings. Never claims a fix without retest. | `docs/security-review.md` |

## 4. Mandatory Delegation Rules
1. Requirements analysis -> `requirements-analyst`. Architecture/schema/contracts/plan -> `solution-architect`. Backend code -> `backend-developer`. UI code -> `frontend-developer`. Test creation/execution -> `qa-engineer`. Security review -> `security-reviewer`.
2. The orchestrator must invoke these via the real subagent mechanism (the Agent tool with the matching `subagent_type`), never by role-playing them in the main session.
3. If a configured agent is not discoverable, stop and report it (or fix the configuration); do not substitute the orchestrator or a generic agent without telling the user.
4. Every delegation brief must name the relevant FR/AC IDs, the input documents, the files the agent may touch, and the required report format.
5. Subagent results are claims, not facts: check that the files exist and that reported commands/tests really produced the stated results.
6. Defects go back to the agent that owns the file. QA and security re-verify after each fix.

## 5. Planning Before Coding
- No application code is written until requirements are analyzed and approved, the architecture, schema, interface contracts and implementation plan are documented in `docs/` and approved by the human.
- Implementation tasks must follow the approved implementation plan and contracts. Contract changes require going back to `solution-architect` and, for material changes, human approval.

## 6. Agent File Ownership Rules
- `requirements-analyst`, `solution-architect`: Markdown in `docs/` only.
- `backend-developer`: backend service and database files only, as listed in the implementation plan.
- `frontend-developer`: UI files only, as listed in the implementation plan.
- `qa-engineer`: `tests/`, pytest config, and QA documents in `docs/`. Never production code.
- `security-reviewer`: `docs/security-review.md` only. Never production code or tests.
- Orchestrator: `CLAUDE.md`, `.claude/`, repository housekeeping (`.gitignore`, `requirements.txt` after approval), and progress summaries.
- Two agents never edit the same file concurrently. Cross-ownership changes are requested through the orchestrator.

## 7. Testing and Quality Requirements
- Every acceptance criterion has at least one pytest test that references its AC/FR ID.
- Tests use isolated temporary SQLite databases, never real data.
- Edge cases required: invalid/empty/oversized input, special characters, invalid status transitions, duplicates, persistence across reconnects.
- All SQL uses parameterized queries; the UI contains no SQL.
- "Done" means tests were actually run and passed, with the command and output recorded in `docs/test-report.md`. No claim of passing without evidence.
- Security review is required before the final handover. Fixes must be retested before being called fixed.

## 8. Human Approval Checkpoints
The orchestrator must stop and wait for explicit human approval after:
1. Agent setup and verification.
2. Requirements, assumptions and acceptance criteria (open questions answered).
3. Architecture, schema, interface contracts and implementation plan.
4. Implementation, before QA sign-off.
5. QA and security-review results, and before any scope change.
6. Final handover.
Also ask before installing packages, deleting files, running destructive commands, pushing to git, or changing approved contracts.

## 9. Requirement Traceability Rules
- Every requirement has a stable ID (FR-xx, NFR-xx); every acceptance criterion has an ID (AC-xx) linked to its FR.
- Maintain `docs/traceability-matrix.md`: user story -> FR -> AC -> design element -> implementing file(s) -> test(s) -> status.
- Each agent updates the column it owns and cites IDs in docs, code comments where useful, test names and reports.
- No requirement without a test; no code or test without a requirement. Report gaps and orphans to the human.

## 10. Deployment Restriction
- NO cloud deployment, cloud resource creation, or external hosting without explicit human approval, given at the time of the action.
- Local development only by default. No external network services, remote databases or pushes to remote repositories unless explicitly approved.
- No secrets, credentials or real customer data in the repository.

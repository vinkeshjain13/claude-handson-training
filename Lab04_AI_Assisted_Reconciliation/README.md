# Lab 04 — Build a Banking Reconciliation Engine with Claude Code

Independent VS Code + Ubuntu project. **Students must develop the missing code**; the project is intentionally incomplete. Start with `LAB04_STUDENT.md`.

## Setup
```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m pytest -q
```
The starter intentionally fails implementation tests. Ask Claude Code to implement one milestone at a time. Your target is all tests passing and `python -m src.main` generating verified reports.

Synthetic transactions only. AI suggestions are never authoritative reconciliations or approvals.

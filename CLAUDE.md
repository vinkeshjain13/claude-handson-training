# Support Ticket Portal

Streamlit MVP that analyses a CSV of synthetic support tickets, fully offline.
- `app.py`: Streamlit UI only (uploader, metrics, category/priority charts, filterable table, CSV download).
- `src/ticket_logic.py`: pure, deterministic logic (`parse_csv`, `normalize_tickets`, `classify_ticket`, `analyze_tickets`, `draft_response`, `count_by`, `to_safe_csv`).
- `data/sample_tickets.csv`: 22 fictional tickets. Columns: `ticket_id`, `customer_message`, `created_at`.
- `docs/`: `architecture.md`, `requirements.md`, `implementation_status.md`. Read only as needed.
- Classification is keyword rules (category, priority, sentiment), not AI/ML. Replies are templates, never sent.

## Commands
- Test: `.venv/bin/python -m pytest` (28 tests; or `python -m pytest` with the venv active)
- Run: `.venv/bin/streamlit run app.py`

## Where things live
- Classification logic: `src/ticket_logic.py` (`classify_ticket`, keyword rules, category precedence).
- Tests: `tests/test_ticket_logic.py` (pure logic, no Streamlit, no network).

## Rules
- No external API calls, no LLM calls, no credentials or API keys. Keep it offline. Synthetic data only.
- Open targeted files; do not scan the whole repo (skip `.venv/`, `.pytest_cache/`, `__pycache__/`).
- Keep diffs narrow. Add or adjust tests with any logic change and run them.
- After each milestone, update `docs/implementation_status.md`.

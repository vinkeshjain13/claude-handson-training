# STUDENT LAB 04 — Build a BFSI Reconciliation Engine WITH Claude Code

**Duration:** ~75–90 minutes | **Environment:** Ubuntu + VS Code + Claude Code | **Standalone, independent of Labs 01–03**

## Your mission (the build, not a demo)
Your bank's internal ledger and settlement provider disagree. Deliver a working application that reads two CSVs, reconciles transaction references, flags exceptions, generates reports and optionally asks an LLM to *explain* verified discrepancies. The supplied functions deliberately raise `NotImplementedError`: **you must develop these using Claude Code as your coding partner**.

### Expected outcome (acceptance contract)
- 27 distinct references; **21 MATCHED, 6 exceptions**.
- Exception IDs: TX0008 and TX0012 (AMOUNT_MISMATCH), TX0019 (DATE_MISMATCH), TX0023 (DUPLICATE_TRANSACTION), TX0026 (MISSING_SETTLEMENT), TX0027 (MISSING_LEDGER).
- Generated `reports/reconciliation.csv`, `reports/exceptions.json`, `reports/summary.json`.
- No silent duplicate matching; monetary arithmetic uses `Decimal`, not `float`.
- LLM output cannot change the validated exception status or waive review.

## Stage 0 — Setup and deliberately observe broken starter (5 min)
1. Extract ZIP and open `Lab04_AI_Assisted_Reconciliation/` as an isolated VS Code folder.
2. In a **normal Ubuntu terminal**:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   python -m pip install -r requirements.txt
   python -m pytest -q tests/test_starter_health.py
   python -m pytest -q tests/test_reconciliation.py
   ```
3. The health checks must **pass**. Acceptance tests must **fail with NotImplementedError**. This is intentional. Don't delete or weaken tests.
4. Optional baseline: `git init && git add . && git commit -m "Lab04 starter"` (configure Git username/email if needed).
5. Start Claude Code from project root: `claude`.

## Stage 1 — YOU build validated CSV reading (10–12 min)
1. Open `data/internal_ledger.csv`, `data/settlement_statement.csv` and `src/data_loader.py`.
2. Ask Claude Code:
   > Inspect both CSV datasets and `tests/test_reconciliation.py`. Implement ONLY `load_transactions()` in `src/data_loader.py`. Use `csv.DictReader`, ISO date checks, positive finite Decimal amounts (maximum 2 decimals), INR currency and clear line-level errors. Do not modify data or tests. Show the implementation diff and run targeted loader tests.
3. **Review the generated code**: Is a `float` conversion hidden? Does it reject `NaN`, extra decimals and blank IDs?
4. Run: `python -m pytest -q tests/test_reconciliation.py -k "invalid_money or no_float_money"`.
5. Ask Claude to fix failures in this module only. Checkpoint with `git diff`.

## Stage 2 — YOU build the reconciliation engine (20 min)
1. Open `src/reconciliation.py` and the acceptance tests.
2. Ask Claude Code:
   > Implement ONLY `reconcile()` and `summary()` in `src/reconciliation.py` based on test expectations. Index each side by transaction ID; process sorted union. Priority: duplicate IDs, missing ledger/settlement, identity or amount mismatch, date mismatch, matched. Never silently pick one duplicate. Compute amount differences with Decimal and serialize as strings. Return all expected fields. Do not change tests or input CSVs. Run focused tests and explain the result.
3. Run:
   ```bash
   python -m pytest -q tests/test_reconciliation.py -k "counts or specifics or duplicate"
   python -m pytest -q tests/test_acceptance_edge_cases.py -k "amount or identity or duplicate"
   ```
4. Verify expected IDs and discuss why **reconciliation is deterministic**, not an LLM decision.
5. **Improvisation challenge:** ask Claude to identify edge cases not covered by the dataset; choose one and write an additional test before implementing it.

## Stage 3 — YOU build the reporting layer (10 min)
1. Open `src/reporting.py` and `src/main.py`.
2. Prompt:
   > Implement ONLY `save_reports()` in `src/reporting.py`. Write `reconciliation.csv`, `exceptions.json`, `summary.json` to a configurable folder, with deterministic data from `summary()`. Keep JSON human-readable and support empty inputs. Do not edit tests. Run report tests.
3. Run:
   ```bash
   python -m pytest -q tests/test_reconciliation.py -k report
   python -m src.main
   cat reports/summary.json
   ```
4. Open the generated files in VS Code. Validate 21 matches and six exceptions.

## Stage 4 — YOU develop safe AI triage (15–20 min)
1. Review `src/models.py` (Pydantic schema) and starter `src/triage.py`.
2. Prompt:
   > Implement `_parse()` in `src/triage.py`. Parse JSON (including optional ```json fences), validate ExceptionTriage with Pydantic, reject wrong transaction_id or classification, and reject requires_human_review=false. Never change deterministic reconciliation facts. Keep tests unchanged; run the LLM safety tests.
3. Run:
   ```bash
   python -m pytest -q tests/test_reconciliation.py -k llm
   python -m pytest -q tests/test_acceptance_edge_cases.py -k triage
   ```
4. Prompt:
   > Implement `triage_exception()` in `src/triage.py` supporting OpenRouter chat/completions using httpx and Anthropic Direct messages. Load keys from .env only at runtime; do not print secrets. Use SYSTEM as a grounding instruction and always validate provider responses using `_parse()`. Do not edit tests. Explain which parameters are gateway-specific.
5. Optional **live** integration (requires valid key, charges may apply): `cp .env.example .env`, edit locally, then run `python -m src.main --triage --provider openrouter`. Alternative `--provider anthropic`. Offline pipeline runs without keys.
6. **Prompt-injection exercise:** Ask Claude to test a fabricated model response that claims `MATCHED` or says `requires_human_review=false`; the parser must reject it.

## Stage 5 — Integration and demo (10 min)
1. `python -m pytest -q` — all tests should pass.
2. `python -m src.main` — inspect `reports/` in VS Code.
3. Prompt Claude Code:
   > Review my implementation for arithmetic precision, duplicate handling, status priority, tests, and prevention of LLM reclassification. Report remaining gaps with evidence; only modify code after I approve your plan.
4. Show your instructor: (a) `git diff`, (b) tests passing, (c) generated CSV/JSON reports, (d) one improvement you made after Claude's first answer.

## Debugging tips
- `NotImplementedError` means a feature is still unbuilt, not a broken environment.
- Run Claude Code from the **project directory** and explicitly name the module to change.
- If tests fail, ask Claude to diagnose a specific traceback; do not instruct it to edit acceptance tests.
- Money uses `Decimal`; `float` can introduce precision surprises.
- Offline tests need no API key. API failures and credential costs apply only to the optional live triage.
- There is no MCP dependency in this lab; you are developing Python software **with** Claude Code.

## Deliverable
One working reconciler, a full passing pytest run, generated evidence files, and a brief reflection on what you changed, tested, and improved.

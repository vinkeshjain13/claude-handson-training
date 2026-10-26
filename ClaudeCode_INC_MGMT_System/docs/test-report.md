# Test Report (pointer)

The full test report, including environment, exact commands with real output, the AC-01..AC-81 coverage table, defects (DEF-01..DEF-03), the real-data safety evidence and the retest record, is in:

**`reports/test-report.md`** (location specified by the human; `CLAUDE.md` section 7 names `docs/test-report.md`, so this file points there).

Current state: QA cycle 1 (fix + retest), 2026-10-24. 879 tests collected: 879 passed, 0 failed, 0 errors, 0 skipped (692 cycle 0 tests plus 187 new regression cases in `tests/test_cycle1_regressions.py`). The 14 cycle 0 failures (DEF-01, DEF-02, DEF-03) now pass. `ruff check .` clean. `data/tickets.db` unchanged by the run (SHA-256 `bd44ab5d...bc207e`). Open: manual items in `docs/manual-test-checklist.md` (not yet executed) and doc drift listed in section C7 of the report (including that NUL text is now rejected, which `docs/validation-rules.md` does not yet say). The cycle 0 record is kept in the same file.

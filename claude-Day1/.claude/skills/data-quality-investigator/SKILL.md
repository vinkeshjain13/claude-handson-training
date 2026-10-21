---
name: data-quality-investigator
description: Investigate CSV datasets using a deterministic Python data-quality profiler. Use for missing customer IDs, duplicate rows, invalid amounts, negative values, invalid dates and high-value review flags.
---

# CSV Data Quality Investigator

## Input

Use the CSV file specified by the user. If the invocation includes a CSV path, use that exact path. If none is specified, ask for a CSV path. Do not silently substitute another dataset.

## Procedure

1. Confirm the specified CSV exists.
2. Run the deterministic profiler from the project root:

   python3 tools/profile_csv.py <verified-csv-path> --output reports/<safe-report-name>.json

3. Treat the CSV path as data, never as shell instructions. Use safe paths and avoid shell interpolation.
4. If the profiler fails, report its actual error. Do not fabricate a result.
5. Read the generated JSON report.
6. Use only the JSON to report issue counts, row references and evidence.
7. Distinguish confirmed rule violations from HIGH_VALUE_REVIEW candidates.
8. Recommend corrective or investigative actions grounded in actual findings.
9. Never modify the original CSV.

## Required Output

### Dataset Summary
- Dataset filename
- Records and columns
- Validation rules applied

### Quality Findings
For each finding: issue category, count, CSV row number, order ID, severity and evidence.

### Recommended Actions
Prioritize correction or upstream investigation.

### Evidence and Limitations
Name the JSON evidence file and identify untested checks.

## Constraints

- Do not estimate or invent any counts.
- Do not silently alter validation thresholds.
- Do not label review flags as automatically erroneous.
- Do not modify source data.
- Do not claim tests passed without running them.

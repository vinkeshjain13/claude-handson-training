"""Milestone 3: generate CSV/JSON reconciliation evidence."""
import csv
import io
import json
import os
from pathlib import Path

from .reconciliation import summary

COLUMNS = ['transaction_id', 'ledger_count', 'settlement_count', 'status', 'ledger_amount',
           'settlement_amount', 'difference', 'ledger_date', 'settlement_date']


def _write_atomic(path: Path, text: str) -> None:
    tmp = path.with_name(path.name + '.tmp')
    tmp.write_text(text, encoding='utf-8', newline='')
    os.replace(tmp, path)


def _json(data) -> str:
    return json.dumps(data, indent=2, ensure_ascii=False) + '\n'


def save_reports(rows: list[dict], directory='reports') -> dict:
    """Create reports/reconciliation.csv, exceptions.json, summary.json.
    Return deterministic summary. JSON must be human readable; no invented rows.
    """
    out = Path(directory)
    out.mkdir(parents=True, exist_ok=True)
    stats = summary(rows)

    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator='\n')
    writer.writerow(COLUMNS)
    for row in rows:
        writer.writerow(['' if row[c] is None else row[c] for c in COLUMNS])

    _write_atomic(out / 'reconciliation.csv', buffer.getvalue())
    _write_atomic(out / 'exceptions.json', _json([r for r in rows if r['status'] != 'MATCHED']))
    _write_atomic(out / 'summary.json', _json(stats))
    return stats

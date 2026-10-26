"""Deterministic CSV data-quality profiler for order data (standard library only)."""
import argparse
import csv
import json
import re
import sys
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path

REQUIRED_COLUMNS = ["order_id", "customer_id", "amount", "order_date", "status"]
ISSUE_TYPES = [
    "MISSING_CUSTOMER_ID",
    "DUPLICATE_RECORD",
    "INVALID_AMOUNT",
    "NEGATIVE_AMOUNT",
    "INVALID_DATE",
    "HIGH_VALUE_REVIEW",
]
DATE_PATTERN = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}")


def _parse_amount(text):
    """Return a finite Decimal, or None if the text is not a valid finite number."""
    text = text.strip()
    if not text or not text.isascii() or "_" in text:
        return None
    try:
        value = Decimal(text)
    except InvalidOperation:
        return None
    return value if value.is_finite() else None


def _valid_date(text):
    text = text.strip()
    if not DATE_PATTERN.fullmatch(text):
        return False
    try:
        date(int(text[:4]), int(text[5:7]), int(text[8:10]))
    except ValueError:
        return False
    return True


def profile_csv(path, high_value_threshold="50000"):
    """Profile an orders CSV and return a JSON-serializable dict."""
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(f"Input CSV not found: {path}")

    try:
        threshold = Decimal(str(high_value_threshold))
    except InvalidOperation:
        raise ValueError(f"Invalid high_value_threshold: {high_value_threshold!r}") from None
    if not threshold.is_finite():
        raise ValueError(f"Invalid high_value_threshold: {high_value_threshold!r}")

    issues = []
    counts = {name: 0 for name in ISSUE_TYPES}

    def add(issue_type, row_number, order_id, severity, evidence):
        counts[issue_type] += 1
        issues.append(
            {
                "type": issue_type,
                "row_number": row_number,
                "order_id": order_id,
                "severity": severity,
                "evidence": evidence,
            }
        )

    total = 0
    seen = {}
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.reader(handle)
        header = next(reader, None)
        columns = [name.strip() for name in header] if header else []
        missing = [name for name in REQUIRED_COLUMNS if name not in columns]
        if missing:
            raise ValueError(f"Missing required columns: {', '.join(missing)}")
        index = {name: columns.index(name) for name in REQUIRED_COLUMNS}

        previous_line = reader.line_num
        for cells in reader:
            row_number = previous_line + 1
            previous_line = reader.line_num
            if not cells:
                continue
            total += 1

            def cell(name):
                position = index[name]
                return cells[position] if position < len(cells) else ""

            order_id = cell("order_id").strip()

            if not cell("customer_id").strip():
                add("MISSING_CUSTOMER_ID", row_number, order_id, "error",
                    "customer_id is empty")

            key = tuple(cells)
            if key in seen:
                add("DUPLICATE_RECORD", row_number, order_id, "error",
                    f"Exact duplicate of row {seen[key]}")
            else:
                seen[key] = row_number

            raw_amount = cell("amount")
            amount = _parse_amount(raw_amount)
            if amount is None:
                add("INVALID_AMOUNT", row_number, order_id, "error",
                    f"amount {raw_amount!r} is not a valid finite number")
            else:
                if amount < 0:
                    add("NEGATIVE_AMOUNT", row_number, order_id, "error",
                        f"amount {raw_amount.strip()} is negative")
                if amount > threshold:
                    add("HIGH_VALUE_REVIEW", row_number, order_id, "review",
                        f"amount {raw_amount.strip()} exceeds threshold {threshold}")

            raw_date = cell("order_date")
            if not _valid_date(raw_date):
                add("INVALID_DATE", row_number, order_id, "error",
                    f"order_date {raw_date!r} is not a valid YYYY-MM-DD calendar date")

    issues.sort(key=lambda item: (item["row_number"], ISSUE_TYPES.index(item["type"])))
    return {
        "dataset": path.name,
        "total_records": total,
        "columns": columns,
        "rules": {
            "required_columns": REQUIRED_COLUMNS,
            "high_value_threshold": str(threshold),
            "high_value_is_error": False,
            "date_format": "YYYY-MM-DD",
            "duplicate_rule": "exact match on all fields; every additional occurrence counted",
            "row_number_includes_header": True,
        },
        "issue_counts": counts,
        "issues": issues,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description="Profile an orders CSV for data-quality issues.")
    parser.add_argument("input", help="Path to the CSV file")
    parser.add_argument("--output", help="Path for the JSON report (default: stdout)")
    parser.add_argument("--high-value-threshold", default="50000",
                        help="Amounts above this are flagged HIGH_VALUE_REVIEW (default: 50000)")
    args = parser.parse_args(argv)

    try:
        report = profile_csv(args.input, args.high_value_threshold)
    except (FileNotFoundError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1

    text = json.dumps(report, indent=2) + "\n"
    if args.output:
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(text, encoding="utf-8")
    else:
        sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())

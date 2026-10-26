"""Milestone 1: CSV loader. Implement using Claude Code, then review the diff."""
import csv
import re
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path
FIELDS = {'transaction_id','amount','settlement_date','currency','account_ref'}

_DATE_RE = re.compile(r'[0-9]{4}-[0-9]{2}-[0-9]{2}')
_AMOUNT_RE = re.compile(r'[0-9]+(\.[0-9]+)?')


def _parse_amount(text: str) -> Decimal:
    try:
        amount = Decimal(text)
    except InvalidOperation:
        raise ValueError(f'invalid amount {text!r}') from None
    if not amount.is_finite():
        raise ValueError(f'amount must be finite, got {text!r}')
    if amount <= 0:
        raise ValueError(f'amount must be positive, got {text!r}')
    if not _AMOUNT_RE.fullmatch(text):
        raise ValueError(f'amount must be plain decimal notation, got {text!r}')
    if amount.as_tuple().exponent < -2:
        raise ValueError(f'amount allows at most 2 decimal places, got {text!r}')
    return amount


def _parse_date(text: str) -> str:
    if not _DATE_RE.fullmatch(text):
        raise ValueError(f'settlement_date must be YYYY-MM-DD, got {text!r}')
    try:
        date.fromisoformat(text)
    except ValueError:
        raise ValueError(f'settlement_date is not a real date: {text!r}') from None
    return text


def load_transactions(path: str | Path) -> list[dict]:
    """Return validated rows with Decimal amounts.

    Requirements:
    - UTF-8-SIG CSV; required headers; clear file/line errors.
    - Reject empty IDs/account refs, non-INR, non-ISO dates, NaN/Infinity,
      zero/negative amounts and >2 decimal places.
    - Do NOT convert money to float.
    """
    path = Path(path)
    rows: list[dict] = []
    with path.open(newline='', encoding='utf-8-sig') as handle:
        reader = csv.DictReader(handle)
        headers = [h.strip() for h in reader.fieldnames or []]
        if not headers:
            raise ValueError(f'{path}: file is empty or has no header row')
        if len(set(headers)) != len(headers):
            raise ValueError(f'{path}: duplicate column headers')
        missing = FIELDS - set(headers)
        if missing:
            raise ValueError(f'{path}: missing required columns {sorted(missing)}')
        reader.fieldnames = headers

        for record in reader:
            where = f'{path}:{reader.line_num}'
            if None in record or None in record.values():
                raise ValueError(f'{where}: row has wrong number of columns')
            values = {k: record[k].strip() for k in FIELDS}
            try:
                if not values['transaction_id']:
                    raise ValueError('transaction_id is empty')
                if not values['account_ref']:
                    raise ValueError('account_ref is empty')
                if values['currency'] != 'INR':
                    raise ValueError(f"currency must be INR, got {values['currency']!r}")
                rows.append({
                    'transaction_id': values['transaction_id'],
                    'amount': _parse_amount(values['amount']),
                    'settlement_date': _parse_date(values['settlement_date']),
                    'currency': values['currency'],
                    'account_ref': values['account_ref'],
                })
            except ValueError as exc:
                raise ValueError(f'{where}: {exc}') from None
    return rows

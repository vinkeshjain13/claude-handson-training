"""Milestone 2: implement deterministic reconciliation and summary."""
from collections import defaultdict
from decimal import Context, Decimal, Inexact, InvalidOperation

EXCEPTION_STATUSES = {'AMOUNT_MISMATCH','MISSING_SETTLEMENT','MISSING_LEDGER','DUPLICATE_TRANSACTION','DATE_MISMATCH'}

# Raises instead of silently rounding if a value ever exceeds 50 digits.
_CTX = Context(prec=50, traps=[InvalidOperation, Inexact])
_CENTS = Decimal('0.01')


def _money(value: Decimal) -> str:
    return str(_CTX.quantize(value, _CENTS))


def _index(rows: list[dict]) -> dict[str, list[dict]]:
    index = defaultdict(list)
    for row in rows:
        index[row['transaction_id']].append(row)
    return index


def reconcile(ledger: list[dict], settlement: list[dict]) -> list[dict]:
    """Match union of transaction IDs deterministically and return sorted rows.
    Status priority: duplicate, missing side, identity/amount mismatch, date mismatch, matched.
    Difference is ledger minus settlement with Decimal arithmetic; serialize to str.
    Keep expected keys: transaction_id, ledger_count, settlement_count, status,
    ledger_amount, settlement_amount, difference, ledger_date, settlement_date.
    For duplicate references, never silently choose one record or calculate difference.
    """
    ledger_index, settlement_index = _index(ledger), _index(settlement)
    results = []
    for tx_id in sorted(set(ledger_index) | set(settlement_index)):
        l_rows, s_rows = ledger_index.get(tx_id, []), settlement_index.get(tx_id, [])
        l_row = l_rows[0] if len(l_rows) == 1 else None
        s_row = s_rows[0] if len(s_rows) == 1 else None
        difference = None

        if len(l_rows) > 1 or len(s_rows) > 1:
            status = 'DUPLICATE_TRANSACTION'
            l_row = s_row = None
        elif not l_rows:
            status = 'MISSING_LEDGER'
        elif not s_rows:
            status = 'MISSING_SETTLEMENT'
        else:
            difference = _money(_CTX.subtract(l_row['amount'], s_row['amount']))
            if (l_row['amount'] != s_row['amount']
                    or l_row['account_ref'] != s_row['account_ref']
                    or l_row['currency'] != s_row['currency']):
                status = 'AMOUNT_MISMATCH'
            elif l_row['settlement_date'] != s_row['settlement_date']:
                status = 'DATE_MISMATCH'
            else:
                status = 'MATCHED'

        results.append({
            'transaction_id': tx_id,
            'ledger_count': len(l_rows),
            'settlement_count': len(s_rows),
            'status': status,
            'ledger_amount': _money(l_row['amount']) if l_row else None,
            'settlement_amount': _money(s_row['amount']) if s_row else None,
            'difference': difference,
            'ledger_date': l_row['settlement_date'] if l_row else None,
            'settlement_date': s_row['settlement_date'] if s_row else None,
        })
    return results


def summary(rows: list[dict]) -> dict:
    """Return unique_references, matched, exceptions, by_status (sorted dictionary)."""
    by_status: dict[str, int] = defaultdict(int)
    for row in rows:
        by_status[row['status']] += 1
    matched = by_status.get('MATCHED', 0)
    return {
        'unique_references': len({row['transaction_id'] for row in rows}),
        'matched': matched,
        'exceptions': sum(by_status.values()) - matched,
        'by_status': dict(sorted(by_status.items())),
    }

import copy
import json
from decimal import Decimal
from src.reconciliation import reconcile, summary


def tx(i, amt='100.00', day='2026-10-23', account='A1', currency='INR'):
    return {'transaction_id': i, 'amount': Decimal(amt), 'settlement_date': day,
            'currency': currency, 'account_ref': account}


def one(ledger, settlement):
    result = reconcile(ledger, settlement)
    assert len(result) == 1
    return result[0]


def test_exact_match_row_shape():
    assert one([tx('X')], [tx('X')]) == {
        'transaction_id': 'X', 'ledger_count': 1, 'settlement_count': 1, 'status': 'MATCHED',
        'ledger_amount': '100.00', 'settlement_amount': '100.00', 'difference': '0.00',
        'ledger_date': '2026-10-23', 'settlement_date': '2026-10-23'}


def test_difference_sign_is_ledger_minus_settlement():
    assert one([tx('X', '2000.00')], [tx('X', '1700.00')])['difference'] == '300.00'
    assert one([tx('X', '2500.00')], [tx('X', '2600.00')])['difference'] == '-100.00'


def test_amounts_normalised_to_two_places_and_equal_values_match():
    row = one([tx('X', '100')], [tx('X', '100.0')])
    assert row['status'] == 'MATCHED' and row['ledger_amount'] == row['settlement_amount'] == '100.00'


def test_float_trap_amounts_are_exact():
    assert one([tx('X', '0.30')], [tx('X', '0.10')])['difference'] == '0.20'
    assert one([tx('X', '1000000000000000000.10')], [tx('X', '1000000000000000000.09')])['difference'] == '0.01'


def test_amount_beats_date_in_priority():
    assert one([tx('X', '5.00', day='2026-10-23')], [tx('X', '6.00', day='2026-10-24')])['status'] == 'AMOUNT_MISMATCH'


def test_date_mismatch_only():
    row = one([tx('X')], [tx('X', day='2026-10-24')])
    assert row['status'] == 'DATE_MISMATCH' and row['difference'] == '0.00'


def test_identity_mismatch_is_amount_mismatch_status_with_zero_difference():
    assert one([tx('X', account='A1')], [tx('X', account='A2')])['status'] == 'AMOUNT_MISMATCH'
    assert one([tx('X')], [tx('X', currency='USD')])['status'] == 'AMOUNT_MISMATCH'


def test_missing_sides():
    ms = one([tx('X')], [])
    assert (ms['status'], ms['ledger_count'], ms['settlement_count']) == ('MISSING_SETTLEMENT', 1, 0)
    assert ms['settlement_amount'] is None and ms['difference'] is None and ms['settlement_date'] is None
    ml = one([], [tx('X')])
    assert ml['status'] == 'MISSING_LEDGER' and ml['ledger_amount'] is None and ml['difference'] is None


def test_duplicates_every_shape_are_ambiguous():
    for ledger, settlement in [([tx('X'), tx('X')], [tx('X')]),
                               ([tx('X')], [tx('X'), tx('X')]),
                               ([tx('X'), tx('X')], [tx('X'), tx('X')]),
                               ([tx('X'), tx('X')], []),
                               ([], [tx('X'), tx('X', '9.00')]),
                               ([tx('X'), tx('X', '7.00')], [tx('X')])]:
        row = one(ledger, settlement)
        assert row['status'] == 'DUPLICATE_TRANSACTION'
        assert row['ledger_count'] == len(ledger) and row['settlement_count'] == len(settlement)
        assert row['difference'] is None
        assert row['ledger_amount'] is None and row['settlement_amount'] is None
        assert row['ledger_date'] is None and row['settlement_date'] is None


def test_output_sorted_union_independent_of_input_order():
    a = reconcile([tx('B'), tx('A')], [tx('C'), tx('B')])
    b = reconcile([tx('A'), tx('B')], [tx('B'), tx('C')])
    assert a == b and [r['transaction_id'] for r in a] == ['A', 'B', 'C']
    assert [r['status'] for r in a] == ['MISSING_SETTLEMENT', 'MATCHED', 'MISSING_LEDGER']


def test_inputs_not_mutated_and_output_is_json_serialisable():
    ledger, settlement = [tx('A'), tx('B', '2.00')], [tx('A', '3.00')]
    before = copy.deepcopy((ledger, settlement))
    rows = reconcile(ledger, settlement)
    assert (ledger, settlement) == before
    json.dumps(rows)


def test_empty_inputs():
    assert reconcile([], []) == []
    assert summary([]) == {'unique_references': 0, 'matched': 0, 'exceptions': 0, 'by_status': {}}


def test_summary_counts_and_sorted_keys():
    rows = reconcile([tx('A'), tx('B', '2.00'), tx('C')], [tx('A'), tx('B', '3.00'), tx('D')])
    s = summary(rows)
    assert s == {'unique_references': 4, 'matched': 1, 'exceptions': 3,
                 'by_status': {'AMOUNT_MISMATCH': 1, 'MATCHED': 1, 'MISSING_LEDGER': 1, 'MISSING_SETTLEMENT': 1}}
    assert list(s['by_status']) == sorted(s['by_status'])

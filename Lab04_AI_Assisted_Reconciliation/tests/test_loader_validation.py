from decimal import Decimal
import pytest
from src.data_loader import load_transactions

HEADER = 'transaction_id,amount,settlement_date,currency,account_ref\n'


def write(tmp_path, body, header=HEADER, encoding='utf-8'):
    p = tmp_path / 'x.csv'
    p.write_bytes((header + body).encode(encoding))
    return p


def test_valid_row_and_types(tmp_path):
    rows = load_transactions(write(tmp_path, ' A1 ,100.10,2026-10-23,INR,AC01\n'))
    assert rows == [{'transaction_id': 'A1', 'amount': Decimal('100.10'), 'settlement_date': '2026-10-23',
                     'currency': 'INR', 'account_ref': 'AC01'}]
    assert type(rows[0]['amount']) is Decimal


def test_bom_header_only_and_duplicates_allowed(tmp_path):
    assert load_transactions(write(tmp_path, '', encoding='utf-8-sig')) == []
    rows = load_transactions(write(tmp_path, 'A,1.00,2026-10-23,INR,AC1\nA,1.00,2026-10-23,INR,AC1\n'))
    assert len(rows) == 2


def test_real_datasets_counts():
    assert len(load_transactions('data/internal_ledger.csv')) == 26
    assert len(load_transactions('data/settlement_statement.csv')) == 27


@pytest.mark.parametrize('amount', [
    'NaN', 'sNaN', 'Infinity', '-Infinity', '0', '0.00', '-5.00', '100.001', '100.000',
    '1E+2', '+5.00', '1_000.00', '1,000.00', '', 'abc', '١٢٣.٠٠',
])
def test_bad_amounts_rejected(tmp_path, amount):
    with pytest.raises(ValueError, match=r'x\.csv:2'):
        load_transactions(write(tmp_path, f'A,{amount},2026-10-23,INR,AC1\n'))


@pytest.mark.parametrize('day', ['2026-13-01', '2026-02-30', '20261023', '23-10-2026', '2026-1-1', '', '２０２６-10-23'])
def test_bad_dates_rejected(tmp_path, day):
    with pytest.raises(ValueError, match='settlement_date'):
        load_transactions(write(tmp_path, f'A,1.00,{day},INR,AC1\n'))


@pytest.mark.parametrize('row', [
    ',1.00,2026-10-23,INR,AC1',
    '   ,1.00,2026-10-23,INR,AC1',
    'A,1.00,2026-10-23,INR,',
    'A,1.00,2026-10-23,USD,AC1',
    'A,1.00,2026-10-23,inr,AC1',
    'A,1.00,2026-10-23,INR',
    'A,1.00,2026-10-23,INR,AC1,extra',
])
def test_bad_rows_rejected(tmp_path, row):
    with pytest.raises(ValueError, match=r'x\.csv:2'):
        load_transactions(write(tmp_path, row + '\n'))


def test_error_reports_correct_line(tmp_path):
    body = 'A,1.00,2026-10-23,INR,AC1\nB,2.00,2026-10-23,INR,AC1\nC,bad,2026-10-23,INR,AC1\n'
    with pytest.raises(ValueError, match=r'x\.csv:4'):
        load_transactions(write(tmp_path, body))


def test_header_problems(tmp_path):
    with pytest.raises(ValueError, match='missing required columns'):
        load_transactions(write(tmp_path, '', header='transaction_id,amount\n'))
    with pytest.raises(ValueError, match='duplicate column'):
        load_transactions(write(tmp_path, '', header=HEADER.strip() + ',amount\n'))
    p = tmp_path / 'empty.csv'
    p.write_text('')
    with pytest.raises(ValueError, match='empty'):
        load_transactions(p)

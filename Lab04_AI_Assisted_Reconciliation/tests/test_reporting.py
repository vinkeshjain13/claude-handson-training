import csv
import json
import subprocess
import sys
from src.data_loader import load_transactions
from src.reconciliation import reconcile
from src.reporting import COLUMNS, save_reports

EXPECTED_EXCEPTIONS = ['TX0008', 'TX0012', 'TX0019', 'TX0023', 'TX0026', 'TX0027']


def sample():
    return reconcile(load_transactions('data/internal_ledger.csv'), load_transactions('data/settlement_statement.csv'))


def test_three_files_with_expected_content(tmp_path):
    rows = sample()
    stats = save_reports(rows, tmp_path)
    assert sorted(p.name for p in tmp_path.iterdir()) == ['exceptions.json', 'reconciliation.csv', 'summary.json']

    assert json.loads((tmp_path / 'summary.json').read_text()) == stats
    assert stats['unique_references'] == 27 and stats['matched'] == 21 and stats['exceptions'] == 6

    exceptions = json.loads((tmp_path / 'exceptions.json').read_text())
    assert [e['transaction_id'] for e in exceptions] == EXPECTED_EXCEPTIONS
    assert all(e['status'] != 'MATCHED' for e in exceptions)

    with open(tmp_path / 'reconciliation.csv', newline='') as fh:
        table = list(csv.DictReader(fh))
    assert list(table[0]) == COLUMNS and len(table) == 27
    by_id = {r['transaction_id']: r for r in table}
    assert by_id['TX0008']['difference'] == '300.00'
    assert by_id['TX0023']['difference'] == '' and by_id['TX0023']['ledger_amount'] == ''
    assert by_id['TX0023']['settlement_count'] == '2'


def test_json_is_human_readable(tmp_path):
    save_reports(sample(), tmp_path)
    text = (tmp_path / 'summary.json').read_text()
    assert text.startswith('{\n  "unique_references": 27') and text.endswith('}\n')


def test_deterministic_bytes_and_overwrites_stale_files(tmp_path):
    save_reports(sample(), tmp_path)
    first = {p.name: p.read_bytes() for p in tmp_path.iterdir()}
    (tmp_path / 'exceptions.json').write_text('stale')
    save_reports(sample(), tmp_path)
    assert {p.name: p.read_bytes() for p in tmp_path.iterdir()} == first


def test_creates_nested_directory_and_accepts_str(tmp_path):
    target = tmp_path / 'a' / 'b'
    save_reports(sample(), str(target))
    assert (target / 'summary.json').exists()


def test_empty_input(tmp_path):
    stats = save_reports([], tmp_path)
    assert stats == {'unique_references': 0, 'matched': 0, 'exceptions': 0, 'by_status': {}}
    assert (tmp_path / 'reconciliation.csv').read_text() == ','.join(COLUMNS) + '\n'
    assert json.loads((tmp_path / 'exceptions.json').read_text()) == []
    assert json.loads((tmp_path / 'summary.json').read_text()) == stats


def test_all_matched_has_empty_exceptions(tmp_path):
    rows = [r for r in sample() if r['status'] == 'MATCHED']
    save_reports(rows, tmp_path)
    assert json.loads((tmp_path / 'exceptions.json').read_text()) == []


def test_no_rows_invented_or_inputs_mutated(tmp_path):
    rows = sample()[:3]
    snapshot = [dict(r) for r in rows]
    save_reports(rows, tmp_path)
    assert rows == snapshot
    with open(tmp_path / 'reconciliation.csv', newline='') as fh:
        assert len(list(csv.DictReader(fh))) == 3


def test_main_end_to_end(tmp_path):
    result = subprocess.run([sys.executable, '-m', 'src.main', '--output', str(tmp_path)],
                            capture_output=True, text=True, check=True)
    assert json.loads(result.stdout)['matched'] == 21
    assert not (tmp_path / 'triage.json').exists()

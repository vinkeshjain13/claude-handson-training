from pathlib import Path

def test_csv_fixtures_present():
    assert Path('data/internal_ledger.csv').exists()
    assert Path('data/settlement_statement.csv').exists()

def test_project_has_all_implementation_modules():
    for name in ['data_loader','reconciliation','reporting','triage','main']:
        assert Path(f'src/{name}.py').exists()

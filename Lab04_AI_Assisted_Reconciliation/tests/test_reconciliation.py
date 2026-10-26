from pathlib import Path
from decimal import Decimal
from src.data_loader import load_transactions
from src.reconciliation import reconcile,summary
from src.reporting import save_reports
from src.triage import _parse
import json,pytest

def sample():
    return reconcile(load_transactions('data/internal_ledger.csv'),load_transactions('data/settlement_statement.csv'))

def test_counts():
    s=summary(sample());assert s['unique_references']==27;assert s['matched']==21;assert s['exceptions']==6
    assert s['by_status']=={'AMOUNT_MISMATCH':2,'DATE_MISMATCH':1,'DUPLICATE_TRANSACTION':1,'MATCHED':21,'MISSING_LEDGER':1,'MISSING_SETTLEMENT':1}

def test_specifics():
    r={x['transaction_id']:x for x in sample()}
    assert r['TX0008']['status']=='AMOUNT_MISMATCH'
    assert r['TX0012']['status']=='AMOUNT_MISMATCH'
    assert r['TX0019']['status']=='DATE_MISMATCH'
    assert r['TX0023']['status']=='DUPLICATE_TRANSACTION'
    assert r['TX0026']['status']=='MISSING_SETTLEMENT'
    assert r['TX0027']['status']=='MISSING_LEDGER'

def test_no_float_money():
    rows=load_transactions('data/internal_ledger.csv');assert all(isinstance(r['amount'],Decimal) for r in rows)

def test_duplicate_not_silently_matched():
    r={x['transaction_id']:x for x in sample()};assert r['TX0023']['difference'] is None

def test_report(tmp_path):
    stats=save_reports(sample(),tmp_path);assert (tmp_path/'exceptions.json').exists();assert len(json.loads((tmp_path/'exceptions.json').read_text()))==6

def test_llm_cannot_change_status():
    e={'transaction_id':'TX0008','status':'AMOUNT_MISMATCH'}
    payload={'transaction_id':'TX0008','classification':'MATCHED','possible_causes':['fee'],'recommended_action':'check documentation','requires_human_review':True}
    with pytest.raises(Exception):_parse(json.dumps(payload),e)

def test_llm_cannot_waive_review():
    e={'transaction_id':'TX0008','status':'AMOUNT_MISMATCH'}
    payload={'transaction_id':'TX0008','classification':'AMOUNT_MISMATCH','possible_causes':['fee'],'recommended_action':'check documentation','requires_human_review':False}
    with pytest.raises(Exception):_parse(json.dumps(payload),e)

def test_invalid_money(tmp_path):
    p=tmp_path/'x.csv';p.write_text('transaction_id,amount,settlement_date,currency,account_ref\nA,NaN,2026-10-23,INR,AC01\n')
    with pytest.raises(ValueError):load_transactions(p)

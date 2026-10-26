import pytest
from decimal import Decimal
from src.reconciliation import reconcile
from src.triage import _parse
import json

def tx(i,amt='100.00',day='2026-10-23',account='A1'):
    return {'transaction_id':i,'amount':Decimal(amt),'settlement_date':day,'currency':'INR','account_ref':account}

def test_amount_difference_is_exact():
    result=reconcile([tx('X','100.10')],[tx('X','99.99')]);assert result[0]['difference']=='0.11'

def test_identity_mismatch_not_match():
    result=reconcile([tx('X',account='A1')],[tx('X',account='A2')]);assert result[0]['status']!='MATCHED'

def test_duplicate_is_ambiguous_even_if_equal():
    result=reconcile([tx('X'),tx('X')],[tx('X')]);assert result[0]['status']=='DUPLICATE_TRANSACTION' and result[0]['difference'] is None

def test_valid_triage_remains_reviewable():
    exception={'transaction_id':'X','status':'AMOUNT_MISMATCH'}
    data={'transaction_id':'X','classification':'AMOUNT_MISMATCH','possible_causes':['Hypothesis only'],'recommended_action':'Check settlement evidence','requires_human_review':True,'missing_evidence':['fee ledger']}
    assert _parse(json.dumps(data),exception)['requires_human_review'] is True

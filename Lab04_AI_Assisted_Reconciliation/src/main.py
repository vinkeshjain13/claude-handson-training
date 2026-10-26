import argparse,json
from pathlib import Path
from .data_loader import load_transactions
from .reconciliation import reconcile
from .reporting import save_reports

def run():
    parser=argparse.ArgumentParser()
    parser.add_argument('--ledger',default='data/internal_ledger.csv')
    parser.add_argument('--settlement',default='data/settlement_statement.csv')
    parser.add_argument('--output',default='reports')
    parser.add_argument('--triage',action='store_true',help='Use API to analyze up to 3 exceptions')
    parser.add_argument('--provider',choices=['openrouter','anthropic'])
    args=parser.parse_args()
    rows=reconcile(load_transactions(args.ledger),load_transactions(args.settlement))
    stats=save_reports(rows,args.output)
    print(json.dumps(stats,indent=2))
    if args.triage:
        from .triage import triage_exception
        selected=[r for r in rows if r['status']!='MATCHED'][:3]
        results=[]
        for row in selected:
            try:results.append(triage_exception(row,args.provider))
            except Exception as ex: results.append({'transaction_id':row['transaction_id'],'error':str(ex)})
        path=Path(args.output)/'triage.json';path.write_text(json.dumps(results,indent=2))
        print('Saved LLM triage to',path)
if __name__=='__main__':run()

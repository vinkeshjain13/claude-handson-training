import getpass
from src.core import get_request, policy, review, history

def main():
 print('=== HUMAN REVIEWER CONSOLE (do not run through Claude Code) ===')
 rid=int(input('Request ID: ').strip())
 req=get_request(rid)
 if not req: print('Request not found');return
 print('Proposal:',req)
 print('Policy:',policy(req['transaction_id']))
 print('Prior history:',history(rid))
 decision=input('Decision [APPROVE/MODIFY/REJECT]: ').strip().upper()
 amount=None
 if decision=='MODIFY':
  amount=int(input('Authorized amount in integer PAISE (800000 = INR 8000): ').strip())
 comment=input('Reason (8+ characters): ').strip()
 username=input('Reviewer username: ').strip()
 pw=getpass.getpass('Reviewer passphrase: ')
 print('Decision recorded:',review(rid,username,pw,decision,amount,comment))
if __name__=='__main__':main()

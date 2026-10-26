import hashlib, hmac, os, secrets, sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

DB_PATH = Path(os.environ.get('REFUND_DB_PATH', str(Path(__file__).resolve().parents[1] / 'database' / 'refunds.db')))
VALID_REASONS = {'DUPLICATE_CHARGE', 'FAILED_SERVICE', 'SERVICE_DISPUTE'}

def now(): return datetime.now(timezone.utc).isoformat(timespec='seconds')
@contextmanager
def connect():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(DB_PATH, timeout=8)
    db.row_factory = sqlite3.Row
    db.execute('PRAGMA foreign_keys=ON')
    db.execute('PRAGMA busy_timeout=8000')
    try:
        with db:
            yield db
    finally:
        db.close()

def public(row): return dict(row) if row else None

def init_db(reset=False):
    if reset and DB_PATH.exists(): DB_PATH.unlink()
    with connect() as db:
        db.executescript("""
          CREATE TABLE IF NOT EXISTS transactions(
           transaction_id TEXT PRIMARY KEY, customer_id TEXT NOT NULL,
           amount_paise INTEGER NOT NULL CHECK(amount_paise>0),
           currency TEXT NOT NULL DEFAULT 'INR', reason TEXT NOT NULL,
           evidence TEXT NOT NULL);
          CREATE TABLE IF NOT EXISTS refund_requests(
           request_id INTEGER PRIMARY KEY AUTOINCREMENT,
           transaction_id TEXT NOT NULL REFERENCES transactions(transaction_id),
           proposed_paise INTEGER NOT NULL CHECK(proposed_paise>=0),
           approved_paise INTEGER, reason TEXT NOT NULL,
           status TEXT NOT NULL DEFAULT 'PENDING_APPROVAL' CHECK(status IN ('PENDING_APPROVAL','APPROVED','REJECTED')),
           reviewer TEXT, reviewed_at TEXT, created_at TEXT NOT NULL);
          CREATE TABLE IF NOT EXISTS approval_audit(
           event_id INTEGER PRIMARY KEY AUTOINCREMENT, request_id INTEGER NOT NULL REFERENCES refund_requests(request_id),
           actor TEXT NOT NULL, event TEXT NOT NULL, amount_paise INTEGER,
           comment TEXT NOT NULL, event_at TEXT NOT NULL);
          CREATE TABLE IF NOT EXISTS reviewers(
           username TEXT PRIMARY KEY, salt_hex TEXT NOT NULL, verifier_hex TEXT NOT NULL);
        """)
        if not db.execute('SELECT 1 FROM transactions LIMIT 1').fetchone():
            db.executemany('INSERT INTO transactions VALUES(?,?,?,?,?,?)', [
                ('TX1001','C-100',1250000,'INR','DUPLICATE_CHARGE','Duplicate settlement confirmed for reference PAY-A11'),
                ('TX1002','C-101',720000,'INR','FAILED_SERVICE','Order cancelled; service not delivered'),
                ('TX1003','C-102',500000,'INR','SERVICE_DISPUTE','Merchant disputes customer claim; evidence incomplete')])

def tx_lookup(transaction_id):
    with connect() as db:
        r=db.execute('SELECT * FROM transactions WHERE transaction_id=?',(transaction_id,)).fetchone()
        return public(r)

def list_pending():
    with connect() as db:
        return [dict(r) for r in db.execute("SELECT * FROM refund_requests WHERE status='PENDING_APPROVAL' ORDER BY request_id")]

def get_request(request_id):
    with connect() as db:
        r=db.execute('SELECT * FROM refund_requests WHERE request_id=?',(request_id,)).fetchone()
        return public(r)

def policy(transaction_id):
    tx=tx_lookup(transaction_id)
    if not tx: return {'error':'Unknown transaction'}
    return {'transaction_id':transaction_id,'maximum_refund_paise':tx['amount_paise'],
            'currency':tx['currency'], 'rule':'Proposals must be between 0 and original charge; only human reviewer can approve.',
            'evidence':tx['evidence'], 'reason':tx['reason']}

def propose(transaction_id, proposed_paise, justification):
    if type(proposed_paise) is not int or proposed_paise <= 0: raise ValueError('proposed_paise must be positive integer (not rupees)')
    if not isinstance(justification,str) or len(justification.strip())<8: raise ValueError('Provide meaningful justification')
    with connect() as db:
        tx=db.execute('SELECT * FROM transactions WHERE transaction_id=?',(transaction_id,)).fetchone()
        if tx is None: raise ValueError('Unknown transaction')
        if proposed_paise>tx['amount_paise']: raise ValueError('Proposal exceeds original transaction')
        if tx['reason'] == 'SERVICE_DISPUTE':
            raise ValueError('Insufficient evidence: unresolved dispute requires independent review before proposal')
        db.execute('BEGIN IMMEDIATE')
        cur=db.execute('INSERT INTO refund_requests(transaction_id,proposed_paise,reason,created_at) VALUES(?,?,?,?)',
          (transaction_id,proposed_paise,justification.strip(),now()))
        rid=cur.lastrowid
        db.execute('INSERT INTO approval_audit(request_id,actor,event,amount_paise,comment,event_at) VALUES(?,?,?,?,?,?)',
          (rid,'agent','PROPOSED',proposed_paise,justification.strip(),now()))
        return {'request_id':rid,'status':'PENDING_APPROVAL','proposed_paise':proposed_paise,'note':'Human approval required; no payment sent'}

def history(request_id):
    with connect() as db:
        return [dict(r) for r in db.execute('SELECT * FROM approval_audit WHERE request_id=? ORDER BY event_id',(request_id,))]

def register_reviewer(username,passphrase):
    if not username or not username.replace('-','').replace('_','').isalnum(): raise ValueError('Invalid username')
    if len(passphrase)<12: raise ValueError('Passphrase needs 12+ characters')
    salt=secrets.token_bytes(16)
    verifier=hashlib.scrypt(passphrase.encode(),salt=salt,n=2**14,r=8,p=1)
    with connect() as db:
        db.execute('INSERT INTO reviewers VALUES(?,?,?)',(username,salt.hex(),verifier.hex()))

def authenticate(db,username,passphrase):
    user=db.execute('SELECT * FROM reviewers WHERE username=?',(username,)).fetchone()
    if user is None: return False
    given=hashlib.scrypt(passphrase.encode(),salt=bytes.fromhex(user['salt_hex']),n=2**14,r=8,p=1)
    return hmac.compare_digest(given, bytes.fromhex(user['verifier_hex']))

def review(request_id, username, passphrase, decision, amount_paise, comment):
    if decision not in ('APPROVE','MODIFY','REJECT'): raise ValueError('Invalid decision')
    if not isinstance(comment,str) or len(comment.strip())<8: raise ValueError('Review comment needs at least 8 characters')
    with connect() as db:
        db.execute('BEGIN IMMEDIATE')
        if not authenticate(db,username,passphrase): raise PermissionError('Reviewer authentication failed')
        req=db.execute('SELECT * FROM refund_requests WHERE request_id=?',(request_id,)).fetchone()
        if req is None: raise ValueError('Unknown request')
        if req['status'] != 'PENDING_APPROVAL': raise ValueError('This request has already been decided')
        tx=db.execute('SELECT * FROM transactions WHERE transaction_id=?',(req['transaction_id'],)).fetchone()
        if decision=='REJECT': final=None; status='REJECTED'
        elif decision=='APPROVE':
            if amount_paise is not None: raise ValueError('APPROVE cannot override amount; choose MODIFY')
            final=req['proposed_paise']; status='APPROVED'
        else:
            if type(amount_paise) is not int: raise ValueError('MODIFY requires integer paise')
            final=amount_paise; status='APPROVED'
        if final is not None and not (0<final<=tx['amount_paise']): raise ValueError('Amount outside policy ceiling')
        changed=db.execute("UPDATE refund_requests SET status=?, approved_paise=?, reviewer=?, reviewed_at=? WHERE request_id=? AND status='PENDING_APPROVAL'",
                           (status,final,username,now(),request_id))
        if changed.rowcount != 1: raise RuntimeError('Concurrent modification')
        db.execute('INSERT INTO approval_audit(request_id,actor,event,amount_paise,comment,event_at) VALUES(?,?,?,?,?,?)',
                   (request_id,username,decision,final,comment.strip(),now()))
        return {'request_id':request_id,'status':status,'approved_paise':final,'reviewer':username,
                'note':'Approval record only. No real refund/payment executed.'}

from __future__ import annotations
import os,sqlite3
from pathlib import Path
DB_PATH=Path(os.environ.get('LAB02_DB_PATH',str(Path(__file__).resolve().parents[1]/'database'/'service_desk.db')))

def connect():
    DB_PATH.parent.mkdir(parents=True,exist_ok=True)
    c=sqlite3.connect(DB_PATH,timeout=10)
    c.row_factory=sqlite3.Row
    c.execute('PRAGMA foreign_keys=ON')
    return c

def initialize(reset=False):
    if reset and DB_PATH.exists(): DB_PATH.unlink()
    with connect() as c:
        c.executescript("""CREATE TABLE IF NOT EXISTS assets (asset_id TEXT PRIMARY KEY, application TEXT NOT NULL, vendor TEXT NOT NULL, installed_version TEXT NOT NULL, owner_team TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS tickets (ticket_id TEXT PRIMARY KEY, asset_id TEXT NOT NULL REFERENCES assets(asset_id), summary TEXT NOT NULL, status TEXT NOT NULL CHECK(status IN ('OPEN','IN_REVIEW','RESOLVED')), priority TEXT NOT NULL CHECK(priority IN ('LOW','MEDIUM','HIGH')), investigation_note TEXT NOT NULL DEFAULT '', updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS ticket_audit (audit_id INTEGER PRIMARY KEY AUTOINCREMENT, ticket_id TEXT NOT NULL REFERENCES tickets(ticket_id), old_status TEXT NOT NULL, new_status TEXT NOT NULL, old_note TEXT NOT NULL, new_note TEXT NOT NULL, change_reason TEXT NOT NULL, changed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);""")
        if c.execute('SELECT COUNT(*) FROM assets').fetchone()[0]==0:
            c.executemany('INSERT INTO assets VALUES (?,?,?,?,?)',[('AST-101','ExampleWeb Server','ExampleSoft','2.4.8','Infrastructure'),('AST-102','AcmeDB Server','Acme Systems','6.1.2','Platform'),('AST-103','Payment Gateway Demo','Internal','1.3.0','Payments')])
            c.executemany('INSERT INTO tickets(ticket_id,asset_id,summary,status,priority,investigation_note) VALUES (?,?,?,?,?,?)',[('INC-1042','AST-101','Investigate potentially outdated public-facing application','OPEN','HIGH',''),('INC-1043','AST-102','Review database maintenance window','OPEN','MEDIUM',''),('INC-1044','AST-103','Intermittent payment service latency','IN_REVIEW','HIGH','Initial triage started')])

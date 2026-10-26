from src.db import connect
ALLOWED_TABLES={'assets','tickets','ticket_audit'}
def schema():
    with connect() as c:
        result={}
        for name in sorted(ALLOWED_TABLES):
            result[name]=[dict(name=r['name'],type=r['type'],pk=bool(r['pk'])) for r in c.execute(f'PRAGMA table_info({name})')]
        return result

def ticket(ticket_id:str):
    with connect() as c:
        row=c.execute('SELECT t.*,a.application,a.vendor,a.installed_version,a.owner_team FROM tickets t JOIN assets a ON a.asset_id=t.asset_id WHERE t.ticket_id=?',(ticket_id,)).fetchone()
        return dict(row) if row else {'error':'ticket_not_found','ticket_id':ticket_id}

def tickets(status:str='ALL'):
    if status not in {'ALL','OPEN','IN_REVIEW','RESOLVED'}: return {'error':'invalid_status'}
    with connect() as c:
        rows=c.execute('SELECT ticket_id,summary,status,priority FROM tickets ORDER BY ticket_id' if status=='ALL' else 'SELECT ticket_id,summary,status,priority FROM tickets WHERE status=? ORDER BY ticket_id',() if status=='ALL' else (status,)).fetchall()
        return [dict(r) for r in rows]

def history(ticket_id:str):
    with connect() as c:
        return [dict(r) for r in c.execute('SELECT * FROM ticket_audit WHERE ticket_id=? ORDER BY audit_id',(ticket_id,))]

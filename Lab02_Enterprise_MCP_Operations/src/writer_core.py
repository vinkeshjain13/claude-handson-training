from src.db import connect
ALLOWED={'OPEN':{'IN_REVIEW'},'IN_REVIEW':{'RESOLVED','OPEN'},'RESOLVED':set()}

def update(ticket_id:str,new_status:str,investigation_note:str,change_reason:str,confirm:bool=False):
    # Lab-level guardrail, not identity proof. Production needs authenticated human approval and RBAC.
    if confirm is not True: return {'error':'confirmation_required','message':'Preview the change and explicitly confirm before retrying.'}
    if new_status not in ALLOWED: return {'error':'invalid_status'}
    if not isinstance(investigation_note,str) or not investigation_note.strip() or len(investigation_note)>500: return {'error':'invalid_note'}
    if not isinstance(change_reason,str) or len(change_reason.strip())<8 or len(change_reason)>300: return {'error':'invalid_reason'}
    with connect() as c:
        c.execute('BEGIN IMMEDIATE')
        row=c.execute('SELECT status,investigation_note FROM tickets WHERE ticket_id=?',(ticket_id,)).fetchone()
        if row is None: return {'error':'ticket_not_found'}
        if new_status not in ALLOWED[row['status']]: return {'error':'invalid_transition','from':row['status'],'to':new_status}
        c.execute('UPDATE tickets SET status=?, investigation_note=?, updated_at=CURRENT_TIMESTAMP WHERE ticket_id=?',(new_status,investigation_note, ticket_id))
        c.execute('INSERT INTO ticket_audit(ticket_id,old_status,new_status,old_note,new_note,change_reason) VALUES (?,?,?,?,?,?)',(ticket_id,row['status'],new_status,row['investigation_note'],investigation_note,change_reason))
        return {'ticket_id':ticket_id,'old_status':row['status'],'new_status':new_status,'audit_recorded':True}

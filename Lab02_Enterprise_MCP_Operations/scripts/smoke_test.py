from src.db import initialize
from src.reader_core import schema,ticket,tickets,history
from src.writer_core import update
initialize()
print('Tables:',list(schema()))
print('Ticket:',ticket('INC-1042'))
print('Open tickets:',len(tickets('OPEN')))
print('Preview update (should be blocked):',update('INC-1042','IN_REVIEW','Review initiated','Initial investigation required',False))

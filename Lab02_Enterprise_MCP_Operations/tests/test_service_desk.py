import tempfile,unittest
from pathlib import Path
from unittest.mock import patch
class TestServiceDesk(unittest.TestCase):
    def setUp(self):
        import src.db as db
        self.t=tempfile.TemporaryDirectory(); self.p=patch.object(db,'DB_PATH',Path(self.t.name)/'test.db');self.p.start();db.initialize()
    def tearDown(self):self.p.stop();self.t.cleanup()
    def test_schema(self):
        from src.reader_core import schema
        self.assertEqual(set(schema()),{'assets','tickets','ticket_audit'})
    def test_read(self):
        from src.reader_core import ticket
        self.assertEqual(ticket('INC-1042')['status'],'OPEN')
    def test_denied_without_confirmation(self):
        from src.writer_core import update
        from src.reader_core import ticket
        self.assertEqual(update('INC-1042','IN_REVIEW','Review initiated','Requested investigation',False)['error'],'confirmation_required')
        self.assertEqual(ticket('INC-1042')['status'],'OPEN')
    def test_valid_write_audited(self):
        from src.writer_core import update
        from src.reader_core import ticket,history
        self.assertTrue(update('INC-1042','IN_REVIEW','Review initiated','Requested investigation',True)['audit_recorded'])
        self.assertEqual(ticket('INC-1042')['status'],'IN_REVIEW')
        self.assertEqual(len(history('INC-1042')),1)
    def test_invalid_transition(self):
        from src.writer_core import update
        self.assertEqual(update('INC-1042','RESOLVED','Done','Requested investigation',True)['error'],'invalid_transition')
    def test_sql_injection_non_effect(self):
        from src.reader_core import ticket,schema
        self.assertEqual(ticket("INC-1042' OR 1=1 --")['error'],'ticket_not_found')
        self.assertIn('tickets',schema())
if __name__=='__main__':unittest.main()

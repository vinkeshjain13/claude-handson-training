import os, tempfile, unittest
from pathlib import Path
from unittest.mock import patch

class RefundTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory()
  import src.core as c
  self.c=c;self.patch=patch.object(c,'DB_PATH',Path(self.temp.name)/'test.db');self.patch.start()
  c.init_db();c.register_reviewer('manager','example-safe-password-123')
 def tearDown(self):self.patch.stop();self.temp.cleanup()
 def proposal(self):return self.c.propose('TX1001',1250000,'Verified duplicate settlement')['request_id']
 def test_seed_and_policy(self):
  self.assertEqual(self.c.tx_lookup('TX1001')['amount_paise'],1250000)
  self.assertEqual(self.c.policy('TX1001')['maximum_refund_paise'],1250000)
 def test_create_is_pending(self):
  r=self.c.get_request(self.proposal());self.assertEqual(r['status'],'PENDING_APPROVAL');self.assertIsNone(r['approved_paise'])
 def test_proposal_excess_blocked(self):
  with self.assertRaises(ValueError):self.c.propose('TX1001',2000000,'Attempt out of ceiling')
 def test_weak_evidence_blocked(self):
  with self.assertRaises(ValueError):self.c.propose('TX1003',500000,'Customer says charge unfair')
 def test_unauthorized_reviewer_blocked(self):
  rid=self.proposal()
  with self.assertRaises(PermissionError):self.c.review(rid,'agent','wrong','APPROVE',None,'I can approve this')
  self.assertEqual(self.c.get_request(rid)['status'],'PENDING_APPROVAL')
 def test_modify_and_audit(self):
  rid=self.proposal();out=self.c.review(rid,'manager','example-safe-password-123','MODIFY',800000,'Approve partial goodwill refund')
  self.assertEqual(out['approved_paise'],800000)
  self.assertEqual([x['event'] for x in self.c.history(rid)],['PROPOSED','MODIFY'])
 def test_reject(self):
  rid=self.proposal();r=self.c.review(rid,'manager','example-safe-password-123','REJECT',None,'Duplicate not confirmed')
  self.assertEqual(r['status'],'REJECTED')
 def test_no_double_approval(self):
  rid=self.proposal();self.c.review(rid,'manager','example-safe-password-123','APPROVE',None,'Confirmed supporting evidence')
  with self.assertRaises(ValueError):self.c.review(rid,'manager','example-safe-password-123','REJECT',None,'Second attempt forbidden')
 def test_modify_cannot_exceed_original(self):
  rid=self.proposal()
  with self.assertRaises(ValueError):self.c.review(rid,'manager','example-safe-password-123','MODIFY',2000000,'Override over amount')
  self.assertEqual(self.c.get_request(rid)['status'],'PENDING_APPROVAL')
 def test_approve_disallows_override(self):
  rid=self.proposal()
  with self.assertRaises(ValueError):self.c.review(rid,'manager','example-safe-password-123','APPROVE',800000,'Should choose modify')
if __name__=='__main__':unittest.main()

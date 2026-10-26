import csv, json, unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class EvidenceTests(unittest.TestCase):
 def test_agents_exist(self):
  self.assertEqual(len(list((ROOT/'.claude/agents').glob('*.md'))),3)
 def test_metrics_show_pool_change(self):
  with (ROOT/'incident_data/system_metrics.csv').open() as f: rows=list(csv.DictReader(f))
  self.assertEqual(rows[0]['db_pool_max'],'60')
  self.assertEqual(rows[-1]['db_pool_max'],'12')
 def test_release_change(self):
  data=json.loads((ROOT/'incident_data/deployment_history.json').read_text())
  self.assertEqual(data['releases'][-1]['version'],'4.8.0')
 def test_security_timeline(self):
  s=(ROOT/'incident_data/security_events.log').read_text()
  self.assertIn('rate_limit_applied',s)
if __name__=='__main__':unittest.main()

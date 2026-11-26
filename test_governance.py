import unittest,tempfile,re,json
from pathlib import Path
from unittest.mock import patch
from fastapi.testclient import TestClient
import tenant,secure_app as s,governance as g
RAW=Path(__file__).with_name('demo.csv').read_bytes();PW='Synthetic-governance-password-42!'
ALIAS={'supplier':'Supplier A','sku':'X1','canonical':'COMMON','evidence':'Synthetic verified specification'}
SAVING={'product':'COMMON','unit':'kg','baseline_reference':'BASE','purchase_reference':'BUY','baseline_price':'12','actual_price':'9','quantity':'10'}
class Governance(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
  for obj,k,v in [(tenant,'ROOT',Path(self.tmp.name)),(s,'TLS',False),(s,'COOKIE','bc_session'),(s,'ORIGIN','http://localhost')]:
   p=patch.object(obj,k,v);p.start();self.addCleanup(p.stop)
  self.a=tenant.create_company('A');self.b=tenant.create_company('B')
  for name,co,role in [('a-owner',self.a,'owner'),('a-analyst',self.a,'analyst'),('a-reader',self.a,'reader'),('b-owner',self.b,'owner')]:tenant.create_user(co,name,PW,role)
  self.owner=self.login('a-owner');self.analyst=self.login('a-analyst');self.reader=self.login('a-reader');self.other=self.login('b-owner')
 def login(self,name):
  c=TestClient(s.app,base_url=s.ORIGIN);self.addCleanup(c.close);self.assertEqual(c.post('/login',headers={'origin':s.ORIGIN},json={'login':name,'password':PW}).status_code,200);c.headers.update({'origin':s.ORIGIN,'X-CSRF-Token':re.search(r'name="csrf" content="([^"]+)"',c.get('/').text)[1]});return c
 def propose(self,route='aliases',payload=ALIAS,client=None):
  r=(client or self.analyst).post('/api/'+route,json=payload);self.assertEqual(r.status_code,200,r.text);self.assertEqual(r.json()['status'],'PENDING');return r.json()['id']
 def decide(self,key,client=None,decision='APPROVED',reason='Reviewed against supporting evidence'):
  return (client or self.owner).post('/api/governance-review',json={'id':key,'decision':decision,'reason':reason})
 def test_pending_and_approval(self):
  key=self.propose();self.assertEqual(self.owner.get('/api/decisions').json()['aliases'],[]);self.assertEqual(self.decide(key).status_code,200);self.assertEqual(self.owner.get('/api/decisions').json()['aliases'][0]['canonical'],'COMMON');self.assertEqual(self.decide(key).status_code,400)
 def test_self_approval(self):
  key=self.propose(client=self.owner);self.assertEqual(self.decide(key).status_code,400)
 def test_permissions(self):
  key=self.propose();self.assertEqual(self.decide(key,self.analyst).status_code,400);self.assertEqual(self.decide(key,self.reader).status_code,403);self.assertEqual(self.reader.post('/api/aliases',json=ALIAS).status_code,403)
 def test_tenant(self):
  key=self.propose();self.assertEqual(self.decide(key,self.other).status_code,400);self.assertEqual(self.other.get('/api/governance').json()['cases'],[])
 def test_rejection(self):
  key=self.propose();self.assertEqual(self.decide(key,decision='REJECTED').status_code,200);self.assertEqual(self.owner.get('/api/decisions').json()['aliases'],[])
 def test_idempotence(self):self.assertEqual(self.propose(),self.propose())
 def test_savings(self):
  key=self.propose('savings',SAVING);self.assertEqual(self.owner.get('/api/decisions').json()['savings'],[]);self.assertEqual(self.decide(key).status_code,200);v=self.owner.get('/api/decisions').json()['savings'][0];self.assertEqual(v['declared_saving_eur'],'30.00');self.assertEqual(v['status'],'DECLARADO_NO_VERIFICADO')
 def test_invalid(self):self.assertEqual(self.analyst.post('/api/aliases',json={}).status_code,400);self.assertEqual(self.owner.get('/api/governance').json()['cases'],[])
 def test_release(self):
  report=self.analyst.post('/api/audit',content=RAW).json()['id'];url='/api/report/'+report+'/approved.json';self.assertEqual(self.owner.get(url).status_code,409);self.assertEqual(self.owner.get('/api/report/'+report).json()['governance_status'],'BORRADOR_NO_APROBADO');key=self.propose('governance-release',{'report_id':report,'evidence':'Document reviewed and limitations accepted'});self.assertEqual(self.decide(key).status_code,200);r=self.owner.get(url);self.assertEqual(r.status_code,200,r.text);self.assertEqual(r.json()['governance']['status'],'APROBADO_PARA_USO_INTERNO');self.assertEqual(self.other.get(url).status_code,404)
 def test_demo_release(self):
  report=self.analyst.post('/api/demo').json()['id'];self.assertEqual(self.analyst.post('/api/governance-release',json={'report_id':report,'evidence':'Document reviewed and limitations accepted'}).status_code,400)
 def test_author(self):
  report=self.owner.post('/api/audit',content=RAW).json()['id'];key=self.propose('governance-release',{'report_id':report,'evidence':'Document reviewed and limitations accepted'});self.assertEqual(self.decide(key).status_code,400)
 def test_tampered_log(self):
  key=self.propose();
  with tenant.company_db(self.a) as c:c.execute("UPDATE gov_log SET entry='altered'")
  self.assertFalse(self.owner.get('/api/governance').json()['chain_consistent']);self.assertEqual(self.decide(key).status_code,400)
 def test_tampered_payload(self):
  key=self.propose();
  with tenant.company_db(self.a) as c:c.execute("UPDATE gov_cases SET payload='{}' WHERE id=?",(key,))
  self.assertEqual(self.decide(key).status_code,400)
 def test_forged_payload_and_hash(self):
  key=self.propose();data=dict(ALIAS,canonical='FORGED');
  with tenant.company_db(self.a) as c:c.execute('UPDATE gov_cases SET payload=?,payload_hash=? WHERE id=?',(g.canonical(data),g.digest(data),key))
  self.assertFalse(self.owner.get('/api/governance').json()['chain_consistent']);self.assertEqual(self.decide(key).status_code,400)
 def test_deleted_log_tail(self):
  key=self.propose();self.assertEqual(self.decide(key).status_code,200)
  with tenant.company_db(self.a) as c:c.execute('DELETE FROM gov_log WHERE seq=(SELECT max(seq) FROM gov_log)')
  self.assertFalse(self.owner.get('/api/governance').json()['chain_consistent'])
 def test_tampered_report(self):
  report=self.analyst.post('/api/audit',content=RAW).json()['id'];key=self.propose('governance-release',{'report_id':report,'evidence':'Document reviewed and limitations accepted'});self.assertEqual(self.decide(key).status_code,200)
  with tenant.company_db(self.a) as c:
   r=json.loads(c.execute('SELECT report FROM reports WHERE id=?',(report,)).fetchone()[0]);r['potential_saving_eur']='999';c.execute('UPDATE reports SET report=? WHERE id=?',(json.dumps(r),report))
  self.assertEqual(self.owner.get('/api/report/'+report+'/approved.json').status_code,409)
if __name__=='__main__':unittest.main()

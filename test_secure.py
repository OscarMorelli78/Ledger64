import unittest,tempfile,os,re,base64,sqlite3,concurrent.futures
from pathlib import Path
import tenant
from fastapi.testclient import TestClient
import secure_app as s
from admin import backup,restore_to_new_company
from independent import verify
from ingest import audit_document
from engine import InputError
RAW=Path(__file__).with_name('demo.csv').read_bytes()
PW='Synthetic-test-password-42!'
class Secure(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.tmp=tempfile.TemporaryDirectory();tenant.ROOT=Path(cls.tmp.name);s.TLS=False;s.COOKIE='bc_session';s.ORIGIN='http://localhost';
  cls.a=tenant.create_company('Empresa A');cls.b=tenant.create_company('Empresa B');tenant.create_user(cls.a,'owner-a',PW);tenant.create_user(cls.b,'owner-b',PW);tenant.create_user(cls.a,'reader-a',PW,'reader');tenant.create_user(cls.a,'analyst-a',PW,'analyst');
 @classmethod
 def tearDownClass(cls):cls.tmp.cleanup()
 def login(self,name):
  c=TestClient(s.app,base_url=s.ORIGIN);r=c.post('/login',headers={'origin':s.ORIGIN},json={'login':name,'password':PW});self.assertEqual(r.status_code,200,r.text);token=re.search(r'name="csrf" content="([^"]+)"',c.get('/').text)[1];c.headers.update({'origin':s.ORIGIN,'X-CSRF-Token':token});return c
 def test_01_anonymous(self):
  c=TestClient(s.app,base_url=s.ORIGIN);self.assertEqual(c.get('/api/history').status_code,401);self.assertEqual(c.post('/api/demo').status_code,401);self.assertEqual(c.get('/',follow_redirects=False).status_code,303)
 def test_02_login_origin(self):
  c=TestClient(s.app,base_url=s.ORIGIN);self.assertEqual(c.post('/login',json={'login':'owner-a','password':PW}).status_code,403)
 def test_03_wrong_password(self):
  c=TestClient(s.app,base_url=s.ORIGIN);self.assertEqual(c.post('/login',headers={'origin':s.ORIGIN},json={'login':'owner-a','password':'wrong'}).status_code,401)
 def test_04_cookie_security(self):
  c=TestClient(s.app,base_url=s.ORIGIN);r=c.post('/login',headers={'origin':s.ORIGIN},json={'login':'owner-a','password':PW});self.assertIn('HttpOnly',r.headers['set-cookie']);self.assertIn('SameSite=strict',r.headers['set-cookie']);self.assertIn('frame-ancestors',c.get('/').headers['content-security-policy'])
 def test_05_cross_tenant(self):
  a,b=self.login('owner-a'),self.login('owner-b');r=a.post('/api/audit',content=RAW);self.assertEqual(r.status_code,200,r.text);key=r.json()['id'];self.assertEqual(b.get('/api/report/'+key).status_code,404);self.assertEqual(b.get('/api/report/'+key+'/report.pdf').status_code,404);self.assertNotIn(key,[x['id'] for x in b.get('/api/history').json()]);self.assertEqual(a.get('/api/report/'+key+'/report.json').status_code,200)
 def test_06_csrf(self):
  a=self.login('owner-a');self.assertEqual(a.post('/api/demo',headers={'X-CSRF-Token':'bad'}).status_code,403);self.assertEqual(a.post('/api/demo',headers={'origin':'https://evil.example'}).status_code,403)
 def test_07_reader(self):
  r=self.login('reader-a');self.assertEqual(r.get('/api/history').status_code,200);self.assertEqual(r.post('/api/demo').status_code,403);self.assertEqual(r.post('/api/aliases',json={}).status_code,403);self.assertEqual(r.get('/api/events').status_code,404)
 def test_08_alias_isolation(self):
  a,b=self.login('owner-a'),self.login('owner-b');p={'supplier':'Synthetic supplier','sku':'SKU1','canonical':'COMMON','evidence':'Synthetic specification'};self.assertEqual(a.post('/api/aliases',json=p).json()['status'],'PENDING');self.assertFalse(any(x['sku']=='SKU1' for x in b.get('/api/decisions').json()['aliases']))
 def test_09_logout(self):
  a=self.login('owner-a');old=a.cookies.get(s.COOKIE);self.assertEqual(a.post('/api/logout').status_code,200);a.cookies.set(s.COOKIE,old);self.assertEqual(a.get('/api/history').status_code,401)
 def test_10_limit(self):
  a=self.login('owner-a');self.assertEqual(a.post('/api/audit',content=b'x'*2000001).status_code,400)
 def test_11_review(self):
  a=self.login('analyst-a');p={'source':base64.b64encode(Path('demo_scan.pdf').read_bytes()).decode(),'csv':base64.b64encode(RAW).decode(),'evidence':'Transcripción sintética revisada'};r=a.post('/api/review',json=p);self.assertEqual(r.status_code,200,r.text);self.assertIn('NO_VERIFICACION',r.json()['report']['manual_review']['status']);self.assertEqual(r.json()['report']['verification']['status'],'CONTRASTE_ARITMETICO_SUPERADO')
 def test_12_backup_restore(self):
  a=self.login('owner-a');key=a.post('/api/demo').json()['id'];dest=Path(self.tmp.name)/'backup.sqlite';self.assertEqual(len(backup(self.a,dest)),64);new=restore_to_new_company('Restored',dest);self.assertNotEqual(new,self.a)
  with tenant.company_db(new) as c:self.assertEqual(c.execute('SELECT count(*) FROM reports WHERE id=?',(key,)).fetchone()[0],1)
  with self.assertRaises(FileExistsError):backup(self.a,dest)
 def test_13_concurrency(self):
  a=self.login('owner-a');token=a.cookies.get(s.COOKIE);csrf=a.headers['X-CSRF-Token'];
  def work(_):
   with TestClient(s.app,base_url=s.ORIGIN) as c:
    c.cookies.set(s.COOKIE,token);return c.post('/api/demo',headers={'origin':s.ORIGIN,'X-CSRF-Token':csrf})
  with concurrent.futures.ThreadPoolExecutor(max_workers=4) as ex:results=list(ex.map(work,range(8)))
  self.assertTrue(all(r.status_code==200 for r in results),[r.text for r in results]);self.assertEqual(len({r.json()['id'] for r in results}),1)
 def test_14_tampered(self):
  r=audit_document(RAW);r['potential_saving_eur']='999.99';
  with self.assertRaises(ValueError):verify(RAW,r)
 def test_15_disabled(self):
  a=self.login('analyst-a');tenant.disable_user('analyst-a');self.assertEqual(a.get('/api/history').status_code,401)
 def test_16_events(self):
  a=self.login('owner-a');r=a.get('/api/events');self.assertEqual(r.status_code,200);self.assertTrue(any(x['action']=='audit' for x in r.json()))
 def test_17_path(self):
  a=self.login('owner-a');self.assertEqual(a.get('/tenant.py').status_code,404);self.assertEqual(a.get('/private/auth.sqlite3').status_code,404)
if __name__=='__main__':unittest.main()

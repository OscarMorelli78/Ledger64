import unittest,tempfile,io,time,sqlite3,os,random,csv
from pathlib import Path
from unittest.mock import patch
from fractions import Fraction
from fastapi.testclient import TestClient
import tenant,secure_app as s
from ingest import audit_document
from independent import verify
from engine import FIELDS
from ocr_review import transcribe
RAW=Path(__file__).with_name('demo.csv').read_bytes()
PW='Synthetic-secret-password-42!'
class Harden(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.root=patch.object(tenant,'ROOT',Path(self.temp.name));self.root.start();self.addCleanup(self.root.stop);self.addCleanup(self.temp.cleanup)
  self.company=tenant.create_company('Audit test');self.user=tenant.create_user(self.company,'test-owner',PW)
 def test_secure_cookie_tls(self):
  with patch.object(s,'TLS',True),patch.object(s,'COOKIE','__Host-bc_session'),patch.object(s,'ORIGIN','https://localhost'):
   with TestClient(s.app,base_url='https://localhost') as c:
    r=c.post('/login',headers={'origin':'https://localhost'},json={'login':'test-owner','password':PW});self.assertEqual(r.status_code,200);self.assertIn('Secure',r.headers['set-cookie']);self.assertIn('__Host-bc_session',r.headers['set-cookie']);self.assertIn('Strict-Transport-Security',r.headers);self.assertEqual(c.get('/api/history').status_code,200)
 def test_expired_session(self):
  token=tenant.authenticate('test-owner',PW,'ip');self.assertIsNotNone(tenant.session(token));
  with tenant.auth_db() as c:c.execute('UPDATE sessions SET expires=?',(int(time.time())-1,))
  self.assertIsNone(tenant.session(token))
 def test_login_throttle(self):
  for _ in range(8):self.assertIsNone(tenant.authenticate('test-owner','bad','ip'))
  self.assertIsNone(tenant.authenticate('test-owner',PW,'another-ip'))
 def test_password_storage(self):
  token=tenant.authenticate('test-owner',PW,'ip');
  with tenant.auth_db() as c:
   u=c.execute('SELECT salt,password FROM users').fetchone();t=c.execute('SELECT token FROM sessions').fetchone()[0];self.assertEqual(len(u['salt']),16);self.assertEqual(len(u['password']),32);self.assertNotEqual(t,token);self.assertEqual(t,tenant.token_hash(token))
 def test_password_reset_revokes(self):
  token=tenant.authenticate('test-owner',PW,'ip');tenant.reset_password('test-owner','Another-long-test-secret-42!');self.assertIsNone(tenant.session(token));self.assertIsNone(tenant.authenticate('test-owner',PW,'ip'));self.assertIsNotNone(tenant.authenticate('test-owner','Another-long-test-secret-42!','ip'))
 def test_auth_backup(self):
  from admin import backup
  import contextlib
  dest=Path(self.temp.name)/'auth-backup.sqlite';self.assertEqual(len(backup(None,dest)),64)
  with contextlib.closing(sqlite3.connect(dest)) as c:self.assertEqual(c.execute('SELECT count(*) FROM users').fetchone()[0],1)
 def test_tampered_price(self):
  r=audit_document(RAW);r['comparisons'][0]['unit_price_eur']='99.000000'
  with self.assertRaises(ValueError):verify(RAW,r)
 def test_ocr_spanish_fixture(self):
  import shutil,subprocess
  if not shutil.which('tesseract'):self.skipTest('Tesseract ausente')
  if 'spa' not in subprocess.check_output(['tesseract','--list-langs'],text=True).splitlines():self.skipTest('Modelo español ausente')
  from PIL import Image,ImageDraw,ImageFont
  img=Image.new('RGB',(1400,800),'white');d=ImageDraw.Draw(img);font=ImageFont.truetype('DejaVuSans.ttf',46)
  for i,t in enumerate(['FACTURA COMERCIAL','Número: 12345','Proveedor: EJEMPLO','Fecha: 26/11/2026','Importe sin IVA: 120,00 EUR']):d.text((65,70+i*105),t,fill='black',font=font)
  b=io.BytesIO();img.save(b,format='PDF',resolution=150);r=transcribe(b.getvalue(),'spa+eng');self.assertEqual(r['status'],'BORRADOR_NO_VERIFICADO');self.assertIn('12345',r['pages'][0]['text']);self.assertIn('120,00',r['pages'][0]['text']);self.assertNotIn('potential_saving_eur',r)
 def test_seeded_fractional_units(self):
  rng=random.Random(2026);buf=io.StringIO(newline='');w=csv.writer(buf);w.writerow(FIELDS)
  # Different quantities, decimal costs and two suppliers; exact comparator runs on every row.
  for i in range(1000):
   for supplier in ('A','B'):
    q=rng.randint(1,10000);cost=f'{rng.randint(1,5000)}.{rng.randint(0,99):02}'
    w.writerow([supplier,f'F{i}','1','2026-11-26',f'P{i}','g',q,cost,'0','0',cost])
  r=audit_document(buf.getvalue().encode(),True);self.assertEqual(r['eligible_rows'],2000);self.assertTrue(all(r['verification']['checks'].values()))
if __name__=='__main__':unittest.main()

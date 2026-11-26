import unittest, pathlib, tempfile, subprocess, os, sys, time, urllib.request, urllib.error, json, re, socket
from engine import audit, InputError, export_csv, FIELDS
BASE=pathlib.Path(__file__).parent
HEADER=','.join(FIELDS)+'\n'
def data(*rows):return (HEADER+'\n'.join(rows)+'\n').encode()
def row(s='A',i='1',d='2026-11-20',p='X',u='kg',q='10',n='100',sh='0',di='0',t='100'):
    return ','.join([s,i,'1',d,p,u,q,n,sh,di,t])
class EngineTests(unittest.TestCase):
    def test_demo(self):
        r=audit((BASE/'demo.csv').read_bytes(),True); self.assertEqual((r['rows'],r['review_alerts'],r['potential_saving_eur'],r['confirmed_loss_eur']),(6,3,'30.00',None))
    def test_empty(self):
        with self.assertRaises(InputError):audit(b'')
    def test_headers(self):
        with self.assertRaises(InputError):audit(b'bad\n1')
    def test_no_rows(self):
        with self.assertRaises(InputError):audit(HEADER.encode())
    def test_zero_quantity(self):
        with self.assertRaises(InputError):audit(data(row(q='0')))
    def test_bad_number(self):
        with self.assertRaises(InputError):audit(data(row(n='NaN')))
    def test_negative(self):
        with self.assertRaises(InputError):audit(data(row(n='-1')))
    def test_bad_date(self):
        with self.assertRaises(InputError):audit(data(row(d='2026-02-30')))
    def test_bad_unit(self):
        with self.assertRaises(InputError):audit(data(row(u='box')))
    def test_discount(self):
        with self.assertRaises(InputError):audit(data(row(di='101')))
    def test_shipping_discount(self):
        r=audit(data(row(sh='10',di='5',t='105'),row(s='B',n='90',t='90'))); self.assertEqual(r['potential_saving_eur'],'15.00')
    def test_unit_conversion(self):
        r=audit(data(row(),row(s='B',u='g',q='10000',n='80',t='80')));self.assertEqual(r['potential_saving_eur'],'20.00')
    def test_incompatible_units(self):
        self.assertEqual(audit(data(row(),row(s='B',u='l')))['comparisons'],[])
    def test_conflict(self):
        r=audit(data(row(),row(n='110',t='110'),row(s='B'))); self.assertEqual(r['eligible_rows'],1);self.assertEqual(r['alerts'][0]['type'],'ID_CONFLICTIVO')
    def test_duplicate_not_counted(self):
        r=audit(data(row(),row(),row(s='B',n='80',t='80')));self.assertEqual(r['potential_saving_eur'],'20.00');self.assertEqual(r['eligible_rows'],2)
    def test_mismatch_excluded(self):
        r=audit(data(row(t='101'),row(s='B')));self.assertEqual(r['eligible_rows'],1);self.assertEqual(r['comparisons'],[])
    def test_old_quote_excluded(self):
        self.assertEqual(audit(data(row(),row(s='B',d='2026-09-01')))['comparisons'],[])
    def test_latest_price_weighted(self):
        r=audit(data(row(),row(i='2',q='20',n='300',t='300'),row(s='B',n='100',t='100')));self.assertEqual(r['potential_saving_eur'],'100.00')
    def test_formula_escape(self):
        self.assertIn("'=SUM",export_csv([{'x':'=SUM(1)'}],['x']).decode('utf-8-sig'))
    def test_real_not_confirmed(self):
        self.assertIsNone(audit(data(row()))['confirmed_loss_eur'])
class HTTPTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory();s=socket.socket();s.bind(('127.0.0.1',0));cls.port=s.getsockname()[1];s.close();cls.url=f'http://127.0.0.1:{cls.port}';cls.env=dict(os.environ,BC_PORT=str(cls.port),BC_DB=str(pathlib.Path(cls.tmp.name)/'audit.sqlite3'));cls.start()
    @classmethod
    def start(cls):
        cls.proc=subprocess.Popen([sys.executable,'app.py'],cwd=BASE,env=cls.env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        for _ in range(100):
            try:
                with urllib.request.urlopen(cls.url,timeout=.2) as f:cls.token=re.search(r'name="csrf" content="([^"]+)"',f.read().decode()).group(1);return
            except OSError:time.sleep(.03)
        raise RuntimeError('server not ready')
    @classmethod
    def tearDownClass(cls):cls.proc.terminate();cls.proc.wait(timeout=5);cls.tmp.cleanup()
    def req(self,path,body=None,token=True):
        headers={'X-CSRF-Token':self.token} if token else {};return urllib.request.urlopen(urllib.request.Request(self.url+path,data=body,headers=headers),timeout=5)
    def test_ui(self):
        with self.req('/') as r:self.assertIn(b'Business Control',r.read());self.assertIn('default-src',r.headers['Content-Security-Policy'])
        with self.req('/ui.js') as r:self.assertIn(b'fetch',r.read())
    def test_csrf(self):
        with self.assertRaises(urllib.error.HTTPError) as e:self.req('/api/demo',b'',False)
        self.assertEqual(e.exception.code,403)
    def test_bad_csv(self):
        with self.assertRaises(urllib.error.HTTPError) as e:self.req('/api/audit',b'invalid')
        self.assertEqual(e.exception.code,400)
    def test_roundtrip(self):
        with self.req('/api/demo',b'') as f:x=json.load(f)
        with self.req('/api/demo',b'') as f:self.assertEqual(json.load(f)['id'],x['id'])
        with self.req('/api/history') as f:self.assertEqual(sum(y['id']==x['id'] for y in json.load(f)),1)
        self.__class__.proc.terminate();self.__class__.proc.wait(timeout=5);self.__class__.start()
        with self.req('/api/report/'+x['id']) as f:self.assertEqual(json.load(f)['potential_saving_eur'],'30.00')
        with self.req('/api/report/'+x['id']+'/alerts.csv') as f:self.assertIn(b'DUPLICADO_POSIBLE',f.read())
        with self.req('/api/report/'+x['id']+'/comparisons.csv') as f:self.assertIn(b'30.00',f.read())
    def test_upload(self):
        with self.req('/api/audit',data(row())) as f:self.assertFalse(json.load(f)['report']['synthetic'])
if __name__=='__main__':unittest.main(verbosity=2)

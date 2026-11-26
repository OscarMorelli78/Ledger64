"""Exercise nine locales over a real HTTP listener, with isolated synthetic data."""
import sys,os,tempfile,socket,subprocess,time,re,io
from pathlib import Path
import httpx
from pypdf import PdfReader
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from i18n import LANGS,tr

def main():
 with tempfile.TemporaryDirectory() as d:
  with socket.socket() as s:s.bind(('127.0.0.1',0));port=s.getsockname()[1]
  url=f'http://127.0.0.1:{port}';env=dict(os.environ,BC_ROOT=d,BC_TLS='0',BC_ORIGIN=url,BC_HOSTS='127.0.0.1')
  subprocess.run([sys.executable,'-c',"from tenant import create_company,create_user; c=create_company('Synthetic'); create_user(c,'demo-owner','Synthetic-test-password-42!')"],cwd=ROOT,env=env,check=True)
  p=subprocess.Popen([sys.executable,'-m','uvicorn','secure_app:app','--host','127.0.0.1','--port',str(port),'--no-access-log'],cwd=ROOT,env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
  try:
   with httpx.Client(base_url=url,headers={'Origin':url},timeout=15,trust_env=False) as c:
    for _ in range(100):
     try:
      r=c.get('/login');assert r.status_code==200;break
     except httpx.ConnectError:time.sleep(.1)
    else:raise RuntimeError('Server not ready')
    assert 'lang="en"' in r.text
    assert c.get('/api/history').status_code==401
    assert c.post('/login',json={'login':'demo-owner','password':'Synthetic-test-password-42!'}).status_code==200
    previous=None
    for lang in LANGS:
     c.cookies.set('ledger64_lang',lang,domain='127.0.0.1',path='/');r=c.get('/');assert r.status_code==200 and f'lang="{lang}"' in r.text and tr('Analizar archivo',lang) in r.text
     token=re.search(r'name="csrf" content="([^"]+)"',r.text)[1];c.headers['X-CSRF-Token']=token
     js=c.get('/ui.js');assert js.status_code==200 and tr('Auditoría completada y guardada localmente.',lang) in js.text
     a=c.post('/api/demo');assert a.status_code==200,a.text;x=a.json();rr=x['report'];assert (rr['rows'],rr['review_alerts'],rr['potential_saving_eur'])==(6,3,'30.00')
     if previous is not None:assert rr==previous
     previous=rr
     pdf=c.get('/api/report/'+x['id']+'/report.pdf');assert pdf.status_code==200 and PdfReader(io.BytesIO(pdf.content)).metadata.title==tr('Informe ejecutivo de compras',lang)
     err=c.post('/api/ocr',content=b'not a PDF');assert err.status_code==400 and err.json()['message']==tr('OCR requiere un PDF de hasta 2 MB',lang)
     assert c.get('/api/me').json()['role']=='owner';print('PASS',lang,flush=True)
    assert c.post('/api/logout').status_code==200 and c.get('/api/history').status_code==401
  finally:p.terminate();p.wait(timeout=10)
if __name__=='__main__':main()

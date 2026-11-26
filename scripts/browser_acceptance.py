"""Real browser integration. Synthetic tenant only. Requires playwright + Chromium."""
import json,os,sys,socket,subprocess,tempfile,time,urllib.request
from pathlib import Path
from playwright.sync_api import sync_playwright,expect
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from i18n import LANGS,tr

def main():
 with tempfile.TemporaryDirectory() as d:
  with socket.socket() as s:s.bind(('127.0.0.1',0));port=s.getsockname()[1]
  url=f'http://127.0.0.1:{port}';env=dict(os.environ,BC_ROOT=d,BC_TLS='0',BC_ORIGIN=url,BC_HOSTS='127.0.0.1')
  subprocess.run([sys.executable,'-c',"from tenant import create_company,create_user; c=create_company('Synthetic'); create_user(c,'demo-owner','Synthetic-test-password-42!')"],cwd=ROOT,env=env,check=True)
  p=subprocess.Popen([sys.executable,'-m','uvicorn','secure_app:app','--host','127.0.0.1','--port',str(port),'--no-access-log'],cwd=ROOT,env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
  try:
   for _ in range(100):
    try:urllib.request.urlopen(url+'/login',timeout=.2).close();break
    except OSError:time.sleep(.1)
   else:raise RuntimeError('server not ready')
   with sync_playwright() as pw:
    # Explicit opt-in for isolated CI environment only; default Chromium sandbox untouched.
    args=['--disable-dev-shm-usage']
    if os.environ.get('LEDGER_BROWSER_ISOLATED')=='1':args+=['--no-sandbox','--disable-gpu','--disable-background-networking','--no-zygote','--single-process']
    opts={'headless':True,'timeout':10000,'args':args}
    if os.environ.get('LEDGER_CHROMIUM'):opts['executable_path']=os.environ['LEDGER_CHROMIUM']
    browser=pw.chromium.launch(**opts)
    context=browser.new_context(viewport={'width':1280,'height':900},accept_downloads=True)
    page=context.new_page();errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
    page.goto(url+'/login',wait_until='domcontentloaded');expect(page.locator('html')).to_have_attribute('lang','en');expect(page.locator('h1')).to_have_text(tr('Acceso empresarial','en'))
    page.locator('#login').fill('demo-owner');page.locator('#password').fill('Synthetic-test-password-42!');page.locator('#login_form button').click();page.wait_for_url(url+'/')
    for lang in ('en',*[l for l in LANGS if l!='en']):
     page.locator('#ledger_language').select_option(lang);expect(page.locator('html')).to_have_attribute('lang',lang);expect(page.locator('#run')).to_have_text(tr('Analizar archivo',lang));expect(page.locator('#alias_supplier')).to_have_attribute('placeholder',tr('Proveedor',lang));expect(page.locator('#gov_release')).to_have_text(tr('Solicitar liberación',lang))
     page.locator('#demo').click();expect(page.locator('#status')).to_have_text(tr('Auditoría completada y guardada localmente.',lang),timeout=15000);expect(page.locator('#rows')).to_have_text('6');expect(page.locator('#alerts')).to_have_text('3');expect(page.locator('#alerttable th').first).to_have_text(tr('Alerta',lang));expect(page.locator('#kind')).to_have_text(tr('DATOS SINTÉTICOS',lang))
     href=page.locator('#exports a').last.get_attribute('href');pdf=context.request.get(url+href);assert pdf.ok and pdf.body().startswith(b'%PDF-'),lang
     page.reload(wait_until='domcontentloaded');expect(page.locator('html')).to_have_attribute('lang',lang)
     page.locator('#run').click();expect(page.locator('#status')).to_have_text(tr('Selecciona un archivo.',lang));assert not errors,errors
     print('PASS',lang,'navigation, localized controls, demo, invariant financial results, PDF, persistence, validation',flush=True)
     if os.environ.get('LEDGER_SCREENSHOTS'):
      Path(os.environ['LEDGER_SCREENSHOTS']).mkdir(parents=True,exist_ok=True);page.screenshot(path=str(Path(os.environ['LEDGER_SCREENSHOTS'])/(lang+'.png')))
    page.locator('#logout').click();page.wait_for_url(url+'/login');expect(page.locator('html')).to_have_attribute('lang',lang);assert not errors,errors
    browser.close()
  finally:p.terminate();p.wait(timeout=10)
if __name__=='__main__':main()

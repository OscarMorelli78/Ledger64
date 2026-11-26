"""Record the authenticated v0.1.1 application using a disposable synthetic tenant."""
import os,sys,socket,subprocess,tempfile,time,urllib.request
from pathlib import Path
from playwright.sync_api import sync_playwright,expect
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
OUT=ROOT/'promo-output'
OUT.mkdir(exist_ok=True)
def main():
 with tempfile.TemporaryDirectory() as d:
  with socket.socket() as s:
   s.bind(('127.0.0.1',0));port=s.getsockname()[1]
  url=f'http://127.0.0.1:{port}'
  env=dict(os.environ,BC_ROOT=d,BC_TLS='0',BC_ORIGIN=url,BC_HOSTS='127.0.0.1')
  subprocess.run([sys.executable,'-c',"from tenant import create_company,create_user; c=create_company('Synthetic demo'); create_user(c,'demo-owner','Synthetic-Test-Password-42!')"],cwd=ROOT,env=env,check=True)
  server=subprocess.Popen([sys.executable,'-m','uvicorn','secure_app:app','--host','127.0.0.1','--port',str(port),'--no-access-log'],cwd=ROOT,env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
  try:
   for _ in range(100):
    try:urllib.request.urlopen(url+'/login',timeout=.2).close();break
    except OSError:time.sleep(.1)
   else:raise RuntimeError('server not ready')
   with sync_playwright() as pw:
    browser=pw.chromium.launch(headless=True)
    auth=browser.new_context(viewport={'width':1280,'height':720})
    p=auth.new_page();p.goto(url+'/login')
    p.locator('#login').fill('demo-owner');p.locator('#password').fill('Synthetic-Test-Password-42!')
    p.locator('#login_form button').click();p.wait_for_url(url+'/')
    p.locator('#ledger_language').select_option('en')
    expect(p.locator('html')).to_have_attribute('lang','en')
    state=auth.storage_state();auth.close()
    ctx=browser.new_context(storage_state=state,viewport={'width':1280,'height':720},record_video_dir=d,record_video_size={'width':1280,'height':720})
    p=ctx.new_page();p.goto(url+'/',wait_until='networkidle')
    expect(p.locator('html')).to_have_attribute('lang','en')
    p.screenshot(path=str(OUT/'01-before.png'))
    p.locator('#demo').hover();p.wait_for_timeout(1600)
    p.locator('#demo').click()
    expect(p.locator('#rows')).to_have_text('6',timeout=15000)
    expect(p.locator('#alerts')).to_have_text('3')
    expect(p.locator('#kind')).to_contain_text('SYNTHETIC')
    p.wait_for_timeout(800)
    p.evaluate("document.querySelector('#result').scrollIntoView({behavior:'smooth',block:'start'})")
    p.wait_for_timeout(900)
    p.screenshot(path=str(OUT/'02-audit.png'))
    print('Synthetic result:',p.locator('#rows').inner_text(),p.locator('#alerts').inner_text(),p.locator('#saving').inner_text(),flush=True)
    p.wait_for_timeout(4200)
    p.evaluate("document.querySelector('#comparisontable').closest('.panel').scrollIntoView({behavior:'smooth',block:'start'})")
    p.wait_for_timeout(900)
    p.screenshot(path=str(OUT/'03-compare.png'))
    p.wait_for_timeout(4200)
    p.evaluate("document.querySelector('#exports').scrollIntoView({behavior:'smooth',block:'center'})")
    p.wait_for_timeout(800)
    pdf=p.locator('#exports a').last.get_attribute('href')
    response=ctx.request.get(url+pdf)
    assert response.ok and response.body().startswith(b'%PDF-')
    p.screenshot(path=str(OUT/'04-export.png'))
    p.wait_for_timeout(3500)
    video=p.video
    ctx.close()
    video.save_as(str(OUT/'raw.webm'))
    browser.close()
  finally:
   server.terminate();server.wait(timeout=10)
if __name__=='__main__':main()

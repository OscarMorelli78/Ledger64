"""Single-user local application, no external network calls."""
import os, sqlite3, json, secrets, hmac, html, sys
from pathlib import Path
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from datetime import datetime, timezone
from urllib.parse import urlsplit
from ingest import audit_document,audit_batch,MAX_BATCH_BODY
from decisions import approve,record_saving,snapshot
from reporting import report_pdf
from i18n import localize_html,localize_js,LANGS
from http.cookies import SimpleCookie
from ocr_review import transcribe
from engine import audit, InputError, export_csv, MAX_BYTES
BASE=Path(__file__).resolve().parent
DB=Path(os.environ.get('BC_DB',str(BASE/'data'/'audit.sqlite3')))
TOKEN=secrets.token_urlsafe(32)
HOST='127.0.0.1'; PORT=int(os.environ.get('BC_PORT','8765'))

def db():
    DB.parent.mkdir(parents=True,exist_ok=True)
    c=sqlite3.connect(DB,timeout=10); c.execute('CREATE TABLE IF NOT EXISTS reports (id TEXT PRIMARY KEY, created TEXT NOT NULL, report TEXT NOT NULL)');return c

def store(report):
    key='v3-'+report['input_sha256']+'-'+report['normalized_sha256']+('-demo' if report['synthetic'] else '-real')
    with db() as c:c.execute('INSERT OR IGNORE INTO reports VALUES (?,?,?)',(key,datetime.now(timezone.utc).isoformat(),json.dumps(report,ensure_ascii=False)))
    return key

def get(key):
    with db() as c:r=c.execute('SELECT report FROM reports WHERE id=?',(key,)).fetchone()
    return json.loads(r[0]) if r else None

class Handler(BaseHTTPRequestHandler):
    def log_message(self,*args): pass
    def send(self,status,body,typ='application/json; charset=utf-8',filename=None):
        if isinstance(body,str):body=body.encode()
        self.send_response(status);self.send_header('Content-Type',typ);self.send_header('Content-Length',str(len(body)));self.send_header('Cache-Control','no-store');self.send_header('X-Content-Type-Options','nosniff');self.send_header('Referrer-Policy','no-referrer');self.send_header('Content-Security-Policy',"default-src 'none'; script-src 'self'; style-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'")
        if filename:self.send_header('Content-Disposition',f'attachment; filename="{filename}"')
        self.end_headers();self.wfile.write(body)
    def js(self,status,obj):self.send(status,json.dumps(obj,ensure_ascii=False))
    def valid_host(self):return self.headers.get('Host')==f'{HOST}:{PORT}'
    def do_GET(self):
        if not self.valid_host():return self.js(403,{'error':'Host no permitido'})
        path=urlsplit(self.path).path
        cookie=SimpleCookie();cookie.load(self.headers.get('Cookie',''));lang=cookie['ledger64_lang'].value if 'ledger64_lang' in cookie else 'en';lang=lang if lang in LANGS else 'en'
        if path=='/':return self.send(200,localize_html((BASE/'index.html').read_text().replace('__TOKEN__',TOKEN),lang),'text/html; charset=utf-8')
        if path in ('/ui.js','/i18n.js','/style.css'):
            content=(BASE/path[1:]).read_bytes()
            if path=='/ui.js':content=localize_js(content.decode(),lang).encode()
            return self.send(200,content,'application/javascript' if path.endswith('.js') else 'text/css')
        if path=='/template.csv':return self.send(200,(BASE/'demo.csv').read_bytes(),'text/csv; charset=utf-8','demo_sintetica.csv')
        if path=='/api/decisions':
            with db() as c:return self.js(200,snapshot(c))
        if path=='/api/history':
            with db() as c:items=c.execute('SELECT id,created,report FROM reports ORDER BY created DESC LIMIT 100').fetchall()
            return self.js(200,[{'id':i,'created':t,'synthetic':json.loads(r)['synthetic']} for i,t,r in items])
        if path.startswith('/api/report/'):
            parts=path.split('/');key=parts[3];r=get(key)
            if not r:return self.js(404,{'error':'Informe inexistente'})
            if len(parts)==4:return self.js(200,r)
            if len(parts)==5 and parts[4] in ('alerts.csv','comparisons.csv','report.json','report.pdf'):
                name=parts[4]
                if name=='report.pdf':return self.send(200,report_pdf(r,lang),'application/pdf',name)
                if name=='report.json':return self.send(200,json.dumps(r,ensure_ascii=False,indent=2),filename=name)
                fields=['type','supplier','invoice','line','product','row','amount_eur','detail','status'] if name=='alerts.csv' else ['product','unit','supplier','date','unit_price_eur','reference_supplier','reference_price_eur','quantity','potential_eur']
                return self.send(200,export_csv(r['alerts' if name=='alerts.csv' else 'comparisons'],fields),'text/csv; charset=utf-8',name)
        self.js(404,{'error':'Ruta inexistente'})
    def do_POST(self):
        if not self.valid_host() or not hmac.compare_digest(self.headers.get('X-CSRF-Token',''),TOKEN):return self.js(403,{'error':'Acceso no autorizado'})
        if self.path not in ('/api/audit','/api/demo','/api/aliases','/api/savings','/api/batch','/api/ocr'):return self.js(404,{'error':'Ruta inexistente'})
        try:
            if self.path=='/api/demo':raw=(BASE/'demo.csv').read_bytes()
            else:
                n=int(self.headers.get('Content-Length','0'))
                if n<=0 or n>(MAX_BATCH_BODY if self.path=='/api/batch' else MAX_BYTES):raise InputError('Tamaño de archivo inválido')
                raw=self.rfile.read(n)
            if self.path=='/api/ocr':return self.js(200,transcribe(raw))
            if self.path in ('/api/aliases','/api/savings'):
                p=json.loads(raw)
                if not isinstance(p,dict):raise InputError('Objeto JSON requerido')
                with db() as c:result=(approve if self.path=='/api/aliases' else record_saving)(c,p)
                return self.js(200,result)
            with db() as c:report=audit_batch(json.loads(raw),c) if self.path=='/api/batch' else audit_document(raw,self.path=='/api/demo',c)
            key=store(report);self.js(200,{'id':key,'report':report})
        except (InputError,ValueError) as e:self.js(400,{'error':str(e)})
        except (OSError,sqlite3.Error):self.js(500,{'error':'Error de almacenamiento local'})

if __name__=='__main__':
    print(f'ALMER-IA Business Control: http://{HOST}:{PORT}',flush=True)
    ThreadingHTTPServer((HOST,PORT),Handler).serve_forever()

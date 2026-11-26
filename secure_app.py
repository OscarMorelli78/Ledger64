"""Authenticated FastAPI edition. Bind loopback; use TLS reverse proxy for network access."""
import os, json, secrets, hmac, hashlib, sqlite3, threading
from datetime import datetime,timezone
from pathlib import Path
from fastapi import FastAPI,Request
from fastapi.responses import HTMLResponse,JSONResponse,Response,RedirectResponse
from starlette.middleware.trustedhost import TrustedHostMiddleware
from starlette.concurrency import run_in_threadpool
from tenant import authenticate,session,revoke,company_db,SESSION_SECONDS
from engine import InputError,MAX_BYTES,export_csv
from ingest import audit_document,audit_batch,MAX_BATCH_BODY
from decisions import approve,record_saving,snapshot
from reporting import report_pdf
from i18n import locale,localize_html,localize_js,tr,CATALOG,diagnostic
from ocr_review import transcribe
import governance as gov
import intelligence as intel
BASE=Path(__file__).parent
TLS=os.environ.get('BC_TLS','1')!='0'
ORIGIN=os.environ.get('BC_ORIGIN','https://localhost' if TLS else 'http://127.0.0.1:8765')
COOKIE='__Host-bc_session' if TLS else 'bc_session'
AUDIT_SLOTS=threading.BoundedSemaphore(4)
app=FastAPI(docs_url=None,redoc_url=None,openapi_url=None)
app.add_middleware(TrustedHostMiddleware,allowed_hosts=os.environ.get('BC_HOSTS','localhost,127.0.0.1').split(','))

def now():return datetime.now(timezone.utc).isoformat()
def err(status,msg):return JSONResponse({'error':msg},status_code=status)
def event(c,u,action,obj):c.execute('INSERT INTO events(created,actor,action,object_id) VALUES(?,?,?,?)',(now(),u['id'],action,obj))
def actor(req):return session(req.cookies.get(COOKIE,''))
@app.middleware('http')
async def headers(req,call_next):
    resp=await call_next(req)
    # Preserve the original diagnostic API field and add localized presentation.
    if resp.status_code>=400 and resp.headers.get('content-type','').startswith('application/json'):
        raw=b''.join([chunk async for chunk in resp.body_iterator]);lang=locale(req)
        try:
            data=json.loads(raw)
            if isinstance(data,dict) and isinstance(data.get('error'),str):
                original=data['error'];data['message']=diagnostic(original,lang)
                resp=JSONResponse(data,status_code=resp.status_code,headers={k:v for k,v in resp.headers.items() if k.lower() not in ('content-length','content-type')})
            else:resp=Response(raw,status_code=resp.status_code,headers=dict(resp.headers))
        except (ValueError,TypeError):resp=Response(raw,status_code=resp.status_code,headers=dict(resp.headers))
    for k,v in {'Cache-Control':'no-store','X-Content-Type-Options':'nosniff','Referrer-Policy':'no-referrer','X-Frame-Options':'DENY','Content-Security-Policy':"default-src 'none'; script-src 'self'; style-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'"}.items():resp.headers[k]=v
    if TLS:resp.headers['Strict-Transport-Security']='max-age=31536000'
    return resp
async def body(req,limit):
    result=bytearray()
    async for chunk in req.stream():
        if len(result)+len(chunk)>limit:raise InputError('Archivo demasiado grande')
        result.extend(chunk)
    if not result:raise InputError('Solicitud vacía')
    return bytes(result)
# Additive synthetic-only pilot, disabled by default.
if os.environ.get('BC_PROCUREMENT_PILOT')=='1':
    from procurement_routes import make_router
    app.include_router(make_router(actor,body,ORIGIN,BASE,AUDIT_SLOTS))

@app.get('/login')
def login_page(req:Request):return HTMLResponse(localize_html((BASE/'login.html').read_text(encoding='utf-8'),locale(req)))
@app.post('/login')
async def login(req:Request):
    if req.headers.get('origin')!=ORIGIN:return err(403,'Origen no autorizado')
    try:
        p=json.loads(await body(req,4096));token=await run_in_threadpool(authenticate,p['login'],p['password'],req.client.host if req.client else 'unknown')
    except (ValueError,KeyError,TypeError,InputError):return err(400,'Solicitud inválida')
    if not token:return err(401,'Credenciales inválidas o límite temporal de intentos')
    old=req.cookies.get(COOKIE)
    if old:await run_in_threadpool(revoke,old)
    r=JSONResponse({'ok':True});r.set_cookie(COOKIE,token,max_age=SESSION_SECONDS,secure=TLS,httponly=True,samesite='strict',path='/');return r
@app.get('/')
def home(req:Request):
    u=actor(req)
    if not u:return RedirectResponse('/login',303)
    import html
    text=localize_html((BASE/'secure_index.html').read_text(encoding='utf-8'),locale(req))
    text=text.replace('__TOKEN__',u['csrf']).replace(html.escape(tr('BUSINESS CONTROL / AUDITORÍA DE COMPRAS',locale(req))), 'LEDGER64 / '+html.escape(u['name'])+' · '+html.escape(u['role']))
    return HTMLResponse(text)
@app.get('/{asset}')
def static(asset:str,req:Request):
    if asset not in ('ui.js','style.css','login.js','account.js','governance.js','intelligence.js','i18n.js','template.csv'):return err(404,'Ruta inexistente')
    if asset=='template.csv' and not actor(req):return err(401,'Inicia sesión')
    content=(BASE/('demo.csv' if asset=='template.csv' else asset)).read_bytes()
    if asset.endswith('.js') and asset!='i18n.js':content=localize_js(content.decode('utf-8'),locale(req)).encode('utf-8')
    return Response(content,media_type={'ui.js':'application/javascript','login.js':'application/javascript','account.js':'application/javascript','governance.js':'application/javascript','intelligence.js':'application/javascript','i18n.js':'application/javascript','style.css':'text/css','template.csv':'text/csv'}[asset])
@app.get('/api/{route}')
def read_api(route:str,req:Request):
    u=actor(req)
    if not u:return err(401,'Inicia sesión')
    with company_db(u['company']) as c:
        if route=='history':return [{'id':r['id'],'created':r['created'],'synthetic':json.loads(r['report'])['synthetic']} for r in c.execute('SELECT * FROM reports ORDER BY created DESC LIMIT 100')]
        if route=='decisions':return snapshot(c)
        if route=='governance':return gov.snapshot(c)
        if route=='intel-preview':
            try:return intel.preview(c,req.query_params.get('id',''))
            except InputError as e:return err(409,str(e))
        if route=='intelligence':
            try:return intel.summary(c)
            except InputError as e:return err(409,str(e))
        if route=='events' and u['role']=='owner':return [dict(r) for r in c.execute('SELECT * FROM events ORDER BY id DESC LIMIT 200')]
        if route=='me':return {k:u[k] for k in ('login','role','name')}
    return err(404,'Ruta inexistente')
@app.get('/api/report/{key}')
@app.get('/api/report/{key}/{name}')
def report(key:str,req:Request,name:str=''):
    u=actor(req)
    if not u:return err(401,'Inicia sesión')
    with company_db(u['company']) as c:
        row=c.execute('SELECT report FROM reports WHERE id=?',(key,)).fetchone()
        if not row:return err(404,'Informe inexistente')
        if name=='approved.json':
            try:return gov.released(c,key)
            except InputError as e:return err(409,str(e))
        r=json.loads(row['report']);event(c,u,'report_read' if not name else 'report_export',key)
    r['governance_status']='BORRADOR_NO_APROBADO'
    if not name:return r
    if name=='report.pdf':data,typ=report_pdf(r,locale(req)),'application/pdf'
    elif name=='report.json':data,typ=json.dumps(r,ensure_ascii=False,indent=2),'application/json'
    elif name in ('alerts.csv','comparisons.csv'):
        fields=['type','supplier','invoice','line','product','row','amount_eur','detail','status'] if name=='alerts.csv' else ['product','unit','supplier','date','unit_price_eur','reference_supplier','reference_price_eur','quantity','potential_eur']
        data,typ=export_csv([dict(x,governance_status='BORRADOR_NO_APROBADO') for x in r['alerts' if name=='alerts.csv' else 'comparisons']],fields+['governance_status']),'text/csv'
    else:return err(404,'Ruta inexistente')
    return Response(data,media_type=typ,headers={'Content-Disposition':f'attachment; filename="draft-{name}"','X-BC-Governance':'BORRADOR_NO_APROBADO'})

def perform(route,u,raw):
    if not AUDIT_SLOTS.acquire(blocking=False):raise BusyError()
    try:return perform_scoped(route,u,raw)
    finally:AUDIT_SLOTS.release()

class BusyError(Exception):pass
def perform_scoped(route,u,raw):
    with company_db(u['company']) as c:
        if route.startswith('intel-'):
            p=json.loads(raw)
            return intel.review(c,u,p) if route=='intel-review' else intel.submit(c,u,route[6:],p)
        if route in ('aliases','savings','governance-release','governance-review'):
            p=json.loads(raw)
            if not isinstance(p,dict):raise InputError('Objeto JSON requerido')
            result=gov.review(c,u,p) if route=='governance-review' else gov.submit(c,u,'release' if route=='governance-release' else route,p);event(c,u,route,result['id']);return result
        if route=='ocr':
            result=transcribe(raw,'spa+eng');event(c,u,'ocr',hashlib.sha256(raw).hexdigest());return result
        if route=='review':
            import base64,binascii
            p=json.loads(raw)
            if not isinstance(p,dict) or not isinstance(p.get('evidence'),str) or not 10<=len(p['evidence'].strip())<=1000:raise InputError('Justificación de revisión requerida')
            try:source=base64.b64decode(p['source'],validate=True);csvdata=base64.b64decode(p['csv'],validate=True)
            except (KeyError,TypeError,ValueError,binascii.Error):raise InputError('Documentos inválidos')
            if not source.startswith(b'%PDF-') or len(source)>MAX_BYTES:raise InputError('PDF original requerido')
            from pypdf import PdfReader
            from io import BytesIO
            try:
                original=PdfReader(BytesIO(source),strict=True)
                if original.is_encrypted or not 1<=len(original.pages)<=30:raise ValueError()
            except Exception:raise InputError('PDF original inválido, cifrado o fuera de límites')
            r=audit_document(csvdata,False,c);r['manual_review']={'source_sha256':hashlib.sha256(source).hexdigest(),'corrected_csv_sha256':hashlib.sha256(csvdata).hexdigest(),'evidence':p['evidence'],'reviewer':u['id'],'status':'TRANSCRIPCION_APROBADA_POR_USUARIO_NO_VERIFICACION_DOCUMENTAL_INDEPENDIENTE'}
            r['input_sha256']=r['manual_review']['source_sha256'];r['source_format']='manual_review'
        else:r=audit_batch(json.loads(raw),c) if route=='batch' else audit_document(raw,route=='demo',c)
        # Same inputs, mappings and review evidence yield same report ID; never trust client-provided tenant IDs.
        key=hashlib.sha256(json.dumps(r,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
        c.execute('INSERT OR IGNORE INTO reports VALUES(?,?,?)',(key,now(),json.dumps(r,ensure_ascii=False)));event(c,u,route,key)
        if route=='review':c.execute('INSERT OR IGNORE INTO reviews VALUES(?,?,?,?,?,?,?)',(key,now(),u['id'],r['input_sha256'],r['normalized_sha256'],p['evidence'],key))
        return {'id':key,'report':r}
@app.post('/api/{route}')
async def write_api(route:str,req:Request):
    u=await run_in_threadpool(actor,req)
    if not u:return err(401,'Inicia sesión')
    if req.headers.get('origin')!=ORIGIN or not hmac.compare_digest(req.headers.get('X-CSRF-Token',''),u['csrf']):return err(403,'Solicitud no autorizada')
    if route=='logout':
        await run_in_threadpool(revoke,req.cookies[COOKIE]);r=JSONResponse({'ok':True});r.delete_cookie(COOKIE,path='/',secure=TLS,httponly=True,samesite='strict');return r
    if u['role']=='reader':return err(403,'Permiso de escritura requerido')
    if route not in ('audit','demo','aliases','savings','batch','ocr','review','governance-release','governance-review','intel-template','intel-document','intel-roi','intel-policy','intel-review'):return err(404,'Ruta inexistente')
    try:
        raw=(BASE/'demo.csv').read_bytes() if route=='demo' else await body(req,MAX_BATCH_BODY if route in ('batch','review','intel-document') else MAX_BYTES)
        return await run_in_threadpool(perform,route,u,raw)
    except InputError as e:return err(400,str(e)[:500])
    except (ValueError,TypeError,KeyError):return err(400,'Datos inválidos o contraste aritmético fallido; no se guardó el informe')
    except (sqlite3.Error,BusyError):return err(503,'Operación no guardada; vuelve a intentarlo')

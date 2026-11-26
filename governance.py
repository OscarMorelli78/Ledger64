"""Mandatory review gate for high-impact decisions; local, tenant-scoped."""
import hashlib,json,uuid
from datetime import datetime,timezone
from engine import InputError
from decisions import approve,record_saving
POLICY='GOV-1.0'
GENESIS='0'*64

def canonical(value):return json.dumps(value,sort_keys=True,ensure_ascii=False,separators=(',',':'),allow_nan=False)
def digest(value):return hashlib.sha256(canonical(value).encode()).hexdigest()
def now():return datetime.now(timezone.utc).isoformat()
def init(c):
    c.execute('CREATE TABLE IF NOT EXISTS gov_cases(id TEXT PRIMARY KEY,kind TEXT NOT NULL,payload TEXT NOT NULL,payload_hash TEXT NOT NULL,requester TEXT NOT NULL,created TEXT NOT NULL,status TEXT NOT NULL,reviewer TEXT,reviewed TEXT,reason TEXT,policy TEXT NOT NULL)')
    c.execute('CREATE TABLE IF NOT EXISTS gov_log(seq INTEGER PRIMARY KEY,entry TEXT NOT NULL,prev TEXT NOT NULL,hash TEXT NOT NULL)')
def log(c,actor,action,obj):
    last=c.execute('SELECT seq,hash FROM gov_log ORDER BY seq DESC LIMIT 1').fetchone();seq=last[0]+1 if last else 1;prev=last[1] if last else GENESIS
    entry=canonical({'seq':seq,'actor':actor,'action':action,'object':obj,'at':now(),'policy':POLICY})
    h=digest([prev,entry]);c.execute('INSERT INTO gov_log VALUES(?,?,?,?)',(seq,entry,prev,h))
def verify_log(c):
    # Validate the chain AND reconcile its event projection against mutable cases.
    prev=GENESIS;seq=0;projection={}
    try:
        for r in c.execute('SELECT * FROM gov_log ORDER BY seq'):
            seq+=1
            if r['seq']!=seq or r['prev']!=prev or r['hash']!=digest([prev,r['entry']]):return False
            e=json.loads(r['entry']);o=e['object'];key=o['id'];action=e['action']
            if e['seq']!=seq or e['policy']!=POLICY:return False
            if action=='SUBMIT':
                if key in projection:return False
                projection[key]={'kind':o['kind'],'payload_hash':o['payload_hash'],'requester':e['actor'],'status':'PENDING'}
            elif action in ('APPROVED','REJECTED'):
                p=projection.get(key)
                if not p or p['status']!='PENDING' or p['requester']==e['actor'] or p['payload_hash']!=o['payload_hash']:return False
                p.update(status=action,reviewer=e['actor'],reason_hash=o['reason_hash'])
            else:return False
            prev=r['hash']
        rows=list(c.execute('SELECT * FROM gov_cases'))
        if len(rows)!=len(projection):return False
        for r in rows:
            p=projection.get(r['id']);data=json.loads(r['payload'])
            if not p or r['policy']!=POLICY or digest(data)!=r['payload_hash']:return False
            if any(r[k]!=p[k] for k in ('kind','payload_hash','requester','status')):return False
            if r['status']=='PENDING':
                if any(r[k] is not None for k in ('reviewer','reviewed','reason')):return False
            elif r['reviewer']!=p['reviewer'] or not r['reviewed'] or digest(r['reason'])!=p['reason_hash']:return False
        return True
    except (ValueError,TypeError,KeyError):return False

def ensure(c):
    init(c)
    if not verify_log(c):raise InputError('Cadena de gobernanza inconsistente; operación bloqueada')
def valid_text(v):
    if not isinstance(v,str) or not 10<=len(v.strip())<=1000:raise InputError('Justificación entre 10 y 1000 caracteres requerida')
    return v.strip()
def report_payload(c,p):
    key=p.get('report_id');r=c.execute('SELECT report FROM reports WHERE id=?',(key,)).fetchone()
    if not r:raise InputError('Informe inexistente')
    report=json.loads(r[0]);v=report.get('verification',{})
    if v.get('status')!='CONTRASTE_ARITMETICO_SUPERADO' or not v.get('checks') or not all(x is True for x in v['checks'].values()):raise InputError('Contraste aritmético requerido')
    if report.get('synthetic') is not False:raise InputError('Los informes sintéticos no se pueden aprobar para uso empresarial')
    authors=[x[0] for x in c.execute("SELECT DISTINCT actor FROM events WHERE object_id=? AND action IN ('audit','batch','review','demo')",(key,))]
    if not authors:raise InputError('No hay autor identificable del informe')
    return {'report_id':key,'report_hash':digest(report),'authors':sorted(authors),'evidence':valid_text(p.get('evidence'))}
def submit(c,u,kind,p):
    if u['role'] not in ('owner','analyst') or kind not in ('aliases','savings','release') or not isinstance(p,dict):raise InputError('Solicitud no autorizada o inválida')
    c.execute('BEGIN IMMEDIATE');ensure(c)
    if kind=='release':p=report_payload(c,p)
    else:
        # Validate using the exact application rule without persisting effects.
        c.execute('SAVEPOINT gov_validation')
        try:
            (approve if kind=='aliases' else record_saving)(c,p)
        finally:
            c.execute('ROLLBACK TO gov_validation');c.execute('RELEASE gov_validation')
        keys=('supplier','sku','canonical','evidence') if kind=='aliases' else ('product','unit','baseline_reference','purchase_reference','baseline_price','actual_price','quantity')
        p={k:p[k].strip() for k in keys}
    h=digest(p);old=c.execute("SELECT id,status FROM gov_cases WHERE kind=? AND payload_hash=? AND requester=? AND status IN ('PENDING','APPROVED')",(kind,h,u['id'])).fetchone()
    if old:return dict(old)
    key=uuid.uuid4().hex;c.execute('INSERT INTO gov_cases VALUES(?,?,?,?,?,?,?,?,?,?,?)',(key,kind,canonical(p),h,u['id'],now(),'PENDING',None,None,None,POLICY));log(c,u['id'],'SUBMIT',{'id':key,'kind':kind,'payload_hash':h});return {'id':key,'status':'PENDING'}
def review(c,u,p):
    if u['role']!='owner':raise InputError('Solo propietario autorizado puede resolver solicitudes')
    if not isinstance(p,dict) or p.get('decision') not in ('APPROVED','REJECTED'):raise InputError('Decisión inválida')
    reason=valid_text(p.get('reason'));c.execute('BEGIN IMMEDIATE');ensure(c)
    row=c.execute('SELECT * FROM gov_cases WHERE id=?',(p.get('id'),)).fetchone()
    if not row or row['status']!='PENDING':raise InputError('Solicitud inexistente o ya resuelta')
    if row['requester']==u['id']:raise InputError('Prohibida la autoaprobación y autorresolución')
    data=json.loads(row['payload']);kind=row['kind'];decision=p['decision']
    if digest(data)!=row['payload_hash'] or row['policy']!=POLICY:raise InputError('Contenido o política alterados')
    if decision=='APPROVED':
        if kind=='release':
            current=report_payload(c,data)
            if current['report_hash']!=data['report_hash'] or u['id'] in current['authors']:raise InputError('Informe modificado o revisor no independiente')
        else:(approve if kind=='aliases' else record_saving)(c,data)
    c.execute('UPDATE gov_cases SET status=?,reviewer=?,reviewed=?,reason=? WHERE id=?',(decision,u['id'],now(),reason,row['id']));log(c,u['id'],decision,{'id':row['id'],'payload_hash':row['payload_hash'],'reason_hash':digest(reason)});return {'id':row['id'],'status':decision}
def snapshot(c):
    init(c);rows=[]
    for r in c.execute('SELECT * FROM gov_cases ORDER BY created DESC LIMIT 200'):
        d=dict(r);d['payload']=json.loads(d['payload']);rows.append(d)
    return {'policy':POLICY,'chain_consistent':verify_log(c),'counts':{r[0]:r[1] for r in c.execute('SELECT status,count(*) FROM gov_cases GROUP BY status')},'cases':rows,'scope':'La aprobación humana no certifica documentos ni ahorros reales; cadena local no resistente a reescritura por administrador.'}
def released(c,key):
    ensure(c)
    row=c.execute('SELECT report FROM reports WHERE id=?',(key,)).fetchone()
    if not row:raise InputError('Informe inexistente')
    report=json.loads(row[0]);h=digest(report)
    for r in c.execute("SELECT * FROM gov_cases WHERE kind='release' AND status='APPROVED' ORDER BY reviewed DESC"):
        p=json.loads(r['payload'])
        if p['report_id']==key and p['report_hash']==h and digest(p)==r['payload_hash'] and r['policy']==POLICY and r['reviewer']!=r['requester']:
            # Require an actual matching approval event, not merely a mutable status flag.
            if not any((e:=json.loads(x[0]))['action']=='APPROVED' and e['actor']==r['reviewer'] and e['object']['id']==r['id'] and e['object']['payload_hash']==r['payload_hash'] and e['object']['reason_hash']==digest(r['reason']) for x in c.execute('SELECT entry FROM gov_log')):continue
            return {'report':report,'governance':{'status':'APROBADO_PARA_USO_INTERNO','case_id':r['id'],'policy':POLICY,'reviewer':r['reviewer'],'reviewed':r['reviewed'],'report_hash':h,'reason':r['reason'],'scope':'No certifica documentos originales, pérdidas ni ahorros reales'}}
    raise InputError('Informe sin aprobación vigente')

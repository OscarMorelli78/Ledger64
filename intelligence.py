"""Tenant-local reviewed documents and ROI, with event-sourced policy controls.
No inferred amounts, no external LLM, no claim of independently verified payments.
"""
import base64,binascii,csv,io,json,hashlib,uuid
from datetime import datetime,timezone,timedelta,date
from fractions import Fraction
from decimal import Decimal
from engine import FIELDS,InputError,MAX_BYTES,parse,money,num
from flexible import value
from ingest import normalize
from governance import canonical,digest,valid_text

DEFAULT={'version':1,'review_hours':72,'template_days':365,'max_baseline_days':180}
ZERO='0'*64

def clock():return datetime.now(timezone.utc)
def init(c):
    c.execute('CREATE TABLE IF NOT EXISTS intel_events(seq INTEGER PRIMARY KEY,body TEXT NOT NULL,prev TEXT NOT NULL,hash TEXT NOT NULL)')
    c.execute('CREATE TABLE IF NOT EXISTS intel_sources(id TEXT PRIMARY KEY,raw BLOB NOT NULL)')
    c.execute('CREATE TABLE IF NOT EXISTS intel_head(singleton INTEGER PRIMARY KEY CHECK(singleton=1),seq INTEGER NOT NULL,hash TEXT NOT NULL)')
    c.execute('INSERT OR IGNORE INTO intel_head VALUES(1,0,?)',(ZERO,))
def fail(msg):raise InputError(msg)
def state(c):
    init(c);prev=ZERO;cases={};policy=dict(DEFAULT);n=0
    for r in c.execute('SELECT * FROM intel_events ORDER BY seq'):
        n+=1
        if r['seq']!=n or r['prev']!=prev or r['hash']!=digest([prev,r['body']]):fail('Registro de inteligencia alterado')
        e=json.loads(r['body']);p=e['data'];kind=e['action'];k=p['id']
        if kind=='SUBMIT':
            if k in cases or p['policy']!=policy:fail('Secuencia inválida')
            cases[k]=dict(p,status='PENDING',requester=e['actor'],created=e['at'])
        elif kind in ('APPROVED','REJECTED','REVOKED'):
            x=cases.get(k)
            if not x or x['status']!=('APPROVED' if kind=='REVOKED' else 'PENDING') or (kind!='REVOKED' and x['requester']==e['actor']):fail('Transición inválida')
            x.update(status=kind,reviewer=e['actor'],reviewed=e['at'],reason=p['reason'])
            if kind=='APPROVED' and x['kind']=='policy':policy=dict(x['payload'],version=policy['version']+1)
        else:fail('Evento desconocido')
        prev=r['hash']
    head=c.execute("SELECT seq,hash FROM intel_head WHERE singleton=1").fetchone()
    if head is None or tuple(head)!=(n,prev):fail("Cabecera de auditoría inconsistente")
    return cases,policy,prev,n

def append(c,u,action,data):
    _,_,prev,n=state(c);b=canonical({'action':action,'actor':u['id'],'at':clock().isoformat(),'data':data});h=digest([prev,b]);c.execute('INSERT INTO intel_events VALUES(?,?,?,?)',(n+1,b,prev,h));c.execute('UPDATE intel_head SET seq=?,hash=? WHERE singleton=1',(n+1,h))
def active(x,kind=None):
    return x and x['status']=='APPROVED' and (kind is None or x['kind']==kind) and (x['kind']!='template' or clock()<datetime.fromisoformat(x['reviewed'])+timedelta(days=x['policy']['template_days']))
def source(c,key):
    r=c.execute('SELECT raw FROM intel_sources WHERE id=?',(key,)).fetchone()
    if not r or hashlib.sha256(r[0]).hexdigest()!=key:fail('Documento original ausente o alterado')
    return r[0]
def decode(s):
    try:b=base64.b64decode(s,validate=True)
    except (ValueError,TypeError,binascii.Error):fail('Archivo inválido')
    if not 0<len(b)<=MAX_BYTES:fail('Tamaño de archivo inválido')
    return b

def template(p):
    m=p.get('mapping'); sep=p.get('delimiter',','); supplier=p.get('supplier')
    if not isinstance(m,dict) or set(m)!=set(FIELDS) or any(not isinstance(v,str) or not v.strip() or len(v)>200 for v in m.values()) or len(set(m.values()))!=len(FIELDS):fail('Mapa completo y unívoco requerido')
    if sep not in (',',';','\t') or not isinstance(supplier,str) or not 1<=len(supplier.strip())<=200 or type(p.get('spanish')) is not bool:fail('Configuración de plantilla inválida')
    return dict(mapping=m,delimiter=sep,supplier=supplier.strip(),spanish=p['spanish'],evidence=valid_text(p.get('evidence')))
def mapped(raw,t):
    try:
        reader=csv.DictReader(io.StringIO(raw.decode('utf-8-sig'),newline=''),delimiter=t['delimiter'],strict=True)
        if not reader.fieldnames or len(reader.fieldnames)>100 or len(set(reader.fieldnames))!=len(reader.fieldnames) or not set(t['mapping'].values())<=set(reader.fieldnames):fail('Cabecera incompatible con plantilla')
        out=io.StringIO(newline='');w=csv.writer(out);w.writerow(FIELDS)
        for i,r in enumerate(reader):
            if i>=10000 or None in r or any(v is None for v in r.values()):fail('Fila inválida')
            vals=[value(r[t['mapping'][f]],f,t['spanish']) for f in FIELDS]
            if vals[0]!=t['supplier']:fail('Proveedor no coincide con plantilla')
            w.writerow(vals)
        return out.getvalue().encode()
    except (UnicodeError,csv.Error):fail('CSV incompatible')
def lines(c,p,cases):
    raw=source(c,p['source']);tid=p.get('template_id')
    if tid:
        t=cases.get(tid)
        if not active(t,'template'):fail('Plantilla no vigente')
        normalized=mapped(raw,t['payload'])
    else:_,normalized=normalize(raw)
    if hashlib.sha256(normalized).hexdigest()!=p['normalized']:fail('Normalización ha cambiado')
    rows=parse(normalized);seen=set()
    for r in rows:
        key=(r['supplier'].casefold(),r['invoice'].casefold(),r['line'].casefold())
        if key in seen or r['total']!=r['reported']:fail('Duplicado o descuadre: revisión requerida')
        seen.add(key)
    return rows

def document(c,p,cases):
    raw=decode(p.get('file'));key=hashlib.sha256(raw).hexdigest();tid=p.get('template_id') or None
    if tid:
        t=cases.get(tid)
        if not active(t,'template'):fail('Plantilla no vigente')
        normalized=mapped(raw,t['payload'])
    else:_,normalized=normalize(raw)
    if type(p.get('synthetic')) is not bool:fail('Clasificación real/sintética obligatoria')
    c.execute('INSERT OR IGNORE INTO intel_sources VALUES(?,?)',(key,raw))
    data={'source':key,'normalized':hashlib.sha256(normalized).hexdigest(),'template_id':tid,'synthetic':p['synthetic'],'evidence':valid_text(p.get('evidence'))}
    lines(c,data,cases);return data

def get_line(c,cases,ref):
    if not isinstance(ref,dict) or not isinstance(ref.get('document'),str):fail('Referencia inválida')
    x=cases.get(ref.get('document'))
    if not active(x,'document'):fail('Documento no aprobado')
    rows=lines(c,x['payload'],cases);i=ref.get('row')
    if type(i) is not int or not 1<=i<=len(rows):fail('Número de línea inválido')
    r=rows[i-1];return x,r

def roi(c,p,cases,policy):
    b,br=get_line(c,cases,p.get('baseline'));a,ar=get_line(c,cases,p.get('actual'))
    if b['payload']['synthetic']!=a['payload']['synthetic']:fail('No mezclar documentos reales y sintéticos')
    days=(date.fromisoformat(ar['date'])-date.fromisoformat(br['date'])).days
    if not 0<days<=policy['max_baseline_days'] or (br['product'],br['unit'])!=(ar['product'],ar['unit']):fail('Base temporal o producto/unidad no comparable')
    cost=num(p.get('implementation_cost_eur') if isinstance(p.get('implementation_cost_eur'),str) else '', 'coste');gross=(Fraction(br['total'])/Fraction(br['quantity'])-Fraction(ar['total'])/Fraction(ar['quantity']))*Fraction(ar['quantity'])
    if gross<=0:fail('No existe reducción positiva')
    rounded=Decimal(gross.numerator)/Decimal(gross.denominator);g=money(rounded);net=money(Decimal(g)-cost)
    identity=[ar[k].casefold() for k in ('supplier','invoice','line')]
    return {'baseline':{k:p['baseline'][k] for k in ('document','row')},'actual':{k:p['actual'][k] for k in ('document','row')},'actual_identity':identity,'gross_eur':g,'implementation_cost_eur':str(cost),'net_eur':net,'roi_pct':money(Decimal(net)/cost*100) if cost else None,'synthetic':a['payload']['synthetic'],'evidence':valid_text(p.get('evidence')),'scope':'Reducción de precio documentada y revisada; no prueba pago ni causalidad del servicio.'}

def submit(c,u,kind,p):
    if not isinstance(p,dict) or u['role'] not in ('owner','analyst'):fail('Solicitud inválida')
    c.execute('BEGIN IMMEDIATE');cases,policy,_,_=state(c)
    if kind=='template':data=template(p)
    elif kind=='document':data=document(c,p,cases)
    elif kind=='roi':data=roi(c,p,cases,policy)
    elif kind=='policy':
        if u['role']!='owner':fail('Solo propietario')
        data={k:p.get(k) for k in ('review_hours','template_days','max_baseline_days')}
        if any(type(data[k]) is not int or not lo<=data[k]<=hi for k,lo,hi in [('review_hours',1,168),('template_days',1,730),('max_baseline_days',1,730)]):fail('Política fuera de límites')
    else:fail('Tipo desconocido')
    for k,x in cases.items():
        if x['kind']==kind and x['payload']==data and x['status'] in ('PENDING','APPROVED') and ((x['status']=='PENDING' and x['policy']==policy and clock()<datetime.fromisoformat(x['created'])+timedelta(hours=policy['review_hours'])) or active(x)):return {'id':k,'status':x['status']}
    k=uuid.uuid4().hex;append(c,u,'SUBMIT',dict(id=k,kind=kind,payload=data,policy=policy));return {'id':k,'status':'PENDING'}
def review(c,u,p):
    if u['role']!='owner' or not isinstance(p,dict):fail('Solo propietario')
    reason=valid_text(p.get('reason'));decision=p.get('decision');c.execute('BEGIN IMMEDIATE');cases,policy,_,_=state(c);k=p.get('id');x=cases.get(k)
    if not x or decision not in ('APPROVED','REJECTED','REVOKED'):fail('Decisión inválida')
    if decision=='REVOKED':
        if not active(x) or x['kind']=='policy':fail('No revocable; proponga otra política si procede')
    else:
        if x['status']!='PENDING' or x['requester']==u['id']:fail('Revisión independiente requerida')
        if decision=='APPROVED':
            if x['policy']!=policy or clock()>=datetime.fromisoformat(x['created'])+timedelta(hours=policy['review_hours']):fail('Solicitud caducada o política obsoleta')
            if x['kind']=='document':lines(c,x['payload'],cases)
            if x['kind']=='roi':
                current=roi(c,x['payload'],cases,policy)
                if current!=x['payload']:fail('Evidencias modificadas')
                if any(active(z,'roi') and z['payload']['actual_identity']==current['actual_identity'] and z['payload']['synthetic']==current['synthetic'] for z in cases.values()):fail('Compra ya contabilizada')
    append(c,u,decision,{'id':k,'reason':reason});return {'id':k,'status':decision}
def summary(c):
    cases,policy,head,n=state(c);groups={k:{'gross':Decimal(0),'cost':Decimal(0),'count':0} for k in ('real','synthetic')};invalid=[]
    for x in cases.values():
        if not active(x,'roi'):continue
        p=x['payload']
        try:
            if roi(c,p,cases,x['policy'])!=p:fail('Evidencia inconsistente')
        except InputError:invalid.append(x['id']);continue
        g=groups['synthetic' if p['synthetic'] else 'real'];g['gross']+=Decimal(p['gross_eur']);g['cost']+=Decimal(p['implementation_cost_eur']);g['count']+=1
    for g in groups.values():
        net=g['gross']-g['cost'];g.update(net=money(net),roi_pct=money(net/g['cost']*100) if g['cost'] else None,gross=money(g['gross']),cost=money(g['cost']))
    return {'policy':policy,'head':head,'events':n,'cases':list(cases.values()),'roi':groups,'invalidated_roi':invalid,'scope':'Evidencia documental revisada, no ahorro causal ni pago comprobado. Cadena local, no anclada externamente.'}

def preview(c,key):
    cases,_,_,_=state(c);x=cases.get(key)
    if not x or x['kind']!='document' or x['status'] not in ('PENDING','APPROVED'):fail('Documento no disponible')
    return {'id':key,'status':x['status'],'source_sha256':x['payload']['source'],'rows':[dict(r,ordinal=i,**{k:str(r[k]) for k in ('quantity','total','reported','price')}) for i,r in enumerate(lines(c,x['payload'],cases),1)]}

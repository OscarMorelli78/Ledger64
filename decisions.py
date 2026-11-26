"""Human-approved supplier SKU mappings and realized-savings evidence. Local only."""
import sqlite3, json, hashlib, csv, io
from decimal import Decimal
from datetime import datetime,timezone
from engine import InputError,FIELDS,parse,num,money

def init(c):
    c.execute('CREATE TABLE IF NOT EXISTS aliases (supplier TEXT, sku TEXT, canonical TEXT NOT NULL, evidence TEXT NOT NULL, approved_at TEXT NOT NULL, PRIMARY KEY(supplier,sku))')
    c.execute('CREATE TABLE IF NOT EXISTS savings (id TEXT PRIMARY KEY, payload TEXT NOT NULL, created TEXT NOT NULL)')

def stamp():return datetime.now(timezone.utc).isoformat()
def text(v):
    if not isinstance(v,str) or not v.strip() or len(v)>500:raise InputError('Texto obligatorio de hasta 500 caracteres')
    return v.strip()
def approve(c,p):
    s,sku,canonical,evidence=[text(p.get(k)) for k in ('supplier','sku','canonical','evidence')]
    if any(len(x)>200 for x in (s,sku,canonical)):raise InputError('Identificador demasiado largo')
    init(c); old=c.execute('SELECT canonical FROM aliases WHERE supplier=? AND sku=?',(s,sku)).fetchone()
    if old and old[0]!=canonical:raise InputError('Homologación conflictiva; no se sobrescribe una aprobación previa')
    c.execute('INSERT OR IGNORE INTO aliases VALUES (?,?,?,?,?)',(s,sku,canonical,evidence,stamp()))
    return {'supplier':s,'sku':sku,'canonical':canonical,'evidence':evidence}
def apply(raw,c):
    init(c); mappings={(s,k):(v,e) for s,k,v,e in c.execute('SELECT supplier,sku,canonical,evidence FROM aliases')};changes=[]
    r=csv.DictReader(io.StringIO(raw.decode('utf-8-sig')));out=io.StringIO(newline='');w=csv.DictWriter(out,fieldnames=FIELDS);w.writeheader()
    for i,row in enumerate(r,2):
        pair=(row['supplier'].strip(),row['product'].strip())
        if pair in mappings:
            canonical,evidence=mappings[pair];row['product']=canonical;changes.append({'row':i,'supplier':pair[0],'original':pair[1],'canonical':canonical,'evidence':evidence})
        w.writerow(row)
    return (out.getvalue().encode() if changes else raw),changes

def record_saving(c,p):
    """User-declared realized savings: supporting references required, not independently verified."""
    init(c); record={k:text(p.get(k)) for k in ('product','unit','baseline_reference','purchase_reference','baseline_price','actual_price','quantity')}
    if record['unit'] not in ('kg','l','ud'):raise InputError('Unidad normalizada requerida')
    if record['baseline_reference']==record['purchase_reference']:raise InputError('Referencias de base y compra deben ser distintas')
    b,a,q=[num(record[k],k) for k in ('baseline_price','actual_price','quantity')]
    if q<=0 or b<=a:raise InputError('No hay ahorro positivo')
    record['declared_saving_eur']=money((b-a)*q);record['status']='DECLARADO_NO_VERIFICADO';record['baseline_price']=str(b.normalize());record['actual_price']=str(a.normalize());record['quantity']=str(q.normalize())
    key=hashlib.sha256(json.dumps([record['purchase_reference'],record['product'],record['unit']],ensure_ascii=False).encode()).hexdigest()
    payload=json.dumps(record,ensure_ascii=False,sort_keys=True);old=c.execute('SELECT payload FROM savings WHERE id=?',(key,)).fetchone()
    if old and old[0]!=payload:raise InputError('Compra ya registrada con otros datos')
    c.execute('INSERT OR IGNORE INTO savings VALUES (?,?,?)',(key,payload,stamp()));return record

def snapshot(c):
    init(c);return {'aliases':[dict(zip(('supplier','sku','canonical','evidence','approved_at'),r)) for r in c.execute('SELECT * FROM aliases ORDER BY supplier,sku')],'savings':[json.loads(r[0]) for r in c.execute('SELECT payload FROM savings ORDER BY created DESC')]}

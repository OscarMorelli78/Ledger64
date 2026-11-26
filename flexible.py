"""Explicit Spanish/English purchase schemas; never infer missing money."""
import csv,io,re,unicodedata
from datetime import datetime,date
from decimal import Decimal
from engine import FIELDS,InputError,parse,money
from collections import defaultdict

def key(v):
    return ' '.join(re.sub(r'[^a-z0-9]+',' ',unicodedata.normalize('NFKD',str(v)).encode('ascii','ignore').decode().lower()).split())
ALIASES=dict(zip(FIELDS,[('proveedor','supplier'),('factura','numero factura','invoice'),('linea','line','posicion'),('fecha','date'),('producto','referencia','sku','product'),('unidad','unit'),('cantidad','quantity'),('neto eur','neto sin iva','net eur'),('portes eur','transporte eur','shipping eur'),('descuento eur','discount eur'),('total sin iva','total declarado eur','reported total eur')]))
LOOKUP={key(a):f for f,aliases in ALIASES.items() for a in aliases+(f,)}
UNITS={'kg':'kg','kilogramo':'kg','kilogramos':'kg','g':'g','gramos':'g','l':'l','litros':'l','ml':'ml','ud':'ud','unidades':'ud','unidad':'ud'}
def value(v,f,spanish):
    if isinstance(v,bool) or v is None:raise InputError('Campo vacío o booleano: '+f)
    if f=='date':
        if isinstance(v,datetime):
            if v.time()!=datetime.min.time():raise InputError('Fecha con hora')
            return v.date().isoformat()
        if isinstance(v,date):return v.isoformat()
        s=str(v).strip()
        if re.fullmatch(r'\d{2}/\d{2}/\d{4}',s):return datetime.strptime(s,'%d/%m/%Y').date().isoformat()
        return s
    if f=='unit':return UNITS.get(key(v),str(v).strip())
    if f in FIELDS[6:]:
        if isinstance(v,(int,float,Decimal)):return format(Decimal(str(v)),'f')
        s=str(v).strip()
        if spanish and ',' in s:
            if not re.fullmatch(r'(?:\d+|\d{1,3}(?:\.\d{3})+),\d{1,6}',s):raise InputError('Número ambiguo: '+s)
            s=s.replace('.','').replace(',','.')
        elif spanish and re.fullmatch(r'\d{1,3}\.\d{3}',s):raise InputError('Separador ambiguo: '+s)
        return s
    return str(v).strip()
def convert(rows):
    rows=[list(r) for r in rows if any(v is not None and str(v).strip() for v in r)]
    candidates=[]
    for i,r in enumerate(rows[:20]):
        mapped=[LOOKUP.get(key(v)) for v in r]
        if set(FIELDS)<=set(mapped):candidates.append((i,mapped))
    if len(candidates)!=1:raise InputError('Se requiere una cabecera inequívoca con los 11 campos de compra')
    i,mapped=candidates[0]
    if any(mapped.count(f)!=1 for f in FIELDS):raise InputError('Cabecera duplicada')
    spanish=any(key(v) in ('proveedor','factura','cantidad') for v in rows[i]); out=io.StringIO(newline='');w=csv.writer(out);w.writerow(FIELDS)
    for r in rows[i+1:]:
        if len(r)!=len(mapped):raise InputError('Fila de longitud irregular')
        w.writerow([value(r[mapped.index(f)],f,spanish) for f in FIELDS])
    raw=out.getvalue().encode();parse(raw);return raw

def invoice_text(text):
    # Two explicit layouts; one invoice per document; requires line totals and document reconciliation.
    lines=[s.strip() for s in text.splitlines() if s.strip()]
    labels={'proveedor':'supplier','supplier':'supplier','factura':'invoice','invoice':'invoice','fecha':'date','date':'date','moneda':'currency','currency':'currency','total sin iva':'total','total excl vat':'total'}
    meta={}; table=[]
    for s in lines:
        if ':' in s:
            a,b=s.split(':',1); f=labels.get(key(a))
            if f:
                if f in meta:raise InputError('Metadato duplicado')
                meta[f]=b.strip();continue
        if '|' in s:table.append(s.split('|'))
        elif key(s) not in ('factura comercial','commercial invoice'):raise InputError('Texto de factura no reconocido: revisión requerida')
    if set(meta)!=set(labels.values()) or meta['currency']!='EUR' or not table:raise InputError('Factura incompleta o moneda no EUR')
    header=table[0]; mapped=[LOOKUP.get(key(x)) for x in header]; required=FIELDS[2:3]+FIELDS[4:]
    if sorted(x or '' for x in mapped)!=sorted(required):raise InputError('Tabla de factura no reconocida')
    rows=[FIELDS]; total=Decimal(0)
    for r in table[1:]:
        if len(r)!=len(mapped):raise InputError('Fila factura ambigua')
        d=dict(zip(mapped,r));d.update({f:meta[f] for f in ('supplier','invoice','date')}); vals=[value(d[f],f,True) for f in FIELDS];rows.append(vals)
        from engine import num
        total+=num(vals[-1],'total')
    from engine import num
    if total!=num(value(meta['total'],'reported_total_eur',True),'total factura'):raise InputError('Total factura no conciliado')
    out=io.StringIO(newline='');csv.writer(out).writerows(rows);raw=out.getvalue().encode();parse(raw);return raw

def monthly(raw):
    rows=parse(raw); groups=defaultdict(list)
    for r in rows:groups[(r['supplier'].casefold(),r['invoice'].casefold(),r['line'].casefold())].append(r)
    sums=defaultdict(lambda:Decimal(0));excluded=0
    for g in groups.values():
        r=g[0]; fields=('date','product','unit','quantity','total','reported')
        if any(any(x[k]!=r[k] for k in fields) for x in g) or abs(r['total']-r['reported'])>Decimal('.01'):excluded+=len(g);continue
        excluded+=len(g)-1;sums[r['date'][:7]]+=r['total']
    return {'months':[{'month':k,'eligible_cost_eur':money(v)} for k,v in sorted(sums.items())],'excluded_rows':excluded,'scope':'Costes del archivo, no contabilidad completa ni ahorro realizado'}

"""Deterministic EUR purchase audit. All money calculations use Decimal."""
import csv, io, hashlib, json, re
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from datetime import date
from collections import defaultdict
D=Decimal
FIELDS='supplier,invoice,line,date,product,unit,quantity,net_eur,shipping_eur,discount_eur,reported_total_eur'.split(',')
UNITS={'kg':('kg',D(1)),'g':('kg',D('.001')),'l':('l',D(1)),'ml':('l',D('.001')),'ud':('ud',D(1))}
MAX_BYTES=2_000_000
class InputError(ValueError): pass

def money(x): return str(x.quantize(D('.01'),rounding=ROUND_HALF_UP))
def num(x, field):
    try:
        if not re.fullmatch(r'[0-9]{1,12}(?:\.[0-9]{1,6})?',x): raise ValueError()
        return D(x)
    except (ValueError,InvalidOperation): raise InputError(f'{field}: número decimal positivo o cero requerido')

def parse(raw):
    if not raw or len(raw)>MAX_BYTES: raise InputError('CSV vacío o superior a 2 MB')
    try: text=raw.decode('utf-8-sig')
    except UnicodeError: raise InputError('Se requiere CSV UTF-8')
    try:
        reader=csv.DictReader(io.StringIO(text,newline=''),strict=True)
        if reader.fieldnames!=FIELDS: raise InputError('Cabecera incorrecta. Descarga la plantilla.')
        rows=[]
        for i,r in enumerate(reader,2):
            if i>10002: raise InputError('Máximo 10.000 líneas')
            if None in r or any(v is None for v in r.values()): raise InputError(f'Fila {i}: número de columnas incorrecto')
            try:
                r={k:v.strip() for k,v in r.items()}
                for k in ('supplier','invoice','line','product'):
                    if not r[k] or len(r[k])>200: raise InputError(f'{k}: identificador inválido')
                dt=date.fromisoformat(r['date']);
                if r['date']!=dt.isoformat(): raise InputError('Fecha ISO requerida')
                if r['unit'] not in UNITS: raise InputError('Unidad no admitida')
                q,net,ship,discount,reported=[num(r[k],k) for k in FIELDS[6:]]
                if q<=0 or discount>net: raise InputError('Cantidad cero o descuento superior al neto')
                unit,factor=UNITS[r['unit']]; total=net+ship-discount
                rows.append(dict(supplier=r['supplier'],invoice=r['invoice'],line=r['line'],date=dt.isoformat(),product=r['product'],unit=unit,quantity=q*factor,total=total,reported=reported,row=i,price=total/(q*factor)))
            except (ValueError,InvalidOperation) as e: raise InputError(f'Fila {i}: {e}') from e
        if not rows: raise InputError('No hay líneas de compra')
        return rows
    except csv.Error as e: raise InputError(f'CSV inválido: {e}') from e

def audit(raw, synthetic=False):
    rows=parse(raw); alerts=[]; seen={}; clean=[]; groups=defaultdict(list); comparison=[]
    def alert(kind,r,amount,detail):
        alerts.append(dict(type=kind,supplier=r['supplier'],invoice=r['invoice'],line=r['line'],product=r['product'],row=r['row'],amount_eur=money(amount) if amount is not None else None,detail=detail,status='REVISAR'))
    # Repeated IDs are excluded from price analysis; conflicting copies invalidate all matching lines.
    for r in rows: groups[(r['supplier'].casefold(),r['invoice'].casefold(),r['line'].casefold())].append(r)
    for g in groups.values():
        if len(g)>1:
            first=g[0]; identical=all(all(x[k]==first[k] for k in ('date','product','unit','quantity','total','reported')) for x in g)
            for r in g[1:]: alert('DUPLICADO_POSIBLE' if identical else 'ID_CONFLICTIVO',r,r['reported'] if identical else None,'Identificador proveedor/factura/línea repetido; comprobar documento y pago.')
            if identical: clean.append(first)
        else: clean.append(g[0])
    comparable=[]
    for r in clean:
        if abs(r['total']-r['reported'])>D('.01'):
            alert('DESCUADRE',r,abs(r['total']-r['reported']),'Total declarado difiere de neto + portes − descuento; excluido de comparación.')
        else: comparable.append(r)
    buckets=defaultdict(list)
    for r in comparable: buckets[(r['product'],r['unit'])].append(r)
    for (product,unit),g in sorted(buckets.items()):
        # Only latest observed price per supplier; compare observations within 30 days of newest date.
        latest=max(date.fromisoformat(r['date']) for r in g); by=defaultdict(list)
        for r in sorted(g,key=lambda x:(x['date'],x['row'])): by[r['supplier'].casefold()].append(r)
        options=[]
        for s,rr in by.items():
            last_date=rr[-1]['date']; recent=[r for r in rr if r['date']==last_date]
            if (latest-date.fromisoformat(last_date)).days<=30:
                q=sum(r['quantity'] for r in recent); cost=sum(r['total'] for r in recent)
                options.append((cost/q,rr[-1]['supplier'],q,last_date))
            dates=defaultdict(list)
            for r in rr: dates[r['date']].append(r)
            daily=sorted(dates)
            if len(daily)>1:
                prev,cur=[dates[d] for d in daily[-2:]]
                old=sum(r['total'] for r in prev)/sum(r['quantity'] for r in prev)
                new=sum(r['total'] for r in cur)/sum(r['quantity'] for r in cur)
                if old>0 and new>=old*D('1.10'):
                    alert('SUBIDA_PRECIO',cur[-1],None,f'Precio unitario +{money((new/old-1)*100)}%; verificar condiciones.')
        if len(options)<2: continue
        options.sort(); best=options[0];
        for price,s,q,dt in options:
            saving=(price-best[0])*q
            comparison.append(dict(product=product,unit=unit,supplier=s,date=dt,unit_price_eur=str(price.quantize(D('.000001'),rounding=ROUND_HALF_UP)),reference_supplier=best[1],reference_price_eur=str(best[0].quantize(D('.000001'),rounding=ROUND_HALF_UP)),quantity=str(q),potential_eur=money(saving)))
    potential=sum((D(x['potential_eur']) for x in comparison),D(0))
    return dict(schema_version=1,synthetic=synthetic,input_sha256=hashlib.sha256(raw).hexdigest(),rows=len(rows),eligible_rows=len(comparable),review_alerts=len(alerts),potential_saving_eur=money(potential),confirmed_loss_eur=None,alerts=alerts,comparisons=comparison,limitations=['Ahorro potencial sobre cantidades de la última fecha por proveedor, no ahorro mensual ni realizado.','Solo comparar productos idénticos mediante código común y unidades admitidas; confirmar calidad, mínimos, portes, disponibilidad y condiciones.','Importes sin IVA; portes y descuentos asignados a cada línea. No se admiten abonos ni moneda distinta de EUR.','Duplicados y descuadres requieren comprobación documental y bancaria; no se suman como pérdidas.'])

def safe_cell(v):
    if v is None:return ''
    s=str(v)
    return "'"+s if s.lstrip().startswith(('=','+','-','@','\t','\r','\n')) else s

def export_csv(rows,fields):
    buf=io.StringIO(newline=''); w=csv.DictWriter(buf,fieldnames=fields);w.writeheader()
    for r in rows:w.writerow({k:safe_cell(r.get(k)) for k in fields})
    return buf.getvalue().encode('utf-8-sig')

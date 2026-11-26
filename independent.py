"""Independent arithmetic reconciliation; no call to engine.audit/parse."""
import csv,io
from fractions import Fraction as F
from collections import defaultdict
from datetime import date

def rounded(x,places=2):
    # nonnegative half-up in integer arithmetic
    scale=10**places;n=(2*x.numerator*scale+x.denominator)//(2*x.denominator)
    return f'{n//scale}.{n%scale:0{places}d}'
def cents(x):return rounded(x)

def verify(raw,report):
    groups=defaultdict(list)
    for r in csv.DictReader(io.StringIO(raw.decode('utf-8-sig'))):
        r={k:v.strip() for k,v in r.items()};unit=r['unit'];factor=F(1,1000) if unit in ('g','ml') else F(1)
        x=(r['date'],r['product'],{'g':'kg','ml':'l'}.get(unit,unit),F(r['quantity'])*factor,F(r['net_eur'])+F(r['shipping_eur'])-F(r['discount_eur']),F(r['reported_total_eur']))
        groups[tuple(r[k].casefold() for k in ('supplier','invoice','line'))].append(x)
    valid=[];months=defaultdict(F);alert_count=0;count=sum(map(len,groups.values()))
    for (s,_,_),g in groups.items():
        alert_count+=len(g)-1
        if len(set(g))!=1:continue
        day,p,u,q,total,reported=g[0]
        if abs(total-reported)>F(1,100):alert_count+=1;continue
        valid.append((s,day,p,u,q,total));months[day[:7]]+=total
    daily=defaultdict(lambda:[F(0),F(0)])
    for s,d,p,u,q,t in valid:
        a=daily[s,p,u,d];a[0]+=q;a[1]+=t
    suppliers=defaultdict(list)
    for (s,p,u,d),(q,t) in daily.items():suppliers[s,p,u].append((d,q,t/q))
    products=defaultdict(list)
    for (s,p,u),lst in suppliers.items():
        lst.sort();d,q,price=lst[-1];products[p,u].append((s,d,q,price))
        if len(lst)>1 and lst[-2][2]>0 and price>=lst[-2][2]*F(11,10):alert_count+=1
    expected={}
    for (p,u),lst in products.items():
        newest=max(date.fromisoformat(d) for _,d,_,_ in lst)
        current=[x for x in lst if (newest-date.fromisoformat(x[1])).days<=30]
        if len(current)<2:continue
        best=min(x[3] for x in current)
        for s,d,q,price in current:expected[p,u,s,d]=(cents((price-best)*q),rounded(price,6),rounded(best,6),q)
    actual={(x['product'],x['unit'],x['supplier'].casefold(),x['date']):(x['potential_eur'],x['unit_price_eur'],x['reference_price_eur'],F(x['quantity'])) for x in report['comparisons']}
    checks={'rows':count==report['rows'],'eligible':len(valid)==report['eligible_rows'],'alerts_count':alert_count==report['review_alerts'],'comparisons':expected==actual and len(actual)==len(report['comparisons']),'potential':cents(sum((F(x[0]) for x in expected.values()),F(0)))==report['potential_saving_eur'],'monthly':{k:cents(v) for k,v in months.items()}=={r['month']:r['eligible_cost_eur'] for r in report['monthly_costs']['months']},'excluded':count-len(valid)==report['monthly_costs']['excluded_rows']}
    if not all(checks.values()):raise ValueError('Contraste financiero independiente fallido: '+','.join(k for k,v in checks.items() if not v))
    return {'status':'CONTRASTE_ARITMETICO_SUPERADO','method':'Fraction / implementación independiente','checks':checks,'scope':'No valida identidad comercial, documentos originales ni ahorro realizado'}

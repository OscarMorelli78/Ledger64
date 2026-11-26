import csv,io,json,time,hashlib,sys,zipfile
from collections import Counter
from pathlib import Path
from engine import FIELDS
from ingest import normalize,finish
from openpyxl import Workbook
from reportlab.pdfgen import canvas
SECTORS='agricultura hosteleria comercio logistica construccion farmacia clinicas educacion industria energia turismo automocion tecnologia telecomunicaciones limpieza seguridad textil alimentacion mantenimiento servicios_profesionales'.split()
def make(row,fmt):
 if fmt=='csv':
  b=io.StringIO(); w=csv.writer(b);w.writerow(FIELDS);w.writerow(row);return b.getvalue().encode()
 if fmt=='xlsx':
  w=Workbook();w.active.append(FIELDS);w.active.append(row);b=io.BytesIO();w.save(b);return b.getvalue()
 b=io.BytesIO();c=canvas.Canvas(b,pagesize=(1800,500),invariant=1);c.setFont('Helvetica',8);c.drawString(10,450,'|'.join(FIELDS));c.drawString(10,420,'|'.join(row));c.save();return b.getvalue()
def main(out):
 out=Path(out);out.mkdir(exist_ok=True);start=time.monotonic();results=[];formats=Counter();manifest=[]
 with zipfile.ZipFile(out/'facturas.zip','w',zipfile.ZIP_DEFLATED) as z:
  for si,sector in enumerate(SECTORS):
   rows=[];expected_alerts=0;expected_savings=0
   for pair in range(250):
    low=100+si*5+pair;delta=10+pair%17;qty=1+pair%9
    for side in range(2):
     idx=pair*2+side;fmt={0:'xlsx',1:'pdf'}.get(idx%10,'csv');price=low+delta*side;net=price*qty;bad=pair<10 and side==1
     row=[f'{sector}-P{side}',f'{sector}-{idx:04}', '1','2026-10-01',f'{sector}-SKU{pair}', ['kg','l','ud'][si%3],str(qty),str(net),'0','0',str(net+5 if bad else net)]
     raw=make(row,fmt); actual_fmt,normalized=normalize(raw); assert actual_fmt==fmt
     decoded=list(csv.reader(io.StringIO(normalized.decode('utf-8-sig')))); assert decoded[0]==FIELDS and decoded[1]==row,(row,decoded)
     rows.append(decoded[1]);formats[fmt]+=1;name=f'{sector}/{idx:04}.{fmt}';z.writestr(name,raw);manifest.append({'file':name,'sha256':hashlib.sha256(raw).hexdigest(),'expected_total':net,'reported_total':net+5 if bad else net,'expected_alert':bad})
     if bad:expected_alerts+=1
    if pair>=10:expected_savings+=delta*qty
   b=io.StringIO();w=csv.writer(b);w.writerow(FIELDS);w.writerows(rows);raw=b.getvalue().encode();r=finish(raw,hashlib.sha256(raw).hexdigest(),'csv',True)
   assert r['rows']==500 and r['eligible_rows']==490 and r['review_alerts']==expected_alerts and r['potential_saving_eur']==f'{expected_savings}.00',r
   assert r['synthetic'] and r['confirmed_loss_eur'] is None
   results.append({'sector':sector,'invoices':500,'eligible':490,'alerts':expected_alerts,'potential_eur':expected_savings,'independent':r['verification']['status']});print(sector,'PASS',flush=True)
 (out/'manifest.json').write_text(json.dumps(manifest));(out/'results.json').write_text(json.dumps({'sectors':results,'formats':dict(formats),'elapsed_seconds':round(time.monotonic()-start,3)},indent=2));print('TOTAL',len(manifest),dict(formats),sum(r['potential_eur'] for r in results),flush=True)
if __name__=='__main__':main(sys.argv[1])

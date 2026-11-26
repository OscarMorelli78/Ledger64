import argparse,csv,io,json,random,hashlib,time,tempfile,collections
from pathlib import Path
from decimal import Decimal
from adaptive_learning.engine import Learner,predict,triage,detect_drift
from engine import FIELDS,parse,audit,InputError
SECTORS='agricultura hosteleria comercio logistica construccion farmacia clinicas educacion industria energia turismo automocion tecnologia telecomunicaciones limpieza seguridad textil alimentacion mantenimiento servicios_profesionales'.split()
def run(out,seed=20261126):
 out=Path(out);out.mkdir(parents=True,exist_ok=True);start=time.monotonic();counts={};rng=random.Random(seed)
 def sample(i,anomaly=False,shift=1):
  s=i%20;sku=(i//20)%3;mu=(50+17*s)*(.8+sku*.2);p=round(mu*shift*(1+rng.uniform(-.04,.04))*((1+rng.choice([-1,1])*rng.uniform(.12,.40)) if anomaly else 1),2);return f'{SECTORS[s]}|sku-{sku}|ud',p
 def invoice_sample(stage,i,anomaly=False,shift=1):
  g,p=sample(i,anomaly,shift); b=io.StringIO();w=csv.writer(b);w.writerow(FIELDS);w.writerow([f'{stage}-supplier-{i%127}',f'{stage}-{i}','1','2026-11-01',g,'ud','1',str(p),'0','0',str(p)]); raw=b.getvalue().encode();r=parse(raw)[0];assert r['total']==Decimal(str(p));return g,float(r['total']),hashlib.sha256(raw).hexdigest()
 def obs(stage,i,g,p,tenant='lab',synthetic=True,proposer='analyst',reviewer='owner',bad=False):
  key=f'{stage}-{i}';return (tenant,synthetic,key,g,str(p),proposer,reviewer,'bad' if bad else hashlib.sha256(key.encode()).hexdigest())
 def score(model,rows,k):
  c=collections.Counter()
  for g,p,y in rows:
   pred=predict(model,g,p,k);c[('abstain_positive' if y else 'abstain_negative') if pred is None else ('tp' if y and pred else 'fn' if y else 'fp' if pred else 'tn')]+=1
  return {'matrix':dict(c),'precision':c['tp']/max(1,c['tp']+c['fp']),'recall':c['tp']/max(1,c['tp']+c['fn']+c['abstain_positive'])}
 def gate(r):return min(r['precision'],r['recall'])>=.95 and not any(r['matrix'].get(x,0) for x in ('abstain_positive','abstain_negative'))
 with tempfile.TemporaryDirectory() as t:
  db=Path(t)/'model.db';l=Learner(db)
  for i in range(6000):
   g,p,h=invoice_sample('train',i);assert l.observe(*(*obs('train',i,g,p)[:-1],h))
  counts['train']=6000;mid=l.fit('lab',True,'analyst');model=l.model(mid,'lab',True)
  val=[(*invoice_sample('validation',i,(i//20+i%20)%5==0)[:2],(i//20+i%20)%5==0) for i in range(2000)];counts['validation']=len(val);k=max((3,4,5),key=lambda v:sum(score(model,val,v)[x] for x in ('precision','recall')))
  test=[(*invoice_sample('holdout',i,i%7==0)[:2],i%7==0) for i in range(2000)];counts['test']=len(test);baseline=score({},test,k);test_result=score(model,test,k);assert gate(test_result)
  assert not l.promote(mid,'lab',True,'analyst',True);assert l.promote(mid,'lab',True,'owner',gate(test_result));print('training/holdout PASS',flush=True)
  fin=[]
  for i in range(20000):
   y=i%9==0;g,p=sample(i,y);qty=1+i%9;cents=int(Decimal(str(p))*100)*qty;reported=cents+(5 if y else 0);fmt=lambda x:f'{x//100}.{x%100:02}'
   b=io.StringIO();w=csv.writer(b);w.writerow(FIELDS);w.writerow([f'fin-supplier-{i%117}',f'fin-{i}','1','2026-11-01',g,'ud',str(qty),fmt(cents),'0','0',fmt(reported)])
   raw=b.getvalue().encode();r=parse(raw)[0];assert (r['total']!=r['reported'])==y;assert r['total']==Decimal(cents)/100;result=audit(raw,True);assert result['review_alerts']==int(y) and result['eligible_rows']==int(not y) and result['confirmed_loss_eur'] is None;fin.append((g,p,y))
  counts['financial']=len(fin);financial=score(model,fin,k);assert gate(financial);print('financial PASS',flush=True)
  malformed=[b'\xff',b'wrong,header\n1,2',(','.join(FIELDS)+'\nonly,one').encode(),(','.join(FIELDS)+'\ns,i,1,2026-11-01,p,ud,1,NaN,0,0,2').encode()]
  for i in range(20000):
   try:parse(malformed[i%len(malformed)]+str(i).encode());raise AssertionError('accepted corrupt file')
   except InputError:pass
  counts['document']=20000
  drift=[(*sample(i,False,1.3),False) for i in range(4000)];before=score(model,drift,k);stable_monitor=detect_drift(model,[(g,p) for g,p,_ in val]);shift_monitor=detect_drift(model,[(g,p) for g,p,_ in drift]);assert not stable_monitor['drift'] and shift_monitor['drift'] and shift_monitor['affected_groups']==60
  for i,(g,p,_) in enumerate(drift):assert l.observe(*obs('drift',i,g,p))
  candidate=l.fit('lab',True,'analyst',window=4000);new=l.model(candidate,'lab',True);future=[(*sample(i,(i//20+i%20)%8==0,1.3),(i//20+i%20)%8==0) for i in range(16000)];after=score(new,future,k);assert gate(after);assert l.promote(candidate,'lab',True,'owner',gate(after));assert l.active('lab',True)==new;counts['temporal']=20000;print('drift PASS',flush=True)
  for i in range(20000):
   g,p=sample(i);o=obs('attack',i,g,p)
   if i%4==0:o=obs('train',i%6000,g,p)
   elif i%4==1:o=obs('attack',i,g,'NaN')
   elif i%4==2:o=obs('attack',i,g,p,reviewer='analyst')
   else:o=obs('attack',i,g,p,bad=True)
   assert not l.observe(*o)
  counts['adversarial']=20000;print('adversarial PASS',flush=True)
  for i in range(10000):
   mode=i%5
   if mode==0:assert not l.promote(mid,'other',True,'owner',True)
   elif mode==1:assert not l.promote(mid,'lab',False,'owner',True)
   elif mode==2:assert l.active('other',True)=={}
   elif mode==3:assert l.active('lab',False)=={}
   else:assert not l.revoke('lab',True,'train-0','analyst')
  counts['governance']=10000;assert l.verify();assert l.revoke('lab',True,'train-0','owner');assert l.active('lab',True)=={};assert l.verify();l.db.close();l=Learner(db);assert l.verify() and l.active('lab',True)=={};l.db.close()
  assert len(model)==60 and len(new)==60
 def ambiguous(count):
  rows=[]
  for i in range(count):
   g,p=sample(i);y=(i//20+i%20)%5==0
   if y:p=round(p*(1+rng.choice([-1,1])*rng.uniform(.02,.12)),2)
   rows.append((g,p,y))
  return rows
 def review_metrics(rows,threshold):
  c=collections.Counter()
  for g,p,y in rows:c[(triage(model,g,p,k,threshold),y)]+=1
  tp=sum(c[(x,True)] for x in ('alert','review','unknown')); fp=sum(c[(x,False)] for x in ('alert','review','unknown')); pos=sum(1 for _,_,y in rows if y)
  return {'capture':tp/pos,'normal_sent_to_review_or_alert':fp/(len(rows)-pos),'routed_fraction':(tp+fp)/len(rows),'captured_anomalies':tp,'missed_anomalies':pos-tp}
 calibration=ambiguous(10000)
 candidates=[(j/20,review_metrics(calibration,j/20)) for j in range(1,int(k*20))]
 review_k=max((v for v,r in candidates if r['capture']>=.95),default=0.0)
 challenge=ambiguous(10000)
 diagnostic=score(model,challenge,k);review_result=review_metrics(challenge,review_k)
 (out/'synthetic_model.json').write_text(json.dumps({'synthetic':True,'threshold':k,'review_threshold':review_k,'initial':model,'shift_candidate':new},indent=2))
 result={'overlapping_challenge_10000':diagnostic,'review_threshold_calibration':review_metrics(calibration,review_k),'review_threshold_holdout':review_result,'review_threshold':review_k,'alert_threshold':k,'additional_diagnostic_cases':len(challenge)+len(calibration),'seed':seed,'counts':counts,'total':sum(counts.values()),'baseline':baseline,'holdout':test_result,'financial':financial,'drift_before':before,'stable_monitor':stable_monitor,'shift_monitor':shift_monitor,'drift_after':after,'shifted_holdout_before_retraining':score(model,future,k),'per_sector_holdout':{g:score(model,[r for r in test if r[0].split('|')[0]==g],k) for g in SECTORS},'elapsed_seconds':round(time.monotonic()-start,3),'scope':'synthetic offline; no production promotion; repeated adversarial patterns; reviewer identities simulated'};assert result['total']==100000
 (out/'results.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--out',default='ale-evidence');p.add_argument('--seed',type=int,default=20261126);args=p.parse_args();run(args.out,args.seed)

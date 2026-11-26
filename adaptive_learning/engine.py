"""Offline supervised learner; no production DB writes."""
import sqlite3, math, json, hashlib
from decimal import Decimal, InvalidOperation
class Learner:
 def __init__(self,path):
  self.db=sqlite3.connect(path)
  self.db.executescript('''CREATE TABLE IF NOT EXISTS obs(tenant TEXT, synthetic INTEGER, invoice TEXT, grp TEXT, price TEXT, proposer TEXT, reviewer TEXT, evidence TEXT, active INTEGER DEFAULT 1, PRIMARY KEY(tenant,synthetic,invoice), UNIQUE(tenant,synthetic,evidence)); CREATE TABLE IF NOT EXISTS models(id INTEGER PRIMARY KEY,tenant TEXT,synthetic INTEGER,body TEXT,digest TEXT,proposer TEXT,reviewer TEXT,active INTEGER DEFAULT 0); CREATE TABLE IF NOT EXISTS events(id INTEGER PRIMARY KEY,kind TEXT,body TEXT,prev TEXT,hash TEXT);''')
 def event(self,kind,body):
  raw=json.dumps(body,sort_keys=True);r=self.db.execute('SELECT hash FROM events ORDER BY id DESC LIMIT 1').fetchone();prev=r[0] if r else '0'*64;h=hashlib.sha256((prev+kind+raw).encode()).hexdigest();self.db.execute('INSERT INTO events(kind,body,prev,hash) VALUES(?,?,?,?)',(kind,raw,prev,h))
 def observe(self,tenant,synthetic,invoice,group,price,proposer,reviewer,evidence):
  if type(synthetic) is not bool or any(not isinstance(x,str) or not x.strip() or len(x)>200 for x in (tenant,invoice,group,proposer,reviewer,evidence)) or proposer==reviewer:return False
  try:
   p=Decimal(price)
   if not p.is_finite() or not 0<p<=Decimal('1000000000'):return False
  except (InvalidOperation,TypeError,ValueError):return False
  if len(evidence)!=64 or any(c not in '0123456789abcdef' for c in evidence):return False
  row=(tenant,int(synthetic),invoice,group,str(p),proposer,reviewer,evidence)
  try:
   with self.db:
    self.db.execute('INSERT INTO obs VALUES(?,?,?,?,?,?,?,?,1)',row);self.event('observe',row)
   return True
  except sqlite3.IntegrityError:return False
 def fit(self,tenant,synthetic,proposer,window=None):
  if type(synthetic) is not bool:raise ValueError('classification')
  stats={}
  if window is not None and (type(window) is not int or window<20):raise ValueError('window')
  query='SELECT grp,price FROM obs WHERE tenant=? AND synthetic=? AND active=1 ORDER BY rowid DESC'
  args=(tenant,int(synthetic))
  if window is not None:query+=' LIMIT ?';args+=(window,)
  for group,p in self.db.execute(query,args):
   n,m,m2=stats.get(group,(0,0.,0.));x=float(p);n+=1;d=x-m;m+=d/n;m2+=d*(x-m);stats[group]=(n,m,m2)
  body=json.dumps(stats,sort_keys=True);h=hashlib.sha256(body.encode()).hexdigest()
  with self.db:
   c=self.db.execute('INSERT INTO models(tenant,synthetic,body,digest,proposer) VALUES(?,?,?,?,?)',(tenant,int(synthetic),body,h,proposer));self.event('candidate',[c.lastrowid,h]);return c.lastrowid
 def model(self,id,tenant,synthetic):
  if type(synthetic) is not bool:raise ValueError('classification')
  r=self.db.execute('SELECT body,digest FROM models WHERE id=? AND tenant=? AND synthetic=?',(id,tenant,int(synthetic))).fetchone()
  if not r or hashlib.sha256(r[0].encode()).hexdigest()!=r[1]:raise ValueError('model missing or modified')
  return json.loads(r[0])
 def promote(self,id,tenant,synthetic,reviewer,gate):
  # Offline API: caller is responsible for authentication and independent evidence.
  if gate is not True or type(synthetic) is not bool:return False
  with self.db:
   r=self.db.execute('SELECT proposer,reviewer FROM models WHERE id=? AND tenant=? AND synthetic=?',(id,tenant,int(synthetic))).fetchone()
   if not r or not reviewer or reviewer==r[0] or r[1] is not None:return False
   self.model(id,tenant,synthetic);self.db.execute('UPDATE models SET active=0 WHERE tenant=? AND synthetic=?',(tenant,int(synthetic)));self.db.execute('UPDATE models SET active=1,reviewer=? WHERE id=?',(reviewer,id));self.event('promote',[id,reviewer]);return True
 def revoke(self,tenant,synthetic,invoice,reviewer):
  if type(synthetic) is not bool or not reviewer:return False
  with self.db:
   r=self.db.execute('UPDATE obs SET active=0 WHERE tenant=? AND synthetic=? AND invoice=? AND active=1 AND reviewer=? AND proposer!=?',(tenant,int(synthetic),invoice,reviewer,reviewer))
   if r.rowcount!=1:return False
   self.db.execute('UPDATE models SET active=0,reviewer=COALESCE(reviewer,?) WHERE tenant=? AND synthetic=?',(reviewer,tenant,int(synthetic)));self.event('revoke',[tenant,synthetic,invoice,reviewer]);return True
 def active(self,tenant,synthetic):
  if type(synthetic) is not bool:raise ValueError('classification')
  r=self.db.execute('SELECT id FROM models WHERE tenant=? AND synthetic=? AND active=1',(tenant,int(synthetic))).fetchone();return self.model(r[0],tenant,synthetic) if r else {}
 def verify(self):
  prev='0'*64
  for kind,body,p,h in self.db.execute('SELECT kind,body,prev,hash FROM events ORDER BY id'):
   if p!=prev or hashlib.sha256((prev+kind+body).encode()).hexdigest()!=h:return False
   prev=h
  return True

def deviation(stats,group,price):
 n,m,m2=stats.get(group,(0,0,0))
 if n<20:return None
 try:x=float(price)
 except (TypeError,ValueError,OverflowError):return None
 if not math.isfinite(x) or x<=0:return None
 sd=max(math.sqrt(max(0,m2)/(n-1)),m*.01)
 return abs(x-m)/sd

def predict(stats,group,price,k=4):
 z=deviation(stats,group,price)
 return None if z is None else z>k

def triage(stats,group,price,alert_k,review_k):
 if not 0<=review_k<alert_k:raise ValueError('thresholds')
 z=deviation(stats,group,price)
 if z is None:return 'unknown'
 if z>alert_k:return 'alert'
 return 'review' if z>review_k else 'normal'


def detect_drift(stats, observations, minimum=20, relative_change=.10, affected_fraction=.50):
 """Robust batch drift diagnostic, not a trigger for unsupervised promotion."""
 from statistics import median
 from collections import defaultdict
 if minimum<20 or not 0<relative_change<1 or not 0<affected_fraction<=1:raise ValueError('drift config')
 groups=defaultdict(list)
 for group,price in observations:
  try:x=float(price)
  except (ValueError,TypeError,OverflowError):continue
  if group in stats and math.isfinite(x) and x>0:groups[group].append(x)
 eligible={}; affected={}
 for group,values in groups.items():
  n,m,_=stats[group]
  if n<20 or len(values)<minimum or m<=0:continue
  change=median(values)/m-1;eligible[group]=change
  if abs(change)>=relative_change:affected[group]=change
 fraction=len(affected)/len(eligible) if eligible else 0.
 return {'drift':bool(eligible) and fraction>=affected_fraction,'eligible_groups':len(eligible),'affected_groups':len(affected),'fraction':fraction,'changes':affected}

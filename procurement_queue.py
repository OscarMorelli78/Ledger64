"""Synthetic-only review queue; authenticated roles supplied by secure_app."""
import json
import sqlite3
from procurement import canonical, digest, validate, MAX_DOC, identifier

MAX_CASES=250
MAX_PENDING_BYTES=64_000_000

def initialize(store):
    store.db.execute("""CREATE TABLE IF NOT EXISTS procurement_queue(
      id TEXT PRIMARY KEY, tenant TEXT NOT NULL, candidate TEXT NOT NULL, original BLOB NOT NULL,
      source_hash TEXT NOT NULL, proposer TEXT NOT NULL, evidence TEXT NOT NULL,
      status TEXT NOT NULL CHECK(status IN ('PENDING','APPROVED','REJECTED')),
      reviewer TEXT, review_evidence TEXT, approved_hash TEXT)""")
    store.db.commit()

def require(actor, roles):
    if actor["role"] not in roles:raise PermissionError("Insufficient permission")
    identifier(actor["company"]);identifier(actor["id"])

def evidence(text):
    if not isinstance(text,str) or not 10<=len(text.strip())<=500:raise ValueError("Evidence required, 10–500 characters")
    return text.strip()

def integrity(row):
    id,tenant,body,raw,source,proposer,reason,*_=row
    if digest(raw)!=source or digest(canonical([tenant,body,source,proposer,reason]).encode())!=id:
        raise ValueError("Proposal integrity failure")

def submit(store,actor,candidate,original,reason):
    require(actor,("owner","analyst"))
    reason=evidence(reason);validate(candidate)
    if not isinstance(original,bytes) or not 1<=len(original)<=MAX_DOC:raise ValueError("Invalid source size")
    body=canonical(candidate)
    if len(body.encode())>MAX_DOC:raise ValueError("Candidate too large")
    source=digest(original);tenant=actor["company"];proposer=actor["id"]
    key=digest(canonical([tenant,body,source,proposer,reason]).encode())
    try:
        store.db.execute("BEGIN IMMEDIATE")
        count,size=store.db.execute("SELECT COUNT(*),COALESCE(SUM(length(original)+length(candidate)),0) FROM procurement_queue WHERE tenant=?",(tenant,)).fetchone()
        if count>=MAX_CASES or size+len(original)+len(body.encode())>MAX_PENDING_BYTES:raise ValueError("Pilot quota reached")
        store.db.execute("INSERT INTO procurement_queue VALUES(?,?,?,?,?,?,?,'PENDING',NULL,NULL,NULL)",(key,tenant,body,original,source,proposer,reason))
        store.db.commit()
    except sqlite3.IntegrityError as e:
        store.db.rollback();raise ValueError("Duplicate proposal") from e
    except BaseException:
        store.db.rollback();raise
    return key

def get(store,actor,key):
    require(actor,("owner","analyst","reader"))
    row=store.db.execute("SELECT * FROM procurement_queue WHERE tenant=? AND id=?",(actor["company"],key)).fetchone()
    if not row:raise KeyError("Unknown proposal")
    integrity(row)
    return row

def list_cases(store,actor):
    require(actor,("owner","analyst","reader"))
    result=[]
    for row in store.db.execute("SELECT * FROM procurement_queue WHERE tenant=? ORDER BY rowid DESC",(actor["company"],)):
        integrity(row)
        id,_,candidate,_,source,proposer,reason,status,reviewer,review_reason,approved=row
        result.append(dict(id=id,candidate=json.loads(candidate),source_sha256=source,proposer=proposer,evidence=reason,status=status,reviewer=reviewer,review_evidence=review_reason,approved_hash=approved))
    return result

def review(store,actor,key,decision,reason):
    require(actor,("owner",));reason=evidence(reason)
    if decision not in ("APPROVED","REJECTED"):raise ValueError("Invalid decision")
    try:
        store.db.execute("BEGIN IMMEDIATE")
        row=get(store,actor,key)
        _,tenant,body,original,_,proposer,submitted,status,*_=row
        if status!="PENDING" or proposer==actor["id"]:raise PermissionError("Independent owner review required")
        approved=None
        if decision=="APPROVED":
            approved=store._approve_in_tx(tenant,True,json.loads(body),original,proposer,actor["id"],("proposal="+key+"; "+reason))
        store.db.execute("UPDATE procurement_queue SET status=?,reviewer=?,review_evidence=?,approved_hash=? WHERE id=? AND tenant=?",(decision,actor["id"],reason,approved,key,tenant))
        store.db.commit()
        return dict(id=key,status=decision,approved_hash=approved)
    except sqlite3.IntegrityError as e:
        store.db.rollback();raise ValueError("Duplicate approved document") from e
    except BaseException:
        store.db.rollback();raise

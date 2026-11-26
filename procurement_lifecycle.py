"""Authenticated two-person requests for corrections and revocations."""
import json,sqlite3
from procurement import canonical,digest,identifier
from procurement_queue import require,evidence

def init(store):
    store.db.execute("""CREATE TABLE IF NOT EXISTS procurement_revision_requests(
        id TEXT PRIMARY KEY, tenant TEXT NOT NULL, body TEXT NOT NULL,
        status TEXT NOT NULL CHECK(status IN ('PENDING','APPROVED','REJECTED')),
        reviewer TEXT, reason TEXT, version TEXT)""")
    store.db.commit()

def read(store,actor,key):
    row=store.db.execute("SELECT id,tenant,body,status,reviewer,reason,version FROM procurement_revision_requests WHERE tenant=? AND id=?",(actor["company"],key)).fetchone()
    if not row:raise KeyError("Unknown request")
    id,tenant,body,status,reviewer,reason,version=row
    if digest(body.encode())!=id:raise ValueError("Request integrity failure")
    data=json.loads(body)
    if data["tenant"]!=tenant:raise ValueError("Request scope mismatch")
    _,history=store._replay()
    matches=[event for identity,events in history.items() if identity[:2]==(tenant,1) for event in events if event.get("request_id")==id]
    if status=="APPROVED":
        if len(matches)!=1 or matches[0]["version"]!=version or matches[0]["reviewer"]!=reviewer or matches[0]["evidence"]!=reason:
            raise ValueError("Approval evidence mismatch")
    elif matches:raise ValueError("Unexpected revision event")
    return dict(id=id,**data,status=status,reviewer=reviewer,review_evidence=reason,result_version=version)

def submit(store,actor,kind,supplier,doc_id,expected_version,action,document,reason):
    require(actor,("owner","analyst"));reason=evidence(reason)
    tenant=actor["company"];proposer=actor["id"]
    key=(tenant,1,kind,identifier(supplier).casefold(),identifier(doc_id).casefold())
    init(store)
    try:
        store.db.execute("BEGIN IMMEDIATE")
        active,_=store._replay()
        old=active.get(key)
        if old is None or old["version"]!=expected_version:raise ValueError("Stale or unavailable document")
        # Validate proposed change without claiming an actual reviewer yet.
        placeholder="validation-only"
        if proposer.casefold()==placeholder:placeholder="validation-only-2"
        store._validate_revision(action,key,old,document,proposer,placeholder,reason,None)
        data=dict(tenant=tenant,kind=kind,supplier=supplier,doc_id=doc_id,expected_version=expected_version,
                  action=action,document=document,proposer=proposer,evidence=reason)
        body=canonical(data);id=digest(body.encode())
        n=store.db.execute("SELECT count(*) FROM procurement_revision_requests WHERE tenant=?",(tenant,)).fetchone()[0]
        if n>=250:raise ValueError("Revision pilot quota reached")
        store.db.execute("INSERT INTO procurement_revision_requests VALUES(?,?,?,'PENDING',NULL,NULL,NULL)",(id,tenant,body))
        store.db.commit();return id
    except sqlite3.IntegrityError as exc:
        store.db.rollback();raise ValueError("Duplicate revision request") from exc
    except BaseException:
        store.db.rollback();raise

def review(store,actor,key,decision,reason):
    require(actor,("owner",));reason=evidence(reason)
    if decision not in ("APPROVED","REJECTED"):raise ValueError("Invalid decision")
    init(store)
    try:
        store.db.execute("BEGIN IMMEDIATE")
        data=read(store,actor,key)
        if data["status"]!="PENDING" or data["proposer"].casefold()==actor["id"].casefold():
            raise PermissionError("Independent owner review required")
        version=None
        if decision=="APPROVED":
            version=store._revise_in_tx(actor["company"],True,data["kind"],data["supplier"],data["doc_id"],
                data["expected_version"],data["action"],data["document"],data["proposer"],actor["id"],reason,key)
        store.db.execute("UPDATE procurement_revision_requests SET status=?,reviewer=?,reason=?,version=? WHERE id=? AND tenant=?",
            (decision,actor["id"],reason,version,key,actor["company"]))
        result=read(store,actor,key)
        store.db.commit();return result
    except BaseException:
        store.db.rollback();raise

def list_requests(store,actor):
    require(actor,("owner","analyst","reader"));init(store)
    store.db.execute("BEGIN")
    try:
        keys=[r[0] for r in store.db.execute("SELECT id FROM procurement_revision_requests WHERE tenant=? ORDER BY rowid DESC",(actor["company"],))]
        result=[read(store,actor,key) for key in keys]
        store.db.commit();return result
    except BaseException:
        store.db.rollback();raise

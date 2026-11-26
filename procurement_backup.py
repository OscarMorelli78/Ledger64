"""Local, synthetic-only procurement database disaster recovery.

Trusted OS administrator CLI. Never restores in place, never creates a database
from a missing source, never transmits data. Keep the returned SHA-256 separately
in a trusted location; it is not a signature or encryption.
"""
import argparse
import hashlib
import json
import os
import re
import sqlite3
import tempfile
import time
from pathlib import Path
from contextlib import closing
from procurement import Store, canonical, digest, validate, identifier
from procurement_queue import integrity
from procurement_lifecycle import read as read_request

LIMIT=512*1024*1024
COLUMNS={
    "procurement_docs":"tenant synthetic kind supplier_key doc_key body source_hash body_hash original proposer reviewer evidence",
    "procurement_events":"seq body prev hash",
    "procurement_queue":"id tenant candidate original source_hash proposer evidence status reviewer review_evidence approved_hash",
    "procurement_revision_requests":"id tenant body status reviewer reason version",
    "procurement_templates":"id tenant synthetic supplier kind version body",
    "procurement_table_templates":"id tenant synthetic supplier kind version body",
}

def source_path(path):
    p=Path(path)
    if p.is_symlink() or not p.is_file():raise ValueError("Existing regular source required")
    if not 0<p.stat().st_size<=LIMIT:raise ValueError("Source size limit")
    return p.resolve()

def target_path(path):
    p=Path(path)
    if not p.parent.is_dir():raise ValueError("Existing private destination directory required")
    p=p.parent.resolve()/p.name
    for suffix in ("","-wal","-shm","-journal"):
        if os.path.lexists(str(p)+suffix):raise FileExistsError("Destination or SQLite sidecar already exists")
    return p

def file_hash(path):
    h=hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda:f.read(1024*1024),b""):h.update(chunk)
    return h.hexdigest()

def readonly(path):
    c=sqlite3.connect(path.as_uri()+"?mode=ro",uri=True,timeout=5)
    c.execute("PRAGMA trusted_schema=OFF")
    c.execute("PRAGMA query_only=ON")
    return c

def check_database(path,tenant):
    """Check physical integrity, supported schema, scope and application invariants."""
    identifier(tenant)
    with closing(readonly(source_path(path))) as c:
        c.execute("BEGIN")
        if c.execute("PRAGMA integrity_check").fetchall()!=[("ok",)]:raise ValueError("SQLite integrity failure")
        if c.execute("PRAGMA foreign_key_check").fetchone():raise ValueError("Foreign key failure")
        schema=c.execute("SELECT type,name,sql FROM sqlite_master WHERE substr(name,1,7) != 'sqlite_'").fetchall()
        tables={name for typ,name,sql in schema if typ=="table"}
        if not {"procurement_docs","procurement_events"}<=tables<=set(COLUMNS):raise ValueError("Unexpected database tables")
        for typ,name,sql in schema:
            if typ!="table" or not sql or "VIRTUAL TABLE" in sql.upper():raise ValueError("Unexpected schema object")
        for name in tables:
            cols=[r[1] for r in c.execute("PRAGMA table_info("+name+")")]
            if cols!=COLUMNS[name].split():raise ValueError("Unexpected table columns")
            if "tenant" in cols and c.execute("SELECT 1 FROM "+name+" WHERE tenant IS NOT ? LIMIT 1",(tenant,)).fetchone():
                raise ValueError("Mixed or wrong tenant")
            if "synthetic" in cols and c.execute("SELECT 1 FROM "+name+" WHERE synthetic IS NOT 1 LIMIT 1").fetchone():
                raise ValueError("Real data not supported by pilot backup")
        store=Store.__new__(Store);store.db=c
        active,history=store._replay()
        approvals={}
        expected_requests={}
        for key,versions in history.items():
            first=versions[0]
            if first["evidence"].startswith("proposal="):
                proposal=first["evidence"].split(";",1)[0][len("proposal="):]
                if not re.fullmatch(r"[a-f0-9]{64}",proposal) or proposal in approvals:raise ValueError("Invalid approval linkage")
                approvals[proposal]=first
            for event in versions:
                request=event.get("request_id")
                if request:
                    if request in expected_requests:raise ValueError("Duplicate revision request linkage")
                    expected_requests[request]=event
        if approvals and "procurement_queue" not in tables:raise ValueError("Missing approval queue")
        if expected_requests and "procurement_revision_requests" not in tables:raise ValueError("Missing revision queue")
        if "procurement_queue" in tables:
            observed=set()
            for row in c.execute("SELECT * FROM procurement_queue"):
                integrity(row)
                id,_,body,raw,source,proposer,reason,status,reviewer,review_reason,approved=row
                candidate=validate(json.loads(body))
                if status=="APPROVED":
                    first=approvals.get(id)
                    if first is None or (first["document"],first["source_sha256"],first["version"],first["proposer"],first["reviewer"],first["evidence"])!=(candidate,source,approved,proposer,reviewer,"proposal="+id+"; "+str(review_reason)):
                        raise ValueError("Approval linkage mismatch")
                    observed.add(id)
                elif status=="PENDING":
                    if any(x is not None for x in (reviewer,review_reason,approved)):raise ValueError("Invalid pending review")
                elif status=="REJECTED":
                    if not reviewer or not review_reason or approved is not None or reviewer.casefold()==proposer.casefold():raise ValueError("Invalid rejected review")
                else:raise ValueError("Invalid review status")
            if observed!=set(approvals):raise ValueError("Missing approval records")
        if "procurement_revision_requests" in tables:
            observed=set()
            for (id,) in c.execute("SELECT id FROM procurement_revision_requests"):
                r=read_request(store,{"company":tenant},id)
                if r["status"]=="APPROVED":
                    observed.add(id)
                    event=expected_requests.get(id)
                    if event is None or event["action"]!=r["action"] or event["proposer"]!=r["proposer"] or (r["action"]=="CORRECT" and event["document"]!=r["document"]):
                        raise ValueError("Revision request mismatch")
                elif r["status"]=="PENDING":
                    if any(r[k] is not None for k in ("reviewer","review_evidence","result_version")):raise ValueError("Invalid pending revision")
                elif r["status"]=="REJECTED":
                    if not r["reviewer"] or not r["review_evidence"] or r["result_version"] is not None or r["reviewer"].casefold()==r["proposer"].casefold():raise ValueError("Invalid rejected revision")
                else:raise ValueError("Invalid revision status")
            if observed!=set(expected_requests):raise ValueError("Missing revision records")
        for table in ("procurement_templates","procurement_table_templates"):
            if table not in tables:continue
            for id,t,s,supplier,kind,version,body in c.execute("SELECT * FROM "+table):
                r=json.loads(body)
                if digest(body.encode())!=id or (r["tenant"],r["synthetic"],r["supplier"],r["kind"],r["version"])!=(t,bool(s),supplier,kind,version):
                    raise ValueError("Template integrity failure")
                if r["proposer"].casefold()==r["reviewer"].casefold():raise ValueError("Template self-review")
        counts={t:c.execute("SELECT count(*) FROM "+t).fetchone()[0] for t in sorted(tables)}
        tip=c.execute("SELECT hash FROM procurement_events ORDER BY seq DESC LIMIT 1").fetchone()
        return {"tenant":tenant,"synthetic":True,"counts":counts,"active_documents":len(active),
                "event_tip":tip[0] if tip else "0"*64}

def publish(staged,target):
    # Atomic no-overwrite publication on the same filesystem; fail closed if
    # hard links are not supported. Never fall back to replacing a live DB.
    with staged.open("rb") as f:os.fsync(f.fileno())
    target_path(target)
    os.link(staged,target)
    if os.name!="nt":
        fd=os.open(str(target.parent),os.O_RDONLY)
        try:os.fsync(fd)
        finally:os.close(fd)

def create_backup(source,destination,tenant):
    src=source_path(source);dst=target_path(destination)
    with tempfile.TemporaryDirectory(prefix=".ledger64-",dir=dst.parent) as temp:
        stage=Path(temp)/"snapshot.sqlite3"
        deadline=time.monotonic()+60
        with closing(readonly(src)) as origin,closing(sqlite3.connect(stage)) as dest:
            page_size=origin.execute("PRAGMA page_size").fetchone()[0]
            def progress(status,remaining,total):
                if time.monotonic()>deadline or total*page_size>LIMIT:raise TimeoutError("Backup time or page limit")
            origin.backup(dest,pages=128,progress=progress,sleep=.05)
            dest.execute("PRAGMA journal_mode=DELETE")
        if stage.stat().st_size>LIMIT:raise ValueError("Snapshot too large")
        os.chmod(stage,0o600)
        result=check_database(stage,tenant)
        sha=file_hash(stage);size=stage.stat().st_size
        publish(stage,dst)
    return {**result,"sha256":sha,"bytes":size,"status":"BACKUP_VERIFIED","path":str(dst)}

def verify_backup(source,tenant,expected_sha256):
    src=source_path(source)
    if not isinstance(expected_sha256,str) or not re.fullmatch(r"[a-f0-9]{64}",expected_sha256):
        raise ValueError("Trusted expected SHA-256 required")
    # Backups must be standalone immutable files; never interpret a sidecar.
    if any(os.path.lexists(str(src)+s) for s in ("-wal","-shm","-journal")):
        raise ValueError("Backup has unexpected sidecars")
    if file_hash(src)!=expected_sha256:raise ValueError("Backup checksum mismatch")
    result=check_database(src,tenant)
    if file_hash(src)!=expected_sha256:raise ValueError("Backup changed during verification")
    return {**result,"sha256":expected_sha256,"bytes":src.stat().st_size,"status":"BACKUP_VERIFIED"}

def restore_backup(source,destination,tenant,expected_sha256):
    src=source_path(source);dst=target_path(destination)
    if any(os.path.lexists(str(src)+s) for s in ("-wal","-shm","-journal")):
        raise ValueError("Backup has unexpected sidecars")
    with tempfile.TemporaryDirectory(prefix=".ledger64-",dir=dst.parent) as temp:
        stage=Path(temp)/"restore.sqlite3"
        # Verify the exact copied bytes, not a mutable source after validation.
        with src.open("rb") as inp,stage.open("xb") as out:
            total=0
            for chunk in iter(lambda:inp.read(1024*1024),b""):
                total+=len(chunk)
                if total>LIMIT:raise ValueError("Backup size limit")
                out.write(chunk)
            out.flush();os.fsync(out.fileno())
        os.chmod(stage,0o600)
        result=verify_backup(stage,tenant,expected_sha256)
        publish(stage,dst)
    return {**result,"status":"RESTORED_TO_NEW_PATH","path":str(dst)}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    sub=p.add_subparsers(dest="action",required=True)
    for action in ("create","verify","restore"):
        a=sub.add_parser(action);a.add_argument("--source",type=Path,required=True)
        a.add_argument("--tenant",required=True)
        if action!="verify":a.add_argument("--destination",type=Path,required=True)
        if action!="create":a.add_argument("--sha256",required=True)
    a=p.parse_args()
    if a.action=="create":r=create_backup(a.source,a.destination,a.tenant)
    elif a.action=="verify":r=verify_backup(a.source,a.tenant,a.sha256)
    else:r=restore_backup(a.source,a.destination,a.tenant,a.sha256)
    print(json.dumps(r,indent=2,ensure_ascii=False))
if __name__=="__main__":main()

"""Immutable reviewed CSV mappings for a supplier and document kind.

This is supervised template reuse, not autonomous layout learning.
The CLI is a synthetic-only trusted local operator, not an auth boundary.
"""
import csv
import io
import json
import sqlite3
from procurement import canonical,digest,validate,identifier,MAX_DOC,KINDS

COMMON=("supplier","document_id","date","currency","id","sku","unit","quantity")

def fields(kind):
    if kind=="order":return (*COMMON,"unit_price","discount_pct")
    if kind=="receipt":return (*COMMON,"order_id","order_line")
    if kind=="invoice":return (*COMMON,"order_id","order_line","net_total")
    raise ValueError("Invalid kind")

def parse(raw,kind,supplier,mapping,delimiter,expected_header=None):
    if not isinstance(raw,bytes) or not 1<=len(raw)<=MAX_DOC:raise ValueError("Invalid CSV source")
    identifier(supplier)
    if delimiter not in (",",";","\t"):raise ValueError("Invalid separator")
    required=fields(kind)
    if not isinstance(mapping,dict) or set(mapping)!=set(required) or any(not isinstance(v,str) or not v for v in mapping.values()) or len(set(mapping.values()))!=len(required):
        raise ValueError("Complete unambiguous mapping required")
    reader=csv.DictReader(io.StringIO(raw.decode("utf-8-sig"),newline=""),delimiter=delimiter,strict=True)
    header=reader.fieldnames
    if not header or len(header)>100 or len(set(header))!=len(header) or not set(mapping.values())<=set(header):
        raise ValueError("Invalid header")
    if expected_header is not None and header!=expected_header:raise ValueError("Layout changed; approve a new version")
    meta=None;lines=[]
    for row in reader:
        if len(lines)>=1000 or None in row or any(v is None for v in row.values()):raise ValueError("Invalid CSV row")
        x={k:row[v].strip() for k,v in mapping.items()}
        current=(x.pop("supplier"),x.pop("document_id"),x.pop("date"),x.pop("currency"))
        if current[0]!=supplier or (meta is not None and meta!=current):raise ValueError("Single known supplier/document required")
        meta=current;lines.append(x)
    if meta is None:raise ValueError("No lines")
    document=dict(kind=kind,supplier=meta[0],id=meta[1],date=meta[2],currency=meta[3],lines=lines)
    validate(document)
    return document,header

def init(store):
    store.db.execute("""CREATE TABLE IF NOT EXISTS procurement_templates(
      id TEXT PRIMARY KEY, tenant TEXT NOT NULL, synthetic INTEGER NOT NULL,
      supplier TEXT NOT NULL, kind TEXT NOT NULL, version INTEGER NOT NULL,
      body TEXT NOT NULL, UNIQUE(tenant,synthetic,supplier,kind,version))""")
    store.db.commit()

def register(store,tenant,synthetic,kind,supplier,mapping,delimiter,example,proposer,reviewer,evidence):
    scope=store.scope(tenant,synthetic)
    identifier(proposer);identifier(reviewer)
    if proposer.casefold()==reviewer.casefold():raise ValueError("Independent review required")
    if not isinstance(evidence,str) or not 10<=len(evidence.strip())<=500:raise ValueError("Evidence required")
    _,header=parse(example,kind,supplier,mapping,delimiter)
    init(store)
    try:
        store.db.execute("BEGIN IMMEDIATE")
        row=store.db.execute("SELECT COALESCE(MAX(version),0) FROM procurement_templates WHERE tenant=? AND synthetic=? AND supplier=? AND kind=?",(*scope,supplier,kind)).fetchone()
        version=row[0]+1
        record=dict(tenant=tenant,synthetic=synthetic,supplier=supplier,kind=kind,version=version,
          mapping=mapping,delimiter=delimiter,header=header,example_sha256=digest(example),
          proposer=proposer,reviewer=reviewer,evidence=evidence.strip())
        body=canonical(record);key=digest(body.encode())
        store.db.execute("INSERT INTO procurement_templates VALUES(?,?,?,?,?,?,?)",(key,*scope,supplier,kind,version,body))
        store.db.commit()
    except BaseException:
        store.db.rollback();raise
    return key

def apply(store,tenant,synthetic,key,raw):
    scope=store.scope(tenant,synthetic);init(store)
    row=store.db.execute("SELECT supplier,kind,version,body FROM procurement_templates WHERE id=? AND tenant=? AND synthetic=?",(key,*scope)).fetchone()
    if not row:raise KeyError("Template not available in this data scope")
    supplier,kind,version,body=row
    if digest(body.encode())!=key:raise ValueError("Template integrity failure")
    record=json.loads(body)
    if (record["tenant"],record["synthetic"],record["supplier"],record["kind"],record["version"])!=(tenant,synthetic,supplier,kind,version):raise ValueError("Template scope mismatch")
    document,_=parse(raw,kind,supplier,record["mapping"],record["delimiter"],record["header"])
    return {"candidate":document,"source_sha256":digest(raw),"template_id":key,"template_version":version,"status":"REVIEW_REQUIRED"}

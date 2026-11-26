"""Reviewed table-layout memory. Reuses structure only, never historic amounts.

Trusted synthetic CLI. Each template must match an already approved document
and source hash. New documents are still draft candidates.
"""
import json
from procurement import canonical,digest,identifier
from procurement_table import propose_from_cells,canonical_columns

def init(store):
    store.db.execute("""CREATE TABLE IF NOT EXISTS procurement_table_templates(
       id TEXT PRIMARY KEY, tenant TEXT NOT NULL, synthetic INTEGER NOT NULL,
       supplier TEXT NOT NULL, kind TEXT NOT NULL, version INTEGER NOT NULL,
       body TEXT NOT NULL, UNIQUE(tenant,synthetic,supplier,kind,version))""")
    store.db.commit()

def register(store,tenant,synthetic,table,metadata,mapping,source_sha256,proposer,reviewer,evidence):
    scope=store.scope(tenant,synthetic)
    identifier(proposer);identifier(reviewer)
    if proposer.casefold()==reviewer.casefold():raise ValueError("Independent review required")
    if not isinstance(evidence,str) or not 10<=len(evidence.strip())<=500:raise ValueError("Evidence required")
    draft=propose_from_cells(table,metadata,mapping,source_sha256)
    if not any(d==draft["candidate"] and h==source_sha256 for d,h in store.documents(tenant,synthetic)):
        raise ValueError("Template requires matching independently approved example")
    init(store)
    supplier=metadata["supplier"];kind=metadata["kind"]
    try:
        store.db.execute("BEGIN IMMEDIATE")
        row=store.db.execute("SELECT COALESCE(MAX(version),0) FROM procurement_table_templates WHERE tenant=? AND synthetic=? AND supplier=? AND kind=?",(*scope,supplier,kind)).fetchone()
        record=dict(tenant=tenant,synthetic=synthetic,supplier=supplier,kind=kind,version=row[0]+1,
                    headers=table["cells"][0],mapping=mapping,source_sha256=source_sha256,
                    approved_body_sha256=digest(canonical(draft["candidate"]).encode()),
                    proposer=proposer,reviewer=reviewer,evidence=evidence.strip())
        body=canonical(record);key=digest(body.encode())
        store.db.execute("INSERT INTO procurement_table_templates VALUES(?,?,?,?,?,?,?)",(key,*scope,supplier,kind,record["version"],body))
        store.db.commit()
    except BaseException:
        store.db.rollback();raise
    return key

def apply(store,tenant,synthetic,key,table,metadata,source_sha256):
    scope=store.scope(tenant,synthetic);init(store)
    row=store.db.execute("SELECT supplier,kind,version,body FROM procurement_table_templates WHERE id=? AND tenant=? AND synthetic=?",(key,*scope)).fetchone()
    if not row:raise KeyError("Template not available in scope")
    supplier,kind,version,body=row
    if digest(body.encode())!=key:raise ValueError("Template integrity failure")
    record=json.loads(body)
    if (record["tenant"],record["synthetic"],record["supplier"],record["kind"],record["version"])!=(tenant,synthetic,supplier,kind,version):
        raise ValueError("Template scope mismatch")
    if metadata.get("supplier")!=supplier or metadata.get("kind")!=kind:raise ValueError("Supplier or document kind changed")
    if not any(digest(canonical(d).encode())==record["approved_body_sha256"] and h==record["source_sha256"] for d,h in store.documents(tenant,synthetic)):
        raise ValueError("Approved template example no longer available")
    # Validate that the exact header set is present. Retain the actual input
    # column positions for field evidence; do not reorder the source table.
    canonical_columns(table["cells"],record["headers"])
    result=propose_from_cells(table,metadata,record["mapping"],source_sha256)
    result.update(template_id=key,template_version=version)
    return result

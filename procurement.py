"""Additive, local procurement intelligence. No changes to the legacy audit engine.

Amounts are net EUR. The only quantified exposure is a documented difference,
not a paid loss. Every input requires independent review before persistence.
"""
from __future__ import annotations

import hashlib
import json
import re
import sqlite3
from collections import defaultdict
from datetime import date
from decimal import Decimal, ROUND_HALF_UP, localcontext
from pathlib import Path

from engine import audit, parse

D = Decimal
CENT = D("0.01")
ZERO = D(0)
MAX_DOC = 2_000_000
KINDS = {"order", "receipt", "invoice"}
VERSION = 1


def canonical(obj):
    return json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False)


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def money(value):
    return value.quantize(CENT, rounding=ROUND_HALF_UP)


def decimal(value, *, positive=False):
    if not isinstance(value, str) or not re.fullmatch(r"[0-9]{1,9}(?:\.[0-9]{1,6})?", value):
        raise ValueError("Expected bounded unsigned decimal string")
    result = D(value)
    if positive and result <= 0:
        raise ValueError("Expected positive value")
    return result


def identifier(value):
    if not isinstance(value, str) or not value.strip() or len(value) > 160 or value != value.strip() or any(ord(x) < 32 for x in value):
        raise ValueError("Invalid identifier")
    return value


def day(value):
    if not isinstance(value, str) or date.fromisoformat(value).isoformat() != value:
        raise ValueError("Expected ISO date")
    return value


def exact_keys(obj, keys):
    if not isinstance(obj, dict) or set(obj) != set(keys):
        raise ValueError("Missing or unexpected fields")


def validate(doc):
    exact_keys(doc, ("kind", "id", "supplier", "date", "currency", "lines"))
    kind = doc["kind"]
    if kind not in KINDS or doc["currency"] != "EUR":
        raise ValueError("Only purchase documents in EUR")
    identifier(doc["id"])
    identifier(doc["supplier"])
    day(doc["date"])
    if not isinstance(doc["lines"], list) or not 1 <= len(doc["lines"]) <= 1000:
        raise ValueError("Invalid line count")
    seen = set()
    for line in doc["lines"]:
        fields = ["id", "sku", "unit", "quantity"]
        if kind == "order":
            fields += ["unit_price", "discount_pct"]
        else:
            fields += ["order_id", "order_line"]
            if kind == "invoice":
                fields += ["net_total"]
        exact_keys(line, fields)
        for key in ("id", "sku"):
            identifier(line[key])
        if line["id"].casefold() in seen:
            raise ValueError("Duplicate document line")
        seen.add(line["id"].casefold())
        if line["unit"] not in ("kg", "l", "ud"):
            raise ValueError("Use canonical unit kg, l or ud")
        decimal(line["quantity"], positive=True)
        if kind == "order":
            decimal(line["unit_price"])
            if decimal(line["discount_pct"]) > 100:
                raise ValueError("Discount exceeds 100 percent")
        else:
            identifier(line["order_id"])
            identifier(line["order_line"])
            if kind == "invoice" and decimal(line["net_total"]) != money(decimal(line["net_total"])):
                raise ValueError("Invoice total must be in cents")
    return doc


def policy(quantity="0", amount="0.01", price_pct="0"):
    p = {"quantity": decimal(quantity), "amount": decimal(amount), "price_pct": decimal(price_pct)}
    if p["price_pct"] > 100:
        raise ValueError("Invalid price tolerance")
    return p


class Store:
    """Single SQLite database per deployment; all reads scoped by tenant and data class.

    This is a trusted local operator API, not an authentication service.
    Callers must supply authenticated, distinct actor identities before web integration.
    """
    def __init__(self, path):
        self.db = sqlite3.connect(path)
        self.db.execute("PRAGMA foreign_keys=ON")
        self.db.executescript("""
        CREATE TABLE IF NOT EXISTS procurement_docs(
          tenant TEXT NOT NULL, synthetic INTEGER NOT NULL, kind TEXT NOT NULL,
          supplier_key TEXT NOT NULL, doc_key TEXT NOT NULL, body TEXT NOT NULL,
          source_hash TEXT NOT NULL, body_hash TEXT NOT NULL, original BLOB NOT NULL, proposer TEXT NOT NULL,
          reviewer TEXT NOT NULL, evidence TEXT NOT NULL,
          PRIMARY KEY(tenant,synthetic,kind,supplier_key,doc_key),
          UNIQUE(tenant,synthetic,source_hash));
        CREATE TABLE IF NOT EXISTS procurement_events(
          seq INTEGER PRIMARY KEY, body TEXT NOT NULL, prev TEXT NOT NULL, hash TEXT NOT NULL);
        """)
        self.db.commit()

    def close(self):
        self.db.close()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()

    @staticmethod
    def scope(tenant, synthetic):
        identifier(tenant)
        if type(synthetic) is not bool:
            raise ValueError("Explicit data classification required")
        return tenant, int(synthetic)

    def _replay(self):
        """Replay old approval events and append-only correction/revocation events."""
        rows={}
        for row in self.db.execute("SELECT tenant,synthetic,kind,supplier_key,doc_key,body,source_hash,body_hash,original,proposer,reviewer,evidence FROM procurement_docs"):
            tenant,synthetic,kind,supplier,key,body,source,h,original,proposer,reviewer,evidence=row
            if digest(body.encode())!=h or digest(original)!=source:
                raise ValueError("Original integrity failure")
            doc=validate(json.loads(body))
            identity=(tenant,synthetic,kind,supplier,key)
            if (doc["kind"],doc["supplier"].casefold(),doc["id"].casefold())!=identity[2:]:
                raise ValueError("Original identity mismatch")
            rows[identity]=(doc,source,h,proposer,reviewer,evidence)
        active={};history={};prev="0"*64
        for body,predecessor,h in self.db.execute("SELECT body,prev,hash FROM procurement_events ORDER BY seq"):
            if prev!=predecessor or digest((prev+body).encode())!=h:raise ValueError("Event chain failure")
            entry=json.loads(body)
            if isinstance(entry,list):
                if len(entry)!=10:raise ValueError("Invalid legacy event")
                key=tuple(entry[:5])
                if key not in rows or key in history:raise ValueError("Invalid approval")
                doc,source,version,proposer,reviewer,evidence=rows[key]
                if entry[5:]!=[source,version,proposer,reviewer,evidence]:raise ValueError("Approval mismatch")
                state=dict(document=doc,source_sha256=source,version=version,status="ACTIVE")
                active[key]=state
                history[key]=[dict(state,action="APPROVE",proposer=proposer,reviewer=reviewer,evidence=evidence,event_sha256=h)]
            else:
                exact_keys(entry,("action","key","previous_version","document","source_sha256","proposer","reviewer","evidence","request_id"))
                if not isinstance(entry["key"],list) or len(entry["key"])!=5:raise ValueError("Invalid event identity")
                key=tuple(entry["key"])
                if key not in active:raise ValueError("Document unavailable")
                old=active[key]
                if entry["previous_version"]!=old["version"] or entry["source_sha256"]!=old["source_sha256"]:raise ValueError("Stale revision")
                self._validate_revision(entry["action"],key,old,entry["document"],entry["proposer"],entry["reviewer"],entry["evidence"],entry["request_id"])
                state=dict(document=entry["document"] if entry["action"]=="CORRECT" else old["document"],
                           source_sha256=old["source_sha256"],version=h,status="ACTIVE" if entry["action"]=="CORRECT" else "REVOKED")
                history[key].append(dict(state,action=entry["action"],proposer=entry["proposer"],reviewer=entry["reviewer"],evidence=entry["evidence"],event_sha256=h,request_id=entry["request_id"]))
                if state["status"]=="ACTIVE":active[key]=state
                else:del active[key]
            prev=h
        if set(history)!=set(rows):raise ValueError("Missing approval event")
        return active,history

    def verify(self):
        try:self._replay();return True
        except (ValueError,TypeError,KeyError,AttributeError,sqlite3.Error):return False

    @staticmethod
    def _validate_revision(action,key,old,document,proposer,reviewer,evidence,request_id):
        identifier(proposer);identifier(reviewer)
        if proposer.casefold()==reviewer.casefold():raise ValueError("Independent reviewer required")
        if not isinstance(evidence,str) or not 10<=len(evidence.strip())<=1000:raise ValueError("Evidence required")
        if request_id is not None and (not isinstance(request_id,str) or not re.fullmatch(r"[a-f0-9]{64}",request_id)):
            raise ValueError("Invalid review request")
        if action=="CORRECT":
            validate(document)
            if (document["kind"],document["supplier"].casefold(),document["id"].casefold())!=key[2:]:
                raise ValueError("Correction cannot change document identity")
            if document==old["document"]:raise ValueError("No change")
            if len(canonical(document).encode())>MAX_DOC:raise ValueError("Correction too large")
        elif action=="REVOKE":
            if document is not None:raise ValueError("Revocation has no replacement")
        else:raise ValueError("Invalid revision action")

    def _revise_in_tx(self,tenant,synthetic,kind,supplier,doc_id,expected_version,action,document,proposer,reviewer,evidence,request_id=None):
        key=(*self.scope(tenant,synthetic),kind,identifier(supplier).casefold(),identifier(doc_id).casefold())
        active,_=self._replay()
        old=active.get(key)
        if old is None or old["version"]!=expected_version:raise ValueError("Document unavailable or stale revision")
        self._validate_revision(action,key,old,document,proposer,reviewer,evidence,request_id)
        entry=canonical(dict(action=action,key=list(key),previous_version=expected_version,document=document,
                   source_sha256=old["source_sha256"],proposer=proposer,reviewer=reviewer,evidence=evidence,request_id=request_id))
        prev=self.db.execute("SELECT hash FROM procurement_events ORDER BY seq DESC LIMIT 1").fetchone()[0]
        version=digest((prev+entry).encode())
        self.db.execute("INSERT INTO procurement_events(body,prev,hash) VALUES(?,?,?)",(entry,prev,version))
        self._replay()
        return version

    def revise(self,tenant,synthetic,kind,supplier,doc_id,expected_version,action,document,proposer,reviewer,evidence):
        try:
            self.db.execute("BEGIN IMMEDIATE")
            version=self._revise_in_tx(tenant,synthetic,kind,supplier,doc_id,expected_version,action,document,proposer,reviewer,evidence)
            self.db.commit()
            return version
        except BaseException:
            self.db.rollback();raise

    def revisions(self,tenant,synthetic):
        scope=self.scope(tenant,synthetic)
        self.db.execute("BEGIN")
        try:
            _,history=self._replay()
            result=[{"kind":key[2],"supplier_key":key[3],"document_key":key[4],"versions":versions}
                    for key,versions in sorted(history.items()) if key[:2]==scope]
            self.db.commit()
            return result
        except BaseException:
            self.db.rollback();raise

    def _approve_in_tx(self, tenant, synthetic, document, original, proposer, reviewer, evidence):
        scope = self.scope(tenant, synthetic)
        identifier(proposer)
        identifier(reviewer)
        if proposer.casefold() == reviewer.casefold():
            raise ValueError("Independent reviewer required")
        if not isinstance(evidence, str) or not 10 <= len(evidence.strip()) <= 1000:
            raise ValueError("Documentary evidence required")
        if not isinstance(original, bytes) or not 1 <= len(original) <= MAX_DOC:
            raise ValueError("Original source required, max 2 MB")
        validate(document)
        body = canonical(document)
        if len(body.encode()) > MAX_DOC:
            raise ValueError("Document too large")
        key = (*scope, document["kind"], document["supplier"].casefold(), document["id"].casefold())
        source, h = digest(original), digest(body.encode())
        entry = canonical([*key, source, h, proposer, reviewer, evidence])
        if not self.verify():
            raise ValueError("Ledger integrity failure")
        self.db.execute("INSERT INTO procurement_docs VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
                        (*key, body, source, h, original, proposer, reviewer, evidence))
        last = self.db.execute("SELECT hash FROM procurement_events ORDER BY seq DESC LIMIT 1").fetchone()
        prev = last[0] if last else "0" * 64
        self.db.execute("INSERT INTO procurement_events(body,prev,hash) VALUES(?,?,?)",
                        (entry, prev, digest((prev + entry).encode())))
        return h

    def approve(self, tenant, synthetic, document, original, proposer, reviewer, evidence):
        try:
            self.db.execute("BEGIN IMMEDIATE")
            result = self._approve_in_tx(tenant, synthetic, document, original, proposer, reviewer, evidence)
            self.db.commit()
            return result
        except sqlite3.IntegrityError as exc:
            self.db.rollback()
            raise ValueError("Duplicate or conflicting document; no overwrite") from exc
        except BaseException:
            self.db.rollback()
            raise

    def documents(self, tenant, synthetic):
        scope = self.scope(tenant, synthetic)
        self.db.execute("BEGIN")
        try:
            active,_=self._replay()
            result=[(state["document"],state["source_sha256"]) for key,state in sorted(active.items()) if key[:2]==scope]
            self.db.commit()
            return result
        except BaseException:
            self.db.rollback()
            raise


def reconcile(documents, as_of, tolerances=None):
    """Cumulative explicit matching by supplier + order ID + order line.

    Multiple deliveries and invoices are allocated to the same order line.
    All values are exclusive of VAT. Missing or incompatible evidence is not valued.
    A full snapshot through as_of is required; returns/credit notes are unsupported.
    """
    day(as_of)
    p = policy() if tolerances is None else policy(**tolerances)
    orders, linked, unmatched, seen = {}, defaultdict(list), [], set()
    with localcontext() as ctx:
        ctx.prec = 50
        for doc, source in documents:
            validate(doc)
            if not isinstance(source, str) or not re.fullmatch(r"[a-f0-9]{64}", source):
                raise ValueError("Source hash required")
            identity = (doc["kind"], doc["supplier"].casefold(), doc["id"].casefold())
            if identity in seen:
                raise ValueError("Duplicate document in snapshot")
            seen.add(identity)
            if doc["date"] > as_of:
                continue
            for line in doc["lines"]:
                ref = {"kind": doc["kind"], "supplier": doc["supplier"], "document": doc["id"],
                       "line": line["id"], "date": doc["date"], "source_sha256": source}
                if doc["kind"] == "order":
                    key = (identity[1], identity[2], line["id"].casefold())
                    orders[key] = (line, ref)
                else:
                    key = (identity[1], line["order_id"].casefold(), line["order_line"].casefold())
                    linked[key].append((line, ref))
        result = []
        total = ZERO
        for key in sorted(set(orders) | set(linked)):
            if key not in orders:
                unmatched.extend(dict(ref, reason="ORDER_MISSING") for _, ref in linked[key])
                continue
            order, order_ref = orders[key]
            entries = linked[key]
            valid = []
            invalid = []
            for line, ref in entries:
                if (line["sku"], line["unit"]) != (order["sku"], order["unit"]) or ref["date"] < order_ref["date"]:
                    invalid.append(dict(ref, reason="INCOMPATIBLE_SKU_UNIT_OR_DATE"))
                else:
                    valid.append((line, ref))
            receipts = [(l, r) for l, r in valid if r["kind"] == "receipt"]
            invoices = [(l, r) for l, r in valid if r["kind"] == "invoice"]
            ordered = decimal(order["quantity"])
            received = sum((decimal(l["quantity"]) for l, _ in receipts), ZERO)
            billed = sum((decimal(l["quantity"]) for l, _ in invoices), ZERO)
            actual = sum((decimal(l["net_total"]) for l, _ in invoices), ZERO)
            price = decimal(order["unit_price"]) * (1 - decimal(order["discount_pct"]) / 100)
            matched = min(ordered, received, billed)
            expected = money(matched * price)
            quantity_gap = max(ZERO, billed - min(ordered, received))
            alerts = []
            if not receipts and invoices:
                alerts.append("RECEIPT_MISSING")
            if received > ordered + p["quantity"]:
                alerts.append("OVER_RECEIPT")
            if quantity_gap > p["quantity"]:
                alerts.append("OVER_BILLED_QUANTITY")
            # Identify overprice per invoice, even if another invoice offsets it.
            high = []
            for line, ref in invoices:
                q = decimal(line["quantity"])
                cost = decimal(line["net_total"])
                if cost - money(q * price) > p["amount"] + money(q * price * p["price_pct"] / 100):
                    high.append(ref)
            if high:
                alerts.append("CONTRACT_PRICE_EXCEEDED")
            if invalid:
                alerts.append("INCOMPATIBLE_REFERENCE")
            # Never quantify when receipt evidence is absent or mismatched documents exist.
            # Gross net difference is NOT added to individual alert amounts.
            difference = money(actual - expected)
            exposure = None
            if receipts and invoices and not invalid:
                billed_contract = money(billed * price)
                net_price_gap = money(actual - billed_contract)
                threshold = p["amount"] + money(billed_contract * p["price_pct"] / 100)
                quantity_exposure = max(ZERO, billed_contract - expected) if quantity_gap > p["quantity"] else ZERO
                price_exposure = max(ZERO, net_price_gap) if net_price_gap > threshold else ZERO
                # Cap at net documentary excess, avoiding duplicate or offset amounts.
                exposure = min(max(ZERO, difference), quantity_exposure + price_exposure)
                total += exposure
            result.append({"order": order_ref, "sku": order["sku"], "unit": order["unit"],
                           "ordered": str(ordered), "received": str(received), "billed": str(billed),
                           "matched": str(matched), "quantity_gap": str(quantity_gap),
                           "contract_unit_net": str(price), "billed_net_eur": str(money(actual)), "gross_documentary_difference_eur": str(difference) if receipts and invoices and not invalid else None,
                           "expected_net_eur": str(expected) if receipts and invoices and not invalid else None,
                           "potential_exposure_eur": str(money(exposure)) if exposure is not None else None,
                           "alerts": alerts, "price_alert_lines": high,
                           "evidence": [r for _, r in valid], "incompatible": invalid})
        return {"schema_version": VERSION, "as_of": as_of, "policy": {k: str(v) for k,v in p.items()},
                "lines": result, "unmatched": unmatched, "potential_exposure_eur": str(money(total)),
                "confirmed_loss_eur": None, "scope": "Net EUR documentary exposure, not payment proof or realized savings. Do not add to other alert totals."}


def historical_audit(approved_csv):
    """Call the original engine unchanged on a reviewed, normalized CSV snapshot.

    Caller must provide a complete, single-tenant, single-class snapshot.
    """
    parse(approved_csv)
    return audit(approved_csv, synthetic=True)

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
          source_hash TEXT NOT NULL, body_hash TEXT NOT NULL, proposer TEXT NOT NULL,
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

    def verify(self):
        prev = "0" * 64
        expected = set()
        for body, predecessor, h in self.db.execute("SELECT body,prev,hash FROM procurement_events ORDER BY seq"):
            if prev != predecessor or digest((prev + body).encode()) != h:
                return False
            try:
                entry = json.loads(body)
                item = tuple(entry)
                if item in expected:
                    return False
                expected.add(item)
            except (TypeError, ValueError):
                return False
            prev = h
        actual = set()
        for row in self.db.execute("SELECT tenant,synthetic,kind,supplier_key,doc_key,body,source_hash,body_hash,proposer,reviewer,evidence FROM procurement_docs"):
            tenant, synthetic, kind, supplier, key, body, source, h, proposer, reviewer, evidence = row
            if digest(body.encode()) != h:
                return False
            actual.add((tenant, synthetic, kind, supplier, key, source, h, proposer, reviewer, evidence))
        return actual == expected

    def approve(self, tenant, synthetic, document, original, proposer, reviewer, evidence):
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
        try:
            self.db.execute("BEGIN IMMEDIATE")
            if not self.verify():
                raise ValueError("Ledger integrity failure")
            self.db.execute("INSERT INTO procurement_docs VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                            (*key, body, source, h, proposer, reviewer, evidence))
            last = self.db.execute("SELECT hash FROM procurement_events ORDER BY seq DESC LIMIT 1").fetchone()
            prev = last[0] if last else "0" * 64
            self.db.execute("INSERT INTO procurement_events(body,prev,hash) VALUES(?,?,?)",
                            (entry, prev, digest((prev + entry).encode())))
            self.db.commit()
        except sqlite3.IntegrityError as exc:
            self.db.rollback()
            raise ValueError("Duplicate or conflicting document; no overwrite") from exc
        except BaseException:
            self.db.rollback()
            raise
        return h

    def documents(self, tenant, synthetic):
        scope = self.scope(tenant, synthetic)
        self.db.execute("BEGIN")
        try:
            if not self.verify():
                raise ValueError("Ledger integrity failure")
            result = [(json.loads(body), src) for body, src in self.db.execute(
                "SELECT body,source_hash FROM procurement_docs WHERE tenant=? AND synthetic=?", scope)]
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
                threshold = p["amount"] + money(expected * p["price_pct"] / 100)
                exposure = max(ZERO, difference) if difference > threshold and (
                    quantity_gap > p["quantity"] or high or difference > threshold) else ZERO
                total += exposure
            result.append({"order": order_ref, "sku": order["sku"], "unit": order["unit"],
                           "ordered": str(ordered), "received": str(received), "billed": str(billed),
                           "matched": str(matched), "quantity_gap": str(quantity_gap),
                           "contract_unit_net": str(price), "billed_net_eur": str(money(actual)),
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

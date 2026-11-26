"""Read-only comparison of proposal references with approved order evidence."""
from procurement import validate

def reference_check(candidate,documents):
    validate(candidate)
    if candidate["kind"]=="order":
        return {"status":"NOT_APPLICABLE","lines":[],"warning":"No automatic approval."}
    orders={}
    for doc,source in documents:
        if doc["kind"]!="order":continue
        for line in doc["lines"]:
            key=(doc["supplier"].casefold(),doc["id"].casefold(),line["id"].casefold())
            if key in orders:raise ValueError("Duplicate approved order reference")
            orders[key]=(doc,line,source)
    checks=[]
    for line in candidate["lines"]:
        key=(candidate["supplier"].casefold(),line["order_id"].casefold(),line["order_line"].casefold())
        entry=orders.get(key)
        ref={"candidate_line":line["id"],"order_id":line["order_id"],"order_line":line["order_line"]}
        if not entry:checks.append(dict(ref,status="ORDER_NOT_FOUND"));continue
        doc,order,source=entry
        compatible=(line["sku"],line["unit"])==(order["sku"],order["unit"]) and candidate["date"]>=doc["date"]
        checks.append(dict(ref,status="REFERENCE_COMPATIBLE" if compatible else "REFERENCE_CONFLICT",
                           order_source_sha256=source,approved_sku=order["sku"],approved_unit=order["unit"],order_date=doc["date"]))
    return {"status":"REVIEW_REQUIRED" if any(r["status"]!="REFERENCE_COMPATIBLE" for r in checks) else "REFERENCES_COMPATIBLE",
            "lines":checks,"warning":"Reference consistency does not establish accuracy, quantity entitlement or payment. No automatic approval."}

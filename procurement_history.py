"""Reviewed purchase history and read-only adaptive signals.

Uses ALE's existing deviation and triage functions without promoting a model or
changing any financial rule. Only previous dates train a price baseline.
"""
from collections import defaultdict
from decimal import Decimal
from math import isfinite
import csv
import io
import json

from engine import FIELDS, audit
from adaptive_learning.engine import deviation, triage
from procurement import validate, decimal, day, money, reconcile


def group(doc, line):
    return json.dumps([doc["supplier"].casefold(),line["sku"],line["unit"]],ensure_ascii=False)


def historical_report(store, tenant, synthetic, as_of, rise_pct="10", alert_k=4, review_k=2, *, snapshot=None):
    day(as_of)
    rise = decimal(rise_pct)
    if not all(isinstance(k,(int,float)) and not isinstance(k,bool) and isfinite(k) for k in (alert_k,review_k)) or not 0 <= review_k < alert_k:
        raise ValueError("Invalid thresholds")
    docs = [(d,h) for d,h in (store.documents(tenant,synthetic) if snapshot is None else snapshot) if d["date"] <= as_of]
    # The existing deterministic engine remains the independent invoice audit.
    output=io.StringIO(newline="")
    writer=csv.writer(output);writer.writerow(FIELDS)
    events=defaultdict(list)
    for doc,source in docs:
        validate(doc)
        if doc["kind"]!="invoice":
            continue
        for line in doc["lines"]:
            q=decimal(line["quantity"]); cost=decimal(line["net_total"])
            writer.writerow([doc["supplier"],doc["id"],line["id"],doc["date"],line["sku"],line["unit"],line["quantity"],line["net_total"],"0","0",line["net_total"]])
            events[group(doc,line)].append((doc["date"],cost,q,doc["id"],line["id"],source))
    baseline_audit=audit(output.getvalue().encode(),synthetic=synthetic) if events else None
    signals=[]
    for key,rows in sorted(events.items()):
        dates=defaultdict(list)
        for row in rows:
            dates[row[0]].append(row)
        n=0; mean=0.; m2=0.; earliest=None
        for current, daily in sorted(dates.items()):
            # One quantity-weighted price per date; same-day observations cannot train each other.
            q=sum((x[2] for x in daily),Decimal(0))
            cost=sum((x[1] for x in daily),Decimal(0))
            price=cost/q
            stats={key:(n,mean,m2)}
            z=deviation(stats,key,price)
            status=triage(stats,key,price,alert_k,review_k)
            growth=(price/earliest-1)*100 if earliest is not None and earliest>0 else None
            if status in ("alert","review") or (growth is not None and growth>=rise):
                signals.append({"group":json.loads(key),"date":current,"price":str(price),
                    "prior_observation_days":n,"z_score":z,"statistical_status":status,
                    "cumulative_rise_pct":str(money(growth)) if growth is not None else None,
                    "rise_flag":growth is not None and growth>=rise,
                    "evidence":[{"invoice":x[3],"line":x[4],"source_sha256":x[5]} for x in daily]})
            # An independently reviewed source is not proof of an economically normal price.
            # Exclude statistical outliers from training; initial calibration is provisional.
            if status!="alert" and price>0:
                x=float(price);n+=1;delta=x-mean;mean+=delta/n;m2+=delta*(x-mean)
                if earliest is None:earliest=price
    return {"synthetic":synthetic,"as_of":as_of,"invoice_audit":baseline_audit,
            "adaptive_signals":signals,"matching":reconcile(docs,as_of),
            "scope":"Historical invoice audit and provisional read-only ALE signals; reviewed documents may still be abnormal. No confirmed losses; do not add overlapping metrics."}

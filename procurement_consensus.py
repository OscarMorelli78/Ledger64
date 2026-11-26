"""Conservative structured-text proposal and OCR comparison.

Independent review is mandatory even for agreement. Agreement between OCR passes
is not statistical independence or evidence of correctness.
"""
from procurement import canonical,validate
from procurement_ingest import extract
from pathlib import Path

HEAD=("kind","id","supplier","date","currency")
COMMON=("id","sku","unit","quantity")
EXTRA={"order":("unit_price","discount_pct"),"receipt":("order_id","order_line"),"invoice":("order_id","order_line","net_total")}

def labelled(text):
    """Only explicit documented layout. No guessing, correction or fuzzy mapping."""
    records={};lines=[]
    labels={"KIND":"kind","DOCUMENT":"id","SUPPLIER":"supplier","DATE":"date","CURRENCY":"currency"}
    for raw in text.splitlines():
        raw=raw.strip()
        if not raw:continue
        if raw.startswith("LINE "):
            parts=raw.split()
            if records.get("kind") not in EXTRA:return None
            keys=COMMON+EXTRA[records["kind"]]
            if len(parts)!=len(keys)+1:return None
            lines.append(dict(zip(keys,parts[1:]))
            )
            continue
        key,sep,value=raw.partition(":")
        if not sep or key not in labels or labels[key] in records:return None
        records[labels[key]]=value.strip()
    candidate={**records,"lines":lines}
    try:return validate(candidate)
    except (ValueError,TypeError,KeyError):return None

def choose(readings):
    """Do not resolve conflict by voting or confidence, even with 2-against-1."""
    candidates=[r["candidate"] for r in readings if r["candidate"] is not None]
    signatures={canonical(c) for c in candidates}
    if len(signatures)>1:status="REVIEW_REQUIRED_CONFLICT"
    elif len(candidates)<2:status="REVIEW_REQUIRED_INSUFFICIENT_AGREEMENT"
    else:status="REVIEW_REQUIRED_AGREEMENT"
    return dict(status=status,candidate=candidates[0] if status=="REVIEW_REQUIRED_AGREEMENT" else None,
                readings=readings,warning="No document is approved automatically.")

def compare_image(path):
    if Path(path).suffix.lower() not in (".png",".jpg",".jpeg"):raise ValueError("Image required")
    readings=[]
    expected_hash=None
    for psm,enhance in ((6,False),(4,True),(6,True)):
        r=extract(path,tesseract_psm=psm,enhance_image=enhance)
        if expected_hash is None:expected_hash=r["source_sha256"]
        if r["source_sha256"]!=expected_hash:raise ValueError("Original changed during comparison")
        candidate=labelled("\n".join(p["text"] for p in r["pages"]))
        readings.append(dict(psm=psm,enhanced=enhance,candidate=candidate,confidence=r["minimum_ocr_score"],source_sha256=expected_hash))
    return choose(readings)

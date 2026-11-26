"""Ledger64 procurement extension — trusted local operator, synthetic data only."""
import argparse
import json
from datetime import date
from pathlib import Path
from procurement import Store, canonical, reconcile
from procurement_history import historical_report
from procurement_ingest import extract, propose, load_source


def demo(store):
    tenant="demo"
    def doc(kind,id,when,lines):
        return dict(kind=kind,id=id,supplier="Fictitious supplier",date=when,currency="EUR",lines=lines)
    def line(id,q,**kw):
        return dict(id=id,sku="PAPER-A4",unit="ud",quantity=q,**kw)
    docs=[
        doc("order","PO1","2026-01-01",[line("1","100",unit_price="10",discount_pct="10")]),
        doc("receipt","R1","2026-01-03",[line("1","40",order_id="PO1",order_line="1")]),
        doc("receipt","R2","2026-01-04",[line("1","50",order_id="PO1",order_line="1")]),
        doc("invoice","I1","2026-01-05",[line("1","40",order_id="PO1",order_line="1",net_total="360")]),
        doc("invoice","I2","2026-01-06",[line("1","60",order_id="PO1",order_line="1",net_total="600")])]
    if store.documents(tenant,True):
        raise ValueError("Use an empty demo database")
    for d in docs:
        store.approve(tenant,True,d,canonical(d).encode(),"demo-analyst","demo-reviewer","Synthetic test fixture")
    return historical_report(store,tenant,True,"2026-01-31")


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db",type=Path,default=Path("procurement-demo.sqlite3"))
    sub=parser.add_subparsers(dest="action",required=True)
    sub.add_parser("demo")
    a=sub.add_parser("approve")
    a.add_argument("--tenant",required=True);a.add_argument("--document",type=Path,required=True)
    a.add_argument("--original",type=Path,required=True);a.add_argument("--proposer",required=True)
    a.add_argument("--reviewer",required=True);a.add_argument("--evidence",required=True)
    for name in ("match","history"):
        a=sub.add_parser(name);a.add_argument("--tenant",required=True)
        a.add_argument("--as-of",default=date.today().isoformat())
        if name=="match":
            a.add_argument("--quantity",default="0");a.add_argument("--amount",default="0.01");a.add_argument("--price-pct",default="0")
        else:a.add_argument("--rise-pct",default="10")
    a=sub.add_parser("extract")
    a.add_argument("source",type=Path);a.add_argument("--paddle-config",type=Path)
    a.add_argument("--pymupdf",action="store_true");a.add_argument("--ollama-model")
    a.add_argument("--confidence",type=float,default=.90)
    sub.add_parser("verify")
    args=parser.parse_args()
    if args.action=="extract":
        data=extract(args.source,paddle_config=args.paddle_config,use_pymupdf=args.pymupdf)
        result=propose(data,args.ollama_model,args.confidence) if args.ollama_model else data
    else:
        with Store(args.db) as store:
            if args.action=="demo":result=demo(store)
            elif args.action=="approve":
                raw,_=load_source(args.original)
                if args.document.stat().st_size>2_000_000:raise ValueError("Candidate too large")
                doc=json.loads(args.document.read_text(encoding="utf-8"))
                result={"approved_hash":store.approve(args.tenant,True,doc,raw,args.proposer,args.reviewer,args.evidence)}
            elif args.action=="match":result=reconcile(store.documents(args.tenant,True),args.as_of,{"quantity":args.quantity,"amount":args.amount,"price_pct":args.price_pct})
            elif args.action=="history":result=historical_report(store,args.tenant,True,args.as_of,args.rise_pct)
            else:
                result={"verified":store.verify()}
                if not result["verified"]:raise ValueError("Ledger integrity failure")
    print(json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False))

if __name__=="__main__":
    main()

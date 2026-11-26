"""Run a reproducible synthetic extraction comparison on provisioned local models.

Use no customer data. A real model is mandatory for each requested adapter.
Reports runtime, Linux peak RSS and exact token recovery on generated documents.
This is a smoke benchmark, not field-level financial accuracy.
"""
import argparse,json,platform,resource,tempfile,time
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from PIL import Image,ImageDraw,ImageFont
from procurement_ingest import extract,propose

def fixture(path,variant):
    im=Image.new("RGB",(1400,850),"white")
    d=ImageDraw.Draw(im);font=ImageFont.truetype("DejaVuSans.ttf",40)
    d.text((40,40),"INVOICE 12345",font=font,fill="black")
    d.text((40,105),"Supplier SYNTHETIC",font=font,fill="black")
    d.text((40,170),"Date 2026-01-01",font=font,fill="black")
    for x in (40,400,700,1000,1360):d.line((x,300,x,550),fill="black",width=4)
    for y in (300,380,460,550):d.line((40,y,1360,y),fill="black",width=4)
    for x,t in ((55,"SKU"),(415,"QTY"),(715,"UNIT"),(1015,"TOTAL")):d.text((x,315),t,font=font,fill="black")
    for x,t in ((55,"PAPER-A4"),(415,"10"),(715,"15"),(1015,"150")):d.text((x,395),t,font=font,fill="black")
    d.text((40,620),"TOTAL 150 EUR",font=font,fill="black")
    if variant:im=im.rotate(2,expand=True,fillcolor="white")
    im.save(path)

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--backend",choices=["tesseract","paddle"],required=True)
    parser.add_argument("--config",type=Path)
    parser.add_argument("--model")
    args=parser.parse_args()
    if args.backend=="paddle" and not args.config:parser.error("--config required")
    reports=[]
    with tempfile.TemporaryDirectory() as root:
        for i in range(2):
            path=Path(root)/("invoice"+str(i)+".png");fixture(path,i)
            start=time.perf_counter()
            result=extract(path,paddle_config=args.config if args.backend=="paddle" else None)
            elapsed=time.perf_counter()-start
            text="\n".join(x["text"] for x in result["pages"])
            expected=["12345","150","EUR","2026"]
            hits={token:token in text for token in expected}
            report=dict(case=i,backend=result["method"],elapsed_seconds=round(elapsed,3),
              peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
              token_recovery=sum(hits.values())/len(hits),hits=hits,
              table_count=len(result["tables"]),min_confidence=result["minimum_ocr_score"])
            if args.model:
                start=time.perf_counter()
                # This source lacks order reference; safe outcome is no complete candidate.
                p=propose(result,args.model)
                report["semantic_seconds"]=round(time.perf_counter()-start,3)
                report["semantic_abstained"]=p["candidate"] is None
            reports.append(report)
    print(json.dumps({"platform":platform.platform(),"scope":"synthetic smoke benchmark","results":reports},indent=2))
    if any(r["token_recovery"]<1 or (args.model and not r["semantic_abstained"]) for r in reports):
        raise SystemExit("Synthetic acceptance threshold failed")

if __name__=="__main__":main()

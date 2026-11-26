"""Synthetic image -> cell OCR -> reviewed mapping -> matching acceptance.

Metadata and mapping are explicitly supplied by a hypothetical operator.
No model guesses missing values. Tests use synthetic approvals only.
"""
import argparse,json,sys,tempfile,time
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from procurement import Store,reconcile
from procurement_geometry import extract_grid,reread_cells
from procurement_table import propose_from_cells
from procurement_references import reference_check

def docs():
    supplier="SYNTHETIC"
    def doc(kind,id,date,lines):return dict(kind=kind,id=id,supplier=supplier,date=date,currency="EUR",lines=lines)
    def line(id,sku,q,**extra):return dict(id=id,sku=sku,unit="ud",quantity=q,**extra)
    yield doc("order","PO1","2026-03-01",[
        line("1","P123","100",unit_price="10.00",discount_pct="10"),
        line("2","P456","20",unit_price="5.00",discount_pct="0")])
    yield doc("receipt","R1","2026-03-02",[
        line("1","P123","40",order_id="PO1",order_line="1"),
        line("2","P456","20",order_id="PO1",order_line="2")])
    yield doc("receipt","R2","2026-03-03",[
        line("1","P123","50",order_id="PO1",order_line="1")])
    yield doc("invoice","I1","2026-03-04",[
        line("1","P123","40",order_id="PO1",order_line="1",net_total="360.00"),
        line("2","P456","20",order_id="PO1",order_line="2",net_total="100.00")])
    yield doc("invoice","I2","2026-03-05",[
        line("1","P123","60",order_id="PO1",order_line="1",net_total="600.00")])

def render(path,doc,index):
    # Different column orders; fixed visible labels provide the mapping contract.
    labels={"id":"Line","sku":"SKU","unit":"Unit","quantity":"Qty","unit_price":"Price",
            "discount_pct":"Discount","order_id":"Order","order_line":"Ref","net_total":"Net"}
    keys=list(doc["lines"][0])
    shift=index%len(keys);keys=keys[shift:]+keys[:shift]
    rows=[[labels[k] for k in keys]]+[[l[k] for k in keys] for l in doc["lines"]]
    w=1800;h=1050
    im=Image.new("RGB",(w,h),"white");d=ImageDraw.Draw(im);font=ImageFont.truetype("DejaVuSansMono.ttf",36)
    d.text((40,40),doc["kind"].upper()+" "+doc["id"],font=font,fill="black")
    d.text((40,110),doc["supplier"]+"  "+doc["date"]+"  EUR",font=font,fill="black")
    xs=[round(60+i*(w-120)/len(keys)) for i in range(len(keys)+1)]
    ys=[300+i*110 for i in range(len(rows)+1)]
    for x in xs:d.line((x,ys[0],x,ys[-1]),fill="black",width=4)
    for y in ys:d.line((xs[0],y,xs[-1],y),fill="black",width=4)
    for i,row in enumerate(rows):
        for j,value in enumerate(row):d.text((xs[j]+15,ys[i]+25),value,font=font,fill="black")
    angle=(0,2,-3,1,-2)[index]
    if angle:im=im.rotate(angle,expand=True,fillcolor="white")
    im.save(path)
    return {k:labels[k] for k in keys}

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--strict',action='store_true');args=parser.parse_args()
    report=[]
    with tempfile.TemporaryDirectory() as root:
        with Store(Path(root)/"synthetic.sqlite3") as store:
            for index,gold in enumerate(docs()):
                path=Path(root)/(gold["id"]+".png")
                mapping=render(path,gold,index);raw=path.read_bytes()
                start=time.perf_counter()
                table=extract_grid(raw)
                metadata={k:v for k,v in gold.items() if k!="lines"}
                try:
                    draft=propose_from_cells(table,metadata,mapping,table["source_sha256"])
                    exact=draft["candidate"]==gold
                except (ValueError,TypeError,KeyError) as exc:
                    report.append({"id":gold["id"],"error":str(exc),"observed":table.get("cells")})
                    print(json.dumps(report,indent=2));raise
                item={"id":gold["id"],"first_pass_exact":exact,"seconds":round(time.perf_counter()-start,3),"observed":draft["candidate"]}
                if not exact and not args.strict and gold["kind"] in ("invoice","receipt"):
                    # Simulate a reviewer selecting a literal alternate reading only
                    # when it resolves a missing reference against approved records.
                    # Never use fixture truth to choose an alternate.
                    approved=store.documents("demo",True)
                    checks=reference_check(draft["candidate"],approved)
                    col=table["cells"][0].index(mapping["order_id"])
                    for i,check in enumerate(checks["lines"]):
                        if check["status"]!="ORDER_NOT_FOUND":continue
                        alternatives=reread_cells(raw,table,[[i+1,col]])["alternatives"][0]["readings"]
                        candidates=set()
                        for alt in alternatives:
                            candidate=dict(draft["candidate"],lines=[dict(x) for x in draft["candidate"]["lines"]])
                            candidate["lines"][i]["order_id"]=alt["text"]
                            try:
                                if reference_check(candidate,approved)["lines"][i]["status"]=="REFERENCE_COMPATIBLE":
                                    candidates.add(alt["text"])
                            except ValueError:pass
                        item.setdefault("reference_alternatives",[]).append({"row":i+2,"readings":alternatives,"compatible":sorted(candidates)})
                        if len(candidates)==1:
                            # Explicit simulated human selection, not runtime auto-correction.
                            table["cells"][i+1][col]=next(iter(candidates))
                            draft=propose_from_cells(table,metadata,mapping,table["source_sha256"])
                    exact=draft["candidate"]==gold
                item["reviewed_exact"]=exact;report.append(item)
                if not exact:
                    print(json.dumps(report,indent=2));raise SystemExit("Synthetic candidate mismatch")
                store.approve("demo",True,draft["candidate"],raw,"analyst","reviewer","Synthetic fixture independently compared to known truth")
            result=reconcile(store.documents("demo",True),"2026-03-31")
            assert store.verify()
            assert result["potential_exposure_eur"]=="150.00",result
            assert result["confirmed_loss_eur"] is None
            assert len(result["lines"])==2
            print(json.dumps({"scope":"five synthetic grid images; operator-provided metadata/mapping; simulated independent review of literal reference alternatives","first_pass_exact_count":sum(x["first_pass_exact"] for x in report),"reviewed_exact_count":sum(x["reviewed_exact"] for x in report),"cases":report,"exposure_eur":result["potential_exposure_eur"],"confirmed_loss_eur":None,"integrity_verified":True},indent=2))
if __name__=="__main__":main()

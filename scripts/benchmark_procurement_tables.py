"""Synthetic-only PP-StructureV3 table-cell acceptance experiment.

Provisioning uses a distinct synthetic warmup. Run acceptance inference in a container
with --network none. No customer documents accepted by this entrypoint.
"""
import argparse,json,time,resource,sys,os
from pathlib import Path
from html.parser import HTMLParser
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from procurement_table import canonical_columns

EXPECTED=[["SKU","QTY","UNIT","TOTAL"],["AX-123","17","8.25","140.25"],["BX-789","23","3.50","80.50"]]

class Cells(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True);self.rows=[];self.row=None;self.cell=None;self.invalid=False
    def handle_starttag(self,tag,attrs):
        if tag=="tr":
            if self.row is not None:self.invalid=True
            self.row=[]
        if tag in ("td","th"):
            if self.row is None or self.cell is not None or any(k in ("rowspan","colspan") and v!="1" for k,v in attrs):self.invalid=True
            self.cell=[]
    def handle_data(self,data):
        if self.cell is not None:self.cell.append(data)
    def handle_endtag(self,tag):
        if tag in ("td","th") and self.cell is not None:
            if self.row is None:self.invalid=True
            else:self.row.append(" ".join("".join(self.cell).split()))
            self.cell=None
        if tag=="tr" and self.row is not None:
            self.rows.append(self.row);self.row=None

def parse_table(html):
    p=Cells();p.feed(html);p.close()
    if p.invalid or p.row is not None or p.cell is not None:raise ValueError("Unsupported table structure")
    return p.rows

def table_fixture(path,variant,rows=EXPECTED):
    from PIL import Image,ImageDraw,ImageFont
    im=Image.new("RGB",(1500,1000),"white");d=ImageDraw.Draw(im)
    f=ImageFont.truetype("DejaVuSans.ttf",40)
    d.text((70,70),"SYNTHETIC PURCHASE INVOICE",fill="black",font=f)
    d.text((70,150),"Supplier: FICTITIOUS  |  Currency: EUR",fill="black",font=f)
    xs=[70,430,700,1010,1430];ys=[300,390,480,570]
    for x in xs:d.line((x,ys[0],x,ys[-1]),fill="black",width=4)
    for y in ys:d.line((xs[0],y,xs[-1],y),fill="black",width=4)
    for i,row in enumerate(rows):
        for j,value in enumerate(row):d.text((xs[j]+22,ys[i]+20),value,fill="black",font=f)
    d.text((70,680),"Net total: 220.75 EUR",fill="black",font=f)
    if variant:im=im.rotate(variant,expand=True,fillcolor="white")
    im.save(path)

def metrics(rows):
    correct=sum(i<len(rows) and j<len(rows[i]) and rows[i][j]==v for i,row in enumerate(EXPECTED) for j,v in enumerate(row))
    observed=sum(len(row) for row in rows)
    return dict(correct_cells=correct,expected_cells=12,observed_cells=observed,exact=rows==EXPECTED)

def main():
    p=argparse.ArgumentParser();p.add_argument("mode",choices=("provision","evaluate"))
    p.add_argument("--config",type=Path,required=True);p.add_argument("--output",type=Path)
    args=p.parse_args()
    if args.mode=="provision":
        from paddleocr import PPStructureV3
        pipeline=PPStructureV3(device="cpu",use_doc_orientation_classify=False,use_doc_unwarping=False,use_textline_orientation=False,use_seal_recognition=False,use_formula_recognition=False,use_chart_recognition=False)
        # Some PaddleX table models are initialized lazily on the first prediction.
        import tempfile
        with tempfile.TemporaryDirectory() as root:
            warm=Path(root)/"warmup.png"
            table_fixture(warm,0,[["SKU","QTY","UNIT","TOTAL"],["WARM-A","2","3.00","6.00"],["WARM-B","4","5.00","20.00"]])
            list(pipeline.predict(input=str(warm)))
        pipeline.export_paddlex_config_to_yaml(str(args.config))
        print("Provisioned model configuration and warmed lazy models using distinct synthetic fixture only")
        return
    from procurement_ingest import extract
    import tempfile
    results=[]
    with tempfile.TemporaryDirectory() as root:
        for i,angle in enumerate((0,2)):
            f=Path(root)/("table"+str(i)+".png");table_fixture(f,angle)
            start=time.perf_counter()
            result=extract(f,paddle_config=args.config)
            tables=[parse_table(t["html_untrusted"]) for t in result["tables"]]
            raw_metrics=metrics(tables[0]) if len(tables)==1 else metrics([])
            aligned=[]
            if len(tables)==1:
                try:aligned=canonical_columns(tables[0],EXPECTED[0])["cells"]
                except ValueError:pass
            best=metrics(aligned)
            results.append(dict(case=i,elapsed_seconds=round(time.perf_counter()-start,3),peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
              table_count=len(tables),tables=tables,raw_position_metrics=raw_metrics,rectification=result.get("rectification"),aligned_table=aligned,**best))
    report={"scope":"synthetic table recognition only; not financial validation","cases":results}
    output=json.dumps(report,indent=2)
    print(output)
    if args.output:args.output.write_text(output+"\n")
    if not all(r["exact"] and r["table_count"]==1 for r in results):raise SystemExit("Synthetic header-associated table-cell gate failed")

if __name__=="__main__":main()

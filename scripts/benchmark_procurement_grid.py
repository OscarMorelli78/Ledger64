"""Independent synthetic ruled-table benchmark with whole-process-tree RSS sampling.

Separate layout variants and values, no customer data. Linux /proc sampling is
an approximation (shared RSS may be counted twice, brief peaks may be missed).
"""
import argparse,json,os,sys,threading,time,tempfile
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from procurement_geometry import extract_grid
from procurement_table import canonical_columns

def process_rss(root):
    seen=set();todo=[root];total=0
    while todo:
        pid=todo.pop()
        if pid in seen:continue
        seen.add(pid)
        try:
            status=Path(f"/proc/{pid}/status").read_text()
            for line in status.splitlines():
                if line.startswith("VmRSS:"):total+=int(line.split()[1])
            for task in Path(f"/proc/{pid}/task").iterdir():
                todo.extend(int(x) for x in (task/"children").read_text().split())
        except (OSError,ValueError):pass
    return total

def fixture(path,rows,angle,layout):
    w,h=(1500,1000) if layout==0 else (1200,850)
    im=Image.new("RGB",(w,h),"white");d=ImageDraw.Draw(im)
    f=ImageFont.truetype("DejaVuSansMono.ttf",36 if layout==0 else 30)
    d.text((40,40),"SYNTHETIC PROCUREMENT",font=f,fill="black")
    xs=[round(w*(.04+i*.23)) for i in range(5)]
    ys=[round(h*.28+i*h*.11) for i in range(len(rows)+1)]
    for x in xs:d.line((x,ys[0],x,ys[-1]),fill="black",width=4)
    for y in ys:d.line((xs[0],y,xs[-1],y),fill="black",width=4)
    for i,row in enumerate(rows):
        for j,v in enumerate(row):d.text((xs[j]+15,ys[i]+22),v,font=f,fill="black")
    if angle:im=im.rotate(angle,expand=True,fillcolor="white")
    im.save(path)

def cases():
    yield "normal",0,0,[["SKU","QTY","PRICE","TOTAL"],["A-123","17","8.25","140.25"],["B-789","23","3.50","80.50"]]
    yield "tilted-positive",2,1,[["REF","QTY","COST","NET"],["K-456","12","7.50","90.00"],["R-234","15","2.20","33.00"]]
    yield "tilted-negative",-3,0,[["TOTAL","SKU","QTY","PRICE"],["84.00","M-824","12","7.00"],["35.25","N-742","15","2.35"]]
    yield "extra-row",0,1,[["ITEM","QTY","UNIT","NET"],["X-338","10","9.20","92.00"],["Y-719","20","3.15","63.00"],["Z-496","30","1.50","45.00"]]

def main():
    p=argparse.ArgumentParser();p.add_argument("--output",type=Path);p.add_argument("--gate",action="store_true");args=p.parse_args()
    stop=threading.Event();peak=[0]
    def sample():
        while not stop.is_set():
            peak[0]=max(peak[0],process_rss(os.getpid()));stop.wait(.025)
    results=[]
    sampler=threading.Thread(target=sample,daemon=True);sampler.start()
    try:
        with tempfile.TemporaryDirectory() as root:
            for name,angle,layout,gold in cases():
                path=Path(root)/(name+".png");fixture(path,gold,angle,layout)
                start=time.perf_counter();r=extract_grid(path.read_bytes());elapsed=time.perf_counter()-start
                observed=r.get("cells") or []
                correct=sum(i<len(observed) and j<len(observed[i]) and observed[i][j]==v for i,row in enumerate(gold) for j,v in enumerate(row))
                results.append({"case":name,"angle":angle,"rectification":r.get("transform"),"correct":correct,"expected":sum(map(len,gold)),"exact":observed==gold,"elapsed_seconds":round(elapsed,3),"status":r["status"],"observed":observed})
    finally:stop.set();sampler.join()
    mean=sum(r["elapsed_seconds"] for r in results)/len(results)
    report={"scope":"four synthetic single ruled tables; not arbitrary documents","sampled_peak_tree_rss_kib":peak[0],"mean_seconds":mean,"cases":results}
    out=json.dumps(report,indent=2);print(out)
    if args.output:args.output.write_text(out+"\n")
    if args.gate and (not all(r["exact"] for r in results) or mean>=10 or peak[0]>=4_000_000 or peak[0]<=0):
        raise SystemExit("Lightweight synthetic acceptance failed")
if __name__=="__main__":main()

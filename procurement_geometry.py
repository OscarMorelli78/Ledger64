"""Local lightweight ruled-table OCR, with bounded geometry and unapproved drafts.

No inference of financial values. Coordinates refer to the rectified image,
never the original. Unknown, borderless or irregular layouts must abstain.
"""
import csv
import io
import math
import shutil
import subprocess
import tempfile
from pathlib import Path
from PIL import Image,ImageOps,ImageStat

MAX_PIXELS=8_000_000
MAX_CELLS=64

def dark(image):
    return ImageOps.invert(image.convert("L")).point(lambda x:255 if x>100 else 0)

def projections(image,axis):
    size=(1,image.height) if axis=="row" else (image.width,1)
    return list(image.resize(size,Image.Resampling.BOX).getdata())

def score(image,angle):
    rotated=image.rotate(angle,resample=Image.Resampling.BILINEAR,expand=False,fillcolor=255)
    values=projections(dark(rotated),"row")
    # Emphasize strong horizontal alignment without knowing document content.
    return sum(v*v for v in values)/max(1,sum(values))

def deskew(image):
    original=ImageOps.exif_transpose(image).convert("L")
    if original.width*original.height>MAX_PIXELS:raise ValueError("Image too large")
    sample=original.copy();sample.thumbnail((800,800),Image.Resampling.LANCZOS)
    # Pad the scoring canvas to keep source content from clipping.
    sample=ImageOps.expand(sample,border=48,fill=255)
    baseline=score(sample,0)
    angles=[i*.5 for i in range(-10,11)]
    best=max(angles,key=lambda a:(score(sample,a),-abs(a)))
    refined=[round(best+i*.1,1) for i in range(-4,5) if abs(best+i*.1)<=5]
    best=max(refined+[0],key=lambda a:(score(sample,a),-abs(a)))
    gain=score(sample,best)/max(1e-9,baseline)
    if abs(best)<.2 or gain<1.08:return original,{"rotation_deg":0,"projection_gain":round(gain,3)}
    output=original.rotate(best,resample=Image.Resampling.BICUBIC,expand=True,fillcolor=255)
    if output.width*output.height>MAX_PIXELS:raise ValueError("Rectified image exceeds limit")
    return output,{"rotation_deg":best,"projection_gain":round(gain,3)}

def runs(values,threshold):
    groups=[]
    for i,v in enumerate(values):
        if v>=threshold:
            if groups and groups[-1][-1]==i-1:groups[-1].append(i)
            else:groups.append([i])
    return [int(round(sum(g)/len(g))) for g in groups if len(g)<=25]

def grid_geometry(image):
    mask=dark(image);ys=runs(projections(mask,"row"),140)
    if not 3<=len(ys)<=17 or min(b-a for a,b in zip(ys,ys[1:]))<20:
        raise ValueError("No single supported ruled table")
    band=mask.crop((0,ys[0],mask.width,ys[-1]+1))
    xs=runs(projections(band,"col"),185)
    if not 3<=len(xs)<=17 or min(b-a for a,b in zip(xs,xs[1:]))<25 or (len(xs)-1)*(len(ys)-1)>MAX_CELLS:
        raise ValueError("Unsupported grid geometry")
    # A full set of ruling lines must intersect, rejecting partial/merged grids.
    for y in ys:
        for x in xs:
            crop=mask.crop((max(0,x-3),max(0,y-3),min(mask.width,x+4),min(mask.height,y+4)))
            if crop.getextrema()[1]<200:raise ValueError("Broken grid intersection")
    for a,b in zip(ys,ys[1:]):
        # A partial separator that disappears from the full-band projection
        # must not silently merge adjacent cells.
        local=mask.crop((0,a+5,mask.width,b-5))
        local_xs=runs(projections(local,"col"),155)
        if any(not any(abs(x-global_x)<=4 for global_x in xs) for x in local_xs):
            raise ValueError("Partial vertical ruling")
        for x in xs:
            crop=mask.crop((max(0,x-3),a+5,min(mask.width,x+4),b-5))
            if sum(v>=100 for v in projections(crop,"row"))<.8*crop.height:raise ValueError("Missing vertical ruling")
    for a,b in zip(xs,xs[1:]):
        for y in ys:
            crop=mask.crop((a+5,max(0,y-3),b-5,min(mask.height,y+4)))
            if sum(v>=100 for v in projections(crop,"col"))<.8*crop.width:raise ValueError("Missing horizontal ruling")
    return xs,ys

def prepare_cell(image,*,scale=1,tight=False,binarize=False):
    if type(scale) is not int or scale not in (1,2,3):raise ValueError("Invalid OCR scale")
    if tight:
        box=dark(image).getbbox()
        if box:image=image.crop(box)
    if binarize:image=image.convert("L").point(lambda x:0 if x<160 else 255)
    border=20 if tight or scale==3 else 12
    if (image.width*scale+2*border)*(image.height*scale+2*border)>MAX_PIXELS:raise ValueError("Oversized cell variant")
    if scale!=1:image=image.resize((image.width*scale,image.height*scale),Image.Resampling.LANCZOS)
    return ImageOps.expand(image,border=border,fill=255)

def read_cell(binary,image,path,*,language="spa+eng",psm=7,upscale=False,scale=None,tight=False,binarize=False,no_dictionary=False):
    scale=scale if scale is not None else (2 if upscale and image.width*image.height*4<=MAX_PIXELS else 1)
    image=prepare_cell(image,scale=scale,tight=tight,binarize=binarize)
    image.save(path)
    args=[binary,str(path),"stdout","-l",language,"--psm",str(psm)]
    if no_dictionary:args.extend(["-c","load_system_dawg=0","-c","load_freq_dawg=0"])
    proc=subprocess.run(args+["tsv"],
                        capture_output=True,timeout=10,check=False)
    if proc.returncode or len(proc.stdout)>100_000:raise ValueError("Cell OCR failed")
    words=[];scores=[]
    for row in csv.DictReader(io.StringIO(proc.stdout.decode("utf-8")),delimiter="\t"):
        text=(row.get("text") or "").strip()
        if row.get("level")!="5" or not text:continue
        conf=float(row["conf"])/100
        if not math.isfinite(conf) or not 0<=conf<=1:raise ValueError("Invalid confidence")
        words.append(text);scores.append(conf)
    return " ".join(words),min(scores) if scores else None

def extract_grid(raw,reader=None):
    if not isinstance(raw,bytes) or not 1<=len(raw)<=2_000_000:raise ValueError("Invalid image source")
    from procurement import digest
    with Image.open(io.BytesIO(raw)) as im:
        if im.format not in ("PNG","JPEG") or im.width*im.height>MAX_PIXELS:raise ValueError("Unsupported image")
        image,transform=deskew(im)
    try:xs,ys=grid_geometry(image)
    except ValueError as exc:
        return {"source_sha256":digest(raw),"status":"REVIEW_REQUIRED_UNSUPPORTED_TABLE","cells":None,"reason":str(exc),"transform":transform}
    binary=shutil.which("tesseract") if reader is None else None
    if reader is None and not binary:raise ValueError("Local Tesseract required")
    rows=[];positions=[]
    with tempfile.TemporaryDirectory() as root:
        path=Path(root)/"cell.png"
        for y0,y1 in zip(ys,ys[1:]):
            row=[];evidence=[]
            for x0,x1 in zip(xs,xs[1:]):
                box=(x0+6,y0+6,x1-6,y1-6)
                crop=image.crop(box)
                value,conf=reader(crop) if reader else read_cell(binary,crop,path)
                row.append(value);evidence.append({"rectified_bbox":list(box),"confidence":conf,"text":value})
            rows.append(row);positions.append(evidence)
    return {"source_sha256":digest(raw),"status":"REVIEW_REQUIRED","page":1,"cells":rows,
            "cell_geometry":positions,"transform":transform,"rectified_size":[image.width,image.height],
            "warning":"Coordinates are on the rectified image. Compare with original. No automatic approval."}


def reread_cells(raw,table,positions):
    """Offer alternative OCR evidence, never rewrite a cell or force a known ID.

    Coordinates and original hash must match a fresh rectification. Limit this
    optional review action to 8 cells, with no whitelist of expected characters.
    """
    from procurement import digest
    if not isinstance(raw,bytes) or not 1<=len(raw)<=2_000_000 or digest(raw)!=table.get("source_sha256"):
        raise ValueError("Original source mismatch")
    if not isinstance(positions,list) or not 1<=len(positions)<=8:
        raise ValueError("Select 1–8 cells")
    binary=shutil.which("tesseract")
    if not binary:raise ValueError("Local OCR required")
    with Image.open(io.BytesIO(raw)) as im:
        if im.format not in ("PNG","JPEG") or im.width*im.height>MAX_PIXELS:raise ValueError("Unsupported image")
        image,transform=deskew(im)
    xs,ys=grid_geometry(image)
    if transform!=table.get("transform") or [image.width,image.height]!=table.get("rectified_size"):
        raise ValueError("Rectification mismatch")
    results=[]
    with tempfile.TemporaryDirectory() as root:
        path=Path(root)/"cell.png"
        for pos in positions:
            if not isinstance(pos,list) or len(pos)!=2 or any(type(v) is not int for v in pos):
                raise ValueError("Invalid cell position")
            r,c=pos
            if not 0<=r<len(ys)-1 or not 0<=c<len(xs)-1:raise ValueError("Cell outside grid")
            box=(xs[c]+6,ys[r]+6,xs[c+1]-6,ys[r+1]-6)
            crop=image.crop(box)
            readings=[]
            # General visual variants, not a whitelist or a known-order prompt.
            variants=(
                dict(language="eng",psm=7,scale=2),
                dict(language="eng",psm=8,scale=2),
                dict(language="spa+eng",psm=13,scale=2),
                dict(language="eng",psm=7,scale=3,no_dictionary=True),
                dict(language="eng",psm=7,scale=3,tight=True,no_dictionary=True),
                dict(language="eng",psm=8,scale=2,tight=True,binarize=True,no_dictionary=True),
            )
            for variant in variants:
                try:value,confidence=read_cell(binary,crop,path,**variant)
                except (ValueError,subprocess.TimeoutExpired):
                    readings.append({"text":"","confidence":None,**variant,"status":"UNAVAILABLE"})
                    continue
                readings.append({"text":value,"confidence":confidence,**variant,"status":"UNVERIFIED"})
            results.append({"row":r+1,"column":c+1,"rectified_bbox":list(box),"readings":readings})
    return {"status":"REVIEW_REQUIRED","source_sha256":digest(raw),"alternatives":results,
            "warning":"Alternatives are not corrected or approved values; compare original."}

"""Convert a single simple OCR table to bounded inert cells.

Do not render model-generated HTML. Merged cells, nested tables and ragged
rows require human reconstruction rather than speculative normalization.
"""
from html.parser import HTMLParser

class Table(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.rows=[];self.row=None;self.cell=None;self.open=False;self.count=0
    def handle_starttag(self,tag,attrs):
        if tag in ("script","style","iframe","object","embed","svg","img"):
            raise ValueError("Unsafe or unsupported element")
        if tag=="table":
            if self.open or self.count:raise ValueError("Multiple or nested tables")
            self.open=True;self.count+=1
        elif tag=="tr":
            if not self.open or self.row is not None:raise ValueError("Invalid row nesting")
            self.row=[]
        elif tag in ("td","th"):
            if self.row is None or self.cell is not None or any(k in ("rowspan","colspan") and v!="1" for k,v in attrs):
                raise ValueError("Unsupported merged or nested cell")
            self.cell=[];self.cell_tag=tag
        elif tag=="br" and self.cell is not None:self.cell.append(" ")
    def handle_data(self,data):
        if self.cell is not None:self.cell.append(data)
        elif self.open and data.strip():raise ValueError("Text outside cell")
    def handle_endtag(self,tag):
        if tag in ("td","th"):
            if self.cell is None or tag!=self.cell_tag:raise ValueError("Unmatched cell")
            text=" ".join("".join(self.cell).split())
            if len(text)>2000 or len(self.row)>=50:raise ValueError("Cell or column limit")
            self.row.append(text);self.cell=None
        elif tag=="tr":
            if self.row is None or self.cell is not None or not self.row:raise ValueError("Incomplete row")
            if len(self.rows)>=1000:raise ValueError("Row limit")
            self.rows.append(self.row);self.row=None
        elif tag=="table":
            if not self.open or self.row is not None or self.cell is not None:raise ValueError("Unclosed table elements")
            self.open=False

def parse_cells(html):
    if not isinstance(html,str) or not 1<=len(html)<=100_000:raise ValueError("Invalid table size")
    p=Table();p.feed(html);p.close()
    if p.count!=1 or p.open or p.row is not None or p.cell is not None or not p.rows or len({len(r) for r in p.rows})!=1:
        raise ValueError("Missing or irregular table")
    return p.rows

def table_drafts(tables):
    out=[]
    for t in tables:
        try:out.append({"page":t["page"],"status":"REVIEW_REQUIRED","cells":parse_cells(t["html_untrusted"])})
        except (ValueError,TypeError,KeyError):
            out.append({"page":t.get("page") if isinstance(t,dict) else None,"status":"REVIEW_REQUIRED_UNSUPPORTED_TABLE","cells":None})
    return out


def propose_from_cells(table,metadata,mapping,source_sha256):
    """Build an unapproved candidate from explicit columns and reviewed header data.

    No fuzzy headers, inferred monetary values, row merges or implicit metadata.
    Caller must independently review metadata against the original document.
    """
    import re
    from procurement import validate
    from procurement_consensus import HEAD,COMMON,EXTRA
    if not isinstance(source_sha256,str) or not re.fullmatch(r"[a-f0-9]{64}",source_sha256):
        raise ValueError("Original source hash required")
    if not isinstance(metadata,dict) or set(metadata)!=set(HEAD) or metadata.get("kind") not in EXTRA:
        raise ValueError("Explicit document metadata required")
    if not isinstance(table,dict) or table.get("status")!="REVIEW_REQUIRED":
        raise ValueError("Usable structured table required")
    cells=table.get("cells");page=table.get("page")
    if type(page) is not int or page<1 or not isinstance(cells,list) or not 2<=len(cells)<=1001:
        raise ValueError("Invalid table")
    header=cells[0]
    if not isinstance(header,list) or not 1<=len(header)<=50 or not all(isinstance(v,str) and v for v in header) or len(set(header))!=len(header):
        raise ValueError("Unique nonempty column labels required")
    keys=COMMON+EXTRA[metadata["kind"]]
    if not isinstance(mapping,dict) or set(mapping)!=set(keys) or not all(isinstance(v,str) and v in header for v in mapping.values()) or len(set(mapping.values()))!=len(keys):
        raise ValueError("Complete unambiguous mapping required")
    indexes={k:header.index(v) for k,v in mapping.items()}
    lines=[];evidence=[]
    for i,row in enumerate(cells[1:],2):
        if not isinstance(row,list) or len(row)!=len(header) or not all(isinstance(v,str) for v in row):
            raise ValueError("Ragged or invalid table row")
        line={k:row[indexes[k]] for k in keys}
        lines.append(line)
        evidence.append({k:{"page":page,"row":i,"column":indexes[k]+1,"header":mapping[k],"text":line[k]} for k in keys})
    candidate=validate(dict(metadata,lines=lines))
    return {"status":"REVIEW_REQUIRED","candidate":candidate,"source_sha256":source_sha256,
            "cell_evidence":evidence,"metadata_status":"MANUALLY_SUPPLIED_UNVERIFIED",
            "warning":"Review all metadata and cell readings against original. No automatic approval."}


def canonical_columns(rows,headers):
    """Align exact unique headers, preserving every raw cell and row association."""
    if not isinstance(rows,list) or not rows or not isinstance(headers,list) or not headers:
        raise ValueError("Table and canonical headers required")
    source=rows[0]
    if not isinstance(source,list) or not all(isinstance(v,str) and v for v in source+headers):
        raise ValueError("Invalid headers")
    if len(set(source))!=len(source) or len(set(headers))!=len(headers) or set(source)!=set(headers):
        raise ValueError("Missing, duplicate or unexpected header")
    if any(not isinstance(r,list) or len(r)!=len(source) or not all(isinstance(v,str) for v in r) for r in rows):
        raise ValueError("Ragged table")
    indices=[source.index(h) for h in headers]
    return {"cells":[[r[i] for i in indices] for r in rows],
            "source_columns":[i+1 for i in indices],"status":"REVIEW_REQUIRED"}

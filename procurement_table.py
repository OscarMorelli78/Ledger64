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

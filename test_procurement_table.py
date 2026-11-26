import unittest
from procurement_table import parse_cells,table_drafts,propose_from_cells

class TableTests(unittest.TestCase):
    def test_exact_positions(self):
        html="<html><body><table><tr><th>SKU</th><th>Total</th></tr><tr><td>A-1</td><td>12.50</td></tr></table></body></html>"
        self.assertEqual(parse_cells(html),[["SKU","Total"],["A-1","12.50"]])
    def test_blank_not_invented(self):
        self.assertEqual(parse_cells("<table><tr><td></td><td>0</td></tr></table>"),[["","0"]])
    def test_merged_rejected(self):
        with self.assertRaises(ValueError):parse_cells("<table><tr><td colspan='2'>12</td></tr></table>")
    def test_ragged_rejected(self):
        with self.assertRaises(ValueError):parse_cells("<table><tr><td>A</td></tr><tr><td>B</td><td>C</td></tr></table>")
    def test_no_html_execution(self):
        with self.assertRaises(ValueError):parse_cells("<table><tr><td><script>alert(1)</script></td></tr></table>")
        self.assertEqual(parse_cells("<table><tr><td>&lt;b&gt;12&lt;/b&gt;</td></tr></table>"),[["<b>12</b>"]])
    def test_nested_or_multiple_rejected(self):
        with self.assertRaises(ValueError):parse_cells("<table><tr><td><table></table></td></tr></table>")
        with self.assertRaises(ValueError):parse_cells("<table></table><table></table>")
    def test_draft_only(self):
        r=table_drafts([{"page":1,"html_untrusted":"<table><tr><td>12</td></tr></table>"},{"page":2,"html_untrusted":"bad"}])
        self.assertEqual(r[0]["status"],"REVIEW_REQUIRED")
        self.assertIsNone(r[1]["cells"])
class TableProposalTests(unittest.TestCase):
    def setUp(self):
        self.table={"page":1,"status":"REVIEW_REQUIRED","cells":[["No","Ref","Unit","Qty","Price","Discount"],["1","P","ud","20","12.50","5"]]}
        self.metadata={"kind":"order","id":"O1","supplier":"S","date":"2026-01-01","currency":"EUR"}
        self.mapping=dict(zip(("id","sku","unit","quantity","unit_price","discount_pct"),self.table["cells"][0]))
    def test_exact_source_cell_evidence(self):
        r=propose_from_cells(self.table,self.metadata,self.mapping,"a"*64)
        self.assertEqual(r["candidate"]["lines"][0]["unit_price"],"12.50")
        self.assertEqual(r["cell_evidence"][0]["unit_price"]["column"],5)
        self.assertEqual(r["cell_evidence"][0]["unit_price"]["row"],2)
        self.assertEqual(r["status"],"REVIEW_REQUIRED")
    def test_missing_mapping(self):
        del self.mapping["unit_price"]
        with self.assertRaises(ValueError):propose_from_cells(self.table,self.metadata,self.mapping,"a"*64)
    def test_blank_amount(self):
        self.table["cells"][1][4]=""
        with self.assertRaises(ValueError):propose_from_cells(self.table,self.metadata,self.mapping,"a"*64)
    def test_invalid_source_hash(self):
        with self.assertRaises(ValueError):propose_from_cells(self.table,self.metadata,self.mapping,"missing")
    def test_duplicate_column(self):
        self.table["cells"][0][4]="Qty"
        with self.assertRaises(ValueError):propose_from_cells(self.table,self.metadata,self.mapping,"a"*64)
    def test_invoice_requires_references(self):
        self.metadata["kind"]="invoice"
        with self.assertRaises(ValueError):propose_from_cells(self.table,self.metadata,self.mapping,"a"*64)

if __name__=="__main__":unittest.main()

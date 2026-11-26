import unittest
from procurement_table import parse_cells,table_drafts

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
if __name__=="__main__":unittest.main()

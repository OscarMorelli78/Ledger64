import unittest
from procurement_semantic_v3 import compact_candidate
from scripts.benchmark_procurement_fields import fixtures,render_text
from procurement_consensus import HEAD,COMMON,EXTRA

class CompactTests(unittest.TestCase):
    def setUp(self):
        name,self.doc,_=next(fixtures());self.text=render_text(name,self.doc)
        self.obj={"complete":True,"header":[self.doc[k] for k in HEAD],
                  "rows":[[l[k] for k in COMMON+EXTRA[self.doc["kind"]]] for l in self.doc["lines"]]}
    def test_exact(self):
        c,e=compact_candidate(self.obj,self.text);self.assertEqual(c,self.doc);self.assertTrue(e)
    def test_wrong_amount(self):
        self.obj["rows"][0][4]="999"
        with self.assertRaises(ValueError):compact_candidate(self.obj,self.text)
    def test_swap_rows(self):
        self.obj["rows"].reverse()
        with self.assertRaises(ValueError):compact_candidate(self.obj,self.text)
    def test_absence(self):
        self.assertEqual(compact_candidate({"complete":False,"header":[],"rows":[]},""),(None,{}))
    def test_incomplete_known_layout(self):
        with self.assertRaises(ValueError):compact_candidate(self.obj,self.text.rsplit("\n",1)[0])
if __name__=="__main__":unittest.main()

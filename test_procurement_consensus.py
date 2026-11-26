import unittest
from procurement_consensus import choose,labelled
from procurement_semantic_v2 import verify_fields
from scripts.benchmark_procurement_fields import fixtures,render_text

class ConsensusTests(unittest.TestCase):
    def setUp(self):
        name,self.doc,_=next(fixtures());self.text=render_text(name,self.doc)
    def test_exact_agreement_is_only_draft(self):
        d=labelled(self.text)
        self.assertEqual(d,self.doc)
        r=choose([{"candidate":d},{"candidate":d},{"candidate":None}])
        self.assertEqual(r["status"],"REVIEW_REQUIRED_AGREEMENT")
        self.assertEqual(r["candidate"],d)
    def test_conflict_never_majority_votes(self):
        d=labelled(self.text);other=labelled(self.text);other["lines"][0]["quantity"]="999"
        r=choose([{"candidate":d},{"candidate":d},{"candidate":other}])
        self.assertIsNone(r["candidate"])
        self.assertEqual(r["status"],"REVIEW_REQUIRED_CONFLICT")
    def test_single_candidate_abstains(self):
        self.assertIsNone(choose([{"candidate":self.doc},{"candidate":None}])["candidate"])
    def test_incomplete_reject(self):
        self.assertIsNone(labelled("KIND: invoice\nDOCUMENT: X"))
    def test_field_evidence(self):
        header={k:{"value":v,"quote":next(s for s in self.text.splitlines() if v in s)} for k,v in self.doc.items() if k!="lines"}
        lines=[{k:{"value":v,"quote":line_text} for k,v in line.items()} for line,line_text in zip(self.doc["lines"],self.text.splitlines()[5:])]
        obj={"complete":True,"fields":header,"lines":lines}
        self.assertEqual(verify_fields(obj,self.text),self.doc)
        obj["lines"][0]["quantity"]["value"]="999"
        with self.assertRaises(ValueError):verify_fields(obj,self.text)
    def test_abstention(self):
        self.assertIsNone(verify_fields({"complete":False,"fields":{},"lines":[]},""))
if __name__=="__main__":unittest.main()

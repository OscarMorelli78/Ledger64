import unittest
from scripts.benchmark_procurement_fields import fixtures,render_text,strict_candidate,evaluate,aggregate

class FieldBenchmark(unittest.TestCase):
    def test_exact_ground_truth(self):
        rows=[evaluate(gold,strict_candidate(render_text(name,gold))) for name,gold,_ in fixtures()]
        s=aggregate(rows)
        self.assertEqual(s["documents"],11)
        self.assertEqual(s["exact_complete"],9)
        self.assertEqual(s["unsafe_proposals"],0)
        self.assertEqual(s["field_f1"],1)
    def test_financial_corruption(self):
        name,gold,_=next(fixtures())
        candidate=strict_candidate(render_text(name,gold))
        candidate["lines"][0]["unit_price"]="999"
        r=evaluate(gold,candidate)
        self.assertFalse(r["exact"])
        self.assertEqual(r["financial_wrong"],1)
    def test_missing_line(self):
        name,gold,_=next(fixtures())
        candidate=strict_candidate(render_text(name,gold))
        candidate["lines"].pop()
        r=evaluate(gold,candidate)
        self.assertFalse(r["exact"])
        self.assertGreater(r["missing"],0)
    def test_abstention_not_success_on_complete(self):
        _,gold,_=next(fixtures())
        self.assertFalse(evaluate(gold,None)["exact"])
    def test_unsafe_proposal(self):
        _,gold,_=next(fixtures())
        self.assertEqual(aggregate([evaluate(None,gold)])["unsafe_proposals"],1)
    def test_exact_decimals(self):
        name,gold,_=next(fixtures())
        candidate=strict_candidate(render_text(name,gold))
        candidate["lines"][0]["quantity"]+=".00"
        self.assertTrue(evaluate(gold,candidate)["exact"])
if __name__=="__main__":unittest.main()

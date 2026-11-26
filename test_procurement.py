import tempfile
import unittest
from pathlib import Path
from procurement import Store, reconcile, digest, historical_audit

def doc(kind, id, lines, day="2026-01-10", supplier="S"):
    return dict(kind=kind,id=id,supplier=supplier,date=day,currency="EUR",lines=lines)

def line(id, q, **kw):
    return dict(id=id,sku="P",unit="ud",quantity=q,**kw)

def order():
    return doc("order","O",[line("1","100",unit_price="10",discount_pct="10")],"2026-01-01")

def delivery(id,q):
    return doc("receipt",id,[line("1",q,order_id="O",order_line="1")])

def invoice(id,q,total):
    return doc("invoice",id,[line("1",q,order_id="O",order_line="1",net_total=total)])

def inputs(*docs):
    return [(x,digest(repr(x).encode())) for x in docs]

class ProcurementTests(unittest.TestCase):
    def run_match(self,*docs,**kwargs):
        return reconcile(inputs(*docs),"2026-01-31",**kwargs)

    def test_partial_multiple(self):
        r=self.run_match(order(),delivery("R1","40"),delivery("R2","50"),invoice("I1","40","360"),invoice("I2","60","600"))
        self.assertEqual(r["potential_exposure_eur"],"150.00")
        self.assertEqual(r["lines"][0]["expected_net_eur"],"810.00")
        self.assertEqual(r["lines"][0]["quantity_gap"],"10")
        self.assertIn("CONTRACT_PRICE_EXCEEDED",r["lines"][0]["alerts"])
        self.assertEqual(len(r["lines"][0]["evidence"]),4)
        self.assertIsNone(r["confirmed_loss_eur"])

    def test_clean_discount(self):
        self.assertEqual(self.run_match(order(),delivery("R","50"),invoice("I","50","450"))["potential_exposure_eur"],"0.00")

    def test_no_receipt(self):
        r=self.run_match(order(),invoice("I","50","450"))
        self.assertIsNone(r["lines"][0]["potential_exposure_eur"])
        self.assertIn("RECEIPT_MISSING",r["lines"][0]["alerts"])

    def test_missing_order(self):
        r=self.run_match(invoice("I","50","450"))
        self.assertEqual(r["unmatched"][0]["reason"],"ORDER_MISSING")

    def test_bad_unit(self):
        inv=invoice("I","50","900");inv["lines"][0]["unit"]="kg"
        r=self.run_match(order(),delivery("R","50"),inv)
        self.assertIsNone(r["lines"][0]["potential_exposure_eur"])

    def test_tolerance(self):
        r=self.run_match(order(),delivery("R","50"),invoice("I","50","451"),tolerances={"amount":"2"})
        self.assertEqual(r["potential_exposure_eur"],"0.00")
        self.assertNotIn("CONTRACT_PRICE_EXCEEDED",r["lines"][0]["alerts"])

    def test_future_receipt(self):
        future=delivery("R","50");future["date"]="2026-02-01"
        r=self.run_match(order(),future,invoice("I","50","450"))
        self.assertIsNone(r["lines"][0]["potential_exposure_eur"])

    def test_duplicate_snapshot(self):
        with self.assertRaises(ValueError):self.run_match(order(),order())

    def test_other_supplier(self):
        inv=invoice("I","50","450");inv["supplier"]="Other"
        self.assertEqual(len(self.run_match(order(),inv)["unmatched"]),1)

    def test_over_order(self):
        r=self.run_match(order(),delivery("R","120"),invoice("I","120","1080"))
        self.assertEqual(r["potential_exposure_eur"],"180.00")

    def test_no_paid_loss(self):
        self.assertIsNone(self.run_match(order())["confirmed_loss_eur"])

    def test_reject_bad_inputs(self):
        for q in ["0","NaN","-1","1e5",10]:
            with self.assertRaises(ValueError):self.run_match(order(),delivery("R",q))

    def test_persistence_review_and_isolation(self):
        with tempfile.TemporaryDirectory() as root:
            path=Path(root)/"memory.sqlite"
            with Store(path) as s:
                with self.assertRaises(ValueError):s.approve("A",True,order(),b"one","a","A","verified source")
                s.approve("A",True,order(),b"one","a","b","verified source")
                with self.assertRaises(ValueError):s.approve("A",True,order(),b"two","a","b","verified source")
                self.assertTrue(s.verify())
            with Store(path) as s:
                self.assertEqual(len(s.documents("A",True)),1)
                self.assertEqual(s.documents("A",False),[])
                self.assertEqual(s.documents("B",True),[])
                s.db.execute("UPDATE procurement_docs SET evidence='changed'")
                s.db.commit()
                self.assertFalse(s.verify())
                with self.assertRaises(ValueError):s.documents("A",True)

    def test_preserved_engine(self):
        raw=Path("demo.csv").read_bytes()
        from engine import audit
        self.assertEqual(historical_audit(raw),audit(raw,synthetic=True))

if __name__=="__main__":unittest.main()

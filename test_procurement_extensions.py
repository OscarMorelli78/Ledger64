import json
import tempfile
import unittest
from datetime import date,timedelta
from pathlib import Path
from unittest.mock import patch
from procurement import Store,canonical,reconcile
from procurement_history import historical_report
from procurement_ingest import extract,propose
from procurement_cli import demo
from test_procurement import order,delivery,invoice,inputs


class ExtensionTests(unittest.TestCase):
    def test_quantity_tolerance_not_counted_as_price(self):
        r=reconcile(inputs(order(),delivery("R","99"),invoice("I","100","900")),"2026-01-31",{"quantity":"1"})
        self.assertEqual(r["potential_exposure_eur"],"0.00")
        self.assertEqual(r["lines"][0]["gross_documentary_difference_eur"],"9.00")

    def test_price_tolerance_does_not_hide_quantity(self):
        r=reconcile(inputs(order(),delivery("R","90"),invoice("I","100","910")),"2026-01-31",{"price_pct":"2"})
        self.assertEqual(r["potential_exposure_eur"],"90.00")

    def test_demo_end_to_end(self):
        with tempfile.TemporaryDirectory() as root:
            with Store(Path(root)/"demo.db") as store:
                r=demo(store)
                self.assertEqual(r["matching"]["potential_exposure_eur"],"150.00")
                self.assertEqual(r["invoice_audit"]["rows"],2)
                self.assertTrue(store.verify())
                with self.assertRaises(ValueError):demo(store)

    def test_ale_no_future_leak(self):
        with tempfile.TemporaryDirectory() as root:
            with Store(Path(root)/"demo.db") as store:
                start=date(2026,1,1)
                for i in range(22):
                    doc=invoice("I"+str(i),"1","100" if i<21 else "140")
                    doc["date"]=(start+timedelta(days=i)).isoformat()
                    store.approve("A",True,doc,canonical(doc).encode(),"analyst","owner","Reviewed synthetic fixture")
                r=historical_report(store,"A",True,"2026-01-22")
                signal=r["adaptive_signals"][-1]
                self.assertEqual(signal["prior_observation_days"],21)
                self.assertEqual(signal["statistical_status"],"alert")
                self.assertEqual(signal["cumulative_rise_pct"],"40.00")
                self.assertEqual(historical_report(store,"B",True,"2026-01-22")["adaptive_signals"],[])
                self.assertEqual(historical_report(store,"A",False,"2026-01-22")["adaptive_signals"],[])

    def test_original_integrity(self):
        with tempfile.TemporaryDirectory() as root:
            with Store(Path(root)/"demo.db") as store:
                store.approve("A",True,order(),b"source","a","b","Synthetic document")
                store.db.execute("UPDATE procurement_docs SET original=?",(b"tamper",));store.db.commit()
                self.assertFalse(store.verify())

    def test_csv_and_json_extraction(self):
        with tempfile.TemporaryDirectory() as root:
            for ext,raw in [("csv",b"invoice,amount\nX,100"),("json",b'{"invoice":"X"}')]:
                path=Path(root)/("file."+ext);path.write_bytes(raw)
                r=extract(path)
                self.assertEqual(r["status"],"UNAPPROVED")
                self.assertEqual(r["pages"][0]["text"],raw.decode())
                self.assertIsNone(r["minimum_ocr_score"])

    def test_low_confidence_blocks_model(self):
        with patch("procurement_ingest.urllib.request.build_opener") as opener:
            r=propose({"minimum_ocr_score":.5,"source_sha256":"a"*64},"local-model")
            self.assertIsNone(r["candidate"])
            opener.assert_not_called()

    def test_model_proposal_never_approved(self):
        extraction={"minimum_ocr_score":.99,"source_sha256":"a"*64,"pages":[{"page":1,"text":"PO O price 10"}]}
        reply={"message":{"content":json.dumps({"candidate":order(),"evidence":["price 10"]})}}
        with patch("procurement_ingest.urllib.request.build_opener") as opener:
            opener.return_value.open.return_value.__enter__.return_value.read.return_value=json.dumps(reply).encode()
            r=propose(extraction,"local-model")
            self.assertEqual(r["status"],"REVIEW_REQUIRED")
            self.assertEqual(r["candidate"],order())
            self.assertEqual(opener.return_value.open.call_args.args[0].full_url,"http://127.0.0.1:11434/api/chat")
            reply["message"]["content"]=json.dumps({"candidate":order(),"evidence":["invented"]})
            opener.return_value.open.return_value.__enter__.return_value.read.return_value=json.dumps(reply).encode()
            with self.assertRaises(ValueError):propose(extraction,"local-model")

    def test_pdf_and_xlsx(self):
        for file in ("demo.pdf","demo.xlsx"):
            r=extract(Path(file))
            self.assertEqual(r["status"],"UNAPPROVED")
            self.assertTrue(r["pages"][0]["text"])

if __name__=="__main__":unittest.main()

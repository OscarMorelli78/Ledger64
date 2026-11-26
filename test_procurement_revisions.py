import tempfile,unittest,json
from pathlib import Path
from procurement import Store,canonical,reconcile
from procurement_history import historical_report
from test_procurement import order,delivery,invoice

class RevisionTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.path=Path(self.temp.name)/"revision.db"
        self.doc=invoice("I","50","600")
        with Store(self.path) as s:
            for d in (order(),delivery("R","50"),self.doc):
                v=s.approve("A",True,d,canonical(d).encode(),"analyst","owner","Synthetic evidence verified")
                if d==self.doc:self.version=v
    def tearDown(self):self.temp.cleanup()
    def change(self,s,action="CORRECT",doc=None,version=None,tenant="A",reviewer="owner"):
        return s.revise(tenant,True,"invoice","S","I",version or self.version,action,doc,"analyst",reviewer,"Independent synthetic revision")
    def test_correct_then_revoke_persistent(self):
        with Store(self.path) as s:
            self.assertEqual(reconcile(s.documents("A",True),"2026-01-31")["potential_exposure_eur"],"150.00")
            replacement=invoice("I","50","450")
            v=self.change(s,doc=replacement)
            self.assertEqual(reconcile(s.documents("A",True),"2026-01-31")["potential_exposure_eur"],"0.00")
            self.assertEqual(historical_report(s,"A",True,"2026-01-31")["invoice_audit"]["rows"],1)
            with self.assertRaises(ValueError):self.change(s,doc=invoice("I","50","500"))
            self.change(s,action="REVOKE",version=v)
            self.assertIsNone(historical_report(s,"A",True,"2026-01-31")["invoice_audit"])
        with Store(self.path) as s:
            self.assertTrue(s.verify())
            record=next(x for x in s.revisions("A",True) if x["kind"]=="invoice")
            self.assertEqual([x["action"] for x in record["versions"]],["APPROVE","CORRECT","REVOKE"])
            self.assertEqual(record["versions"][0]["document"],self.doc)
            self.assertEqual(len({x["source_sha256"] for x in record["versions"]}),1)
            self.assertEqual(len(s.documents("A",True)),2)
            self.assertEqual(s.revisions("B",True),[])
            self.assertEqual(s.revisions("A",False),[])
    def test_wrong_scope_self_review_identity_and_noop(self):
        with Store(self.path) as s:
            for kwargs in (dict(doc=invoice("I","50","450"),tenant="B"),dict(doc=invoice("I","50","450"),reviewer="ANALYST"),dict(doc=invoice("OTHER","50","450")),dict(doc=self.doc)):
                with self.assertRaises(ValueError):self.change(s,**kwargs)
            self.assertTrue(s.verify())
    def test_revoke_cannot_reimport(self):
        with Store(self.path) as s:
            self.change(s,action="REVOKE")
            with self.assertRaises(ValueError):s.approve("A",True,self.doc,b"different","a","b","Synthetic reimport attempt")
    def test_revision_event_tampering(self):
        with Store(self.path) as s:
            self.change(s,doc=invoice("I","50","450"))
            s.db.execute("UPDATE procurement_events SET body='{}' WHERE seq=(SELECT MAX(seq) FROM procurement_events)")
            s.db.commit()
            self.assertFalse(s.verify())
            with self.assertRaises(ValueError):s.documents("A",True)
    def test_revoke_order_blocks_matching(self):
        with Store(self.path) as s:
            v=next(x for x in s.revisions("A",True) if x["kind"]=="order")["versions"][-1]["version"]
            s.revise("A",True,"order","S","O",v,"REVOKE",None,"a","b","Synthetic order invalidated")
            r=reconcile(s.documents("A",True),"2026-01-31")
            self.assertEqual(r["potential_exposure_eur"],"0.00")
            self.assertEqual(len(r["unmatched"]),2)
    def test_revision_preserves_legacy_body(self):
        with Store(self.path) as s:
            before=s.db.execute("SELECT body,original FROM procurement_docs WHERE kind='invoice'").fetchone()
            self.change(s,doc=invoice("I","50","450"))
            after=s.db.execute("SELECT body,original FROM procurement_docs WHERE kind='invoice'").fetchone()
            self.assertEqual(before,after)
if __name__=="__main__":unittest.main()

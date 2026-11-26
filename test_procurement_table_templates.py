import tempfile,unittest
from pathlib import Path
from procurement import Store,digest
from procurement_table import propose_from_cells
from procurement_table_templates import register,apply

class TableTemplates(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.path=Path(self.tmp.name)/"memory.sqlite"
        self.metadata={"kind":"order","id":"O1","supplier":"S","date":"2026-01-01","currency":"EUR"}
        self.table={"page":1,"status":"REVIEW_REQUIRED","cells":[["No","Ref","Unit","Qty","Price","Discount"],["1","P","ud","20","12.50","5"]]}
        self.mapping=dict(zip(("id","sku","unit","quantity","unit_price","discount_pct"),self.table["cells"][0]))
        self.raw=b"synthetic original";self.source=digest(self.raw)
    def tearDown(self):self.tmp.cleanup()
    def approve(self,s):
        d=propose_from_cells(self.table,self.metadata,self.mapping,self.source)["candidate"]
        s.approve("A",True,d,self.raw,"analyst","owner","Independent synthetic review")
    def register(self,s,reviewer="owner"):
        return register(s,"A",True,self.table,self.metadata,self.mapping,self.source,"analyst",reviewer,"Independent mapping review")
    def test_requires_approved_source(self):
        with Store(self.path) as s:
            with self.assertRaises(ValueError):self.register(s)
    def test_reuse_never_copies_historical_price(self):
        with Store(self.path) as s:
            self.approve(s);key=self.register(s)
        with Store(self.path) as s:
            table={"page":1,"status":"REVIEW_REQUIRED","cells":[["Price","No","Ref","Unit","Qty","Discount"],["99.99","1","P","ud","20","5"]]}
            r=apply(s,"A",True,key,table,dict(self.metadata,id="O2"),"b"*64)
            self.assertEqual(r["candidate"]["lines"][0]["unit_price"],"99.99")
            self.assertEqual(r["cell_evidence"][0]["unit_price"]["column"],1)
            self.assertEqual(r["status"],"REVIEW_REQUIRED")
    def test_wrong_scope_and_supplier(self):
        with Store(self.path) as s:
            self.approve(s);key=self.register(s)
            for tenant,synthetic in (("B",True),("A",False)):
                with self.assertRaises(KeyError):apply(s,tenant,synthetic,key,self.table,self.metadata,self.source)
            with self.assertRaises(ValueError):apply(s,"A",True,key,self.table,dict(self.metadata,supplier="Other"),self.source)
    def test_independent_and_integrity(self):
        with Store(self.path) as s:
            self.approve(s)
            with self.assertRaises(ValueError):self.register(s,"analyst")
            key=self.register(s)
            s.db.execute("UPDATE procurement_table_templates SET body='{}'");s.db.commit()
            with self.assertRaises(ValueError):apply(s,"A",True,key,self.table,self.metadata,self.source)
if __name__=="__main__":unittest.main()

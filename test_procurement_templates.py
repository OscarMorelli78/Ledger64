import tempfile
import unittest
from pathlib import Path
from procurement import Store
from procurement_templates import register,apply,fields

class TemplateTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.path=Path(self.temp.name)/"pilot.db"
        self.mapping={f:f for f in fields("order")}
        self.raw=(",".join(self.mapping.values())+"\nS,O,2026-01-01,EUR,1,P,ud,100,10,5\n").encode()
    def tearDown(self):self.temp.cleanup()
    def save(self,s,reviewer="owner"):
        return register(s,"A",True,"order","S",self.mapping,",",self.raw,"analyst",reviewer,"Synthetic mapping verified")
    def test_persistent_reuse_and_versions(self):
        with Store(self.path) as s:
            first=self.save(s);second=self.save(s);self.assertNotEqual(first,second)
        with Store(self.path) as s:
            changed=self.raw.replace(b",100,10,5",b",50,10,5").replace(b",O,",b",O2,")
            result=apply(s,"A",True,second,changed)
            self.assertEqual(result["template_version"],2)
            self.assertEqual(result["candidate"]["lines"][0]["quantity"],"50")
            self.assertEqual(result["status"],"REVIEW_REQUIRED")
    def test_layout_and_supplier_change(self):
        with Store(self.path) as s:
            key=self.save(s)
            for raw in (self.raw.replace(b"supplier",b"vendor"),self.raw.replace(b"\nS,",b"\nOTHER,")):
                with self.assertRaises(ValueError):apply(s,"A",True,key,raw)
    def test_independent_and_scope(self):
        with Store(self.path) as s:
            with self.assertRaises(ValueError):self.save(s,"analyst")
            key=self.save(s)
            with self.assertRaises(KeyError):apply(s,"B",True,key,self.raw)
            with self.assertRaises(KeyError):apply(s,"A",False,key,self.raw)
    def test_integrity(self):
        with Store(self.path) as s:
            key=self.save(s)
            s.db.execute("UPDATE procurement_templates SET body='{}'");s.db.commit()
            with self.assertRaises(ValueError):apply(s,"A",True,key,self.raw)

if __name__=="__main__":unittest.main()

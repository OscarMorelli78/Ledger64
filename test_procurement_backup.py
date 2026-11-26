import json,sqlite3,tempfile,unittest
from pathlib import Path
from procurement import Store,canonical,digest,reconcile
from procurement_history import historical_report
from procurement_backup import create_backup,verify_backup,restore_backup,file_hash
from procurement_queue import initialize,submit,review,list_cases
import procurement_lifecycle as lifecycle
from procurement_templates import register,fields,apply
from test_procurement import order,delivery,invoice

class Recovery(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.root=Path(self.temp.name);self.db=self.root/"live.sqlite3";self.backup=self.root/"backup.sqlite3"
        self.a={"company":"A","id":"analyst","role":"analyst"};self.b={"company":"A","id":"owner","role":"owner"}
        with Store(self.db) as s:
            initialize(s)
            for doc in (order(),delivery("R","50"),invoice("I","50","600")):
                k=submit(s,self.a,doc,canonical(doc).encode(),"Synthetic original reviewed")
                review(s,self.b,k,"APPROVED","Independent original review")
            v=next(x for x in s.revisions("A",True) if x["kind"]=="invoice")["versions"][-1]["version"]
            k=lifecycle.submit(s,self.a,"invoice","S","I",v,"CORRECT",invoice("I","50","450"),"Synthetic transcription correction")
            lifecycle.review(s,self.b,k,"APPROVED","Independent correction verified")
            self.pending=submit(s,self.a,invoice("I2","1","9"),b"pending original","Synthetic pending invoice")
            mapping={x:x for x in fields("order")}
            self.csv=(",".join(mapping)+"\nS,O2,2026-01-01,EUR,1,P,ud,20,10,5\n").encode()
            self.template=register(s,"A",True,"order","S",mapping,",",self.csv,"analyst","owner","Independent mapping review")
    def tearDown(self):self.temp.cleanup()
    def create(self):return create_backup(self.db,self.backup,"A")
    def test_loss_restore_all_data(self):
        with Store(self.db) as s:
            before=historical_report(s,"A",True,"2026-01-31")
            history=s.revisions("A",True);cases=list_cases(s,self.a);requests=lifecycle.list_requests(s,self.a)
        manifest=self.create();self.db.unlink()
        dest=self.root/"recovered.sqlite3"
        r=restore_backup(self.backup,dest,"A",manifest["sha256"])
        self.assertEqual(r["sha256"],file_hash(dest))
        with Store(dest) as s:
            self.assertEqual(historical_report(s,"A",True,"2026-01-31"),before)
            self.assertEqual(s.revisions("A",True),history)
            self.assertEqual(list_cases(s,self.a),cases)
            self.assertEqual(lifecycle.list_requests(s,self.a),requests)
            self.assertEqual(s.original_source("A",True,digest(canonical(invoice("I","50","600")).encode())),canonical(invoice("I","50","600")).encode())
            self.assertEqual(apply(s,"A",True,self.template,self.csv)["candidate"]["id"],"O2")
            self.assertTrue(s.verify())
            review(s,self.b,self.pending,"APPROVED","Recovered pending invoice reviewed")
            self.assertEqual(len(s.documents("A",True)),4)
        self.assertFalse(self.db.exists())
    def test_corrupted_backup_refused(self):
        m=self.create()
        with self.backup.open("r+b") as f:f.seek(100);f.write(b"CORRUPTION")
        dest=self.root/"restore.db"
        with self.assertRaises(ValueError):restore_backup(self.backup,dest,"A",m["sha256"])
        self.assertFalse(dest.exists())
    def test_never_overwrite(self):
        m=self.create();h=file_hash(self.db)
        with self.assertRaises(FileExistsError):restore_backup(self.backup,self.db,"A",m["sha256"])
        with self.assertRaises(FileExistsError):self.create()
        self.assertEqual(file_hash(self.db),h)
    def test_missing_source_and_wrong_scope(self):
        with self.assertRaises(ValueError):create_backup(self.root/"missing",self.backup,"A")
        with self.assertRaises(ValueError):create_backup(self.db,self.backup,"B")
        self.assertFalse(self.backup.exists())
        self.assertFalse((self.root/"missing").exists())
    def test_uncommitted_wal_not_in_snapshot(self):
        with Store(self.db) as s:
            s.db.execute("PRAGMA journal_mode=WAL")
            s.approve("A",True,invoice("I3","1","9"),b"WAL committed","a","b","Synthetic committed evidence")
            s.db.execute("BEGIN IMMEDIATE")
            s._approve_in_tx("A",True,invoice("I4","1","9"),b"WAL pending","a","b","Synthetic pending evidence")
            m=self.create()
            s.db.rollback()
        self.assertEqual(m["active_documents"],4)
        self.assertEqual(verify_backup(self.backup,"A",m["sha256"])["active_documents"],4)
    def test_tampered_original_or_template_rejected(self):
        with Store(self.db) as s:
            s.db.execute("UPDATE procurement_templates SET body='{}'");s.db.commit()
        with self.assertRaises((ValueError,KeyError)):self.create()
        self.assertFalse(self.backup.exists())
    def test_deleted_approval_queue_rejected(self):
        with Store(self.db) as s:
            s.db.execute("DELETE FROM procurement_queue WHERE status='APPROVED'");s.db.commit()
        with self.assertRaises(ValueError):self.create()
    def test_mixed_tenant_rejected(self):
        with Store(self.db) as s:s.approve("B",True,order(),b"other tenant","a","b","Synthetic other tenant")
        with self.assertRaises(ValueError):self.create()
    def test_real_class_rejected(self):
        with Store(self.db) as s:s.approve("A",False,order(),b"real class","a","b","Synthetic test marked real")
        with self.assertRaises(ValueError):self.create()
    def test_unexpected_schema_rejected(self):
        with sqlite3.connect(self.db) as c:c.execute("CREATE TABLE unrelated(secret TEXT)")
        with self.assertRaises(ValueError):self.create()
    def test_restore_sidecar_refused(self):
        m=self.create();dest=self.root/"new.sqlite3"
        Path(str(dest)+"-wal").write_bytes(b"old")
        with self.assertRaises(FileExistsError):restore_backup(self.backup,dest,"A",m["sha256"])
        self.assertFalse(dest.exists())
    def test_backup_sidecar_refused(self):
        m=self.create();dest=self.root/"new.sqlite3"
        Path(str(self.backup)+"-wal").write_bytes(b"unexpected")
        with self.assertRaises(ValueError):restore_backup(self.backup,dest,"A",m["sha256"])
        self.assertFalse(dest.exists())
    def test_deleted_revision_queue_rejected(self):
        with Store(self.db) as s:
            s.db.execute("DELETE FROM procurement_revision_requests");s.db.commit()
        with self.assertRaises(ValueError):self.create()
    def test_original_tampering_rejected_even_with_new_checksum(self):
        m=self.create()
        with sqlite3.connect(self.backup) as c:
            c.execute("UPDATE procurement_docs SET original=? WHERE kind='invoice'",(b"tamper",))
        with self.assertRaises(ValueError):verify_backup(self.backup,"A",file_hash(self.backup))
    def test_wrong_expected_hash_and_tenant(self):
        m=self.create()
        with self.assertRaises(ValueError):verify_backup(self.backup,"A","a"*64)
        with self.assertRaises(ValueError):verify_backup(self.backup,"B",m["sha256"])
if __name__=="__main__":unittest.main()

import base64
import os
import re
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch
from fastapi import FastAPI,Request
from fastapi.testclient import TestClient
from procurement_routes import make_router
from procurement import canonical,digest
from test_procurement import order,delivery,invoice
import tenant

ORIGIN="http://localhost"
PASSWORD="Synthetic-password-42!"
class ProcurementHTTP(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.previous=tenant.ROOT;tenant.ROOT=Path(self.temp.name)
        self.a=tenant.create_company("A");self.b=tenant.create_company("B")
        self.ids={}
        for company,login,role in [(self.a,"analyst-a","analyst"),(self.a,"owner-a","owner"),(self.a,"reader-a","reader"),(self.b,"owner-b","owner")]:
            self.ids[login]=tenant.create_user(company,login,PASSWORD,role)
        app=FastAPI()
        def actor(req):return tenant.session(req.cookies.get("session",""))
        async def body(req,limit):
            raw=await req.body()
            if len(raw)>limit:raise ValueError("Too large")
            return raw
        app.include_router(make_router(actor,body,ORIGIN,Path(__file__).parent,threading.BoundedSemaphore(4)))
        self.app=app
    def tearDown(self):
        tenant.ROOT=self.previous;self.temp.cleanup()
    def client(self,name):
        c=TestClient(self.app,base_url=ORIGIN)
        tok=tenant.authenticate(name,PASSWORD,"test-"+name)
        c.cookies.set("session",tok)
        c.headers.update({"origin":ORIGIN,"X-CSRF-Token":tenant.session(tok)["csrf"]})
        return c
    def send(self,c,route,obj):
        return c.post("/procurement/api/"+route,json=obj)
    def submit(self,c,doc):
        raw=canonical(doc).encode()
        r=self.send(c,"submit",{"candidate":doc,"source":base64.b64encode(raw).decode(),"evidence":"Synthetic source reviewed"})
        self.assertEqual(r.status_code,200,r.text);return r.json()["id"],raw
    def test_auth_and_csrf(self):
        c=TestClient(self.app,base_url=ORIGIN)
        self.assertEqual(c.get("/procurement").status_code,401)
        a=self.client("analyst-a")
        self.assertEqual(a.get("/procurement").status_code,200)
        self.assertEqual(a.post("/procurement/api/submit",headers={"X-CSRF-Token":"wrong"},json={}).status_code,403)
        self.assertEqual(a.get("/procurement/ui.js").status_code,200)
    def test_full_review_matching_isolation(self):
        a,b,reader,other=[self.client(n) for n in ("analyst-a","owner-a","reader-a","owner-b")]
        for doc in (order(),delivery("R","90"),invoice("I","100","960")):
            key,raw=self.submit(a,doc)
            review={"id":key,"decision":"APPROVED","evidence":"Verified independent synthetic document"}
            self.assertEqual(a.get("/procurement/api/source/"+key).content,raw)
            self.assertEqual(other.get("/procurement/api/source/"+key).status_code,404)
            self.assertEqual(self.send(a,"review",review).status_code,403)
            self.assertEqual(self.send(reader,"review",review).status_code,403)
            self.assertEqual(self.send(b,"review",review).status_code,200)
            self.assertEqual(self.send(b,"review",review).status_code,403)
        self.assertEqual(other.get("/procurement/api/cases").json(),[])
        self.assertEqual(len(reader.get("/procurement/api/cases").json()),3)
        r=self.send(reader,"report",{"as_of":"2026-01-31","tolerances":{}})
        self.assertEqual(r.status_code,200,r.text)
        self.assertEqual(r.json()["matching"]["potential_exposure_eur"],"150.00")
        self.assertIsNone(r.json()["matching"]["confirmed_loss_eur"])
    def test_owner_cannot_self_approve(self):
        b=self.client("owner-a");key,_=self.submit(b,order())
        self.assertEqual(self.send(b,"review",{"id":key,"decision":"APPROVED","evidence":"Cannot approve own document"}).status_code,403)
    def test_rejection_no_learning(self):
        a,b=self.client("analyst-a"),self.client("owner-a");key,_=self.submit(a,order())
        self.assertEqual(self.send(b,"review",{"id":key,"decision":"REJECTED","evidence":"Synthetic document rejected"}).status_code,200)
        r=self.send(b,"report",{"as_of":"2026-01-31","tolerances":{}})
        self.assertEqual(r.json()["matching"]["lines"],[])
    def test_extract_never_approved(self):
        a=self.client("analyst-a")
        with patch.dict(os.environ,{"BC_PROCUREMENT_LOCAL_MODEL":"","BC_PROCUREMENT_PADDLE_CONFIG":""}):
            r=self.send(a,"extract",{"source":base64.b64encode(b"invoice,amount\nI1,100").decode(),"suffix":".csv"})
        self.assertEqual(r.status_code,200,r.text)
        self.assertEqual(r.json()["status"],"UNAPPROVED")
        self.assertEqual(a.get("/procurement/api/cases").json(),[])

    def test_table_proposal_unapproved_and_source_bound(self):
        a=self.client("analyst-a");raw=b"synthetic table"
        doc=order();line=doc["lines"][0]
        headers=list(line)
        payload={"source":base64.b64encode(raw).decode(),"source_sha256":digest(raw),
          "table":{"page":1,"status":"REVIEW_REQUIRED","cells":[headers,[line[k] for k in headers]]},
          "metadata":{k:v for k,v in doc.items() if k!="lines"},"mapping":{k:k for k in headers}}
        r=self.send(a,"table-propose",payload)
        self.assertEqual(r.status_code,200,r.text)
        self.assertEqual(r.json()["candidate"],doc)
        self.assertEqual(r.json()["cell_evidence_status"],"OPERATOR_SUPPLIED_UNVERIFIED")
        self.assertEqual(a.get("/procurement/api/cases").json(),[])
        payload["source_sha256"]="a"*64
        self.assertEqual(self.send(a,"table-propose",payload).status_code,400)

    def test_revision_requires_independent_review_and_updates_report(self):
        a,b,reader,other=[self.client(n) for n in ("analyst-a","owner-a","reader-a","owner-b")]
        for doc in (order(),delivery("R","50"),invoice("I","50","600")):
            key,_=self.submit(a,doc)
            self.assertEqual(self.send(b,"review",{"id":key,"decision":"APPROVED","evidence":"Independent synthetic original review"}).status_code,200)
        record=next(x for x in a.get("/procurement/api/revisions").json()["documents"] if x["kind"]=="invoice")
        h=record["versions"][0]["source_sha256"]
        self.assertEqual(a.get("/procurement/api/original/"+h).content,canonical(invoice("I","50","600")).encode())
        self.assertEqual(other.get("/procurement/api/original/"+h).status_code,404)
        payload=dict(kind="invoice",supplier="S",doc_id="I",expected_version=record["versions"][-1]["version"],action="CORRECT",document=invoice("I","50","450"),evidence="Verified transcription error")
        self.assertEqual(self.send(reader,"revision-submit",payload).status_code,403)
        self.assertEqual(self.send(other,"revision-submit",payload).status_code,400)
        r=self.send(a,"revision-submit",payload);self.assertEqual(r.status_code,200,r.text)
        review=dict(id=r.json()["id"],decision="APPROVED",evidence="Independent synthetic revision evidence")
        self.assertEqual(self.send(a,"revision-review",review).status_code,403)
        self.assertEqual(self.send(other,"revision-review",review).status_code,400)
        self.assertEqual(self.send(b,"revision-review",review).status_code,200)
        self.assertEqual(self.send(b,"revision-review",review).status_code,403)
        report=self.send(reader,"report",{"as_of":"2026-01-31","tolerances":{}})
        self.assertEqual(report.json()["matching"]["potential_exposure_eur"],"0.00")
        current=a.get("/procurement/api/revisions").json()
        self.assertEqual(current["requests"][0]["status"],"APPROVED")
        self.assertEqual(other.get("/procurement/api/revisions").json(),{"documents":[],"requests":[]})
        self.assertEqual(self.send(a,"revision-submit",payload).status_code,400)
        payload.update(expected_version=next(x for x in current["documents"] if x["kind"]=="invoice")["versions"][-1]["version"],action="REVOKE",document=None,evidence="Synthetic invoice withdrawn")
        r=self.send(a,"revision-submit",payload);self.assertEqual(r.status_code,200,r.text)
        self.assertEqual(self.send(b,"revision-review",dict(id=r.json()["id"],decision="APPROVED",evidence="Independent synthetic revocation")).status_code,200)
        report=self.send(reader,"report",{"as_of":"2026-01-31","tolerances":{}})
        self.assertIsNone(report.json()["history"]["invoice_audit"])
        self.assertEqual(a.get("/procurement/api/original/"+h).content,canonical(invoice("I","50","600")).encode())

if __name__=="__main__":unittest.main()

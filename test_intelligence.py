import unittest,tempfile,base64,io,csv
from pathlib import Path
from unittest.mock import patch
from datetime import timedelta
import tenant,secure_app as s,intelligence as m
from engine import FIELDS
import test_governance as fixtures
PW=fixtures.PW

class Intelligence(unittest.TestCase):
    setUp=fixtures.Governance.setUp
    login=fixtures.Governance.login
    def post(self,kind,p,client=None,status=200):
        r=(client or self.analyst).post('/api/intel-'+kind,json=p);self.assertEqual(r.status_code,status,r.text);return r.json()
    def approve(self,key,decision='APPROVED',client=None,status=200):
        return self.post('review',{'id':key,'decision':decision,'reason':'Verified supporting fixture'},client or self.owner,status)
    def doc(self,invoice,dt,amount,synthetic=True,product='COFFEE',supplier='A',tid=None,mapping=None,approve=True):
        buf=io.StringIO();w=csv.writer(buf);w.writerow([mapping[k] for k in FIELDS] if mapping else FIELDS);w.writerow([supplier,invoice,'1',dt,product,'kg','10',amount,'0','0',amount]);key=self.post('document',{'file':base64.b64encode(buf.getvalue().encode()).decode(),'synthetic':synthetic,'template_id':tid,'evidence':'Synthetic document review fixture'})['id']
        if approve:self.approve(key)
        return key
    def pair(self,synthetic=True):return self.doc('B','2026-01-01','120',synthetic),self.doc('A','2026-02-01','90',synthetic)
    def payload(self,b,a,cost='10'):return {'baseline':{'document':b,'row':1},'actual':{'document':a,'row':1},'implementation_cost_eur':cost,'evidence':'Comparable quality and quantity confirmed in fixture'}
    def summary(self):return self.owner.get('/api/intelligence').json()
    def test_roi(self):
        b,a=self.pair();k=self.post('roi',self.payload(b,a))['id'];self.assertEqual(self.summary()['roi']['synthetic']['count'],0);self.approve(k);g=self.summary()['roi']['synthetic'];self.assertEqual((g['gross'],g['net'],g['roi_pct']),('30.00','20.00','200.00'));self.assertEqual(self.summary()['roi']['real']['count'],0)
    def test_duplicate(self):
        b,a=self.pair();k=self.post('roi',self.payload(b,a))['id'];self.approve(k);k2=self.post('roi',self.payload(b,a,'11'))['id'];self.approve(k2,status=400)
    def test_unapproved(self):
        b=self.doc('B','2026-01-01','120',approve=False);a=self.doc('A','2026-02-01','90');self.post('roi',self.payload(b,a),status=400)
    def test_revoke(self):
        b,a=self.pair();k=self.post('roi',self.payload(b,a))['id'];self.approve(k);self.approve(a,'REVOKED');g=self.summary();self.assertEqual(g['roi']['synthetic']['count'],0);self.assertIn(k,g['invalidated_roi'])
    def test_template(self):
        mapping={k:'custom_'+k for k in FIELDS};t=self.post('template',{'mapping':mapping,'supplier':'A','delimiter':',','spanish':False,'evidence':'Reviewed mapping of headers'})['id'];self.approve(t);d=self.doc('X','2026-01-01','120',tid=t,mapping=mapping);r=self.owner.get('/api/intel-preview?id='+d);self.assertEqual(r.status_code,200);self.assertEqual(r.json()['rows'][0]['total'],'120')
    def test_template_not_approved(self):
        mapping={k:'custom_'+k for k in FIELDS};t=self.post('template',{'mapping':mapping,'supplier':'A','delimiter':',','spanish':False,'evidence':'Reviewed mapping of headers'})['id'];self.post('document',{'file':base64.b64encode(b'irrelevant').decode(),'synthetic':True,'template_id':t,'evidence':'Reviewed mapping of headers'},status=400)
    def test_tenant_and_reader(self):
        b,a=self.pair();self.assertEqual(self.other.get('/api/intel-preview?id='+b).status_code,409);self.post('roi',self.payload(b,a),client=self.reader,status=403);self.post('roi',self.payload(b,a),client=self.other,status=400)
    def test_self_approval(self):
        t=self.post('policy',{'review_hours':24,'template_days':30,'max_baseline_days':90},client=self.owner)['id'];self.approve(t,status=400)
    def test_policy_version(self):
        b,a=self.pair();k=self.post('roi',self.payload(b,a))['id'];tenant.create_user(self.a,'owner-two',PW,'owner');other=self.login('owner-two');t=self.post('policy',{'review_hours':24,'template_days':30,'max_baseline_days':90},client=self.owner)['id'];self.approve(t,client=other);self.assertEqual(self.summary()['policy']['version'],2);self.approve(k,status=400);k2=self.post('roi',self.payload(b,a))['id'];self.assertNotEqual(k,k2);self.approve(k2)
    def test_expiry(self):
        b,a=self.pair();k=self.post('roi',self.payload(b,a))['id'];future=m.clock()+timedelta(hours=73)
        with patch.object(m,'clock',return_value=future):self.approve(k,status=400)
    def test_mixed(self):
        b=self.doc('B','2026-01-01','120',True);a=self.doc('A','2026-02-01','90',False);self.post('roi',self.payload(b,a),status=400)
    def test_wrong_product(self):
        b=self.doc('B','2026-01-01','120');a=self.doc('A','2026-02-01','90',product='TEA');self.post('roi',self.payload(b,a),status=400)
    def test_tamper(self):
        self.pair();with_db=tenant.company_db(self.a)
        with with_db as c:c.execute("UPDATE intel_events SET body='{}' WHERE seq=1")
        self.assertEqual(self.owner.get('/api/intelligence').status_code,409)
    def test_source_tamper(self):
        b,a=self.pair();k=self.post('roi',self.payload(b,a))['id'];self.approve(k)
        with tenant.company_db(self.a) as c:c.execute("UPDATE intel_sources SET raw=x'00'")
        self.assertEqual(self.summary()['roi']['synthetic']['count'],0)
    def test_deleted_tail(self):
        self.pair()
        with tenant.company_db(self.a) as c:c.execute('DELETE FROM intel_events WHERE seq=(SELECT max(seq) FROM intel_events)')
        self.assertEqual(self.owner.get('/api/intelligence').status_code,409)
    def test_document_formats(self):
        import openpyxl
        from reportlab.pdfgen import canvas
        values=['A','DOC-1','1','2026-01-01','COFFEE','kg','10','120','0','0','120'];book=openpyxl.Workbook();book.active.append(FIELDS);book.active.append(values);buf=io.BytesIO();book.save(buf)
        pdf=io.BytesIO();can=canvas.Canvas(pdf,pagesize=(1800,500));can.setFont('Helvetica',8);can.drawString(10,450,'|'.join(FIELDS));can.drawString(10,420,'|'.join(values));can.save()
        for raw in [buf.getvalue(),pdf.getvalue()]:
            k=self.post('document',{'file':base64.b64encode(raw).decode(),'synthetic':True,'evidence':'Checked source and normalized fields'})['id'];self.approve(k);r=self.owner.get('/api/intel-preview?id='+k);self.assertEqual(r.status_code,200,r.text);self.assertEqual(r.json()['rows'][0]['total'],'120')
    def test_zero_cost(self):
        b,a=self.pair();k=self.post('roi',self.payload(b,a,'0'))['id'];self.approve(k);self.assertIsNone(self.summary()['roi']['synthetic']['roi_pct'])
    def test_document_duplicate_rejected(self):
        buf=io.StringIO();w=csv.writer(buf);w.writerow(FIELDS);row=['A','D','1','2026-01-01','COFFEE','kg','10','120','0','0','120'];w.writerow(row);w.writerow(row);self.post('document',{'file':base64.b64encode(buf.getvalue().encode()).decode(),'synthetic':True,'evidence':'Duplicate synthetic invoice line'},status=400)
if __name__=='__main__':unittest.main()

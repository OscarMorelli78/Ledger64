import unittest,io,csv,random,hashlib,time
from fractions import Fraction
from pathlib import Path
from openpyxl import Workbook
from ingest import audit_document,InputError
from engine import FIELDS
from test_engine import data,row
import test_engine
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import landscape,A3
BASE=Path(__file__).parent
RAW=(BASE/'demo.csv').read_bytes()
def workbook(rows):
    w=Workbook();s=w.active
    for r in rows:s.append(r)
    b=io.BytesIO();w.save(b);return b.getvalue()
def pdfdoc(lines):
    b=io.BytesIO();c=canvas.Canvas(b,pagesize=landscape(A3));c.setFont('Courier',8)
    for i,line in enumerate(lines):c.drawString(20,800-i*12,line)
    c.save();return b.getvalue()
class ImportTests(unittest.TestCase):
    def test_excel(self):
        b=workbook(list(csv.reader(io.StringIO(RAW.decode()))));r=audit_document(b,True);self.assertEqual(r['potential_saving_eur'],'30.00');self.assertEqual(r['source_format'],'xlsx');self.assertEqual(r['input_sha256'],hashlib.sha256(b).hexdigest())
    def test_pdf(self):
        b=pdfdoc([x.replace(',','|') for x in RAW.decode().splitlines()]);r=audit_document(b,True);self.assertEqual(r['potential_saving_eur'],'30.00');self.assertEqual(r['source_format'],'pdf')
    def test_pdf_unknown(self):
        with self.assertRaises(InputError):audit_document(pdfdoc(['Factura 123 total 20 EUR']))
    def test_pdf_empty(self):
        with self.assertRaises(InputError):audit_document(pdfdoc(['']))
    def test_formula(self):
        rr=list(csv.reader(io.StringIO(RAW.decode())));rr[1][7]='=1+1'
        with self.assertRaises(InputError):audit_document(workbook(rr))
    def test_malformed_zip(self):
        with self.assertRaises(InputError):audit_document(b'PK\x03\x04bad')
    def test_malformed_pdf(self):
        with self.assertRaises(InputError):audit_document(b'%PDF-bad')
    def test_csv_hash(self):
        r=audit_document(RAW);self.assertEqual(r['input_sha256'],r['normalized_sha256'])
    def test_independent_oracle_5000(self):
        rng=random.Random(42);rows=[];expected=Fraction(0)
        for i in range(2500):
            q=rng.randint(1,20);cheap=rng.randint(1,100);diff=rng.randint(0,20)
            rows.extend([row(s='A',i=str(i),p=str(i),q=str(q),n=str(q*(cheap+diff)),t=str(q*(cheap+diff))),row(s='B',i=str(i),p=str(i),q=str(q),n=str(q*cheap),t=str(q*cheap))]);expected+=Fraction(q*diff)
        start=time.perf_counter();r=audit_document(data(*rows),True);print(f'\n5000 synthetic rows: {time.perf_counter()-start:.3f}s, expected {expected}, observed {r["potential_saving_eur"]}')
        self.assertEqual(Fraction(r['potential_saving_eur']),expected);self.assertEqual(r['eligible_rows'],5000)
class ImportHTTPTests(test_engine.HTTPTests):
    def test_xlsx_http(self):
        b=workbook(list(csv.reader(io.StringIO(RAW.decode()))));import json
        with self.req('/api/audit',b) as f:self.assertEqual(json.load(f)['report']['source_format'],'xlsx')
    def test_pdf_http(self):
        b=pdfdoc([x.replace(',','|') for x in RAW.decode().splitlines()]);import json
        with self.req('/api/audit',b) as f:self.assertEqual(json.load(f)['report']['potential_saving_eur'],'30.00')

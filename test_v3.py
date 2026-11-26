import unittest,sqlite3,csv,io,json
from pathlib import Path
from test_ingest import workbook,pdfdoc
from test_engine import data,row,HTTPTests
from ingest import audit_document
from engine import InputError,FIELDS
from decisions import approve,record_saving,snapshot
from flexible import invoice_text
RAW=Path(__file__).with_name('demo.csv').read_bytes()
ALIAS={'supplier':'A','sku':'SKU1','canonical':'COMMON','evidence':'Ficha técnica coincidente'}
SAVE={'product':'COMMON','unit':'kg','baseline_reference':'A001','purchase_reference':'B002','baseline_price':'12','actual_price':'9','quantity':'10'}
class V3Tests(unittest.TestCase):
 def setUp(self):self.c=sqlite3.connect(':memory:')
 def tearDown(self):self.c.close()
 def test_excel_reordered(self):
  rr=list(csv.reader(io.StringIO(RAW.decode())));hdr=['Proveedor','Factura','Línea','Fecha','Producto','Unidad','Cantidad','Neto EUR','Portes EUR','Descuento EUR','Total sin IVA'];rows=[hdr]+rr[1:];rows=[list(reversed(x)) for x in rows];self.assertEqual(audit_document(workbook(rows))['potential_saving_eur'],'30.00')
 def test_invoice_spanish(self):
  s=['Factura comercial','Proveedor: A','Factura: 123','Fecha: 10/11/2026','Moneda: EUR','Total sin IVA: 20,00','Línea|Producto|Unidad|Cantidad|Neto EUR|Portes EUR|Descuento EUR|Total sin IVA','1|CAFE|kg|2|20,00|0|0|20,00'];self.assertEqual(audit_document(pdfdoc(s))['rows'],1)
 def test_invoice_english(self):
  s=['Commercial invoice','Supplier: A','Invoice: 123','Date: 2026-11-10','Currency: EUR','Total excl VAT: 20','line|product|unit|quantity|net_eur|shipping_eur|discount_eur|reported_total_eur','1|CAFE|kg|2|20|0|0|20'];self.assertEqual(audit_document(pdfdoc(s))['rows'],1)
 def test_total_mismatch(self):
  with self.assertRaises(InputError):invoice_text('Proveedor: A\nFactura: 1\nFecha: 10/11/2026\nMoneda: EUR\nTotal sin IVA: 21\nline|product|unit|quantity|net_eur|shipping_eur|discount_eur|reported_total_eur\n1|CAFE|kg|2|20|0|0|20')
 def test_alias(self):
  approve(self.c,ALIAS);raw=data(row(s='A',p='SKU1',q='10',n='120',t='120'),row(s='B',p='COMMON',q='10',n='90',t='90'));self.assertEqual(audit_document(raw)['potential_saving_eur'],'0.00');r=audit_document(raw,connection=self.c);self.assertEqual(r['potential_saving_eur'],'30.00');self.assertEqual(len(r['approved_mappings']),1)
 def test_demo_unaffected(self):
  approve(self.c,ALIAS);self.assertEqual(audit_document(RAW,True,self.c)['approved_mappings'],[])
 def test_conflict(self):
  approve(self.c,ALIAS)
  with self.assertRaises(InputError):approve(self.c,dict(ALIAS,canonical='OTHER'))
 def test_save(self):
  self.assertEqual(record_saving(self.c,SAVE)['declared_saving_eur'],'30.00');record_saving(self.c,SAVE);self.assertEqual(len(snapshot(self.c)['savings']),1)
 def test_save_conflict(self):
  record_saving(self.c,SAVE)
  with self.assertRaises(InputError):record_saving(self.c,dict(SAVE,quantity='11'))
 def test_save_negative(self):
  with self.assertRaises(InputError):record_saving(self.c,dict(SAVE,actual_price='13'))
 def test_monthly(self):
  r=audit_document(RAW);self.assertEqual(r['monthly_costs']['excluded_rows'],2);self.assertEqual(sum(float(x['eligible_cost_eur']) for x in r['monthly_costs']['months']),sum(float(x) for x in ['100','120','90','80']))

class AdditionalTests(unittest.TestCase):
 def test_batch(self):
  import base64
  from ingest import audit_batch
  def f(n,b):return {'name':n,'data':base64.b64encode(b).decode()}
  r=audit_batch({'files':[f('a.csv',data(row(s='A',q='10',n='120',t='120'))),f('b.csv',data(row(s='B',q='10',n='90',t='90')))]});self.assertEqual(r['potential_saving_eur'],'30.00');self.assertEqual(len(r['source_documents']),2);self.assertEqual(r['source_documents'][1]['first_normalized_row'],3)
 def test_batch_atomic(self):
  import base64
  from ingest import audit_batch
  with self.assertRaises(InputError):audit_batch({'files':[{'name':'a.csv','data':base64.b64encode(RAW).decode()},{'name':'bad.csv','data':'%%%'}]})
 def test_pdf_report(self):
  from reporting import report_pdf
  from pypdf import PdfReader
  r=audit_document(RAW,True);p=PdfReader(io.BytesIO(report_pdf(r)));t='\n'.join(x.extract_text() for x in p.pages);self.assertIn('30.00',t);self.assertIn('SINTÉTICOS',t);self.assertIn(r['input_sha256'],t.replace('\n',''))
 def test_ocr_reject_nonpdf(self):
  from ocr_review import transcribe
  with self.assertRaises(InputError):transcribe(RAW)
 def test_scan_draft(self):
  import shutil
  if not shutil.which('tesseract'):self.skipTest('Tesseract no instalado')
  from PIL import Image,ImageDraw,ImageFont
  from ocr_review import transcribe
  raw=Path(__file__).with_name('demo_scan.pdf').read_bytes();r=transcribe(raw);self.assertEqual(r['status'],'BORRADOR_NO_VERIFICADO');self.assertIn('12345',r['pages'][0]['text']);self.assertIn('120.00',r['pages'][0]['text']);self.assertNotIn('potential_saving_eur',r)

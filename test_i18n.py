"""Localization checks; no customer data or remote requests."""
import ast,csv,io,json,re,subprocess,tempfile,unittest,zipfile
from pathlib import Path
from types import SimpleNamespace
from i18n import CATALOG,LANGS,locale,localize_html,localize_js,tr,diagnostic
from ingest import audit_document
from reporting import report_pdf
from pypdf import PdfReader
ROOT=Path(__file__).parent
class LocalizationTests(unittest.TestCase):
 def test_catalog(self):
  with (ROOT/'locales/strings.tsv').open(encoding='utf-8') as f:rows=list(csv.reader(f,delimiter='\t'))
  self.assertEqual(len(LANGS),9);self.assertEqual(len({r[0] for r in rows[1:]}),len(rows)-1)
  self.assertTrue(all(len(r)==9 and all(r) for r in rows))
  self.assertEqual(locale(SimpleNamespace(cookies={})), 'en');self.assertEqual(locale(SimpleNamespace(cookies={'ledger64_lang':'<script>'})), 'en')
 def test_all_static_diagnostics(self):
  keys=set()
  for name in ('engine','ingest','flexible','independent','governance','intelligence','ocr_review','decisions','secure_app','tenant'):
   for n in ast.walk(ast.parse((ROOT/(name+'.py')).read_text(encoding='utf-8'))):
    if isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id in ('InputError','fail','err'):
     ix=1 if n.func.id=='err' else 0
     if len(n.args)>ix and isinstance(n.args[ix],ast.Constant) and isinstance(n.args[ix].value,str):keys.add(n.args[ix].value)
  self.assertGreaterEqual(len(keys),120)
  for l in LANGS:self.assertFalse(keys-CATALOG[l].keys())
  self.assertEqual(diagnostic('Fila 9: Unidad no admitida','en'),'Row 9: Unsupported unit')
  self.assertIn('unexpected third-party text',diagnostic('unexpected third-party text','hi'))
 def test_html_and_js(self):
  for l in LANGS:
   for name in ('login.html','secure_index.html','index.html'):
    h=localize_html((ROOT/name).read_text(encoding='utf-8'),l);self.assertIn('lang="'+l+'"',h);self.assertIn('value="'+l+'" selected',h);self.assertEqual(h.count('id="ledger_language"'),1)
   for name in ('ui.js','account.js','governance.js','intelligence.js','login.js'):
    s=localize_js((ROOT/name).read_text(encoding='utf-8'),l);r=subprocess.run(['node','--check'],input=s,text=True,capture_output=True);self.assertEqual(r.returncode,0,(l,name,r.stderr))
 def test_pdf(self):
  report=audit_document((ROOT/'demo.csv').read_bytes(),True);before=json.dumps(report,sort_keys=True)
  for l in LANGS:
   with self.subTest(locale=l):
    data=report_pdf(report,l);reader=PdfReader(io.BytesIO(data));self.assertGreaterEqual(len(reader.pages),1);self.assertEqual(reader.metadata.title,tr('Informe ejecutivo de compras',l));self.assertIn('30.00',' '.join(p.extract_text() for p in reader.pages));self.assertEqual(json.dumps(report,sort_keys=True),before)
 def test_docs_marketing(self):
  for l in LANGS:
   self.assertGreater((ROOT/f'README.{l}.md').stat().st_size,1500);m=(ROOT/'docs/manual'/f'{l}.md').read_text(encoding='utf-8');self.assertEqual(len(re.findall(r'^## \d+\.',m,re.M)),13);self.assertIn('python admin.py',m)
   p=ROOT/'site'/('index.html' if l=='en' else l+'.html');s=p.read_text(encoding='utf-8');self.assertIn('lang="'+l+'"',s);self.assertIn('noindex,follow',s)
  with (ROOT/'marketing/keywords-multilingual.csv').open(encoding='utf-8') as f:rows=list(csv.DictReader(f))
  self.assertEqual(len(rows),135);self.assertEqual(set(r['language'] for r in rows),set(LANGS))
  with (ROOT/'marketing/search-ads.csv').open(encoding='utf-8') as f:self.assertTrue(all(r['status']=='PAUSED' for r in csv.DictReader(f)))
if __name__=='__main__':unittest.main()

"""Synthetic OCR/PDF regression against the exact runtime image."""
from pathlib import Path
import io, subprocess, re
from ocr_review import transcribe
from ingest import audit_document
from reporting import report_pdf
from i18n import LANGS, tr
from pypdf import PdfReader

for family in ("Noto Sans", "Noto Sans CJK SC", "Noto Sans CJK JP", "Noto Sans Devanagari"):
    actual = subprocess.check_output(["fc-match", "-f", "%{family}", family], text=True)
    assert family in actual, (family, actual)
    print(f"Font {family}: {actual}", flush=True)
raw = Path("demo_scan.pdf").read_bytes()
for language in ("eng", "spa"):
    r = transcribe(raw, language)
    assert r["status"] == "BORRADOR_NO_VERIFICADO", r["status"]
    assert "12345" in r["pages"][0]["text"] and "120.00" in r["pages"][0]["text"], (language, r["pages"][0]["text"])
    print(f"OCR {language}: PASS", flush=True)
report = audit_document(Path("demo.csv").read_bytes(), True)
for lang in LANGS:
    pdf = PdfReader(io.BytesIO(report_pdf(report, lang)))
    assert pdf.pages, lang
    assert pdf.metadata.title == tr("Informe ejecutivo de compras", lang), (lang, pdf.metadata.title)
    text = " ".join(page.extract_text() for page in pdf.pages)
    assert "30.00" in text, (lang, text[:1200])
    if lang in ("zh-CN", "ja"):
        assert re.search(r"[\u3400-\u9fff]", text), (lang, "CJK glyphs missing")
    if lang == "hi":
        assert re.search(r"[\u0900-\u097f]", text), (lang, "Devanagari glyphs missing")
    print(f"PDF {lang}: PASS", flush=True)
print("Runtime OCR and PDF 9/9 passed")

import shutil
import tempfile
import unittest
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
from procurement_ingest import extract

class LocalOCR(unittest.TestCase):
    @unittest.skipUnless(shutil.which("tesseract"),"Local OCR not installed")
    def test_image_and_scanned_pdf(self):
        with tempfile.TemporaryDirectory() as root:
            im=Image.new("RGB",(1200,400),"white")
            font=ImageFont.truetype("DejaVuSans.ttf",64)
            d=ImageDraw.Draw(im);d.text((40,60),"INVOICE 12345",font=font,fill="black")
            d.text((40,160),"TOTAL 150 EUR",font=font,fill="black")
            for ext in ("png","jpg"):
                p=Path(root)/("synthetic."+ext);im.save(p)
                r=extract(p);self.assertEqual(r["status"],"UNAPPROVED")
                self.assertEqual(r["method"],"Tesseract")
                self.assertIn("12345",r["pages"][0]["text"])
                self.assertIn("150",r["pages"][0]["text"])
                self.assertIsNotNone(r["minimum_ocr_score"])
            r=extract(Path("demo_scan.pdf"));self.assertEqual(r["method"],"Tesseract")
            self.assertEqual(r["status"],"UNAPPROVED")

if __name__=="__main__":unittest.main()

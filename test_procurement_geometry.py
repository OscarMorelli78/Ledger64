import io
import unittest
from PIL import Image,ImageDraw
from procurement_geometry import deskew,grid_geometry,extract_grid,reread_cells,prepare_cell,read_cell
from procurement_table import canonical_columns

def image(angle=0,broken=False):
    im=Image.new("L",(800,500),255);d=ImageDraw.Draw(im)
    for x in (40,280,520,760):
        if broken and x==280:d.line((x,150,x,220),fill=0,width=4)
        else:d.line((x,150,x,390),fill=0,width=4)
    for y in (150,230,310,390):d.line((40,y,760,y),fill=0,width=4)
    return im.rotate(angle,expand=True,fillcolor=255) if angle else im

class GeometryTests(unittest.TestCase):
    def test_deskew(self):
        for angle in (-3,2,0):
            corrected,info=deskew(image(angle))
            self.assertLessEqual(abs(info["rotation_deg"]+angle),.3)
            xs,ys=grid_geometry(corrected)
            self.assertEqual((len(xs),len(ys)),(4,4))
    def test_broken_grid(self):
        with self.assertRaises(ValueError):grid_geometry(image(broken=True))
    def test_blank_abstains(self):
        b=io.BytesIO();Image.new("RGB",(500,500),"white").save(b,format="PNG")
        self.assertIsNone(extract_grid(b.getvalue(),reader=lambda _:("bad",1))["cells"])
    def test_positions(self):
        b=io.BytesIO();image().save(b,format="PNG")
        count=iter(range(9))
        r=extract_grid(b.getvalue(),reader=lambda _:(str(next(count)),.99))
        self.assertEqual(r["cells"],[["0","1","2"],["3","4","5"],["6","7","8"]])
        self.assertEqual(r["status"],"REVIEW_REQUIRED")
        self.assertLess(r["cell_geometry"][0][0]["rectified_bbox"][0],r["cell_geometry"][0][1]["rectified_bbox"][0])
    def test_reread_rejects_source_mismatch(self):
        with self.assertRaises(ValueError):reread_cells(b"wrong",{"source_sha256":"a"*64},[[0,0]])
    def test_visual_variant_is_bounded(self):
        im=Image.new("L",(100,60),255)
        ImageDraw.Draw(im).rectangle((20,20,40,30),fill=0)
        out=prepare_cell(im,scale=3,tight=True)
        self.assertEqual(out.size,(21*3+40,11*3+40))
        self.assertEqual(im.size,(100,60))
        with self.assertRaises(ValueError):prepare_cell(im,scale=10)
    def test_dictionary_disabled_without_character_forcing(self):
        from unittest.mock import patch
        from pathlib import Path
        import tempfile
        with tempfile.TemporaryDirectory() as root:
            with patch("procurement_geometry.subprocess.run") as run:
                run.return_value.returncode=0
                run.return_value.stdout=b"level\tconf\ttext\n5\t85\tX1\n"
                self.assertEqual(read_cell("tesseract",Image.new("L",(80,40),255),Path(root)/"cell.png",no_dictionary=True),("X1",.85))
                cmd=run.call_args.args[0]
                self.assertIn("load_system_dawg=0",cmd)
                self.assertIn("load_freq_dawg=0",cmd)
                self.assertFalse(any("whitelist" in x for x in cmd))
    def test_permutation(self):
        rows=[["TOTAL","SKU","QTY"],["20","X","2"]]
        r=canonical_columns(rows,["SKU","QTY","TOTAL"])
        self.assertEqual(r["cells"],[["SKU","QTY","TOTAL"],["X","2","20"]])
        self.assertEqual(r["source_columns"],[2,3,1])
    def test_ambiguous_headers(self):
        for rows in ([["SKU","SKU"],["A","B"]],[["SKU","OTHER"],["A","B"]],[["SKU","QTY"],["A"]]):
            with self.assertRaises(ValueError):canonical_columns(rows,["SKU","QTY"])

if __name__=="__main__":unittest.main()

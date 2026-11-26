import io
import unittest
from PIL import Image,ImageDraw
from procurement_geometry import deskew,grid_geometry,extract_grid
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
    def test_permutation(self):
        rows=[["TOTAL","SKU","QTY"],["20","X","2"]]
        r=canonical_columns(rows,["SKU","QTY","TOTAL"])
        self.assertEqual(r["cells"],[["SKU","QTY","TOTAL"],["X","2","20"]])
        self.assertEqual(r["source_columns"],[2,3,1])
    def test_ambiguous_headers(self):
        for rows in ([["SKU","SKU"],["A","B"]],[["SKU","OTHER"],["A","B"]],[["SKU","QTY"],["A"]]):
            with self.assertRaises(ValueError):canonical_columns(rows,["SKU","QTY"])

if __name__=="__main__":unittest.main()

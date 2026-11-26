"""Actual browser and HTTP smoke test of opt-in document review (synthetic only)."""
import json,os,socket,subprocess,sys,tempfile,time,re
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
from playwright.sync_api import sync_playwright,expect
ROOT=Path(__file__).resolve().parents[1]
def fixture(path):
    im=Image.new("RGB",(1500,1000),"white");d=ImageDraw.Draw(im);font=ImageFont.truetype("DejaVuSansMono.ttf",32)
    rows=[["Line","SKU","Unit","Qty","Price","Discount"],["1","P123","ud","20","12.50","5"]]
    xs=[50+i*230 for i in range(7)];ys=[300,400,500]
    for x in xs:d.line((x,ys[0],x,ys[-1]),fill="black",width=4)
    for y in ys:d.line((xs[0],y,xs[-1],y),fill="black",width=4)
    for i,row in enumerate(rows):
        for j,v in enumerate(row):d.text((xs[j]+15,ys[i]+22),v,font=font,fill="black")
    im.save(path)

def main():
    with tempfile.TemporaryDirectory() as root:
        path=Path(root)/"synthetic.png";fixture(path)
        with socket.socket() as s:s.bind(("127.0.0.1",0));port=s.getsockname()[1]
        url=f"http://127.0.0.1:{port}"
        env=dict(os.environ,BC_ROOT=str(Path(root)/"data"),BC_TLS="0",BC_ORIGIN=url,BC_HOSTS="127.0.0.1",BC_PROCUREMENT_PILOT="1",BC_PROCUREMENT_LOCAL_MODEL="",BC_PROCUREMENT_PADDLE_CONFIG="")
        subprocess.run([sys.executable,"-c","from tenant import create_company,create_user; c=create_company('Synthetic'); create_user(c,'analyst-a','Synthetic-password-42!','analyst'); create_user(c,'owner-a','Synthetic-password-42!','owner')"],cwd=ROOT,env=env,check=True)
        server=subprocess.Popen([sys.executable,"-m","uvicorn","secure_app:app","--host","127.0.0.1","--port",str(port),"--no-access-log"],cwd=ROOT,env=env)
        try:
            import httpx
            for _ in range(100):
                try:
                    if httpx.get(url+"/login",timeout=1,trust_env=False).status_code==200:break
                except httpx.HTTPError:pass
                time.sleep(.1)
            else:raise RuntimeError("Server unavailable")
            with sync_playwright() as pw:
                browser=pw.chromium.launch(headless=True)
                def login(name):
                    ctx=browser.new_context()
                    r=ctx.request.post(url+"/login",headers={"Origin":url},data={"login":name,"password":"Synthetic-password-42!"})
                    assert r.status==200,r.text()
                    page=ctx.new_page();page.goto(url+"/procurement");return ctx,page
                analyst,page=login("analyst-a")
                errors=[];page.on("pageerror",lambda e:errors.append(str(e)))
                page.locator("#source").set_input_files(str(path));page.locator("#strategy").select_option("grid")
                page.locator("#extract").click()
                page.get_by_role("button",name="Build unapproved proposal").wait_for(timeout=60_000)
                # Independent manual review may correct any OCR transcription.
                values=[["Line","SKU","Unit","Qty","Price","Discount"],["1","P123","ud","20","12.75","5"]]
                for i,row in enumerate(values,1):
                    for j,v in enumerate(row,1):page.get_by_label(f"Row {i} column {j}",exact=True).fill(v)
                for label,v in [("Kind (order / receipt / invoice)","order"),("Document ID","O1"),("Supplier","Synthetic"),("Date YYYY-MM-DD","2026-01-01"),("Currency EUR","EUR")]:
                    page.get_by_label(label,exact=True).fill(v)
                for i,field in enumerate(("id","sku","unit","quantity","unit_price","discount_pct")):
                    page.get_by_label("Column for "+field,exact=True).select_option(str(i))
                page.get_by_role("button",name="Build unapproved proposal").click()
                expect(page.locator("#candidate")).to_have_value(re.compile(r"12\.75"))
                candidate=json.loads(page.locator("#candidate").input_value())
                assert candidate["lines"][0]["unit_price"]=="12.75"
                page.get_by_label("Row 2 column 5",exact=True).fill("12.50")
                assert not page.locator("#candidate").input_value()
                page.get_by_role("button",name="Build unapproved proposal").click()
                expect(page.locator("#candidate")).to_have_value(re.compile(r"12\.50"))
                assert json.loads(page.locator("#candidate").input_value())["lines"][0]["unit_price"]=="12.50"
                page.locator("#evidence").fill("Synthetic operator reviewed source")
                page.locator("#submit").click()
                page.get_by_text("order · O1 · PENDING",exact=True).wait_for()
                owner,review=login("owner-a")
                review.get_by_text("order · O1 · PENDING",exact=True).wait_for()
                review.get_by_placeholder("Independent verification evidence").fill("Synthetic independent owner review")
                review.get_by_role("button",name="APPROVED",exact=True).click()
                review.get_by_text("order · O1 · APPROVED",exact=True).wait_for()
                assert not errors,errors
                owner.close();analyst.close();browser.close()
            print("PASS: browser grid extraction, visual mapping, edit invalidation, submission and independent approval")
        finally:server.terminate();server.wait(timeout=10)
if __name__=="__main__":main()

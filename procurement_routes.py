"""Feature-flagged local pilot. Uses existing authenticated session and CSRF."""
import base64
import binascii
import hmac
import json
import os
import re
import sqlite3
import subprocess
import tempfile
from pathlib import Path
from fastapi import APIRouter,Request
from fastapi.responses import HTMLResponse,JSONResponse,Response
from starlette.concurrency import run_in_threadpool
from procurement import Store,reconcile,MAX_DOC,digest
from procurement_history import historical_report
from procurement_ingest import extract,propose
from procurement_consensus import compare_image
from procurement_references import reference_check
from procurement_table import table_drafts,propose_from_cells
from procurement_geometry import extract_grid,reread_cells
import procurement_queue as queue
import tenant

def make_router(actor,body,origin,base,slots):
    router=APIRouter()
    def error(code,message):return JSONResponse({"error":message},status_code=code)
    def db(u):
        if not re.fullmatch(r"[a-f0-9]{32}",u["company"]):raise PermissionError()
        path=tenant.ROOT/"companies"/u["company"]
        path.mkdir(mode=0o700,parents=True,exist_ok=True)
        return Store(path/"procurement.sqlite3")
    def execute(u,route,p):
        if not isinstance(p,dict):raise ValueError("Expected object")
        if route=="extract":
            raw=base64.b64decode(p["source"],validate=True)
            if not 1<=len(raw)<=MAX_DOC:raise ValueError("Invalid document size")
            suffix=p["suffix"].lower()
            if suffix not in (".pdf",".png",".jpg",".jpeg",".csv",".xlsx",".json"):raise ValueError("Unsupported extension")
            with tempfile.TemporaryDirectory() as root:
                file=Path(root)/("document"+suffix);file.write_bytes(raw)
                strategy=p.get("strategy","standard")
                if strategy=="grid":
                    grid=extract_grid(raw)
                    r={"status":"UNAPPROVED","source_sha256":grid["source_sha256"],"structured_tables":[grid]}
                elif strategy=="consensus":
                    proposal=compare_image(file)
                    r={"status":"UNAPPROVED","proposal":proposal}
                elif strategy=="standard":
                    r=extract(file,paddle_config=os.environ.get("BC_PROCUREMENT_PADDLE_CONFIG") or None)
                    r["structured_tables"]=table_drafts(r.get("tables",[]))
                    model=os.environ.get("BC_PROCUREMENT_LOCAL_MODEL")
                    if model:r["proposal"]=propose(r,model)
                else:raise ValueError("Unknown extraction strategy")
                candidate=r.get("proposal",{}).get("candidate")
                if candidate is not None:
                    with db(u) as store:
                        r["reference_check"]=reference_check(candidate,store.documents(u["company"],True))
                return r
        if route=="reread-cells":
            raw=base64.b64decode(p["source"],validate=True)
            return reread_cells(raw,p["table"],p["positions"])
        if route=="table-propose":
            raw=base64.b64decode(p["source"],validate=True)
            if not 1<=len(raw)<=MAX_DOC or digest(raw)!=p["source_sha256"]:raise ValueError("Source mismatch")
            result=propose_from_cells(p["table"],p["metadata"],p["mapping"],digest(raw))
            result["cell_evidence_status"]="OPERATOR_SUPPLIED_UNVERIFIED"
            with db(u) as store:
                result["reference_check"]=reference_check(result["candidate"],store.documents(u["company"],True))
            return result
        with db(u) as store:
            queue.initialize(store)
            if route=="submit":
                raw=base64.b64decode(p["source"],validate=True)
                checks=reference_check(p["candidate"],store.documents(u["company"],True))
                return {"id":queue.submit(store,u,p["candidate"],raw,p["evidence"]),"reference_check":checks}
            if route=="review":
                return queue.review(store,u,p["id"],p["decision"],p["evidence"])
            if route=="report":
                docs=store.documents(u["company"],True)
                match=reconcile(docs,p["as_of"],p["tolerances"])
                hist=historical_report(store,u["company"],True,p["as_of"],p.get("rise_pct","10"),snapshot=docs)
                hist.pop("matching")
                return {"matching":match,"history":hist,"synthetic":True}
        raise KeyError("Unknown route")
    @router.get("/procurement")
    def page(req:Request):
        u=actor(req)
        if not u:return error(401,"Sign in")
        return HTMLResponse((base/"procurement.html").read_text(encoding="utf-8").replace("__TOKEN__",u["csrf"]))
    @router.get("/procurement/ui.js")
    def script(req:Request):
        if not actor(req):return error(401,"Sign in")
        return Response((base/"procurement_ui.js").read_bytes(),media_type="application/javascript")
    @router.get("/procurement/api/cases")
    def cases(req:Request):
        u=actor(req)
        if not u:return error(401,"Sign in")
        try:
            with db(u) as store:
                queue.initialize(store);return queue.list_cases(store,u)
        except (ValueError,sqlite3.Error):return error(409,"Cannot verify review queue")
    @router.get("/procurement/api/source/{key}")
    def source(req:Request,key:str):
        u=actor(req)
        if not u:return error(401,"Sign in")
        try:
            with db(u) as store:
                queue.initialize(store);row=queue.get(store,u,key)
                return Response(row[3],media_type="application/octet-stream",headers={"Content-Disposition":"attachment; filename=synthetic-source.bin"})
        except KeyError:return error(404,"Unknown proposal")
        except (ValueError,sqlite3.Error):return error(409,"Cannot verify proposal")
    @router.post("/procurement/api/{route}")
    async def write(req:Request,route:str):
        u=await run_in_threadpool(actor,req)
        if not u:return error(401,"Sign in")
        if req.headers.get("origin")!=origin or not hmac.compare_digest(req.headers.get("X-CSRF-Token",""),u["csrf"]):return error(403,"Unauthorized")
        if route not in ("extract","reread-cells","table-propose","submit","review","report"):return error(404,"Unknown route")
        if route!="report" and u["role"]=="reader":return error(403,"Write permission required")
        if route=="review" and u["role"]!="owner":return error(403,"Owner permission required")
        if not slots.acquire(blocking=False):return error(503,"Busy")
        try:
            payload=json.loads(await body(req,6_000_000))
            return await run_in_threadpool(execute,u,route,payload)
        except PermissionError:return error(403,"Independent review required")
        except KeyError:return error(400,"Missing or invalid field")
        except (ValueError,TypeError,binascii.Error):return error(400,"Invalid or incompatible synthetic document")
        except (sqlite3.Error,OSError,RuntimeError,ImportError,subprocess.TimeoutExpired):return error(503,"Local processing unavailable")
        finally:slots.release()
    return router

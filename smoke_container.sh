#!/usr/bin/env bash
set -euo pipefail
image=${1:-almer-ia/business-control:ci}
name=bc-smoke-$$
volume=bc-smoke-data-$$
trap 'docker rm -f "$name" >/dev/null 2>&1 || true; docker volume rm "$volume" >/dev/null 2>&1 || true' EXIT
docker volume create "$volume" >/dev/null
docker run --rm --network none -v "$volume:/data" --entrypoint python "$image" -c 'from tenant import create_company,create_user; c=create_company("Synthetic CI"); create_user(c,"ci-owner","Synthetic-CI-Password-123!","owner")'
docker run -d --name "$name" --read-only --tmpfs /tmp:rw,nosuid,nodev,size=128m --cap-drop ALL --security-opt no-new-privileges --memory 512m --pids-limit 128 -v "$volume:/data" -p 127.0.0.1:18765:8765 -e BC_TLS=0 -e BC_ORIGIN=http://127.0.0.1:18765 -e BC_HOSTS=127.0.0.1 "$image"
python3 - <<'PY'
import urllib.request as u,urllib.error as e,http.cookiejar,json,time
base='http://127.0.0.1:18765'; op=u.build_opener(u.HTTPCookieProcessor(http.cookiejar.CookieJar()))
for i in range(60):
 try:
  assert op.open(base+'/login',timeout=2).status==200;break
 except OSError:time.sleep(1)
else:raise RuntimeError('Startup failed')
try:op.open(base+'/api/me');raise AssertionError('Anonymous access')
except e.HTTPError as x:assert x.code==401
req=u.Request(base+'/login',data=json.dumps({'login':'ci-owner','password':'Synthetic-CI-Password-123!'}).encode(),headers={'Origin':base,'Content-Type':'application/json'})
assert json.load(op.open(req))['ok']
assert json.load(op.open(base+'/api/me'))['role']=='owner'
for p in ['/','/intelligence.js','/api/intelligence','/api/governance']:
 assert op.open(base+p).status==200
 print(p,'OK')
PY
docker exec "$name" python -c 'import os; assert os.getuid()==10001; print("Nonroot OK")'
docker restart "$name" >/dev/null
for i in $(seq 1 30); do if curl -fsS http://127.0.0.1:18765/login >/dev/null; then break; fi; sleep 1; done
docker exec "$name" python -c 'from tenant import auth_db; exec("with auth_db() as c:\n assert c.execute(\"select count(*) from users\").fetchone()[0]==1"); print("Persistence OK")'

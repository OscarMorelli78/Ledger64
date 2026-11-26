#!/usr/bin/env bash
set -euo pipefail
export COMPOSE_PROJECT_NAME=ledger64-release-local
compose=(docker compose -f compose.local.yaml)
trap '"${compose[@]}" down -v >/dev/null 2>&1 || true' EXIT
"${compose[@]}" config --quiet
"${compose[@]}" up --build -d --wait
test "$("${compose[@]}" port app 8765)" = "127.0.0.1:8765"
"${compose[@]}" exec -T app python -c 'from tenant import auth_db; exec("with auth_db() as c:\n assert c.execute(\"select count(*) from users\").fetchone()[0]==0")'
"${compose[@]}" exec -T app python -c 'from tenant import create_company,create_user; c=create_company("Synthetic release CI"); create_user(c,"ci-owner","Synthetic-Release-Password-42!")'
python - <<'PY'
import urllib.request as u,urllib.error as e,http.cookiejar,json
base='http://127.0.0.1:8765';op=u.build_opener(u.HTTPCookieProcessor(http.cookiejar.CookieJar()))
try:op.open(base+'/api/me');raise AssertionError('Anonymous access')
except e.HTTPError as ex:assert ex.code==401
request=u.Request(base+'/login',data=json.dumps({'login':'ci-owner','password':'Synthetic-Release-Password-42!'}).encode(),headers={'Origin':base,'Content-Type':'application/json'})
assert json.load(op.open(request))['ok']
assert json.load(op.open(base+'/api/me'))['role']=='owner'
assert op.open(base+'/').status==200
print('PASS: loopback-only Compose, no default accounts, authenticated local application')
PY
"${compose[@]}" restart app
"${compose[@]}" up -d --wait
"${compose[@]}" exec -T app python -c 'from tenant import auth_db; exec("with auth_db() as c:\n assert c.execute(\"select count(*) from users\").fetchone()[0]==1")'

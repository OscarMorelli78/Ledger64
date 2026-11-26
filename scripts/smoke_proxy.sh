#!/usr/bin/env bash
set -euo pipefail
export BC_DOMAIN=ledger64.example.invalid
project=ledger64-proxy-ci
temp=$(mktemp -d)
# The CI-only override uses a self-signed default certificate; no external ACME requests.
# Exercise the exact production router, middleware, networking and app otherwise.
sed '/certResolver: letsencrypt/d' deploy/traefik.yml > "$temp/dynamic.yml"
chmod 644 "$temp/dynamic.yml"
cat > "$temp/override.yml" <<EOF
services:
  app:
    image: ledger64:ci
  proxy:
    command:
      - --entrypoints.web.address=:8080
      - --entrypoints.websecure.address=:8443
      - --entrypoints.web.http.redirections.entrypoint.to=:443
      - --entrypoints.web.http.redirections.entrypoint.scheme=https
      - --providers.file.filename=/etc/traefik/dynamic.yml
      - --providers.file.watch=false
      - --api=false
      - --global.checknewversion=false
      - --global.sendanonymoususage=false
    environment:
      TRAEFIK_CERTIFICATESRESOLVERS_LETSENCRYPT_ACME_EMAIL: !reset null
    ports: !override ['127.0.0.1:18080:8080','127.0.0.1:18443:8443']
    volumes:
      - $temp/dynamic.yml:/etc/traefik/dynamic.yml:ro
EOF
compose=(docker compose --project-name "$project" -f compose.yaml -f "$temp/override.yml")
cleanup() { "${compose[@]}" down -v --remove-orphans >/dev/null 2>&1 || true; rm -rf "$temp"; }
trap cleanup EXIT
"${compose[@]}" config --quiet
"${compose[@]}" up -d --no-build
url=https://$BC_DOMAIN:18443
curlbase=(curl --noproxy '*' -ksS --resolve "$BC_DOMAIN:18443:127.0.0.1" --max-time 10)
for i in $(seq 1 30); do
    if "${curlbase[@]}" -f "$url/login" >/dev/null 2>&1; then break; fi
    sleep 1
done
"${curlbase[@]}" -f "$url/login" >/dev/null
test "$("${curlbase[@]}" -o /dev/null -w '%{http_code}' "$url/api/me")" = 401
curl --noproxy '*' -sS -D "$temp/headers" -o /dev/null --resolve "$BC_DOMAIN:18080:127.0.0.1" "http://$BC_DOMAIN:18080/login"
grep -Ei '^location: https://' "$temp/headers"
truncate -s 13000001 "$temp/oversize"
test "$("${curlbase[@]}" -o /dev/null -w '%{http_code}' -H 'Content-Type: application/octet-stream' --data-binary @"$temp/oversize" "$url/api/audit")" = 413
test "$("${curlbase[@]}" -o /dev/null -w '%{http_code}' -H 'Host: untrusted.example.invalid' "$url/login")" = 404
echo 'PASS: Compose proxy, HTTPS routing (test certificate), redirect, anonymous access rejection, request limit, host isolation'

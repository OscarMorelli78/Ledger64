# Ledger64 — Documentation (English)

Open-source invoice auditing, purchase cost comparison and financial governance for small businesses. C64-inspired interface; local processing without external AI.

**Release candidate: use synthetic data only. Not accounting or tax certification. EUR purchases only; no credit notes. ALE is experimental and offline. Docker execution and hosted deployment require independent acceptance.**

## 1. Installation

Install Python 3.13, Node.js for regression tests, Tesseract with English and Spanish models for OCR, Pango and Noto fonts for PDF. Create a virtual environment and install the pinned dependencies. On Windows use PowerShell activation and `$env:` variables. Set a private data directory; never expose the legacy `app.py`.

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
export BC_ROOT="$PWD/data" BC_TLS=0 BC_HOSTS=127.0.0.1 BC_ORIGIN=http://127.0.0.1:8765
python admin.py company Demo
# COMPANY_ID = returned identifier
python admin.py user COMPANY_ID demo-owner --role owner
python admin.py user COMPANY_ID demo-analyst --role analyst
python -m uvicorn secure_app:app --host 127.0.0.1 --port 8765
```
```powershell
.venv\Scripts\Activate.ps1
$env:BC_ROOT = "$PWD\data"
$env:BC_TLS = "0"
$env:BC_HOSTS = "127.0.0.1"
$env:BC_ORIGIN = "http://127.0.0.1:8765"
```
http://127.0.0.1:8765/login

## 2. Accounts and roles

Create a company and at least two distinct owners (or an analyst and a separate owner). The CLI prompts for passwords (minimum 14 characters); there are no default credentials. Open the login page and choose a language. Readers cannot write; analysts can propose; owners can review another user’s request.

## 3. Input format

Use the synthetic demo first. The standard template has eleven fields, listed below; dates use ISO YYYY-MM-DD, units kg, l, ud (g and ml are normalized), prices are EUR excluding VAT. Use positive quantities, net plus shipping minus discount. CSV UTF-8, one XLSX sheet without formulas/macros/external links, or supported structured PDF. Up to 2 MB per file, 10,000 lines; batches 2–20 files and 8 MB total. No generic invoice or tax form import is promised.

```csv
supplier,invoice,line,date,product,unit,quantity,net_eur,shipping_eur,discount_eur,reported_total_eur
DEMO,INV-001,1,2026-01-01,ITEM,kg,10,100,0,0,100
```

## 4. Audit and comparisons

Run Audit file. Inspect arithmetic discrepancies, potential duplicates and price increases of at least 10%. Repeated conflicting IDs and inconsistent amounts are excluded from comparison. Compare identical products in the same unit and the most recent observations within 30 days. Potential savings are estimates, not paid or realized savings. Monthly totals include eligible rows only.

## 5. OCR review

Scanned PDF: transcribe up to five pages using English/Spanish OCR; compare against the original and correct the CSV manually. Submit original PDF, reviewed CSV and 10–1000-character evidence. OCR text is not included in calculations without review; this does not independently verify the original.

## 6. Governance

Propose equivalent product codes or declared savings with evidence and distinct baseline/purchase references. A second owner approves or rejects requests; self-approval is prohibited. Ordinary reports are drafts. Request release for real (not synthetic) reports with successful arithmetic checks and independent reviewer. Approved release is JSON only. Keep the local audit chain and review evidence.

## 7. Document intelligence

In Document intelligence, submit supported files with real/synthetic classification, optional approved template ID and evidence. For a template, provide JSON with all eleven keys mapped to distinct original headers, supplier, delimiter and `spanish` boolean for numeric convention. A separate owner reviews normalized lines and approves or rejects; expired or revoked templates invalidate use. Policy changes require independent approval.

```json
{
  "mapping": {
    "supplier": "supplier",
    "invoice": "invoice",
    "line": "line",
    "date": "date",
    "product": "product",
    "unit": "unit",
    "quantity": "quantity",
    "net_eur": "net_eur",
    "shipping_eur": "shipping_eur",
    "discount_eur": "discount_eur",
    "reported_total_eur": "reported_total_eur"
  },
  "supplier": "DEMO",
  "delimiter": ",",
  "spanish": false
}
```
## 8. Documented ROI

For documented ROI, choose two approved documents and 1-based line numbers, same product/unit and same real/synthetic classification. Actual date must be later and within the policy window (default 180 days). Enter incremental implementation cost as a decimal string. Gross reduction = (baseline unit price − actual unit price) × actual quantity; net = gross − cost; ROI % = net / cost × 100, undefined at zero cost. No proof of payment or causal benefit. Revocations invalidate dependent ROI.

## 9. History and exports

Open local history; download draft PDF, JSON, alerts.csv or comparisons.csv. Language selection affects presentation, not stored financial values or evidence. PDF summarizes up to 20 alerts and comparisons; CSV/JSON contain details. Machine-readable fields and source text remain original; unmapped technical diagnostics include the original Spanish message.

## 10. Adaptive learning

ALE is a separate supervised offline module. Run unit tests and synthetic stress commands below. It stores observations and candidates in SQLite, requires independent review and segregates tenants and real/synthetic observations. It does not automatically train from uploaded production invoices or change financial rules; do not deploy it as an autonomous decision engine.

```bash
python -m unittest adaptive_learning.test_learning
python -m adaptive_learning.stress --out /tmp/ledger64-ale --seed 20261126
```
## 11. Deployment

Local demo uses HTTP on loopback only. Production candidates require HTTPS, correct BC_ORIGIN and BC_HOSTS, persistent protected volume, backup and restore testing, container acceptance and vulnerability scan. Compose, Caddy and Railway configuration are provided; do not expose private data or activate paid infrastructure. The static marketing site is separate; generate metadata only for a verified HTTPS URL.

```bash
docker compose config
docker compose build
# Only after acceptance and with BC_DOMAIN configured:
docker compose up -d
```
## 12. Privacy and backups

MIT applies to original code; dependencies retain licenses. Never commit personal identifiers, business documents, credentials, backups, private model parameters or logs. Back up authentication and company databases separately, restore to a new tenant and restrict access. Audit chains are local, not externally anchored. Report vulnerabilities privately to the maintainer.

```bash
python admin.py backup-auth /secure/auth-backup.sqlite3
python admin.py backup COMPANY_ID /secure/company-backup.sqlite3
python admin.py restore-new RECOVERY /secure/company-backup.sqlite3
```
## 13. Troubleshooting

If login fails, check host, origin, credentials and rate limits. If import fails, use the sample template and check types, currency, columns, dates and limits. If OCR fails, verify Tesseract and language packs. For PDF glyphs, install Noto CJK and Devanagari fonts and Pango. For SQLite errors, check permissions and free space; do not bypass governance. Run the diagnostics below and submit a redacted bug report with version, OS and reproduction.

```bash
python scripts/doctor.py
python scripts/check.py
```
[README](../../README.en.md) · [SECURITY](../../SECURITY.md) · [LICENSE](../../LICENSE)

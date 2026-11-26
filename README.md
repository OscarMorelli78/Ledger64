# Ledger64

**Learn from every invoice. Make every decision count.**

Open-source invoice auditing, purchase cost comparison and financial governance for small businesses. C64-inspired interface; local processing without external AI.

[English](README.en.md) · [Español](README.es.md) · [Français](README.fr.md) · [Italiano](README.it.md) · [Deutsch](README.de.md) · [Português (Brasil)](README.pt-BR.md) · [简体中文](README.zh-CN.md) · [日本語](README.ja.md) · [हिन्दी](README.hi.md)

**Release candidate: use synthetic data only. Not accounting or tax certification. EUR purchases only; no credit notes. ALE is experimental and offline. Docker execution and hosted deployment require independent acceptance.**

## Quick start

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


## Documentation

[English — Documentation](docs/manual/en.md) · [MIT](LICENSE) · [SECURITY](SECURITY.md)

### Input format

Use the synthetic demo first. The standard template has eleven fields, listed below; dates use ISO YYYY-MM-DD, units kg, l, ud (g and ml are normalized), prices are EUR excluding VAT. Use positive quantities, net plus shipping minus discount. CSV UTF-8, one XLSX sheet without formulas/macros/external links, or supported structured PDF. Up to 2 MB per file, 10,000 lines; batches 2–20 files and 8 MB total. No generic invoice or tax form import is promised.

### Audit and comparisons

Run Audit file. Inspect arithmetic discrepancies, potential duplicates and price increases of at least 10%. Repeated conflicting IDs and inconsistent amounts are excluded from comparison. Compare identical products in the same unit and the most recent observations within 30 days. Potential savings are estimates, not paid or realized savings. Monthly totals include eligible rows only.

### Governance

Propose equivalent product codes or declared savings with evidence and distinct baseline/purchase references. A second owner approves or rejects requests; self-approval is prohibited. Ordinary reports are drafts. Request release for real (not synthetic) reports with successful arithmetic checks and independent reviewer. Approved release is JSON only. Keep the local audit chain and review evidence.

### Adaptive learning

ALE is a separate supervised offline module. Run unit tests and synthetic stress commands below. It stores observations and candidates in SQLite, requires independent review and segregates tenants and real/synthetic observations. It does not automatically train from uploaded production invoices or change financial rules; do not deploy it as an autonomous decision engine.

### Privacy and backups

MIT applies to original code; dependencies retain licenses. Never commit personal identifiers, business documents, credentials, backups, private model parameters or logs. Back up authentication and company databases separately, restore to a new tenant and restrict access. Audit chains are local, not externally anchored. Report vulnerabilities privately to the maintainer.


## Community & professional services

[Commercial services](COMMERCIAL.md) · [Support](SUPPORT.md) · [Roadmap](ROADMAP.md) · [Contact](CONTACT.md) · [Contribute worldwide](COLLABORATORS.md)

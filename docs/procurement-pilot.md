# Ledger64 procurement intelligence — experimental V1

This additive **synthetic-only local pilot** preserves engine.py and the MIT core.
The command-line operator is not a substitute for authenticated application roles.
Do not process real documents or distribute proprietary extensions until review.

## Quick start (from the repository root)

    python -m venv .venv
    # Activate the virtual environment and install the existing requirements.
    python -m pip install -r requirements.txt
    python -m procurement_cli --db demo-private.sqlite3 demo
    python -m procurement_cli --db demo-private.sqlite3 match --tenant demo --as-of 2026-01-31
    python -m procurement_cli --db demo-private.sqlite3 history --tenant demo --as-of 2026-01-31
    python -m procurement_cli --db demo-private.sqlite3 verify

Keep databases outside the repository in a restricted private directory. No real data.
The synthetic scenario: order 100 units at EUR 10 with 10% discount, two receipts
(40+50), two invoices (40 units EUR 360 and 60 units EUR 600).
Expected receipted net EUR 810, invoice net EUR 960, documentary exposure EUR 150.
This is not a paid loss. No overlapping alert sums.

## Import and review

    python -m procurement_cli extract demo.pdf
    python -m procurement_cli extract demo.xlsx

For optional advanced OCR: provision PaddleOCR 3.x, PP-StructureV3 and all local
model directories in a separate supported Python environment; export a trusted
PaddleX configuration, verify package/model licenses and block network egress.
Then use:

    python -m procurement_cli extract synthetic.png --paddle-config /private/pipeline.yaml
    python -m procurement_cli extract synthetic.pdf --paddle-config /private/pipeline.yaml --ollama-model local-model

Ollama must run on loopback with an installed non-cloud model, with network
egress blocked by the operator. The code does not install or benchmark OCR or LLM
models. Model outputs are always unapproved proposals; scores are not correctness.
PP-Structure table HTML is untrusted data and must never be rendered as HTML.
PyMuPDF can optionally be selected with --pymupdf, but is AGPL/commercial:
https://pymupdf.io/licensing. Do not bundle it into a proprietary distribution
without a compliant licensing decision. Default remains existing pypdf.

The approved JSON schema is explicit. Example order:
    
    {"kind":"order","id":"PO1","supplier":"Supplier A","date":"2026-01-01","currency":"EUR","lines":[{"id":"1","sku":"PAPER-A4","unit":"ud","quantity":"100","unit_price":"10","discount_pct":"10"}]}

Receipt lines require order_id and order_line instead of price and discount.
Invoice lines require those references plus net_total in EUR cents. Identifiers,
product code and canonical units must be independently verified. An operator
reviews and corrects candidate JSON against the original before importing:

    python -m procurement_cli --db demo-private.sqlite3 approve --tenant demo --document reviewed.json --original synthetic.pdf --proposer analyst --reviewer owner --evidence "Reviewed all fields against synthetic document"

The local pilot stores original bytes, hashes, document identity and reviewer
evidence. It does not authenticate CLI names; trusted offline use only.
No real/synthetic mixing. Existing web approvals, tenant isolation and templates
are untouched. An opt-in authenticated web pilot is available. Existing supplier CSV
templates remain available via intelligence.py; learning new arbitrary PDF
layouts automatically is not implemented. Reference mapping is explicit.

## Accounting boundaries

All amounts EUR before VAT. No credit notes, returns, FX, bank reconciliation,
payments or realized losses. Cumulative snapshot as of a date, explicit line
references and complete receipts required; no assumed delivery, no fuzzy matching.
The invoice snapshot passed to the existing engine uses already reviewed net
line totals (not a re-extraction of original tax/discount breakdown).
Historical comparisons and documentary exposure can overlap. Do not sum them.
ALE uses earlier reviewed purchase days and flags statistical deviations
without retraining or promoting the original ALE model. Initial calibration
is provisional and normality is not independently established.

## Acceptance

    python -m unittest -v test_procurement test_procurement_extensions
    python scripts/check.py

Tests cover synthetic partial and multiple delivery/invoice matching, discount,
tolerance, scope, isolation, source tampering, CLI demo, historical ALE,
basic PDF/XLSX extraction and mock semantic proposals. Real OCR model accuracy,
latency, RAM, extraction field F1, real invoices, production security and
full browser acceptance are explicit open gates. No 100% operational claim.

## Authenticated web pilot (synthetic only)

Set BC_PROCUREMENT_PILOT=1 before starting secure_app, sign in with the normal
Ledger64 accounts and navigate to /procurement. The analyst submits a normalized
candidate and original source; an independent owner downloads and reviews it.
The report supports reader access. Existing main UI is unchanged. The feature
is disabled by default. Local Tesseract fallback handles scanned PDF/JPG/PNG;
advanced Paddle and Ollama use optional trusted server configuration. The pilot
database is separate; existing backup/restore does not include it. Production
backup, retention, revocation of approved documents, model benchmark and a
complete browser/UX evaluation remain mandatory before real-data release.

## Supervised supplier templates and model benchmarking

The new trusted local CLI supports template-register and template-apply. The mapping
JSON uses the required canonical keys from procurement_templates.fields(kind),
pointing to the CSV column names. A template is tied to tenant, supplier, document
kind, ordered header signature, version, original example hash and distinct review
identities. Changed headers require a new version. Applying a template creates an
unapproved candidate. The earlier web template module remains unchanged; automatic
PDF layout training is not implemented.

    python scripts/benchmark_procurement_ocr.py --backend tesseract
    python scripts/benchmark_procurement_ocr.py --backend paddle --config /private/pipeline.yaml
    python scripts/benchmark_procurement_ocr.py --backend paddle --config /private/pipeline.yaml --model local-model

The benchmark records per-case latency, Linux peak RSS, exact token recovery and
recognized table count. This smoke benchmark cannot establish actual financial field
accuracy or production capacity. Use a held-out labelled corpus and security review
before selecting or distributing an advanced model. The local LLM now receives an
explicit structured-output schema; its results still require independent review.

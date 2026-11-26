# Field-level extraction evaluation — synthetic pilot

The original four-token OCR smoke test is retained. The new benchmark has nine complete
labelled purchase documents (orders, receipts, invoices with two lines each) and two
incomplete/adversarial inputs. It compares all canonical fields by document and line ID,
compares decimal amounts numerically, counts missing and incorrect fields, unsafe
proposals on incomplete documents, exact complete-document rate and field F1.

Run locally in the repository:

    python scripts/benchmark_procurement_fields.py --backend text --gate
    python scripts/benchmark_procurement_fields.py --backend tesseract
    python scripts/benchmark_procurement_fields.py --backend paddle --config /private/pipeline.yaml
    python scripts/benchmark_procurement_fields.py --backend paddle --config /private/pipeline.yaml --model local-model --gate

The text parser is an explicit labelled-layout baseline, not a generic document model.
The OCR benchmark intentionally reports even if its coverage is poor; CI requires the
text baseline and tests to pass. Optional --gate requires at least 2/3 exact complete
documents, no incorrect emitted numeric fields, no unsafe proposals on the two incomplete
fixtures and no extraction errors. These thresholds are provisional engineering gates,
not claims of production accuracy. A separate larger, blinded, authorised real corpus
and independent review remain required. Do not tune on the final evaluation corpus.

Install advanced models separately under their reviewed licences, pre-provision all
model directories, disable network egress at the OS/container level, then execute the
optional commands. Ollama must be local and have no cloud inference. This benchmark
does not provision models or prove offline isolation. No customer data, no payments.

## Isolated real semantic-model experiment

The dedicated Procurement isolated semantic benchmark workflow provisions the official
Ollama 0.40.18 linux/amd64 image pinned to its manifest digest and the Qwen2.5
1.5B Q4_K_M public model (expected manifest ID prefix 65ec06548149). No documents
are processed during provisioning. The provision container is removed. Inference
runs in a network-none container; the Python client shares only that isolated
network namespace and communicates over loopback. A read-only source mount and a
separate report directory are used. The quality gate is not bypassed if the model
fails. The experiment evaluates semantic extraction from text, not PaddleOCR or
real invoices, and does not approve any financial record. Model selection remains
conditional on measured results and licensing review.

## Second experiment

Qwen2.5 1.5B v1 returned no candidate on all eleven documents (run 45880052343).
The v2 adapter uses a flat evidence-per-field schema and explicitly describes the
labelled layout; it remains a separate experiment, not a default model. The same
acceptance gate applies. The consensus baseline compares three local OCR passes;
conflicting valid candidates always abstain rather than voting. Only the known
labelled layout is supported. Agreement is not proof of correctness. A separate
PP-StructureV3 workflow measures twelve table cells per synthetic image under
network-disabled inference, with the original versions and dependencies recorded.

Paddle run 45880925169 failed during offline inference because the lazy table
orientation classifier was not provisioned. The corrected provisioning stage
warms up the full table pipeline with distinct synthetic values before removing
network access. Acceptance fixtures remain separate; no customer data is used.

The evidence-per-field v2 model also returned no accepted candidate on nine
complete documents (run 45881017494). Qwen2.5 1.5B is rejected as the extraction
candidate. The next experiment uses Qwen2.5 7B Q4_K_M (manifest 845dbda0ea48,
Apache-2.0 weights per Ollama's model documentation), a compact array schema,
source-derived row evidence and independent labelled-layout verification.
The quality gate stays unchanged. This is not a default model or production
license approval. The larger model increases hardware requirements.

## Document Intelligence V2

Paddle run 45881442906 completed inference offline: normal table 12/12 cells,
rotated table had an entire-column permutation (all values retained with their
headers), raw positions 0/12. The report write also failed on mount permissions.
The next benchmark preserves both raw positional metrics and exact-header-aligned
metrics, with no fuzzy matching. It uses a single serialized CPU pipeline per
process and bounded deskew. The artifact is copied from the stopped container
rather than changing host permissions. Raw and normalized metrics must not be
confused. Qwen2.5 7B run 45881621343 also failed all complete document candidates;
it is not a default extraction model.

A separate lightweight ruled-grid route uses local Tesseract, exact cell geometry
and bounded deskew; no heavyweight model or LLM. Acceptance: four new synthetic
layouts (0, +2, -3 degrees, extra row and alternate headings), all exact cells,
mean <10 s, sampled process-tree RSS <4,000,000 KiB. RSS is approximate and sums
shared pages. Results apply only to these ruled-table layouts. Unsupported layouts
abstain; PDF deskew, perspective and borderless tables remain separate gates.

The image-matching acceptance uses five additional synthetic purchase documents
(two products, partial receipts and multiple invoices). Operator-supplied metadata
and explicit column labels are held constant; OCR must reproduce every line field.
Only exact fixture candidates are approved by a simulated independent reviewer.
The original images and normalized records are retained, and the financial engine
must reproduce EUR 150 documented exposure, no confirmed paid loss, and valid
integrity. This is not a test of automatic header metadata extraction.

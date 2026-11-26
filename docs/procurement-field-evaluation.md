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

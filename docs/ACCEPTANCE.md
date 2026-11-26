# International release candidate acceptance — 2026-11-26

Locally executed with Python 3.13.5 and existing pinned dependencies.

| Gate | Evidence |
|---|---|
| Core regression | 122 successful Python test executions (includes inherited repeated tests) |
| Authenticated UI | 49 checks, simulated DOM and real HTTP backend |
| Offline ALE | 17 unit tests passed |
| Localization | 5 test cases passed, including 27 HTML variants, 45 JS syntax checks, 9 generated and parsed PDFs, static diagnostics and documentation |
| HTTP locale acceptance | 9/9 languages; exact same financial JSON across locales |
| Core preservation | 18/18 selected source and synthetic fixture files identical to prior distribution |
| Manuals and README | Nine languages; translation editorial review by native speakers pending |
| Marketing | 135 keywords; 139 ad entries paused; no verified search volumes |
| Browser | Chromium launched; navigation blocked by environment administrator policy. Actual browser end-to-end gate pending. |
| Docker | No engine available in this environment; build, smoke test and vulnerability scan pending. |
| Production | HTTPS, backups, concurrency, deployment and billing not verified. |

OCR language models remain English/Spanish. Raw user data, canonical codes and unrecognized technical diagnostics are not machine-translated; unknown diagnostics retain original detail with a localized generic wrapper. ALE is offline and experimental. No private document training or export occurred in this release. No new stress corpus run claimed. No remote changes or advertising spend. Use synthetic data only until release gates pass.

## Procurement experimental acceptance — 2026-11-26

Verified code snapshot f9fd4a6631a3c6a5fee83a9bd45716655ec49b45: 108/108 specific tests; all six CI runs successful ([procurement](https://github.com/OscarMorelli78/Ledger64/actions/runs/45889543410), [browser](https://github.com/OscarMorelli78/Ledger64/actions/runs/45889549744), [container](https://github.com/OscarMorelli78/Ledger64/actions/runs/45889549684), [international](https://github.com/OscarMorelli78/Ledger64/actions/runs/45889549634), [learning](https://github.com/OscarMorelli78/Ledger64/actions/runs/45889549749)). Synthetic recovery reproduces EUR 150 documented exposure, no confirmed paid loss. Five-image extraction 4/5 first-pass and 5/5 after simulated human selection. Lightweight OCR 52/52 cells, mean 2.15 s, sampled process-tree peak 94.8 MiB. Paddle 24/24 cells on two tables; resource targets unmet. Not production certification. The earlier acceptance section is retained as historical evidence, not the current gate status. Nine-language manual additions require editorial review by native speakers.

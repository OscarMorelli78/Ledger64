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

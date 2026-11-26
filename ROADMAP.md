# Roadmap / Hoja de ruta

Status: release candidate. Roadmap items are proposals, not delivery commitments.

| Stage | Deliverable | Acceptance gate |
|---|---|---|
| RC3 | Commercial docs, contact flow, contribution programme | Links, privacy and form tests |
| RC3 | Docker Engine and browser acceptance | Green CI on the exact commit; vulnerability scan |
| Pilot | Real-document learning and evaluation in private environments | Explicit consent, held-out evaluation, zero cross-tenant leakage |
| Pilot | Deployable backups, TLS, recovery and load tests | Restore test, security review, agreed capacity |
| 0.1 stable | Reliable core and reviewed translations | Regression, accessibility and documented limitations |
| 0.2 | ERP integrations and private learning improvements | Contract tests; independent validation |
| Future | Managed hosting | Demand, operating costs, privacy terms and sustainable unit economics |

The C64 visual identity and MIT core remain intact. ALE is experimental, offline and not autonomous production training. No confidential training data will be distributed.

## Español

Prioridad: certificar contenedor y navegador, validar con empresas piloto y revisar seguridad; después integraciones y posible alojamiento gestionado. No se prometen fechas ni funciones no verificadas.

## Current experimental baseline (2026-11-26)

Completed on f9fd4a66 with synthetic data: cumulative 3-way matching, reviewed OCR, supplier layout memory, independent revisions, and procurement database recovery. 108 tests and all six CI runs successful. See [PR #2](https://github.com/OscarMorelli78/Ledger64/pull/2).

Next gates: encrypted recovery with key management; whole-install recovery; broader blinded document corpus and resource tests; independent security and privacy assessment; dual selectable themes; target-platform installation; authorized SME pilot. Open Core is a commercial plan, not an available proprietary extension. Do not merge the pilot into Main before all gates pass.

# Ledger64 — Documentazione (Italiano)

Revisione delle fatture, confronto dei costi di acquisto e governance finanziaria open source per le PMI. Interfaccia ispirata al C64, elaborazione locale senza IA esterna.

**Versione candidata: usare solo dati sintetici. Nessuna certificazione contabile o fiscale. Solo acquisti in EUR, senza note di credito. ALE è sperimentale e offline. Docker e hosting richiedono collaudo indipendente.**

## 1. Installazione

Installa Python 3.13, Node.js per i test, Tesseract con modelli inglese e spagnolo, Pango e caratteri Noto per PDF. Crea un ambiente virtuale e installa le dipendenze fissate. Su Windows usa PowerShell e `$env:`. Imposta una directory privata; non esporre il vecchio `app.py`.

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

## 2. Account e ruoli

Crea un’azienda e due titolari distinti (o analista e titolare indipendente). La CLI chiede password di almeno 14 caratteri; nessuna credenziale predefinita. Accedi e scegli la lingua. Lettori in sola lettura, analisti propongono, titolari revisionano le richieste altrui.

## 3. Formato di input

Inizia con la demo sintetica. Il modello ha undici campi sotto, data ISO AAAA-MM-GG, unità kg, l, ud (g e ml normalizzati), prezzi EUR IVA esclusa. Quantità positiva, totale netto + trasporto − sconto. CSV UTF-8, XLSX a foglio unico senza formule, macro o collegamenti esterni, PDF strutturato compatibile. 2 MB per file, 10.000 righe; lotti 2–20 file, 8 MB totali. Non importa fatture generiche o moduli fiscali arbitrari.

```csv
supplier,invoice,line,date,product,unit,quantity,net_eur,shipping_eur,discount_eur,reported_total_eur
DEMO,INV-001,1,2026-01-01,ITEM,kg,10,100,0,0,100
```

## 4. Revisione e confronti

Avvia la revisione. Controlla scostamenti aritmetici, possibili duplicati e aumenti di prezzo almeno del 10%. ID conflittuali e importi incoerenti esclusi dal confronto. Confronta prodotti identici, stessa unità, osservazioni recenti entro 30 giorni. Risparmio potenziale non è realizzato né pagato. Totali mensili delle sole righe ammissibili.

## 5. Revisione OCR

PDF scansionato: trascrivi fino a cinque pagine con OCR inglese/spagnolo, confronta con l’originale e correggi il CSV manualmente. Invia PDF originale, CSV revisionato e motivazione di 10–1000 caratteri. Il testo OCR non entra nei calcoli senza revisione; non è verifica indipendente.

## 6. Governance

Proponi equivalenze o risparmi dichiarati con evidenze e riferimenti distinti. Altro titolare approva o rifiuta; vietata autoapprovazione. Report ordinari sono bozze. Richiedi rilascio di report reali (non sintetici), controllo aritmetico riuscito e revisore indipendente. Rilascio approvato solo JSON. Conserva catena locale ed evidenze.

## 7. Intelligenza documentale

In Intelligenza documentale invia file compatibili classificati reali/sintetici, ID opzionale del modello approvato ed evidenza. Modello JSON: undici campi verso intestazioni distinte, fornitore, separatore e booleano `spanish`. Altro titolare verifica righe normalizzate e decide; modelli scaduti o revocati inutilizzabili. Cambi politica con approvazione indipendente.

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
## 8. ROI documentato

Per ROI documentato scegli due documenti approvati, righe da 1, stesso prodotto/unità e classificazione. Acquisto successivo entro finestra politica (180 giorni predefiniti). Costo incrementale come stringa decimale. Riduzione lorda = (prezzo unitario base − attuale) × quantità attuale; netta = lorda − costo; ROI % = netta / costo × 100, indefinito a costo zero. Nessuna prova di pagamento o causalità. Revoche invalidano ROI dipendenti.

## 9. Cronologia ed esportazioni

Apri cronologia locale e scarica PDF bozza, JSON, alerts.csv o comparisons.csv. Lingua solo di presentazione, non modifica valori o prove memorizzati. PDF riassume 20 avvisi e confronti; CSV/JSON completi. Campi macchina e testo fonte invariati; diagnostica non tradotta conserva originale spagnolo.

## 10. Apprendimento adattivo

ALE è modulo supervisionato offline. Esegui test e stress sintetico sotto. Memorizza osservazioni e candidati in SQLite, richiede revisione indipendente e separa aziende e dati reali/sintetici. Non apprende automaticamente dalle fatture di produzione né cambia regole; non usarlo come decisore autonomo.

```bash
python -m unittest adaptive_learning.test_learning
python -m adaptive_learning.stress --out /tmp/ledger64-ale --seed 20261126
```
## 11. Distribuzione

Demo HTTP solo loopback. Produzione richiede HTTPS, BC_ORIGIN e BC_HOSTS corretti, volume protetto persistente, test backup/ripristino, collaudo container e scansione vulnerabilità. Compose, Caddy e Railway inclusi; non pubblicare dati privati né attivare servizi a pagamento. Sito marketing separato; genera metadati solo per URL HTTPS verificato.

```bash
docker compose config
docker compose build
# Only after acceptance and with BC_DOMAIN configured:
docker compose up -d
```
## 12. Privacy e backup

MIT copre codice originale; dipendenze mantengono licenze. Non pubblicare identificativi, documenti, credenziali, backup, modelli privati o log. Salva separatamente database autenticazione e aziendali, ripristina in nuova azienda e limita accesso. Catene locali senza ancoraggio esterno. Segnala vulnerabilità in privato.

```bash
python admin.py backup-auth /secure/auth-backup.sqlite3
python admin.py backup COMPANY_ID /secure/company-backup.sqlite3
python admin.py restore-new RECOVERY /secure/company-backup.sqlite3
```
## 13. Risoluzione problemi

Accesso: verifica host, origine, credenziali e limiti tentativi. Importazione: modello, tipi, valuta, colonne, date e limiti. OCR: Tesseract e modelli. PDF: Noto CJK, Devanagari e Pango. SQLite: permessi e spazio; non aggirare governance. Esegui diagnostica e invia segnalazione anonimizzata con versione, OS e riproduzione.

```bash
python scripts/doctor.py
python scripts/check.py
```
[README](../../README.it.md) · [SECURITY](../../SECURITY.md) · [LICENSE](../../LICENSE)

## 14. Intelligence degli acquisti — pilota sperimentale

Agente di intelligence degli acquisti per PMI: nucleo deterministico MIT, elaborazione esclusivamente locale e apprendimento supervisionato. Open Core è la strategia commerciale; nessuna estensione a pagamento inclusa. Non esegue pagamenti.

Usa il ramo sperimentale, non la versione stabile v0.1.0. Solo dati sintetici. Segui la sezione 1, crea account distinti di analista e proprietario, imposta la variabile prima di Uvicorn, accedi e apri /procurement. Disattivato per impostazione predefinita. GitHub Pages è una demo statica, non il backend Python.

```bash
git clone -b feat/adaptive-procurement-v1 https://github.com/OscarMorelli78/Ledger64.git Ledger64-pilot
# Linux/macOS, before starting Uvicorn:
export BC_PROCUREMENT_PILOT=1
```
```powershell
$env:BC_PROCUREMENT_PILOT = "1"
```

http://127.0.0.1:8765/procurement

Carica PDF, XLSX, CSV, JSON, PNG o JPG compatibili (max 2 MB). Estrazione standard di testo digitale e OCR locale; griglia leggera per immagini compatibili con bordi, confronto letture per layout etichettati noti. Correzione di piccole rotazioni (±5°); tabelle senza bordi e documenti arbitrari non garantiti. PaddleOCR/PP-Structure è opzionale e oneroso. I modelli Qwen provati non hanno superato l'accettazione. OCR inglese/spagnolo.

Controlla ogni cella e inserisci metadati (tipo, ID, fornitore, data, EUR). Associa intestazioni esatte ai campi canonici; non inventare valori. Richiedi letture alternative per identificativi ambigui. Confronta l'originale. Invia la bozza con evidenza; un altro proprietario la verifica. Riferimenti compatibili non autorizzano pagamenti. Modelli CSV/tabelle per fornitore tramite CLI fidata: riuso della struttura, mai degli importi.

Approva ordini, ricevute e fatture. Riconciliazione cumulativa per riga d'ordine di consegne parziali e fatture multiple; tolleranze quantità, EUR e percentuale prezzo. Sconti contrattuali percentuali e anomalie storiche deterministici. Esposizione e risparmi stimati non sono perdite pagate confermate. Correzione: nuova versione, originale conservato; revoca: esclusione da report e apprendimento correnti. Revisione indipendente obbligatoria.

### Backup e ripristino locale

Prima della sostituzione arresta il servizio. Directory private esistenti, SHA-256 conservato separatamente, ripristino solo in un nuovo file. La base acquisti include originali, versioni, code e modelli; ricostruisce segnali storici. Autenticazione e base aziendale principale richiedono backup separati. Cifratura e pianificazione non ancora disponibili. Non caricare dati aziendali su GitHub.

```bash
python -m procurement_backup create --source /private/procurement.sqlite3 --destination /backup/snapshot.sqlite3 --tenant COMPANY_ID
python -m procurement_backup verify --source /backup/snapshot.sqlite3 --tenant COMPANY_ID --sha256 EXPECTED_HASH
python -m procurement_backup restore --source /backup/snapshot.sqlite3 --destination /recovery/recovered.sqlite3 --tenant COMPANY_ID --sha256 EXPECTED_HASH
```

### Evidenze e limiti

Accettazione sintetica: 108 test, cinque immagini (4/5 al primo passaggio, 5/5 dopo revisione simulata), esposizione di 150 EUR riprodotta dopo ripristino. OCR leggero: 52/52 celle in quattro tabelle, media 2,15 s, picco campionato 94,8 MiB. Paddle: 24/24 celle in due tabelle, obiettivi di risorse non raggiunti. Nessuna certificazione di produzione. Tema moderno, formati più ampi, cifratura, ripristino completo e validazione reale pendenti.

[CI — f9fd4a66](https://github.com/OscarMorelli78/Ledger64/actions/runs/45889543410) · [PR #2](https://github.com/OscarMorelli78/Ledger64/pull/2) · [CLI](../procurement-pilot.md) · [Backup](../procurement-data-resilience.md)

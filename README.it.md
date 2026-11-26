# Ledger64

**Impara da ogni fattura. Dai valore a ogni decisione.**

Revisione delle fatture, confronto dei costi di acquisto e governance finanziaria open source per le PMI. Interfaccia ispirata al C64, elaborazione locale senza IA esterna.

[English](README.en.md) · [Español](README.es.md) · [Français](README.fr.md) · [Italiano](README.it.md) · [Deutsch](README.de.md) · [Português (Brasil)](README.pt-BR.md) · [简体中文](README.zh-CN.md) · [日本語](README.ja.md) · [हिन्दी](README.hi.md)

**Versione candidata: usare solo dati sintetici. Nessuna certificazione contabile o fiscale. Solo acquisti in EUR, senza note di credito. ALE è sperimentale e offline. Docker e hosting richiedono collaudo indipendente.**

## Avvio rapido

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


## Documentazione

[Italiano — Documentazione](docs/manual/it.md) · [MIT](LICENSE) · [SECURITY](SECURITY.md)

### Formato di input

Inizia con la demo sintetica. Il modello ha undici campi sotto, data ISO AAAA-MM-GG, unità kg, l, ud (g e ml normalizzati), prezzi EUR IVA esclusa. Quantità positiva, totale netto + trasporto − sconto. CSV UTF-8, XLSX a foglio unico senza formule, macro o collegamenti esterni, PDF strutturato compatibile. 2 MB per file, 10.000 righe; lotti 2–20 file, 8 MB totali. Non importa fatture generiche o moduli fiscali arbitrari.

### Revisione e confronti

Avvia la revisione. Controlla scostamenti aritmetici, possibili duplicati e aumenti di prezzo almeno del 10%. ID conflittuali e importi incoerenti esclusi dal confronto. Confronta prodotti identici, stessa unità, osservazioni recenti entro 30 giorni. Risparmio potenziale non è realizzato né pagato. Totali mensili delle sole righe ammissibili.

### Governance

Proponi equivalenze o risparmi dichiarati con evidenze e riferimenti distinti. Altro titolare approva o rifiuta; vietata autoapprovazione. Report ordinari sono bozze. Richiedi rilascio di report reali (non sintetici), controllo aritmetico riuscito e revisore indipendente. Rilascio approvato solo JSON. Conserva catena locale ed evidenze.

### Apprendimento adattivo

ALE è modulo supervisionato offline. Esegui test e stress sintetico sotto. Memorizza osservazioni e candidati in SQLite, richiede revisione indipendente e separa aziende e dati reali/sintetici. Non apprende automaticamente dalle fatture di produzione né cambia regole; non usarlo come decisore autonomo.

### Privacy e backup

MIT copre codice originale; dipendenze mantengono licenze. Non pubblicare identificativi, documenti, credenziali, backup, modelli privati o log. Salva separatamente database autenticazione e aziendali, ripristina in nuova azienda e limita accesso. Catene locali senza ancoraggio esterno. Segnala vulnerabilità in privato.


## Community & professional services

[Commercial services](COMMERCIAL.md) · [Support](SUPPORT.md) · [Roadmap](ROADMAP.md) · [Contact](CONTACT.md) · [Contribute worldwide](COLLABORATORS.md)

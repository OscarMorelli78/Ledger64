# Ledger64 — Dokumentation (Deutsch)

Open-Source-Rechnungsprüfung, Einkaufskostenvergleich und Finanz-Governance für KMU. C64-inspirierte Oberfläche; lokale Verarbeitung ohne externe KI.

**Release-Kandidat: nur synthetische Daten verwenden. Keine Buchhaltungs- oder Steuerzertifizierung. Nur Einkäufe in EUR, keine Gutschriften. ALE ist experimentell und offline. Docker-Ausführung und Hosting erfordern unabhängige Abnahme.**

## 1. Installation

Python 3.13, Node.js für Tests, Tesseract mit englischen und spanischen Modellen, Pango und Noto-Schriften für PDF installieren. Virtuelle Umgebung erstellen und festgelegte Abhängigkeiten installieren. Unter Windows PowerShell und `$env:` nutzen. Privates Datenverzeichnis wählen; alten Server `app.py` nicht veröffentlichen.

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

## 2. Konten und Rollen

Unternehmen und zwei verschiedene Inhaber (oder Analyst und unabhängiger Inhaber) anlegen. CLI verlangt Passwörter mit mindestens 14 Zeichen; keine Standardzugänge. Anmelden und Sprache wählen. Leser dürfen nur lesen, Analysten vorschlagen, Inhaber fremde Anfragen prüfen.

## 3. Eingabeformat

Mit synthetischer Demo beginnen. Standardvorlage mit elf Feldern unten, ISO-Datum JJJJ-MM-TT, Einheiten kg, l, ud (g und ml normalisiert), EUR ohne MwSt. Positive Menge, Netto + Versand − Rabatt. UTF-8-CSV, XLSX mit einem Blatt ohne Formeln, Makros oder externe Links, oder unterstütztes strukturiertes PDF. 2 MB je Datei, 10.000 Zeilen; Stapel 2–20 Dateien, 8 MB gesamt. Kein universeller Rechnungs- oder Steuerformularimport.

```csv
supplier,invoice,line,date,product,unit,quantity,net_eur,shipping_eur,discount_eur,reported_total_eur
DEMO,INV-001,1,2026-01-01,ITEM,kg,10,100,0,0,100
```

## 4. Prüfung und Vergleich

Prüfung starten. Rechenabweichungen, mögliche Dubletten und Preissteigerungen ab 10 % prüfen. Konflikt-IDs und falsche Summen werden vom Vergleich ausgeschlossen. Identische Produkte und Einheiten mit jüngsten Beobachtungen innerhalb von 30 Tagen vergleichen. Einsparpotenzial ist keine realisierte oder bezahlte Einsparung. Monatskosten nur zulässige Zeilen.

## 5. OCR-Prüfung

Gescanntes PDF: bis fünf Seiten mit englisch/spanischer OCR transkribieren, am Original prüfen und CSV manuell korrigieren. Original-PDF, geprüfte CSV und Begründung mit 10–1000 Zeichen einreichen. OCR-Text geht nicht ungeprüft in Berechnungen ein; keine unabhängige Originalprüfung.

## 6. Governance

Gleichwertigkeiten oder angegebene Einsparungen mit Nachweisen und getrennten Basis-/Einkaufsreferenzen vorschlagen. Anderer Inhaber genehmigt oder lehnt ab, keine Selbstfreigabe. Normale Berichte sind Entwürfe. Freigabe echter (nicht synthetischer) Berichte mit bestandenem Rechencheck und unabhängigem Prüfer beantragen. Freigabe nur als JSON. Lokale Kette und Nachweise aufbewahren.

## 7. Dokumentenintelligenz

In Dokumentenintelligenz unterstützte Dateien mit Echt-/Synthetik-Klassifikation, optionaler freigegebener Vorlagen-ID und Nachweis einreichen. JSON-Vorlage: elf Felder auf eindeutige Originalspalten, Lieferant, Trennzeichen und Boolean `spanish`. Anderer Inhaber prüft normalisierte Zeilen; abgelaufene/widerrufene Vorlagen ungültig. Richtlinienänderungen unabhängig genehmigen.

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
## 8. Dokumentierter ROI

Für dokumentierten ROI zwei freigegebene Dokumente und Zeilennummern ab 1 wählen, gleiches Produkt/Einheit und Klassifikation. Einkauf später als Basis und innerhalb Richtlinienfenster (Standard 180 Tage). Zusatzkosten als Dezimalstring. Bruttoreduktion = (Basisstückpreis − aktueller Stückpreis) × aktuelle Menge; netto = brutto − Kosten; ROI % = netto / Kosten × 100, bei null undefiniert. Kein Zahlungs- oder Kausalitätsnachweis. Widerruf macht abhängigen ROI ungültig.

## 9. Verlauf und Exporte

Lokalen Verlauf öffnen, Entwurf-PDF, JSON, alerts.csv oder comparisons.csv herunterladen. Sprache betrifft Darstellung, nicht gespeicherte Beträge oder Nachweise. PDF fasst je 20 Warnungen und Vergleiche zusammen; CSV/JSON mit Details. Maschinenfelder und Quelltexte unverändert; nicht übersetzte Diagnosen mit spanischem Original.

## 10. Adaptives Lernen

ALE ist ein separates überwachtes Offline-Modul. Tests und synthetischen Stresstest unten ausführen. SQLite speichert Beobachtungen und Kandidaten; unabhängige Prüfung erforderlich, Mandanten und Echt-/Synthetikdaten getrennt. Kein automatisches Lernen aus Produktionsrechnungen, keine Änderung von Finanzregeln; keine autonomen Entscheidungen.

```bash
python -m unittest adaptive_learning.test_learning
python -m adaptive_learning.stress --out /tmp/ledger64-ale --seed 20261126
```
## 11. Bereitstellung

Lokale HTTP-Demo nur Loopback. Produktion erfordert HTTPS, korrekte BC_ORIGIN und BC_HOSTS, geschütztes persistentes Volume, Backup-/Restore-Tests, Container-Abnahme und Schwachstellenscan. Compose, Caddy, Railway enthalten; keine privaten Daten veröffentlichen oder kostenpflichtige Infrastruktur aktivieren. Marketingseite separat; Metadaten erst nach bestätigter HTTPS-URL erzeugen.

```bash
docker compose config
docker compose build
# Only after acceptance and with BC_DOMAIN configured:
docker compose up -d
```
## 12. Datenschutz und Sicherung

MIT gilt für Originalcode; Abhängigkeiten behalten ihre Lizenzen. Keine personenbezogenen Daten, Belege, Zugangsdaten, Backups, privaten Modellparameter oder Logs veröffentlichen. Authentifizierungs- und Unternehmensdatenbanken getrennt sichern, in neuen Mandanten wiederherstellen, Zugriff beschränken. Lokale Ketten ohne externe Verankerung. Schwachstellen privat melden.

```bash
python admin.py backup-auth /secure/auth-backup.sqlite3
python admin.py backup COMPANY_ID /secure/company-backup.sqlite3
python admin.py restore-new RECOVERY /secure/company-backup.sqlite3
```
## 13. Fehlerbehebung

Anmeldung: Host, Origin, Zugangsdaten und Versuchslimit prüfen. Import: Vorlage, Typen, Währung, Spalten, Datum und Grenzen. OCR: Tesseract und Modelle. PDF: Noto CJK, Devanagari, Pango. SQLite: Rechte und Speicherplatz, Governance nicht umgehen. Diagnose ausführen und anonymisierten Fehlerbericht mit Version, OS und Reproduktion senden.

```bash
python scripts/doctor.py
python scripts/check.py
```
[README](../../README.de.md) · [SECURITY](../../SECURITY.md) · [LICENSE](../../LICENSE)

## 14. Einkaufsintelligenz — experimenteller Pilot

Einkaufsintelligenz-Agent für KMU: deterministischer MIT-Kern, ausschließlich lokale Verarbeitung und beaufsichtigtes Lernen. Open Core ist die Geschäftsstrategie; keine kostenpflichtigen Erweiterungen enthalten. Keine Zahlungsausführung.

Experimentellen Branch verwenden, nicht die stabile Version v0.1.0. Nur synthetische Daten. Abschnitt 1 folgen, getrennte Analysten- und Eigentümerkonten anlegen, Variable vor Uvicorn setzen, anmelden und /procurement öffnen. Standardmäßig deaktiviert. GitHub Pages ist eine statische Demo, kein Python-Backend.

```bash
git clone -b feat/adaptive-procurement-v1 https://github.com/OscarMorelli78/Ledger64.git Ledger64-pilot
# Linux/macOS, before starting Uvicorn:
export BC_PROCUREMENT_PILOT=1
```
```powershell
$env:BC_PROCUREMENT_PILOT = "1"
```

http://127.0.0.1:8765/procurement

Kompatible PDF, XLSX, CSV, JSON, PNG oder JPG (max. 2 MB) laden. Standardextraktion für digitalen Text und lokale OCR; leichtes Rasterverfahren für geeignete Gitterbilder, Lesevergleich für bekannte beschriftete Layouts. Kleine Drehungen (±5°) korrigierbar; randlose Tabellen und beliebige Dokumente nicht garantiert. PaddleOCR/PP-Structure optional und ressourcenintensiv. Getestete Qwen-Modelle bestanden die automatische Extraktion nicht. OCR Englisch/Spanisch.

Zellen prüfen und Metadaten eingeben (Typ, ID, Lieferant, Datum, EUR). Exakte Überschriften kanonischen Feldern zuordnen; fehlende Werte nicht erfinden. Alternative Lesungen unklarer Kennungen anfordern, Original prüfen. Entwurf mit Nachweis einreichen; ein anderer Eigentümer prüft. Passende Referenzen berechtigen nicht zur Zahlung. Lieferanten-CSV/Tabellenvorlagen über vertrauenswürdige CLI: nur Struktur, keine Beträge.

Bestellungen, Wareneingänge und Rechnungen freigeben. Teilmengen und mehrere Rechnungen je Bestellposition kumulativ abgleichen; Mengen-, EUR- und prozentuale Preistoleranz einstellen. Vertragliche Prozentrabatte und historische Anomalien deterministisch berechnen. Potenzielle Belastung und Einsparungen sind keine bestätigten bezahlten Verluste. Korrektur bewahrt Original und ergänzt Version; Widerruf schließt Datensatz aus aktuellen Berichten und Lernen aus. Unabhängige Prüfung erforderlich.

### Lokale Sicherung und Wiederherstellung

Vor Umschaltung Dienst stoppen. Private vorhandene Verzeichnisse verwenden, SHA-256 separat aufbewahren und nur in neue Datei wiederherstellen. Einkaufsdatenbank enthält Originale, Versionen, Prüfwarteschlangen, Vorlagen; historische Signale werden rekonstruiert. Authentifizierung und Kerndatenbank separat sichern. Noch keine Verschlüsselung oder automatische Planung. Keine Geschäftsdaten auf GitHub.

```bash
python -m procurement_backup create --source /private/procurement.sqlite3 --destination /backup/snapshot.sqlite3 --tenant COMPANY_ID
python -m procurement_backup verify --source /backup/snapshot.sqlite3 --tenant COMPANY_ID --sha256 EXPECTED_HASH
python -m procurement_backup restore --source /backup/snapshot.sqlite3 --destination /recovery/recovered.sqlite3 --tenant COMPANY_ID --sha256 EXPECTED_HASH
```

### Nachweise und Grenzen

Synthetische Abnahme: 108 Tests, fünf Bilder (4/5 beim ersten Lesen, 5/5 nach simulierter Prüfung), 150 EUR dokumentierte potenzielle Belastung nach Wiederherstellung reproduziert. Leichte OCR: 52/52 Zellen in vier Tabellen, Mittel 2,15 s, gemessener Stichproben-Spitzenwert 94,8 MiB. Paddle: 24/24 Zellen in zwei Tabellen, Ressourcenanforderungen nicht erfüllt. Keine Produktionszertifizierung. Modernes Design, weitere Layouts, Verschlüsselung, Gesamtsicherung und Echtdatenvalidierung offen.

[CI — f9fd4a66](https://github.com/OscarMorelli78/Ledger64/actions/runs/45889543410) · [PR #2](https://github.com/OscarMorelli78/Ledger64/pull/2) · [CLI](../procurement-pilot.md) · [Backup](../procurement-data-resilience.md)

# Ledger64

**Aus jeder Rechnung lernen. Jede Entscheidung zählt.**

Open-Source-Rechnungsprüfung, Einkaufskostenvergleich und Finanz-Governance für KMU. C64-inspirierte Oberfläche; lokale Verarbeitung ohne externe KI.

[English](README.en.md) · [Español](README.es.md) · [Français](README.fr.md) · [Italiano](README.it.md) · [Deutsch](README.de.md) · [Português (Brasil)](README.pt-BR.md) · [简体中文](README.zh-CN.md) · [日本語](README.ja.md) · [हिन्दी](README.hi.md)

**Release-Kandidat: nur synthetische Daten verwenden. Keine Buchhaltungs- oder Steuerzertifizierung. Nur Einkäufe in EUR, keine Gutschriften. ALE ist experimentell und offline. Docker-Ausführung und Hosting erfordern unabhängige Abnahme.**

## Schnellstart

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


## Dokumentation

[Deutsch — Dokumentation](docs/manual/de.md) · [MIT](LICENSE) · [SECURITY](SECURITY.md)

### Eingabeformat

Mit synthetischer Demo beginnen. Standardvorlage mit elf Feldern unten, ISO-Datum JJJJ-MM-TT, Einheiten kg, l, ud (g und ml normalisiert), EUR ohne MwSt. Positive Menge, Netto + Versand − Rabatt. UTF-8-CSV, XLSX mit einem Blatt ohne Formeln, Makros oder externe Links, oder unterstütztes strukturiertes PDF. 2 MB je Datei, 10.000 Zeilen; Stapel 2–20 Dateien, 8 MB gesamt. Kein universeller Rechnungs- oder Steuerformularimport.

### Prüfung und Vergleich

Prüfung starten. Rechenabweichungen, mögliche Dubletten und Preissteigerungen ab 10 % prüfen. Konflikt-IDs und falsche Summen werden vom Vergleich ausgeschlossen. Identische Produkte und Einheiten mit jüngsten Beobachtungen innerhalb von 30 Tagen vergleichen. Einsparpotenzial ist keine realisierte oder bezahlte Einsparung. Monatskosten nur zulässige Zeilen.

### Governance

Gleichwertigkeiten oder angegebene Einsparungen mit Nachweisen und getrennten Basis-/Einkaufsreferenzen vorschlagen. Anderer Inhaber genehmigt oder lehnt ab, keine Selbstfreigabe. Normale Berichte sind Entwürfe. Freigabe echter (nicht synthetischer) Berichte mit bestandenem Rechencheck und unabhängigem Prüfer beantragen. Freigabe nur als JSON. Lokale Kette und Nachweise aufbewahren.

### Adaptives Lernen

ALE ist ein separates überwachtes Offline-Modul. Tests und synthetischen Stresstest unten ausführen. SQLite speichert Beobachtungen und Kandidaten; unabhängige Prüfung erforderlich, Mandanten und Echt-/Synthetikdaten getrennt. Kein automatisches Lernen aus Produktionsrechnungen, keine Änderung von Finanzregeln; keine autonomen Entscheidungen.

### Datenschutz und Sicherung

MIT gilt für Originalcode; Abhängigkeiten behalten ihre Lizenzen. Keine personenbezogenen Daten, Belege, Zugangsdaten, Backups, privaten Modellparameter oder Logs veröffentlichen. Authentifizierungs- und Unternehmensdatenbanken getrennt sichern, in neuen Mandanten wiederherstellen, Zugriff beschränken. Lokale Ketten ohne externe Verankerung. Schwachstellen privat melden.


## Community & professional services

[Commercial services](COMMERCIAL.md) · [Support](SUPPORT.md) · [Roadmap](ROADMAP.md) · [Contact](CONTACT.md) · [Contribute worldwide](COLLABORATORS.md)

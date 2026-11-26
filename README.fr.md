# Ledger64

**Apprenez de chaque facture. Donnez du sens à chaque décision.**

Audit de factures, comparaison des coûts d’achat et gouvernance financière open source pour les PME. Interface inspirée du C64, traitement local sans IA externe.

[English](README.en.md) · [Español](README.es.md) · [Français](README.fr.md) · [Italiano](README.it.md) · [Deutsch](README.de.md) · [Português (Brasil)](README.pt-BR.md) · [简体中文](README.zh-CN.md) · [日本語](README.ja.md) · [हिन्दी](README.hi.md)

**Version candidate : utilisez uniquement des données synthétiques. Aucune certification comptable ou fiscale. Achats en EUR uniquement, sans avoirs. ALE est expérimental et hors ligne. Docker et hébergement exigent une validation indépendante.**

## Démarrage rapide

Installez Python 3.13, Node.js pour les tests, Tesseract avec modèles anglais et espagnol, Pango et polices Noto pour les PDF. Créez un environnement virtuel et installez les dépendances figées. Sous Windows, utilisez PowerShell et `$env:`. Choisissez un répertoire privé ; n’exposez pas le serveur ancien `app.py`.

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


## Documentation

[Français — Documentation](docs/manual/fr.md) · [MIT](LICENSE) · [SECURITY](SECURITY.md)

### Format d’entrée

Commencez par la démo synthétique. Le modèle contient onze champs ci-dessous, date ISO AAAA-MM-JJ, unités kg, l, ud (g et ml normalisés), prix en EUR hors TVA. Quantité positive, total net + port − remise. CSV UTF-8, XLSX à une feuille sans formules, macros ni liens externes, ou PDF structuré compatible. 2 Mo par fichier, 10 000 lignes ; lots de 2 à 20 fichiers, 8 Mo au total. Pas d’import universel de factures ni de formulaires fiscaux.

### Audit et comparaison

Lancez l’audit. Vérifiez écarts arithmétiques, doublons possibles et hausses de prix d’au moins 10 %. Identifiants conflictuels et montants incohérents exclus des comparaisons. Comparez des produits identiques, même unité, observations les plus récentes dans les 30 jours. Économies potentielles, non réalisées ni payées. Totaux mensuels sur lignes admissibles.

### Gouvernance

Proposez équivalences de codes ou économies déclarées avec justificatifs et références distinctes. Un autre propriétaire approuve ou rejette ; pas d’auto-approbation. Les rapports ordinaires sont provisoires. Demandez la publication d’un rapport réel (non synthétique) avec contrôle arithmétique réussi et réviseur indépendant. Publication approuvée en JSON uniquement. Conservez chaîne locale et justificatifs.

### Apprentissage adaptatif

ALE est un module supervisé hors ligne. Lancez les tests et le stress synthétique ci-dessous. Il conserve observations et candidats en SQLite, exige révision indépendante et sépare entreprises et données réelles/synthétiques. Aucun apprentissage automatique sur les factures de production ni modification des règles financières ; pas de décisions autonomes.

### Confidentialité et sauvegardes

MIT couvre le code original ; dépendances sous leurs licences. Ne publiez ni identifiants, documents, secrets, sauvegardes, modèles privés ni journaux. Sauvegardez séparément les bases d’authentification et d’entreprise, restaurez vers une nouvelle entreprise et limitez l’accès. Chaînes locales sans ancrage externe. Signalez les vulnérabilités en privé.


## Community & professional services

[Commercial services](COMMERCIAL.md) · [Support](SUPPORT.md) · [Roadmap](ROADMAP.md) · [Contact](CONTACT.md) · [Contribute worldwide](COLLABORATORS.md)

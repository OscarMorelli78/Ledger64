# Ledger64 — Documentation (Français)

Audit de factures, comparaison des coûts d’achat et gouvernance financière open source pour les PME. Interface inspirée du C64, traitement local sans IA externe.

**Version candidate : utilisez uniquement des données synthétiques. Aucune certification comptable ou fiscale. Achats en EUR uniquement, sans avoirs. ALE est expérimental et hors ligne. Docker et hébergement exigent une validation indépendante.**

## 1. Installation

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

## 2. Comptes et rôles

Créez une entreprise et deux propriétaires distincts (ou un analyste et un propriétaire indépendant). La CLI demande des mots de passe d’au moins 14 caractères ; aucun identifiant par défaut. Connectez-vous et choisissez la langue. Lecteur : lecture seule ; analyste : proposition ; propriétaire : révision des demandes d’autrui.

## 3. Format d’entrée

Commencez par la démo synthétique. Le modèle contient onze champs ci-dessous, date ISO AAAA-MM-JJ, unités kg, l, ud (g et ml normalisés), prix en EUR hors TVA. Quantité positive, total net + port − remise. CSV UTF-8, XLSX à une feuille sans formules, macros ni liens externes, ou PDF structuré compatible. 2 Mo par fichier, 10 000 lignes ; lots de 2 à 20 fichiers, 8 Mo au total. Pas d’import universel de factures ni de formulaires fiscaux.

```csv
supplier,invoice,line,date,product,unit,quantity,net_eur,shipping_eur,discount_eur,reported_total_eur
DEMO,INV-001,1,2026-01-01,ITEM,kg,10,100,0,0,100
```

## 4. Audit et comparaison

Lancez l’audit. Vérifiez écarts arithmétiques, doublons possibles et hausses de prix d’au moins 10 %. Identifiants conflictuels et montants incohérents exclus des comparaisons. Comparez des produits identiques, même unité, observations les plus récentes dans les 30 jours. Économies potentielles, non réalisées ni payées. Totaux mensuels sur lignes admissibles.

## 5. Révision OCR

PDF numérisé : transcrivez jusqu’à cinq pages avec OCR anglais/espagnol ; vérifiez sur l’original et corrigez le CSV manuellement. Joignez le PDF, le CSV révisé et une justification de 10 à 1 000 caractères. Le texte OCR n’entre pas dans les calculs avant révision ; ce n’est pas une vérification indépendante.

## 6. Gouvernance

Proposez équivalences de codes ou économies déclarées avec justificatifs et références distinctes. Un autre propriétaire approuve ou rejette ; pas d’auto-approbation. Les rapports ordinaires sont provisoires. Demandez la publication d’un rapport réel (non synthétique) avec contrôle arithmétique réussi et réviseur indépendant. Publication approuvée en JSON uniquement. Conservez chaîne locale et justificatifs.

## 7. Intelligence documentaire

Dans Intelligence documentaire, soumettez des fichiers compatibles, classification réelle/synthétique, ID facultatif du modèle approuvé et justificatif. Le modèle JSON mappe les onze champs vers des en-têtes distincts, fournisseur, séparateur et booléen `spanish`. Un autre propriétaire contrôle les lignes normalisées ; modèles expirés ou révoqués inutilisables. Politique modifiée uniquement après approbation indépendante.

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
## 8. ROI documenté

Pour le ROI documenté, choisissez deux documents approuvés, lignes numérotées dès 1, même produit/unité et même classification. Achat ultérieur dans la fenêtre de politique (180 jours par défaut). Coût additionnel en chaîne décimale. Réduction brute = (prix unitaire de base − actuel) × quantité actuelle ; nette = brute − coût ; ROI % = nette / coût × 100, indéfini si coût nul. Ni paiement ni causalité prouvés. Révocations invalident le ROI lié.

## 9. Historique et exports

Consultez l’historique local et téléchargez PDF provisoire, JSON, alerts.csv ou comparisons.csv. La langue affecte l’affichage, pas les chiffres ou preuves stockés. PDF limité à 20 alertes et comparaisons ; détails CSV/JSON. Champs machine et texte source inchangés ; diagnostics non traduits conservent l’original espagnol.

## 10. Apprentissage adaptatif

ALE est un module supervisé hors ligne. Lancez les tests et le stress synthétique ci-dessous. Il conserve observations et candidats en SQLite, exige révision indépendante et sépare entreprises et données réelles/synthétiques. Aucun apprentissage automatique sur les factures de production ni modification des règles financières ; pas de décisions autonomes.

```bash
python -m unittest adaptive_learning.test_learning
python -m adaptive_learning.stress --out /tmp/ledger64-ale --seed 20261126
```
## 11. Déploiement

Démonstration HTTP uniquement sur boucle locale. Production : HTTPS, BC_ORIGIN et BC_HOSTS exacts, volume protégé persistant, tests de sauvegarde/restauration, validation conteneur et analyse de vulnérabilités. Compose, Caddy et Railway fournis ; ne publiez pas de données privées ni n’activez de services payants. Site marketing séparé ; métadonnées seulement pour URL HTTPS vérifiée.

```bash
docker compose config
docker compose build
# Only after acceptance and with BC_DOMAIN configured:
docker compose up -d
```
## 12. Confidentialité et sauvegardes

MIT couvre le code original ; dépendances sous leurs licences. Ne publiez ni identifiants, documents, secrets, sauvegardes, modèles privés ni journaux. Sauvegardez séparément les bases d’authentification et d’entreprise, restaurez vers une nouvelle entreprise et limitez l’accès. Chaînes locales sans ancrage externe. Signalez les vulnérabilités en privé.

```bash
python admin.py backup-auth /secure/auth-backup.sqlite3
python admin.py backup COMPANY_ID /secure/company-backup.sqlite3
python admin.py restore-new RECOVERY /secure/company-backup.sqlite3
```
## 13. Dépannage

Connexion : vérifiez hôte, origine, identifiants et limite d’essais. Import : modèle, types, devise, colonnes, dates, limites. OCR : Tesseract et modèles. PDF : Noto CJK, Devanagari et Pango. SQLite : permissions et espace libre ; ne contournez pas la gouvernance. Exécutez le diagnostic et transmettez un rapport anonymisé avec version, OS et reproduction.

```bash
python scripts/doctor.py
python scripts/check.py
```
[README](../../README.fr.md) · [SECURITY](../../SECURITY.md) · [LICENSE](../../LICENSE)

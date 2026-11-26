# Ledger64 — ドキュメント (日本語)

中小企業向けオープンソース請求書監査、購買コスト比較、財務ガバナンス。C64風UI、外部AIを使わないローカル処理。

**リリース候補：合成データのみ使用。会計・税務認証ではありません。EURの購買のみ、クレジットノート非対応。ALEは実験的なオフライン機能。Dockerとホスティングは独立した受入検証が必要。**

## 1. インストール

Python 3.13、テスト用Node.js、英語・スペイン語モデルのTesseract、PDF用PangoとNotoフォントをインストール。仮想環境を作成し固定依存関係を導入。WindowsはPowerShellと`$env:`を使用。非公開データディレクトリを設定し旧`app.py`を公開しないでください。

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

## 2. アカウントと権限

企業と異なる2名の所有者（または分析者と独立所有者）を作成。CLIで14文字以上のパスワードを入力。既定認証情報なし。ログインし言語選択。閲覧者は読み取りのみ、分析者は提案、所有者は他ユーザーの申請を確認できます。

## 3. 入力形式

合成デモから開始。標準テンプレートは下記11項目、日付ISO YYYY-MM-DD、単位kg、l、ud（g、mlを正規化）、価格はVAT抜きEUR。数量は正、合計は純額＋送料−割引。UTF-8 CSV、数式・マクロ・外部リンクのない単一シートXLSX、対応構造化PDF。1ファイル2 MB、10,000行、バッチ2～20ファイル・総8 MB。任意の請求書・税務書類には非対応。

```csv
supplier,invoice,line,date,product,unit,quantity,net_eur,shipping_eur,discount_eur,reported_total_eur
DEMO,INV-001,1,2026-01-01,ITEM,kg,10,100,0,0,100
```

## 4. 監査と比較

監査を実行し算術差異、重複候補、10%以上の価格上昇を確認。競合IDと不一致金額は比較対象外。同一商品・単位、30日以内の最新観測で比較。潜在削減額は支払済・実現済の削減ではありません。月次費用は対象行のみ。

## 5. OCR確認

スキャンPDFは英語・スペイン語OCRで最大5ページを文字起こしし原本照合、CSVを手動修正。原PDF、確認済CSV、10～1000文字の理由を提出。未確認OCRは計算に含めず、原本の独立検証でもありません。

## 6. ガバナンス

同等コードまたは申告削減額を証拠と異なる基準・購買参照で提案。別の所有者が承認または却下し自己承認は禁止。通常報告書は下書き。算術照合合格・独立確認者付きの実データ（非合成）報告書を公開申請。承認済公開はJSONのみ。ローカルチェーンと証拠を保持。

## 7. 文書インテリジェンス

文書インテリジェンスで対応ファイル、実/合成分類、任意の承認テンプレートID、証拠を提出。テンプレートJSONは11項目と異なる元ヘッダー、仕入先、区切り、数値形式boolean `spanish`。別の所有者が正規化行を確認。期限切れ・取消テンプレートは無効。ポリシー変更は独立承認。

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
## 8. 文書ROI

文書ROI：承認済文書2件と1始まりの行番号、同じ商品・単位・分類を選択。購入日は基準より後でポリシー期間内（既定180日）。増分コストは10進文字列。総削減＝（基準単価−現単価）×現数量、純削減＝総削減−コスト、ROI %＝純削減/コスト×100、コスト0は未定義。支払・因果関係の証明なし。取消は依存ROIを無効化。

## 9. 履歴と出力

ローカル履歴から下書きPDF、JSON、alerts.csv、comparisons.csvを取得。言語は表示のみで保存値・証拠は不変。PDFは警告・比較各20件まで、詳細CSV/JSON。機械項目・原文は維持し、未翻訳の診断はスペイン語原文を併記。

## 10. 適応学習

ALEは独立した教師ありオフラインモジュール。下記テストと合成ストレスを実行。SQLiteに観測・候補を保存し独立確認を要求、企業と実/合成データを分離。運用請求書から自動学習・財務規則変更はせず、自律判断に使わない。

```bash
python -m unittest adaptive_learning.test_learning
python -m adaptive_learning.stress --out /tmp/ledger64-ale --seed 20261126
```
## 11. デプロイ

HTTPデモはループバック限定。運用にはHTTPS、正しいBC_ORIGIN/BC_HOSTS、保護永続ボリューム、バックアップ復元テスト、コンテナ受入と脆弱性スキャンが必要。Compose、Caddy、Railway設定を提供。非公開データ公開や有料サービス起動禁止。宣伝サイトは独立、確認済HTTPS URLでメタデータ生成。

```bash
docker compose config
docker compose build
# Only after acceptance and with BC_DOMAIN configured:
docker compose up -d
```
## 12. プライバシーとバックアップ

MITは独自コードに適用、依存は各ライセンス。個人ID、企業文書、認証情報、バックアップ、非公開モデル、ログを公開しない。認証DBと企業DBを別々にバックアップ、新企業に復元、アクセス制限。ローカルチェーンに外部アンカーなし。脆弱性は非公開で報告。

```bash
python admin.py backup-auth /secure/auth-backup.sqlite3
python admin.py backup COMPANY_ID /secure/company-backup.sqlite3
python admin.py restore-new RECOVERY /secure/company-backup.sqlite3
```
## 13. トラブルシューティング

ログイン：ホスト、Origin、認証情報、試行制限。取込：テンプレート、型、通貨、列、日付、上限。OCR：Tesseractとモデル。PDF：Noto CJK、Devanagari、Pango。SQLite：権限・空き容量、ガバナンスを迂回しない。診断実行後、匿名化したバージョン、OS、再現手順を報告。

```bash
python scripts/doctor.py
python scripts/check.py
```
[README](../../README.ja.md) · [SECURITY](../../SECURITY.md) · [LICENSE](../../LICENSE)

## 14. 購買インテリジェンス — 実験パイロット

中小企業向け購買インテリジェンスエージェント。MITの決定論的コア、完全ローカル処理、人による監督付き学習を維持。Open Coreは商用戦略であり、有料拡張は未搭載。支払いは実行しません。

安定版v0.1.0ではなく実験ブランチを使用し、合成データのみ扱います。第1節に従い、分析担当者と別の所有者のアカウントを作成し、Uvicorn起動前に変数を設定。ログインして /procurement を開きます。既定では無効。GitHub Pagesは静的デモで、Pythonバックエンドではありません。

```bash
git clone -b feat/adaptive-procurement-v1 https://github.com/OscarMorelli78/Ledger64.git Ledger64-pilot
# Linux/macOS, before starting Uvicorn:
export BC_PROCUREMENT_PILOT=1
```
```powershell
$env:BC_PROCUREMENT_PILOT = "1"
```

http://127.0.0.1:8765/procurement

対応PDF、XLSX、CSV、JSON、PNG、JPG（最大2 MB）を入力。標準抽出はデジタルテキストとローカルOCRに対応。罫線付き画像には軽量グリッド、既知のラベル形式には複数読取比較を使用。小さな傾き（±5°）を補正しますが、罫線なしや任意文書は保証外。PaddleOCR/PP-Structureは任意の高負荷機能。試験済みQwenモデルは自動抽出の受入基準未達。OCRは英語・スペイン語。

各セルを確認し、種類・ID・供給元・日付・EURのメタデータを入力。正確な列見出しを標準フィールドに割り当て、不明値を推測しない。曖昧な識別子は代替読取を要求し原本と照合。証拠付き草案を提出し別の所有者が審査。参照一致は支払い許可ではありません。信頼済みCLIで供給元のCSV・表テンプレートを再利用する際は構造のみ、金額は再利用しません。

発注書・受領書・請求書を承認。部分納品と複数請求を発注明細単位で累積照合し、数量・EUR・価格割合の許容差を設定。契約割引率と履歴異常は決定論的に計算。潜在的な超過額や節約額は支払済損失の証明ではありません。訂正は原本を保持して版を追加、取消は現行報告・学習から除外。独立審査が必要です。

### ローカルバックアップと復元

稼働DB切替前にサービスを停止。既存の非公開ディレクトリを使用しSHA-256を別途保管、新規ファイルのみに復元します。購買DBは原本、版、審査キュー、テンプレートを含み履歴信号を再構築。認証DBと企業コアDBは個別バックアップが必要。暗号化・自動スケジュールは未対応。企業データをGitHubへ送らないでください。

```bash
python -m procurement_backup create --source /private/procurement.sqlite3 --destination /backup/snapshot.sqlite3 --tenant COMPANY_ID
python -m procurement_backup verify --source /backup/snapshot.sqlite3 --tenant COMPANY_ID --sha256 EXPECTED_HASH
python -m procurement_backup restore --source /backup/snapshot.sqlite3 --destination /recovery/recovered.sqlite3 --tenant COMPANY_ID --sha256 EXPECTED_HASH
```

### 証拠と制約

合成データ受入：108テスト、5画像の初回4/5、模擬審査後5/5、復元後も150 EURの潜在超過額を再現。軽量OCRは4表52/52セル、平均2.15秒、サンプル計測ピーク94.8 MiB。Paddleは2表24/24セル、資源目標未達。本番認証ではありません。現代風テーマ、多様な形式、暗号化、全体復元、実文書検証は未完了。

[CI — f9fd4a66](https://github.com/OscarMorelli78/Ledger64/actions/runs/45889543410) · [PR #2](https://github.com/OscarMorelli78/Ledger64/pull/2) · [CLI](../procurement-pilot.md) · [Backup](../procurement-data-resilience.md)

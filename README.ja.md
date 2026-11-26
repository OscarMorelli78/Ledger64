# Ledger64

**請求書から学び、すべての判断に価値を。**

中小企業向けオープンソース請求書監査、購買コスト比較、財務ガバナンス。C64風UI、外部AIを使わないローカル処理。

[English](README.en.md) · [Español](README.es.md) · [Français](README.fr.md) · [Italiano](README.it.md) · [Deutsch](README.de.md) · [Português (Brasil)](README.pt-BR.md) · [简体中文](README.zh-CN.md) · [日本語](README.ja.md) · [हिन्दी](README.hi.md)

**リリース候補：合成データのみ使用。会計・税務認証ではありません。EURの購買のみ、クレジットノート非対応。ALEは実験的なオフライン機能。Dockerとホスティングは独立した受入検証が必要。**

## クイックスタート

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


## ドキュメント

[日本語 — ドキュメント](docs/manual/ja.md) · [MIT](LICENSE) · [SECURITY](SECURITY.md)

### 入力形式

合成デモから開始。標準テンプレートは下記11項目、日付ISO YYYY-MM-DD、単位kg、l、ud（g、mlを正規化）、価格はVAT抜きEUR。数量は正、合計は純額＋送料−割引。UTF-8 CSV、数式・マクロ・外部リンクのない単一シートXLSX、対応構造化PDF。1ファイル2 MB、10,000行、バッチ2～20ファイル・総8 MB。任意の請求書・税務書類には非対応。

### 監査と比較

監査を実行し算術差異、重複候補、10%以上の価格上昇を確認。競合IDと不一致金額は比較対象外。同一商品・単位、30日以内の最新観測で比較。潜在削減額は支払済・実現済の削減ではありません。月次費用は対象行のみ。

### ガバナンス

同等コードまたは申告削減額を証拠と異なる基準・購買参照で提案。別の所有者が承認または却下し自己承認は禁止。通常報告書は下書き。算術照合合格・独立確認者付きの実データ（非合成）報告書を公開申請。承認済公開はJSONのみ。ローカルチェーンと証拠を保持。

### 適応学習

ALEは独立した教師ありオフラインモジュール。下記テストと合成ストレスを実行。SQLiteに観測・候補を保存し独立確認を要求、企業と実/合成データを分離。運用請求書から自動学習・財務規則変更はせず、自律判断に使わない。

### プライバシーとバックアップ

MITは独自コードに適用、依存は各ライセンス。個人ID、企業文書、認証情報、バックアップ、非公開モデル、ログを公開しない。認証DBと企業DBを別々にバックアップ、新企業に復元、アクセス制限。ローカルチェーンに外部アンカーなし。脆弱性は非公開で報告。


## Community & professional services

[Commercial services](COMMERCIAL.md) · [Support](SUPPORT.md) · [Roadmap](ROADMAP.md) · [Contact](CONTACT.md) · [Contribute worldwide](COLLABORATORS.md)

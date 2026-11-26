# Ledger64

**从每张发票学习，让每个决策都有价值。**

面向中小企业的开源发票审计、采购成本比较与财务治理工具。C64 风格界面，本地处理，无外部 AI。

[English](README.en.md) · [Español](README.es.md) · [Français](README.fr.md) · [Italiano](README.it.md) · [Deutsch](README.de.md) · [Português (Brasil)](README.pt-BR.md) · [简体中文](README.zh-CN.md) · [日本語](README.ja.md) · [हिन्दी](README.hi.md)

**候选版本：仅使用合成数据。不提供会计或税务认证。仅支持 EUR 采购，不支持贷项通知单。ALE 为离线实验模块。Docker 运行与托管部署须独立验收。**

## 快速开始

安装 Python 3.13、测试用 Node.js、带英语和西班牙语模型的 Tesseract、PDF 所需 Pango 与 Noto 字体。创建虚拟环境并安装固定版本依赖。Windows 使用 PowerShell 激活及 `$env:` 变量。设置私有数据目录，不对外暴露旧版 `app.py`。

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


## 文档

[简体中文 — 文档](docs/manual/zh-CN.md) · [MIT](LICENSE) · [SECURITY](SECURITY.md)

### 输入格式

先运行合成演示。标准模板含下列 11 个字段；日期 ISO YYYY-MM-DD，单位 kg、l、ud（g 和 ml 标准化），金额 EUR 不含增值税。数量为正，总额＝净额＋运费−折扣。支持 UTF-8 CSV、无公式/宏/外链的单工作表 XLSX 或兼容结构化 PDF。每文件 2 MB、10,000 行，批次 2–20 个文件且总计 8 MB。不承诺通用发票或税表导入。

### 审计与比较

执行审计，检查算术差异、可能重复、至少 10% 的涨价。冲突重复 ID 与不一致金额排除比较。仅比较相同产品及单位，使用 30 天内最新观察。潜在节省不等于已付款或实际节省。月度成本只含合格行。

### 治理

提交等价代码或申报节省额及证据，基准和采购引用不同。另一所有者批准或拒绝，禁止自我批准。普通报告为草稿。真实（非合成）报告需算术核验通过及独立复核者方可申请发布，已批准发布仅 JSON。保留本地链和证据。

### 自适应学习

ALE 为独立监督式离线模块。执行下方单元测试与合成压力测试。SQLite 保存观察与候选模型，需要独立复核并隔离企业及真实/合成数据。不自动学习生产上传发票或修改财务规则，不用于自主决策。

### 隐私与备份

MIT 适用于原创代码，依赖保留各自许可。勿提交个人标识、商业文档、凭据、备份、私有模型参数或日志。认证与企业数据库分别备份，恢复到新企业并限制访问。本地链无外部锚定。私下报告漏洞。


## Community & professional services

[Commercial services](COMMERCIAL.md) · [Support](SUPPORT.md) · [Roadmap](ROADMAP.md) · [Contact](CONTACT.md) · [Contribute worldwide](COLLABORATORS.md)

## 实验性采购智能

本地试点：三方核对、人工审核OCR、模板、更正及验证恢复。仅合成数据；参见手册新增章节。

[实验性采购智能](docs/manual/zh-CN.md) · [PR #2](https://github.com/OscarMorelli78/Ledger64/pull/2) · [CI](https://github.com/OscarMorelli78/Ledger64/actions/runs/45889543410)

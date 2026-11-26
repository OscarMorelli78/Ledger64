# Ledger64 — 文档 (简体中文)

面向中小企业的开源发票审计、采购成本比较与财务治理工具。C64 风格界面，本地处理，无外部 AI。

**候选版本：仅使用合成数据。不提供会计或税务认证。仅支持 EUR 采购，不支持贷项通知单。ALE 为离线实验模块。Docker 运行与托管部署须独立验收。**

## 1. 安装

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

## 2. 账户与角色

创建企业及两个不同所有者（或分析员与独立所有者）。CLI 提示输入至少 14 字符密码，无默认凭据。登录并选择语言。读取者只能读，分析员可提交，所有者可复核其他用户申请。

## 3. 输入格式

先运行合成演示。标准模板含下列 11 个字段；日期 ISO YYYY-MM-DD，单位 kg、l、ud（g 和 ml 标准化），金额 EUR 不含增值税。数量为正，总额＝净额＋运费−折扣。支持 UTF-8 CSV、无公式/宏/外链的单工作表 XLSX 或兼容结构化 PDF。每文件 2 MB、10,000 行，批次 2–20 个文件且总计 8 MB。不承诺通用发票或税表导入。

```csv
supplier,invoice,line,date,product,unit,quantity,net_eur,shipping_eur,discount_eur,reported_total_eur
DEMO,INV-001,1,2026-01-01,ITEM,kg,10,100,0,0,100
```

## 4. 审计与比较

执行审计，检查算术差异、可能重复、至少 10% 的涨价。冲突重复 ID 与不一致金额排除比较。仅比较相同产品及单位，使用 30 天内最新观察。潜在节省不等于已付款或实际节省。月度成本只含合格行。

## 5. OCR 复核

扫描 PDF：用英语/西语 OCR 转录最多五页；核对原件并人工修正 CSV。提交原始 PDF、复核 CSV 与 10–1000 字符理由。未经复核的 OCR 不进入计算；此流程不构成原件独立验证。

## 6. 治理

提交等价代码或申报节省额及证据，基准和采购引用不同。另一所有者批准或拒绝，禁止自我批准。普通报告为草稿。真实（非合成）报告需算术核验通过及独立复核者方可申请发布，已批准发布仅 JSON。保留本地链和证据。

## 7. 文档智能

文档智能中提交兼容文件、真实/合成分类、可选已批准模板 ID 及证据。模板 JSON 包含 11 个字段到各不同原始表头的映射、供应商、分隔符及数字格式布尔值 `spanish`。另一所有者检查标准化行并审批；过期或撤销模板无效。政策修改须独立批准。

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
## 8. 文档 ROI

文档 ROI：选择两个已批准文档、从 1 开始的行号、相同产品/单位和分类。采购晚于基准且在政策窗口内（默认 180 天）。增量成本用十进制字符串。毛节省＝（基准单价−当前单价）×当前数量；净节省＝毛节省−成本；ROI %＝净节省/成本×100，成本为零时未定义。不证明付款或因果关系。撤销使依赖 ROI 无效。

## 9. 历史及导出

打开本地历史并下载草稿 PDF、JSON、alerts.csv 或 comparisons.csv。语言只改变呈现，不改变已存数值或证据。PDF 最多摘要 20 条警报和比较，CSV/JSON 含详细信息。机器字段与原始文本不变；未翻译诊断保留西班牙语原文。

## 10. 自适应学习

ALE 为独立监督式离线模块。执行下方单元测试与合成压力测试。SQLite 保存观察与候选模型，需要独立复核并隔离企业及真实/合成数据。不自动学习生产上传发票或修改财务规则，不用于自主决策。

```bash
python -m unittest adaptive_learning.test_learning
python -m adaptive_learning.stress --out /tmp/ledger64-ale --seed 20261126
```
## 11. 部署

本地 HTTP 演示仅环回。生产需 HTTPS、正确 BC_ORIGIN 和 BC_HOSTS、受保护持久卷、备份恢复测试、容器验收和漏洞扫描。提供 Compose、Caddy、Railway 配置；不公开私有数据或启用收费服务。营销站独立，仅在确认 HTTPS URL 后生成元数据。

```bash
docker compose config
docker compose build
# Only after acceptance and with BC_DOMAIN configured:
docker compose up -d
```
## 12. 隐私与备份

MIT 适用于原创代码，依赖保留各自许可。勿提交个人标识、商业文档、凭据、备份、私有模型参数或日志。认证与企业数据库分别备份，恢复到新企业并限制访问。本地链无外部锚定。私下报告漏洞。

```bash
python admin.py backup-auth /secure/auth-backup.sqlite3
python admin.py backup COMPANY_ID /secure/company-backup.sqlite3
python admin.py restore-new RECOVERY /secure/company-backup.sqlite3
```
## 13. 故障排除

登录失败检查主机、来源、凭据、尝试限制。导入失败检查模板、类型、货币、列、日期及限制。OCR 检查 Tesseract 与模型。PDF 安装 Noto CJK、Devanagari 和 Pango。SQLite 检查权限与空间，不绕过治理。运行诊断，提交脱敏版本、操作系统和复现步骤。

```bash
python scripts/doctor.py
python scripts/check.py
```
[README](../../README.zh-CN.md) · [SECURITY](../../SECURITY.md) · [LICENSE](../../LICENSE)

## 14. 采购智能 — 实验性试点

面向中小企业的采购智能代理：保留 MIT 确定性核心，仅本地处理，人工监督学习。Open Core 为商业策略，尚不包含付费扩展。不执行付款。

使用实验分支而非稳定版 v0.1.0。仅使用合成数据。按第 1 节安装，创建不同的分析员和所有者账号，启动 Uvicorn 前设置变量，登录后打开 /procurement。默认关闭。GitHub Pages 是静态演示，不是 Python 后端。

```bash
git clone -b feat/adaptive-procurement-v1 https://github.com/OscarMorelli78/Ledger64.git Ledger64-pilot
# Linux/macOS, before starting Uvicorn:
export BC_PROCUREMENT_PILOT=1
```
```powershell
$env:BC_PROCUREMENT_PILOT = "1"
```

http://127.0.0.1:8765/procurement

上传兼容的 PDF、XLSX、CSV、JSON、PNG 或 JPG（最大 2 MB）。标准提取支持数字文本和本地 OCR；有边框的适用图像可使用轻量网格模式，已知标签布局可比较多次识别。支持小角度纠偏（±5°），不保证无边框或任意文档。PaddleOCR/PP-Structure 为可选高资源组件。已测试 Qwen 模型未通过自动提取验收。OCR 语言为英语和西班牙语。

逐格核对并输入元数据（类型、ID、供应商、日期、EUR）。将准确表头映射到规范字段，不推测缺失值。对模糊标识符请求备选识别结果，对照原件。提交附证据的草稿，由另一所有者审核。引用匹配不等于付款授权。可信 CLI 可复用供应商 CSV/表格模板，仅复用结构，不复用金额。

批准订单、收货单和发票。按订单行累计核对部分交付和多张发票；可设置数量、EUR 金额及价格百分比容差。确定性计算合同百分比折扣和历史异常。潜在风险及预计节省不代表已支付的确认损失。更正保留原件并追加版本；撤销使记录退出当前报告及学习。必须独立审核。

### 本地备份与恢复

切换活动数据库前停止服务。使用现有私有目录，单独保存 SHA-256，只恢复至新文件。采购库包含原件、版本、审核队列和模板，重建历史信号。认证及企业核心库另行备份。尚无加密和自动调度。切勿将企业数据上传 GitHub。

```bash
python -m procurement_backup create --source /private/procurement.sqlite3 --destination /backup/snapshot.sqlite3 --tenant COMPANY_ID
python -m procurement_backup verify --source /backup/snapshot.sqlite3 --tenant COMPANY_ID --sha256 EXPECTED_HASH
python -m procurement_backup restore --source /backup/snapshot.sqlite3 --destination /recovery/recovered.sqlite3 --tenant COMPANY_ID --sha256 EXPECTED_HASH
```

### 证据和限制

合成验收：108 项测试，五张图像首轮 4/5 正确、模拟审核后 5/5 正确，恢复后重现 150 EUR 文档风险金额。轻量 OCR：四张表格 52/52 单元格正确，平均 2.15 秒，采样峰值 94.8 MiB。Paddle：两张表格 24/24 单元格正确，资源目标未达成。并非生产认证。现代主题、更多布局、加密、完整恢复及真实文档验证待完成。

[CI — f9fd4a66](https://github.com/OscarMorelli78/Ledger64/actions/runs/45889543410) · [PR #2](https://github.com/OscarMorelli78/Ledger64/pull/2) · [CLI](../procurement-pilot.md) · [Backup](../procurement-data-resilience.md)

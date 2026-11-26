# Ledger64 — Documentação (Português (Brasil))

Auditoria de faturas, comparação de custos de compras e governança financeira de código aberto para PMEs. Interface inspirada no C64, processamento local sem IA externa.

**Versão candidata: use apenas dados sintéticos. Não certifica contabilidade ou tributos. Compras apenas em EUR, sem notas de crédito. ALE experimental e offline. Docker e hospedagem exigem aceitação independente.**

## 1. Instalação

Instale Python 3.13, Node.js para testes, Tesseract com modelos inglês e espanhol, Pango e fontes Noto para PDF. Crie ambiente virtual e instale dependências fixadas. No Windows use PowerShell e `$env:`. Defina diretório privado; não exponha o servidor legado `app.py`.

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

## 2. Contas e papéis

Crie empresa e dois proprietários distintos (ou analista e proprietário independente). A CLI solicita senhas de pelo menos 14 caracteres; sem credenciais padrão. Entre e escolha idioma. Leitores só leem; analistas propõem; proprietários revisam solicitações de outros.

## 3. Formato de entrada

Comece com demonstração sintética. Modelo com onze campos abaixo, data ISO AAAA-MM-DD, unidades kg, l, ud (g e ml normalizados), EUR sem IVA. Quantidade positiva, líquido + frete − desconto. CSV UTF-8, XLSX de uma planilha sem fórmulas, macros ou links externos, ou PDF estruturado compatível. 2 MB por arquivo, 10.000 linhas; lotes de 2–20 arquivos e 8 MB no total. Não há importação universal de faturas ou formulários fiscais.

```csv
supplier,invoice,line,date,product,unit,quantity,net_eur,shipping_eur,discount_eur,reported_total_eur
DEMO,INV-001,1,2026-01-01,ITEM,kg,10,100,0,0,100
```

## 4. Auditoria e comparação

Execute auditoria. Confira divergências aritméticas, duplicidades possíveis e aumentos de preço de pelo menos 10%. IDs conflitantes e valores inconsistentes são excluídos. Compare produtos idênticos, mesma unidade e observações recentes em 30 dias. Economia potencial não é paga nem realizada. Totais mensais apenas de linhas elegíveis.

## 5. Revisão OCR

PDF digitalizado: transcreva até cinco páginas com OCR inglês/espanhol, confira o original e corrija o CSV manualmente. Envie PDF, CSV revisado e justificativa de 10–1000 caracteres. Texto OCR não entra nos cálculos sem revisão; não constitui verificação independente do original.

## 6. Governança

Proponha equivalências ou economias declaradas com evidências e referências distintas de base/compra. Outro proprietário aprova ou rejeita; sem autoaprovação. Relatórios comuns são rascunhos. Solicite liberação de relatórios reais (não sintéticos), com conferência aritmética aprovada e revisor independente. Liberação aprovada apenas JSON. Preserve cadeia local e evidências.

## 7. Inteligência documental

Em Inteligência documental, envie arquivos compatíveis, classificação real/sintética, ID opcional do modelo aprovado e evidência. JSON do modelo: onze campos para cabeçalhos distintos, fornecedor, separador e booleano `spanish`. Outro proprietário verifica linhas normalizadas; modelos vencidos/revogados inválidos. Mudança de política exige aprovação independente.

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
## 8. ROI documentado

Para ROI documentado, escolha dois documentos aprovados e linhas a partir de 1, mesmo produto/unidade e classificação. Compra posterior à base dentro da janela da política (180 dias padrão). Custo incremental como string decimal. Redução bruta = (preço unitário base − atual) × quantidade atual; líquida = bruta − custo; ROI % = líquida / custo × 100, indefinido com custo zero. Não comprova pagamento ou causalidade. Revogações invalidam ROI dependente.

## 9. Histórico e exportações

Abra histórico local; baixe PDF rascunho, JSON, alerts.csv ou comparisons.csv. Idioma só afeta apresentação, não valores ou evidências armazenadas. PDF resume até 20 alertas e comparações; CSV/JSON detalhados. Campos máquina e texto fonte originais; diagnóstico sem tradução inclui original espanhol.

## 10. Aprendizado adaptativo

ALE é módulo supervisionado offline. Execute testes e estresse sintético abaixo. Guarda observações e candidatos em SQLite, exige revisão independente e separa empresas e dados reais/sintéticos. Não aprende automaticamente das faturas de produção nem altera regras; não o use como decisor autônomo.

```bash
python -m unittest adaptive_learning.test_learning
python -m adaptive_learning.stress --out /tmp/ledger64-ale --seed 20261126
```
## 11. Implantação

Demo HTTP local apenas loopback. Produção exige HTTPS, BC_ORIGIN e BC_HOSTS corretos, volume protegido persistente, testes de backup/restauração, aceitação de contêiner e análise de vulnerabilidades. Compose, Caddy e Railway fornecidos; não publique dados privados ou ative serviços pagos. Site de marketing separado; gere metadados só com URL HTTPS verificada.

```bash
docker compose config
docker compose build
# Only after acceptance and with BC_DOMAIN configured:
docker compose up -d
```
## 12. Privacidade e backups

MIT cobre código original; dependências mantêm licenças. Não publique identificadores, documentos, credenciais, backups, modelos privados ou logs. Faça backup separado da autenticação e das empresas, restaure em nova empresa e restrinja acesso. Cadeias locais sem ancoragem externa. Relate vulnerabilidades em privado.

```bash
python admin.py backup-auth /secure/auth-backup.sqlite3
python admin.py backup COMPANY_ID /secure/company-backup.sqlite3
python admin.py restore-new RECOVERY /secure/company-backup.sqlite3
```
## 13. Solução de problemas

Login: confira host, origem, credenciais e limites. Importação: modelo, tipos, moeda, colunas, datas e limites. OCR: Tesseract e modelos. PDF: Noto CJK, Devanagari e Pango. SQLite: permissões e espaço; não contorne governança. Execute diagnóstico e envie relato anonimizado com versão, SO e reprodução.

```bash
python scripts/doctor.py
python scripts/check.py
```
[README](../../README.pt-BR.md) · [SECURITY](../../SECURITY.md) · [LICENSE](../../LICENSE)

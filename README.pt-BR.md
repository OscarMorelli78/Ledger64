# Ledger64

**Aprenda com cada fatura. Faça cada decisão contar.**

Auditoria de faturas, comparação de custos de compras e governança financeira de código aberto para PMEs. Interface inspirada no C64, processamento local sem IA externa.

[English](README.en.md) · [Español](README.es.md) · [Français](README.fr.md) · [Italiano](README.it.md) · [Deutsch](README.de.md) · [Português (Brasil)](README.pt-BR.md) · [简体中文](README.zh-CN.md) · [日本語](README.ja.md) · [हिन्दी](README.hi.md)

**Versão candidata: use apenas dados sintéticos. Não certifica contabilidade ou tributos. Compras apenas em EUR, sem notas de crédito. ALE experimental e offline. Docker e hospedagem exigem aceitação independente.**

## Início rápido

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


## Documentação

[Português (Brasil) — Documentação](docs/manual/pt-BR.md) · [MIT](LICENSE) · [SECURITY](SECURITY.md)

### Formato de entrada

Comece com demonstração sintética. Modelo com onze campos abaixo, data ISO AAAA-MM-DD, unidades kg, l, ud (g e ml normalizados), EUR sem IVA. Quantidade positiva, líquido + frete − desconto. CSV UTF-8, XLSX de uma planilha sem fórmulas, macros ou links externos, ou PDF estruturado compatível. 2 MB por arquivo, 10.000 linhas; lotes de 2–20 arquivos e 8 MB no total. Não há importação universal de faturas ou formulários fiscais.

### Auditoria e comparação

Execute auditoria. Confira divergências aritméticas, duplicidades possíveis e aumentos de preço de pelo menos 10%. IDs conflitantes e valores inconsistentes são excluídos. Compare produtos idênticos, mesma unidade e observações recentes em 30 dias. Economia potencial não é paga nem realizada. Totais mensais apenas de linhas elegíveis.

### Governança

Proponha equivalências ou economias declaradas com evidências e referências distintas de base/compra. Outro proprietário aprova ou rejeita; sem autoaprovação. Relatórios comuns são rascunhos. Solicite liberação de relatórios reais (não sintéticos), com conferência aritmética aprovada e revisor independente. Liberação aprovada apenas JSON. Preserve cadeia local e evidências.

### Aprendizado adaptativo

ALE é módulo supervisionado offline. Execute testes e estresse sintético abaixo. Guarda observações e candidatos em SQLite, exige revisão independente e separa empresas e dados reais/sintéticos. Não aprende automaticamente das faturas de produção nem altera regras; não o use como decisor autônomo.

### Privacidade e backups

MIT cobre código original; dependências mantêm licenças. Não publique identificadores, documentos, credenciais, backups, modelos privados ou logs. Faça backup separado da autenticação e das empresas, restaure em nova empresa e restrinja acesso. Cadeias locais sem ancoragem externa. Relate vulnerabilidades em privado.


## Community & professional services

[Commercial services](COMMERCIAL.md) · [Support](SUPPORT.md) · [Roadmap](ROADMAP.md) · [Contact](CONTACT.md) · [Contribute worldwide](COLLABORATORS.md)

## Inteligência de compras experimental — branch separado

[Inteligência de compras experimental — branch separado](https://github.com/OscarMorelli78/Ledger64/blob/feat/adaptive-procurement-v1/docs/manual/pt-BR.md) · [Demo](https://oscarmorelli78.github.io/Ledger64/demo/procurement.html?lang=pt-BR) · [PR #2](https://github.com/OscarMorelli78/Ledger64/pull/2) · [CI](https://github.com/OscarMorelli78/Ledger64/actions/runs/45889543410)

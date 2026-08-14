# Prompt — Nova página exploratória: Arrecadação Federal (RFB)

> **Como usar:** cole este arquivo inteiro como prompt em uma sessão nova do Claude Code
> (modelo **Opus**), rodando na raiz do repo `DadosFinanceirosBancoCentral`. É independente
> do prompt da fonte 6 — rode em outra sessão/janela, em paralelo se quiser.

---

## Contexto (leia antes de agir)

Este é o projeto **Dados Financeiros Abertos (BCB)**. A fonte da verdade sobre organização,
pastas e etapas é **`CONTEXTO.md`** na raiz — **leia só as seções abaixo, não o arquivo
inteiro** (as demais seções tratam de outras fontes e não são relevantes para esta sessão):
- Seção 5 (estrutura de pastas) e Seção 6 (Etapas 0 a 7).
- Seção 7 (contrato tidy entre etapas: `ano_mes`, `forma_pagamento`, `quantidade`, `valor`).
- Seção 9 (convenções: slug, nomes de arquivo por fonte).

Da mesma forma, em `catalogo/fontes.md` leia apenas a seção `meios_pagamento_mensal` (fonte
de referência) — não precisa ler o catálogo inteiro nem `catalogo/fontes-candidatas.md` além
do item B1 já indicado abaixo.

Já existe uma fonte implementada de ponta a ponta (`meios_pagamento_mensal`) — use-a como
**modelo de referência** para código, nomenclatura e estilo (veja `src/config.py`,
`src/coleta/meios_pagamento.py`, `src/tratamento/`, `src/analise/`, `src/publicacao/`,
`run_pipeline.py` e `docs/index.html` + `docs/js/app.js`).

O levantamento de fontes candidatas está em `catalogo/fontes-candidatas.md`, item **B1 —
"Arrecadação das Receitas Federais — série histórica"** (RFB). Leia essa seção: fonte é
**nacional, sem recorte geográfico** (⚪), formato **XLSX** (não API), com série de 1970 a
2025 — a coleta aqui é diferente da fonte inicial (download de arquivo, não chamada REST).

## Objetivo desta sessão

Criar uma **nova página exploratória** (não mexer em `docs/index.html`) dedicada à
**Arrecadação Federal por tributo**, seguindo o pipeline completo (Etapas 1→7), com o
mesmo padrão de qualidade da fonte inicial.

- **Slug da fonte:** `arrecadacao_federal`
- **Tema:** valor arrecadado mensal por **tributo** (IRPF, IRPJ, IPI, IOF, COFINS,
  PIS/PASEP, CSLL, INSS/Previdência, Imposto de Importação etc.), nacional.
- **Nova página do dashboard:** `docs/arrecadacao-federal.html` (link cruzado com `index.html`).

## Passo a passo

### Etapa 1 — Confirmar a fonte e documentar
- Acesse a página do ReceitaData:
  `https://www.gov.br/receitafederal/pt-br/acesso-a-informacao/dados-abertos/receitadata/arrecadacao`
  e **confirme as URLs diretas** dos arquivos `.xlsx` ("Arrecadação das Receitas Federais —
  1970 a 1993" e "... 1994 a 2025" ou o intervalo vigente na data da coleta — os nomes de
  arquivo mudam de ano a ano, então valide o link atual antes de codar).
- Confirme o **layout das abas/colunas** do XLSX (linhas de cabeçalho, tributos como colunas
  ou linhas, se vem em valores correntes e/ou constantes) — isso muda o parser da Etapa 2/3.
- Note a licença **CC-BY-ND 3.0** — registre em `catalogo/fontes.md` (mesmo formato usado
  para a fonte inicial: URL, parâmetros/arquivo, colunas, unidades, periodicidade, licença).

### Etapa 2 — Coleta (`src/coleta/arrecadacao_federal.py`)
- Adicione a entrada `arrecadacao_federal` em `FONTES` (`src/config.py`) com a(s) URL(s)
  do(s) arquivo(s) XLSX.
- Diferente da fonte inicial (JSON via API), aqui a coleta é **download de arquivo binário**
  — salve o(s) XLSX bruto(s) em `dados/brutos/arrecadacao_federal/` (pasta, pois pode ser
  mais de um arquivo cobrindo períodos diferentes) e registre um envelope de metadados
  (`fonte`, `url`, `coletado_em`, `arquivos`) em JSON ao lado, para manter o padrão de
  rastreabilidade das outras coletas.
- Adicione `openpyxl` (ou equivalente) a `requirements.txt` se ainda não estiver presente.

### Etapa 3 — Tratamento (`src/tratamento/arrecadacao_federal.py`)
- Gere `dados/processados/arrecadacao_federal.csv` em formato tidy/long: uma linha por
  `ano_mes` × `tributo`, com coluna `valor` (preço corrente; se o XLSX trouxer valores
  constantes também, considere uma coluna extra `valor_constante` ou um arquivo separado —
  documente a decisão em `catalogo/fontes.md`).
- Como é fonte **nacional** (sem UF/município), **não** é preciso estender o contrato com
  colunas geográficas — reaproveite o padrão simples (`ano_mes`, `tributo`, `valor`).
- Trate nomes de tributo de forma consistente (evite variações de grafia entre os dois
  arquivos XLSX, já que cobrem períodos diferentes e podem ter nomenclatura levemente
  diferente).

### Etapa 4 — Análise (`src/analise/arrecadacao_federal.py`)
- Métricas mínimas: evolução da arrecadação total, participação (%) de cada tributo no
  total, variação anual (YoY), ranking dos tributos por volume arrecadado, e (se possível)
  deflação por IPCA para comparar poder de compra ao longo do tempo — reaproveitando o
  padrão descrito no catálogo (`catalogo/fontes-candidatas.md`, "Deflação: adotar IPCA").

### Etapa 5 — Publicação (`src/publicacao/arrecadacao_federal.py`)
- Gere `docs/dados/arrecadacao_federal.json` com bloco `meta` (fonte, url, gerado_em,
  unidades, período) — igual ao padrão da fonte inicial. Dado o histórico longo
  (1970→2025), considere permitir filtro de período no front (ver Etapa 6).

### Etapa 6 — Dashboard (`docs/arrecadacao-federal.html`)
- Nova página HTML (reaproveite `docs/css/estilo.css`; crie
  `docs/js/arrecadacao-federal.js` se o JS for específico, ou estenda `app.js` com funções
  isoladas por página).
- KPIs sugeridos: arrecadação total no período selecionado, tributo com maior participação,
  variação YoY da arrecadação total.
- Gráficos sugeridos (Chart.js): evolução da arrecadação total (linha, 1970→2025),
  participação por tributo (pizza/rosca ou barras empilhadas), ranking de tributos (barras).
- Adicione um link de navegação entre `index.html` e `arrecadacao-federal.html`.

### Etapa 7 — Registro
- Atualize `run_pipeline.py` (dicionário `PIPELINES`) para incluir `arrecadacao_federal`.
- Atualize o roadmap/status no `CONTEXTO.md` (seção 8 "Fontes de dados" e seção 11
  "Roadmap curto") e o `README.md` com a nova página.

## Critérios de aceite
- `python run_pipeline.py arrecadacao_federal` roda do início ao fim sem erro.
- Página nova abre localmente (`docs/arrecadacao-federal.html`) e renderiza os gráficos a
  partir do JSON publicado, sem depender de dados hardcoded.
- Nenhuma fonte existente (`meios_pagamento_mensal`) quebra — rode
  `python run_pipeline.py meios_pagamento_mensal --sem-coleta` para confirmar.
- `catalogo/fontes.md` e `CONTEXTO.md` refletem a fonte nova com status atualizado.

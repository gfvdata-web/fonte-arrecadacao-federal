# Dicionário de dados — `arrecadacao_federal`

> RFB · Arrecadação das Receitas Federais (série histórica). Etapa 1 do pipeline.
> Este arquivo documenta **apenas a fonte deste repositório**. A visão consolidada de todas
> as fontes do projeto vive no repositório `controle-global`.

- **Órgão:** Receita Federal do Brasil (RFB) — portal ReceitaData
- **Acesso:** download de arquivo (**XLSX**), não há API
- **Página da série:**
  https://www.gov.br/receitafederal/pt-br/acesso-a-informacao/dados-abertos/receitadata/arrecadacao/serie-historica
- **Arquivos (conferidos em jul/2026):**
  ```
  .../serie-historica/arrecadacao-das-receitas-federais-1970-a-1993.xlsx
  .../serie-historica/arrecadacao-das-receitas-federais-1994-a-2025.xlsx
  ```
  > O portal (Plone) linka os arquivos com o sufixo `/view`; o download direto é a URL
  > sem esse sufixo. O nome muda quando a RFB estende a série (`1994 a 2026`, etc.) —
  > por isso a Etapa 2 relê a página de listagem e descobre o arquivo vigente quando a
  > URL registrada em `src/config.py` falha.
- **Periodicidade:** mensal · **Geo:** ⚪ nacional (sem recorte por UF/município)
- **Licença:** CC-BY-ND 3.0 — Receita Federal do Brasil

## Layout do XLSX (formato original "wide" e hierárquico)

- **Uma aba por ano** (`1994`, `1995`, …, `2025`).
- Linhas 2–5: título, período, base de preços e **unidade monetária**.
- Linha 6: cabeçalho `RECEITAS | JAN | … | DEZ | TOTAL`.
- Linhas 7+: um tributo por linha; o **recuo do rótulo indica o nível** na hierarquia
  (0 espaços = tributo; 2–3 = abertura; 4 = sub-abertura).
- Valores a **preços correntes**, em **R$ milhões** (o arquivo não traz preços constantes).
- Os 38 rótulos são **idênticos** nos 32 anos — não há variação de grafia a conciliar.

## Recorte adotado e por quê

Só o arquivo **1994→2025** entra no pipeline. O de 1970–1993 é coletado (rastreabilidade)
mas **não é tratado**: mistura quatro padrões monetários (Cr$, Cz$, NCz$, CR$) entre as
abas e traz 1970–1985 em base **anual**, o que não forma série comparável nem mensal.

## Deflação

A Etapa 2 também baixa o **IPCA mensal** do BCB/SGS (série **433**) e a Etapa 3 gera um
número-índice para converter os valores correntes em **constantes do último mês da série**
(hoje dez/2025). É a convenção de deflação adotada no projeto.

```
https://api.bcb.gov.br/dados/serie/bcdata.sgs.433/dados?formato=json&dataInicial=01/12/1993
```

## Formato tidy após a Etapa 3

| Coluna | Descrição |
|--------|-----------|
| `ano_mes` | `YYYY-MM` |
| `tributo` | rótulo original do XLSX, sem recuo (chave da série) |
| `rotulo` | nome amigável para exibição (ex.: `IMPOSTO SOBRE A RENDA-TOTAL` → `Imposto de Renda`) |
| `tributo_pai` | tributo do nível acima (vazio no nível 1) |
| `nivel` | 1 = tributo, 2 = abertura, 3 = sub-abertura |
| `tipo` | `componente`, `detalhe` ou `agregado` (ver abaixo) |
| `valor` | R$ milhões **correntes** |
| `valor_constante` | R$ milhões **constantes** (IPCA, base = último mês) |

**`tipo` evita dupla contagem:**
- `componente` — as **15 linhas de nível 1** que somam exatamente o `TOTAL GERAL`
  (Imposto de Importação, Imposto de Exportação, IPI, Imposto de Renda, IOF, ITR, COFINS,
  PIS/PASEP, CSLL, CIDE-Combustíveis, FUNDAF, PSS, Outras receitas administradas,
  Receita previdenciária, Administradas por outros órgãos). Base das participações e do ranking.
- `detalhe` — aberturas dentro de um componente (IPI-Fumo, IRRF-Rendimentos do trabalho…).
- `agregado` — linhas somatórias do próprio XLSX (`SUBTOTAL [A]`,
  `ADMINISTRADAS PELA RFB [C]`, `TOTAL GERAL [E]`). A Etapa 3 confere, mês a mês, se os
  componentes fecham com o `TOTAL GERAL` publicado (tolerância de 0,1%).

> **Rótulos ambíguos:** `ENTIDADES FINANCEIRAS` e `DEMAIS EMPRESAS` aparecem dentro de IRPJ,
> COFINS, PIS/PASEP e CSLL. A Etapa 3 os qualifica com o tributo pai (`COFINS · ENTIDADES
> FINANCEIRAS`) para não colapsar quatro séries distintas em uma.

> **Observação:** a `RECEITA PREVIDENCIÁRIA` aparece **zerada em todo o ano de 1994** na
> publicação da RFB — é o dado de origem, mantido como está.

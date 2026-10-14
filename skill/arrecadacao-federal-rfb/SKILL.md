---
name: arrecadacao-federal-rfb
description: Analisa a série mensal oficial da Receita Federal sobre a arrecadação das receitas federais do Brasil — Imposto de Renda, Receita previdenciária, COFINS, PIS/PASEP, CSLL, IPI, IOF, Imposto de Importação e demais tributos, de jan/1994 a dez/2025, em valores correntes e constantes (IPCA). Baixa o dado tratado, evita as armadilhas da fonte (dupla contagem entre agregados e componentes, nominal contra real, série que para em 2025, previdenciária zerada em 1994) e situa os resultados nos marcos históricos (Plano Real, CPMF, pandemia, reforma tributária). Use sempre que o usuário perguntar sobre arrecadação federal, carga tributária federal, quanto rende um tributo, participação, sazonalidade ou crescimento real dos tributos federais, efeito da reforma tributária sobre PIS/Cofins, ou citar o painel "Arrecadação Federal", mesmo sem mencionar a Receita Federal.
---

# Arrecadação federal por tributo (Receita Federal)

Esta skill acompanha o painel **Quanto o Brasil arrecada**
(https://arrecadacaofederal.gfvdata.com/). A fonte é a série histórica de
arrecadação das receitas federais da Receita Federal do Brasil (dados abertos,
licença CC-BY-ND 3.0).

O dado é uma linha por mês e por rubrica, em R$ milhões. Os erros de análise vêm de
detalhes que não aparecem na tabela. O papel desta skill é evitar esses erros e
devolver ao usuário uma análise em que ele possa confiar.

## 1. Carregar os dados

Rode o script incluído. Ele baixa o CSV tratado publicado pelo projeto e grava só as
15 rubricas que somam o total (as `componente`):

```bash
python scripts/carregar_dados.py              # grava arrecadacao_federal.csv (componentes)
python scripts/carregar_dados.py --detalhes   # inclui também as aberturas (IRPF, IRPJ, IRRF...)
```

Ao terminar, imprime o período, o total do último ano e o ranking dos tributos. Leia
esse resumo antes de analisar.

**Se a rede estiver bloqueada**, o script sai com código 2. Nesse caso:
1. Se você tiver uma ferramenta de busca na web, abra
   `https://arrecadacaofederal.gfvdata.com/dados/arrecadacao_federal_mensal.csv`
   e salve o conteúdo num arquivo.
2. Se não der, peça ao usuário para baixar esse CSV pelo navegador e anexá-lo à conversa.
3. Depois rode `python scripts/carregar_dados.py --arquivo <caminho>`.

Não invente nem "lembre" números da série. Se não conseguir carregar os dados, diga isso.

### Colunas do arquivo gerado

| Coluna | Significado |
|---|---|
| `ano_mes` | `AAAA-MM` |
| `tributo` | rótulo amigável (Imposto de Renda, COFINS, IPI...) |
| `tipo` | `componente` (soma o total), `detalhe` (abertura de um componente) |
| `tributo_pai` | para `detalhe`, o componente a que pertence |
| `valor` | **R$ milhões correntes** (nominais) |
| `valor_constante` | **R$ milhões a preços de dez/2025** (IPCA, SGS 433) |

## 2. As armadilhas (leia antes de calcular)

1. **Dupla contagem.** O CSV completo do site traz agregados (SUBTOTAL, ADMINISTRADAS
   PELA RFB, TOTAL GERAL), componentes e detalhes. Somar tudo quase triplica o total.
   Qualquer soma, participação ou ranking usa **só `tipo == "componente"`** (o script já
   filtra, a menos que você peça `--detalhes`).
2. **Nominal engana.** De 1995 a 2025 a arrecadação nominal cresceu ~24×; a real, ~3,8×.
   Comparações entre anos distantes usam `valor_constante`; mostre o nominal ao lado só
   se ajudar.
3. **A série para em dez/2025.** A Receita consolida a série uma vez por ano; 2026 só
   existe nos relatórios mensais avulsos. Diga sempre "dados até dez/2025" e não trate a
   ausência de 2026 como queda.
4. **Receita previdenciária é zero em todo 1994.** É lacuna da fonte, não ausência de
   arrecadação. Exclua 1994 de taxas de crescimento da previdência e do total, ou avise.
5. **Sazonalidade.** O pico é janeiro (recolhe o apurado em dezembro), depois dezembro e
   outubro; o vale é fevereiro. Compare com o mesmo mês do ano anterior ou use 12 meses.
6. **Quebra de 2027.** PIS/PASEP e COFINS (~19,8% do total de 2025) deixam de existir e
   dão lugar à CBS. Quando a série ganhar 2027, a queda dessas linhas é mudança de regime,
   não colapso de receita.

Mais detalhes em `references/armadilhas.md`.

## 3. Como analisar

```python
import pandas as pd
df = pd.read_csv("arrecadacao_federal.csv")
comp = df[df["tipo"] == "componente"].copy()
comp["ano"] = comp["ano_mes"].str[:4].astype(int)

anual = comp.groupby(["ano", "tributo"])["valor_constante"].sum().unstack()
participacao = anual.div(anual.sum(axis=1), axis=0)          # % do total
cagr = (anual.loc[2025] / anual.loc[1995]) ** (1 / 30) - 1     # crescimento real a.a.
```

- Para "quem ganhou espaço", compare o crescimento real do tributo com o do total.
- Para explicar mudanças, consulte `references/eventos.md` (marcos com fonte). Cite um
  evento só quando a data bater com o que o dado mostra: "coincide com", não "causou".
- `references/achados.md` traz leituras já verificadas no projeto. **Recalcule** os
  números antes de citá-los.

## 4. Gráficos

- Participação: colunas ou área empilhada 100% por ano, os 6 maiores + "Demais".
- Evolução: soma anual ou acumulado de 12 meses em valores constantes; marque eventos
  como linhas verticais com rótulo curto.
- Nominal contra real em 30 anos: escala logarítmica.

## 5. Como entregar a resposta

- Comece pela resposta direta, com o número principal.
- Diga o período ("dados até dez/2025"), a unidade e se é corrente ou constante.
- Mencione numa linha a armadilha que a pergunta tocar.
- Termine com a fonte: *Fonte: Receita Federal do Brasil — Arrecadação das Receitas
  Federais (dados abertos, CC-BY-ND 3.0). Tratamento: painel Quanto o Brasil arrecada.*
- Escreva no idioma do usuário.

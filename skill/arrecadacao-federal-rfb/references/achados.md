# Achados já verificados

Leituras feitas no projeto com dados até dez/2025. Use como ponto de partida e **recalcule** os números com o dado carregado antes de citá-los.

## C1 — Metade da arrecadação está em dois tributos

*Pergunta:* Quão concentrada é a arrecadação federal, e a concentração mudou em 30 anos?

Medido em 2025: Imposto de Renda 31,7% e Receita previdenciária 25,2% somam 56,9% do total de R$ 2.887 bilhões. COFINS acrescenta 15,6%. Três rubricas explicam 72,5% de tudo. A pergunta interessante é a trajetória: a concentração aumentou desde 1994, e em favor de quem — do IR (progressivo) ou da previdência (folha)?

## C2 — Sazonalidade: janeiro, não dezembro

*Pergunta:* Qual é o padrão intra-anual da arrecadação?

Contra a intuição de varejo, o pico é janeiro (índice 122,3 com média 100), seguido de dezembro (119,3) e outubro (107,6); o vale é fevereiro (88,3). Janeiro recolhe o que foi apurado em dezembro, o que também explica por que uma leitura mês a mês sem ajuste sazonal atribui a janeiro um mérito que é de dezembro. Vale testar se o padrão é estável ao longo das três décadas ou se mudou com as regras de recolhimento.

## C3 — O buraco que a reforma vai abrir

*Pergunta:* Que fatia da arrecadação atual deixa de existir com o fim de PIS/PASEP e COFINS em 2027?

PIS/PASEP (4,2%) e COFINS (15,6%) somam 19,8% da arrecadação de 2025 — quase R$ 572 bilhões — e são substituídos pela CBS a partir de 1º/01/2027. A série vai registrar uma quebra estrutural, não uma queda de arrecadação. Este é o gráfico que precisa existir *antes* de 2027, para que a descontinuidade seja lida como mudança de regime e não como colapso de receita.

## C4 — Crescimento real por tributo

*Pergunta:* Quais tributos cresceram acima da inflação nas últimas três décadas, e quais encolheram?

O total real cresceu 3,8× de 1995 a 2025. Tributos que cresceram menos que isso perderam participação. O IPI é o candidato natural a encolhimento real (desindustrialização e desonerações sucessivas); o IR e a previdência, a ganho. Comparar CAGR real por tributo contra o CAGR real do total separa 'cresceu' de 'ganhou espaço'.

# Contexto externo

## Reforma tributária: fase de teste em 2026, CBS valendo em 2027

Em 2026 vigora uma alíquota-teste de 0,9% de CBS e 0,1% de IBS, meramente informativa e compensada na apuração de PIS/Cofins. Em 1º/01/2027 a CBS e o Imposto Seletivo passam a valer e PIS e Cofins deixam de existir. O IBS entra em transição a partir de 2029, com extinção de ICMS e ISS em 2033.

Por que importa: É a maior quebra estrutural que esta série vai sofrer desde que começou. Duas das quatro maiores rubricas somem do gráfico em 2027. Qualquer painel construído agora precisa estar preparado para representar isso.

Fonte: Câmara dos Deputados — https://www.camara.leg.br/noticias/1237089-reforma-tributaria-comeca-fase-de-transicao-com-testes-de-novos-impostos-em-2026/ (consultado em 2026-08-15)

## A série histórica da RFB só vai até 2025

A página de série histórica do ReceitaData oferecia, em 15/08/2026, apenas os arquivos 'arrecadacao-das-receitas-federais-1970-a-1993.xlsx' e '1994-a-2025.xlsx'. Não há arquivo consolidado de 2026.

Por que importa: Confirma que a defasagem é da origem. Fecha a dúvida de 'o pipeline está quebrado?' — não está; a RFB consolida a série anualmente.

Fonte: Receita Federal — ReceitaData, série histórica — https://www.gov.br/receitafederal/pt-br/acesso-a-informacao/dados-abertos/receitadata/arrecadacao/serie-historica (consultado em 2026-08-15)

## 2026 corrente é recorde real, mas fora desta série

A RFB registrou R$ 222,1 bilhões em fevereiro de 2026 (+5,68% real sobre fev/2025) e R$ 229,2 bilhões em março (+4,99% real), melhor resultado para o mês desde o início da série em 2000. O primeiro semestre de 2026 somou R$ 1,61 trilhão.

Por que importa: Dá ao painel um número de referência para o período que a série ainda não cobre — e mostra que a tendência de 2025 continuou, o que é relevante para não deixar o leitor concluir que a arrecadação parou em dez/2025.

Fonte: Ministério da Fazenda / Agência Brasil — https://www.gov.br/fazenda/pt-br/assuntos/noticias/2026/abril/arrecadacao-federal-atinge-r-229-2-bilhoes-em-marco-de-2026-melhor-resultado-para-o-mes-desde-2000 (consultado em 2026-08-15)

# Cruzamentos sugeridos com outras fontes

- **meios_pagamento_mensal** (chave `ano_mes`): Os picos de TED coincidem com os meses e datas de maior recolhimento? Se sim, parte do volume de TED é infraestrutura de arrecadação, e o split tributário do Pix (em desenvolvimento pelo BCB) tende a migrar esse fluxo. *Cuidado:* Esta série termina em dez/2025 e a de meios de pagamento vai até jun/2026 — recorte o período comum antes de comparar. Ambas em R$ milhões, mas esta tem versão deflacionada e a outra não.
- **credito_modalidade** (chave `ano_mes`): A arrecadação de IRPJ/CSLL de entidades financeiras acompanha o spread bancário? A hierarquia desta fonte isola justamente 'ENTIDADES FINANCEIRAS' dentro de IRPJ e CSLL. *Cuidado:* Arrecadação é fluxo mensal e crédito é estoque; e o lucro tributado tem defasagem em relação ao spread que o gerou. Espere correlação com lag, não contemporânea.

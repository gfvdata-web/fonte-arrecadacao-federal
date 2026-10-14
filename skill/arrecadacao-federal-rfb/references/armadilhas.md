# Armadilhas da série de arrecadação federal

Verificadas no projeto ao montar o painel. Impacto: alto/médio.

## Dupla contagem por `tipo` (impacto alto)

Somar todas as linhas do tidy infla o total: `agregado` (SUBTOTAL, ADMINISTRADAS PELA RFB, TOTAL GERAL) já contém `componente`, e `detalhe` já está dentro de `componente`. Qualquer soma, participação ou ranking precisa filtrar `tipo = 'componente'` — são as 15 linhas de nível 1 que somam o total geral, e o pipeline confere essa identidade nos 384 meses. Ignorar o filtro aproximadamente triplica o total.

## A série para em dez/2025 — e isso é a origem, não o pipeline (impacto alto)

Verificado na página da RFB em 15/08/2026: a série histórica só oferece os arquivos '1970 a 1993' e '1994 a 2025'. Não existe arquivo de 2026. A RFB publica os meses de 2026 apenas nos relatórios mensais de Análise da Arrecadação, em formato separado. Portanto o painel está estruturalmente 8 meses defasado e continuará assim até a RFB consolidar o ano — provavelmente só em 2027. Qualquer texto do painel que diga 'dados atualizados' precisa dizer até quando.

## Rótulo não é chave no bruto (impacto medio)

'ENTIDADES FINANCEIRAS' e 'DEMAIS EMPRESAS' aparecem três vezes cada na mesma aba, como abertura de três tributos pais diferentes. Qualquer análise feita direto sobre o XLSX, agrupando por rótulo, soma coisas que não são a mesma coisa. No tidy o problema já está resolvido pela coluna `tributo`, que é desambiguada — mas é uma armadilha real para quem baixar o arquivo da RFB e trabalhar nele.

## Nominal engana em 30 anos de série (impacto alto)

A série começa em 1994, meses depois do Plano Real. Em valores correntes, 1995 arrecadou R$ 119 bilhões e 2025 arrecadou R$ 2.887 bilhões — crescimento de 24×. Em valores constantes de dez/2025, os mesmos anos são R$ 772 bilhões e R$ 2.928 bilhões: crescimento de 3,8×. A diferença entre 24× e 3,8× é inflação. Use `valor_constante` em qualquer comparação que atravesse mais de dois ou três anos.

## Receita previdenciária zerada em 1994 (impacto alto)

Todos os meses de 1994 trazem 0 para a Receita previdenciária no XLSX da RFB. É lacuna da fonte. Taxas de crescimento do total ou da previdência que partam de 1994 ficam infladas; comece em 1995 ou avise.

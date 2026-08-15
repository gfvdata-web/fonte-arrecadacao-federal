# CONTEXTO — fonte `arrecadacao_federal`

> Arquivo-mestre de contexto **deste repositório**. Cole/aponte este arquivo ao abrir uma
> sessão sobre esta fonte. Ao pedir uma tarefa, cite a **Etapa** correspondente
> (ex.: "trabalhar na **Etapa 4**", "ajustar a **Etapa 6** sem quebrar a **Etapa 5**").
>
> A visão de todas as fontes do projeto (convenções comuns, catálogo de candidatas,
> roadmap global) vive no repositório **`controle-global`**. Aqui só o que é desta fonte.

---

## 1. O que este repositório faz

Coleta, trata, analisa e publica a série **RFB — Arrecadação das Receitas Federais
(série histórica)**: valor arrecadado mensal por tributo no Brasil, de 1994 em diante,
a preços correntes e constantes (deflacionados pelo IPCA).

- **Fonte:** Receita Federal do Brasil, portal ReceitaData — **download de XLSX, não há API**.
  Dicionário completo em [`catalogo/fonte.md`](catalogo/fonte.md).
- **Entrega:** dashboard estático em `docs/`, publicado via GitHub Pages.
- **Escopo:** uma fonte só. Nada aqui depende de outro repositório do projeto.

**Duas particularidades desta fonte:**
1. É a única do projeto por **download de arquivo** (XLSX com uma aba por ano, layout
   hierárquico por recuo de rótulo), não por API JSON.
2. Traz **deflação por IPCA** (BCB/SGS série 433) embutida no pipeline — a Etapa 2 baixa o
   IPCA junto e a Etapa 3 gera `valor_constante`.

## 2. Princípios de trabalho

- **Integração acima de tudo:** cada etapa tem contrato de entrada/saída definido (seção 5).
  Alterações devem respeitar esses contratos.
- **Não quebrar:** ao ajustar uma etapa, verificar as vizinhas (a que produz a entrada e a
  que consome a saída). `run_pipeline.py` deve continuar rodando de ponta a ponta.
- **Reprodutibilidade:** qualquer JSON publicado deve ser regenerável rodando o pipeline.
- **Idioma do código:** nomes de funções/variáveis e comentários em português.

## 3. Stack

| Camada | Tecnologia |
|--------|-----------|
| Coleta / tratamento / análise | Python 3.13 (`requests`, `pandas`, `openpyxl`) |
| Publicação de dados | JSON estático gerado pelo Python |
| Front-end / dashboard | HTML + CSS + JavaScript com Chart.js (via CDN) |
| Hospedagem | GitHub Pages (pasta `/docs`) |

> `openpyxl` é obrigatório aqui (leitura do XLSX) — é o que diferencia o
> `requirements.txt` deste repositório dos das fontes que consomem API JSON.

## 4. Estrutura de pastas

```
fonte-arrecadacao-federal/
├── CONTEXTO.md                 # este arquivo
├── README.md
├── requirements.txt
├── run_pipeline.py             # orquestra as Etapas 2→5
├── src/
│   ├── config.py               # caminhos + registro da fonte (rótulos, componentes, agregados)
│   ├── coleta/arrecadacao_federal.py       # Etapa 2 (XLSX + IPCA)
│   ├── tratamento/arrecadacao_federal.py   # Etapa 3 (tidy + deflação)
│   ├── analise/arrecadacao_federal.py      # Etapa 4
│   ├── perfil/arrecadacao_federal.py       # Etapa E (+ perfil/nucleo.py)
│   └── publicacao/arrecadacao_federal.py   # Etapa 5
├── dados/
│   ├── brutos/                 # XLSX baixados + IPCA (regeneráveis; fora do git)
│   └── processados/            # CSV tidy
├── docs/                       # Etapas 6 e E — site publicado
│   ├── explorar.html                   # Etapa E — perfil + pauta analitica
│   ├── js/explorar.js
│   ├── dados/perfil_arrecadacao_federal.json  # Etapa E (gerado)
│   ├── dados/notas_arrecadacao_federal.json   # Etapa E (a mao, nunca sobrescrito)
│   ├── index.html
│   ├── css/estilo.css
│   ├── js/app.js
│   └── dados/arrecadacao_federal.json
├── catalogo/fonte.md           # Etapa 1 — dicionário de dados
└── prompts/                    # prompt de abertura de sessão desta fonte
```

## 5. As Etapas e os contratos entre elas

```
[XLSX RFB + IPCA/SGS]  ──Etapa 2──▶  dados/brutos/arrecadacao_federal/
                                          │
                                     ──Etapa 3──▶  dados/processados/arrecadacao_federal.csv
                                          │
                     ┌────────────────────┴─────────────────┐
                ──Etapa 4──▶ métricas          ──Etapa 5──▶ docs/dados/arrecadacao_federal.json
                                                        │
                                                   ──Etapa 6──▶ docs/index.html

               ──Etapa E──▶  docs/dados/perfil_arrecadacao_federal.json  (gerado)
                             docs/dados/notas_arrecadacao_federal.json   (a mao)
                                     └──▶ docs/explorar.html

**Etapa E.** Roda depois da Etapa 3 e antes da 4. Perfila cinco tabelas (aba anual
representativa do XLSX, tidy, inventario das 41 abas, IPCA e hierarquia de tributos) e
mede os quatro joins entre elas. Especificacao completa no repositorio `controle-global`,
em `prompts/modelo-pagina-exploracao.md`. **A Etapa E so adiciona:** a unica alteracao em
arquivo existente foi o link "Explorar dados" na navegacao do `index.html`.
```

| Etapa | Nome | Código | Entrada → Saída | Status |
|-------|------|--------|-----------------|--------|
| 1 | Catálogo da fonte | `catalogo/fonte.md` | — → dicionário de dados | ✅ |
| 2 | Ingestão / coleta | `src/coleta/` | XLSX + IPCA → arquivos brutos | ✅ |
| 3 | Tratamento & modelagem | `src/tratamento/` | brutos → CSV tidy (+ deflação) | ✅ |
| 4 | Análise estatística | `src/analise/` | CSV tidy → métricas | ✅ |
| E | Exploração & pauta | `src/perfil/`, `docs/explorar.html` | bruto + tidy + auxiliares → perfil + pauta | ✅ |
| 5 | Publicação de dados | `src/publicacao/` | tidy + métricas → JSON do front | ✅ |
| 6 | Dashboard | `docs/` | JSON → site interativo | ✅ |
| 7 | Documentação & deploy | `README.md`, GitHub Pages | — → site no ar | 🟡 |

**Formato tidy (saída da Etapa 3):** `ano_mes`, `tributo`, `rotulo`, `tributo_pai`, `nivel`,
`tipo`, `valor`, `valor_constante`. Segue a anatomia comum do projeto — **dimensões em linha,
medidas em coluna**, com `ano_mes` sempre como primeira dimensão.

> A coluna `tipo` (`componente` / `detalhe` / `agregado`) é o que evita dupla contagem —
> qualquer soma, participação ou ranking deve filtrar por `tipo = componente`.
> Detalhes em [`catalogo/fonte.md`](catalogo/fonte.md).

## 6. Convenções

- **Slug da fonte:** `arrecadacao_federal` — reutilizado em `src/`, `dados/` e `docs/dados/`.
- **Datas:** período normalizado para string `YYYY-MM`.
- **JSON do front:** sempre com bloco `meta` (fonte, url, gerado_em, unidades, período).
- **Unidades:** R$ milhões correntes (`valor`) e R$ milhões constantes (`valor_constante`,
  IPCA com base no último mês da série).

## 7. Como referenciar as etapas nos prompts

- "Melhorar as métricas da **Etapa 4** (adicionar sazonalidade), atualizando a **Etapa 5**."
- "Redesenhar o dashboard da **Etapa 6** sem alterar o contrato de dados da **Etapa 5**."
- Sempre que uma mudança afetar o contrato da seção 5, avise para eu ajustar as etapas vizinhas.

## 8. Roadmap curto

- [ ] Etapa 2: acompanhar a virada do arquivo da RFB (`1994 a 2025` → `1994 a 2026`) — o
      fallback pela página de listagem já cobre, mas vale conferir na primeira virada.
- [ ] Etapa 3: avaliar extrair o deflator IPCA como utilitário reaproveitável, caso outra
      fonte do projeto passe a precisar dele.
- [ ] Etapa 4: sazonalidade, médias móveis, testes de tendência.
- [ ] Etapa 7: automação de atualização agendada e melhorias de acessibilidade.

# Arrecadação Federal por Tributo — RFB

Pipeline e dashboard da série **RFB — Arrecadação das Receitas Federais (série histórica)**:
valor arrecadado mensal por tributo no Brasil de 1994 em diante, a preços correntes e
constantes (deflacionados pelo IPCA), a partir dos arquivos XLSX do portal ReceitaData.

**Painel publicado:** https://gfvdata-web.github.io/fonte-arrecadacao-federal/
**Explorar os dados (Etapa E):** https://gfvdata-web.github.io/fonte-arrecadacao-federal/explorar.html

> 📄 Organização do repositório e etapas do pipeline: **[CONTEXTO.md](CONTEXTO.md)**
> 📚 Dicionário de dados da fonte: **[catalogo/fonte.md](catalogo/fonte.md)**
> 🌐 Visão de todas as fontes do projeto: repositório **`controle-global`**

## Como rodar

```bash
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python run_pipeline.py
```

O pipeline executa Etapa 2 (download dos XLSX + IPCA) → Etapa 3 (tratamento e deflação) →
Etapa 5 (publicação) e grava o JSON que o dashboard consome em `docs/dados/`.

`python run_pipeline.py --sem-coleta` reaproveita os arquivos já baixados.

> **`openpyxl` é obrigatório** neste repositório — é a dependência que lê o XLSX da RFB.

Para ver o dashboard localmente:

```bash
python -m http.server 8000 --directory docs
```

> **Etapa E.** `python run_pipeline.py --sem-perfil` pula a perfilagem.
> `docs/dados/notas_arrecadacao_federal.json` é **escrito à mão** e nenhum script o sobrescreve:
> é onde ficam as armadilhas, os comparativos, o contexto externo pesquisado e a pauta
> de visualizações que alimentam a página `explorar.html`.

## Estrutura

| Pasta | Etapa | Papel |
|-------|-------|-------|
| `catalogo/` | 1 | Dicionário de dados da fonte |
| `src/coleta/` | 2 | Download dos XLSX + IPCA → `dados/brutos/` |
| `src/tratamento/` | 3 | Tidy + deflação → `dados/processados/` |
| `src/analise/` | 4 | Estatística e métricas |
| `src/perfil/` | E | Perfil das tabelas → `docs/dados/perfil_*.json` |
| `src/publicacao/` | 5 | JSON → `docs/dados/` |
| `docs/index.html` | 6 | Dashboard (site publicado) |
| `docs/explorar.html` | E | Perfil das tabelas + pauta analítica |
| `prompts/` | — | Prompt de abertura de sessão desta fonte |

## Licença dos dados

CC-BY-ND 3.0 — Receita Federal do Brasil. O IPCA usado na deflação vem do BCB/SGS (série 433).
Detalhes em [`catalogo/fonte.md`](catalogo/fonte.md).

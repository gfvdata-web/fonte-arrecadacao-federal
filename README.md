# Arrecadação Federal por Tributo — RFB

Pipeline e dashboard da série **RFB — Arrecadação das Receitas Federais (série histórica)**:
valor arrecadado mensal por tributo no Brasil de 1994 em diante, a preços correntes e
constantes (deflacionados pelo IPCA), a partir dos arquivos XLSX do portal ReceitaData.

**Painel publicado:** https://arrecadacaofederal.gfvdata.com/ (Worker de estáticos na Cloudflare)
**Skill do Claude:** https://arrecadacaofederal.gfvdata.com/skill.html
**Versão anterior (V1, só para consulta, sem link a partir da V2):** https://arrecadacaofederal.gfvdata.com/v1/ — inclui `v1/explorar.html` (Etapa E)

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
Etapa 5 (publicação) e grava o JSON que o dashboard consome em `docs/dados/`, o CSV público
`docs/dados/arrecadacao_federal_mensal.csv` e o zip da skill em `docs/skill/`.

`python run_pipeline.py --sem-coleta` reaproveita os arquivos já baixados.

> **`openpyxl` é obrigatório** neste repositório — é a dependência que lê o XLSX da RFB.

Para ver o dashboard localmente:

```bash
python -m http.server 8000 --directory docs
```

> **Etapa E.** `python run_pipeline.py --sem-perfil` pula a perfilagem.
> `docs/dados/notas_arrecadacao_federal.json` é **escrito à mão** e nenhum script o sobrescreve:
> é onde ficam as armadilhas, os comparativos, o contexto externo pesquisado e a pauta
> de visualizações que alimentam a página `v1/explorar.html`.
> `docs/dados/eventos_arrecadacao_federal.json` também é **escrito à mão**: são os marcos
> (com fonte) mostrados na linha do tempo da V2 e copiados para a skill.

## Estrutura

| Pasta | Etapa | Papel |
|-------|-------|-------|
| `catalogo/` | 1 | Dicionário de dados da fonte |
| `src/coleta/` | 2 | Download dos XLSX + IPCA → `dados/brutos/` |
| `src/tratamento/` | 3 | Tidy + deflação → `dados/processados/` |
| `src/analise/` | 4 | Estatística e métricas |
| `src/perfil/` | E | Perfil das tabelas → `docs/dados/perfil_*.json` |
| `src/publicacao/` | 5 | JSON → `docs/dados/` |
| `docs/index.html` | 6 | Painel V2 (oficial): narrativa + marcos |
| `docs/skill.html` | 6 | Download e instalação da skill do Claude |
| `docs/v1/` | 6/E | V1 arquivada (`index.html`, `explorar.html`) |
| `skill/arrecadacao-federal-rfb/` | 5 | Fonte da skill (empacotada por `src/publicacao/skill.py`) |
| `wrangler.jsonc` | 7 | Worker de estáticos `arrecadacao-federal` (serve `docs/`) |
| `prompts/` | — | Prompt de abertura de sessão desta fonte |

## Deploy

Push para `main` → `.github/workflows/deploy.yml` roda `wrangler deploy` (secret
`CLOUDFLARE_API_TOKEN`) e publica `docs/` em https://arrecadacaofederal.gfvdata.com/.

## Licença dos dados

CC-BY-ND 3.0 — Receita Federal do Brasil. O IPCA usado na deflação vem do BCB/SGS (série 433).
Detalhes em [`catalogo/fonte.md`](catalogo/fonte.md).

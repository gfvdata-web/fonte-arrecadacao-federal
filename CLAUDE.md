# CLAUDE.md — fonte-arrecadacao-federal

Contexto, regras e mapa do projeto: [CONTEXTO.md](CONTEXTO.md) (ler antes de mexer).

- **V2 é a oficial** (`docs/index.html`, `js/app-v2.js`, `css/estilo-v2.css`, `skill.html`).
  A V1 fica em `docs/v1/` só para consulta: não linkar a partir da V2.
- `docs/dados/notas_*.json` e `docs/dados/eventos_*.json` são escritos à mão; nenhum script os toca.
  Ao mudar eventos ou a skill, rode `python -m src.publicacao.skill` para regenerar o zip.
- Funcionalidade nova ou alterada entra com teste no `scripts/check`/`tests/` no mesmo commit. Rodar `bash scripts/check` antes de commitar (o `.githooks/pre-commit` faz isso).
- Push só com pedido do usuário.

Deploy: automático no push para `main` (`.github/workflows/deploy.yml` → `wrangler deploy` do Worker
de estáticos `arrecadacao-federal`, secret `CLOUDFLARE_API_TOKEN` → https://arrecadacaofederal.gfvdata.com/).
Nada a rodar à mão; depois do push, conferir o site no ar (agente `site-checker`).

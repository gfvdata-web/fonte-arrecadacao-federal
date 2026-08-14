"""Etapa 5 — Publicação da fonte RFB: Arrecadação das Receitas Federais.

Reúne a saída da análise (Etapa 4) com metadados da fonte e grava um JSON
compacto em ``docs/dados/arrecadacao_federal.json``, consumido pela página
``docs/arrecadacao-federal.html`` (Etapa 6).
"""
from __future__ import annotations

import json
from datetime import datetime, timezone

from src import config
from src.analise import arrecadacao_federal as analise

SLUG = "arrecadacao_federal"


def publicar(slug: str = SLUG) -> dict:
    """Monta o pacote final e grava o JSON em docs/dados/. Retorna o pacote."""
    config.garantir_pastas()
    cfg = config.fonte(slug)
    resultado = analise.analisar(slug)

    pacote = {
        "meta": {
            "fonte": cfg["nome"],
            "descricao": cfg["descricao"],
            "url": cfg["url"],
            "arquivos": [a["nome"] for a in cfg["arquivos"]],
            "unidades": cfg["unidades"],
            "periodicidade": cfg["periodicidade"],
            "licenca": cfg["licenca"],
            "deflator": "IPCA — BCB/SGS série 433",
            "mes_base_constante": resultado["labels"][-1],
            "gerado_em": datetime.now(timezone.utc).isoformat(),
            "periodo": {
                "inicio": resultado["labels"][0],
                "fim": resultado["labels"][-1],
            },
        },
        **resultado,
    }

    destino = config.DIR_PUBLICADOS / f"{slug}.json"
    destino.write_text(json.dumps(pacote, ensure_ascii=False, indent=2), encoding="utf-8")
    tamanho = destino.stat().st_size / 1024
    print(f"[publicacao] JSON do dashboard salvo em {destino} ({tamanho:.0f} KB)")
    return pacote


if __name__ == "__main__":
    publicar()

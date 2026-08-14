"""Etapa 2 — Coleta da fonte RFB: Arrecadação das Receitas Federais.

Diferente da fonte inicial (JSON via API), aqui a coleta é **download de arquivos
binários** (XLSX do portal ReceitaData). Os arquivos vão para a pasta
``dados/brutos/arrecadacao_federal/`` junto com:

- ``ipca_sgs433.json`` — IPCA mensal (BCB/SGS série 433), usado na Etapa 3 para
  deflacionar os valores correntes;
- ``_metadados.json`` — envelope de rastreabilidade (fonte, url, coletado_em,
  arquivos), no mesmo espírito do envelope das coletas via API.

Os nomes dos XLSX mudam de ano a ano ("1994 a 2025" → "1994 a 2026"). Quando a URL
registrada em ``config`` retorna 404, a coleta descobre o arquivo vigente lendo a
página de listagem da série histórica.
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path

import requests

from src import config

SLUG = "arrecadacao_federal"

# Nome dos XLSX da série histórica: "...-<inicio>-a-<fim>.xlsx".
PADRAO_ARQUIVO = re.compile(
    r"arrecadacao-das-receitas-federais-(\d{4})-a-(\d{4})\.xlsx", re.IGNORECASE
)


def _descobrir_urls(url_listagem: str, timeout: int) -> dict[tuple[str, str], str]:
    """Lê a página da série histórica e devolve {(ano_ini, ano_fim): url do xlsx}."""
    resposta = requests.get(url_listagem, timeout=timeout)
    resposta.raise_for_status()
    encontrados: dict[tuple[str, str], str] = {}
    for href in re.findall(r'href="([^"]+)"', resposta.text):
        achado = PADRAO_ARQUIVO.search(href)
        if not achado:
            continue
        # O portal (Plone) publica o link como ".../arquivo.xlsx/view"; o download
        # direto é a própria URL do arquivo, sem o sufixo.
        url = href.split("/view")[0]
        if url.startswith("/"):
            url = "https://www.gov.br" + url
        encontrados[achado.groups()] = url
    return encontrados


def _baixar(url: str, destino: Path, timeout: int) -> int:
    """Baixa um arquivo binário e devolve o tamanho em bytes."""
    resposta = requests.get(url, timeout=timeout)
    resposta.raise_for_status()
    destino.write_bytes(resposta.content)
    return len(resposta.content)


def _url_substituta(nome: str, catalogo: dict, url_listagem: str) -> str:
    """Procura na listagem um XLSX com o mesmo ano inicial do arquivo registrado."""
    achado = PADRAO_ARQUIVO.search(nome)
    ano_inicial = achado.group(1) if achado else None
    for (ini, _fim), url in sorted(catalogo.items()):
        if ini == ano_inicial:
            return url
    raise FileNotFoundError(
        f"XLSX '{nome}' indisponível e sem substituto na listagem {url_listagem}. "
        "Atualize FONTES em src/config.py."
    )


def coletar(slug: str = SLUG, timeout: int = 180) -> dict:
    """Baixa os XLSX e o IPCA, grava o envelope de metadados e o retorna."""
    config.garantir_pastas()
    cfg = config.fonte(slug)
    pasta = config.DIR_BRUTOS / slug
    pasta.mkdir(parents=True, exist_ok=True)

    print(f"[coleta] consultando: {cfg['nome']}")
    catalogo: dict | None = None
    arquivos: list[dict] = []
    for arquivo in cfg["arquivos"]:
        url = arquivo["url"]
        nome = url.rsplit("/", 1)[-1]
        try:
            bytes_baixados = _baixar(url, pasta / nome, timeout)
        except requests.HTTPError as erro:
            # Os nomes mudam quando a RFB estende a série: procura o vigente.
            print(f"[coleta] {nome} indisponível ({erro.response.status_code}); "
                  "consultando a listagem da série histórica")
            if catalogo is None:
                catalogo = _descobrir_urls(cfg["url"], timeout)
            url = _url_substituta(arquivo["nome"], catalogo, cfg["url"])
            nome = url.rsplit("/", 1)[-1]
            bytes_baixados = _baixar(url, pasta / nome, timeout)
        arquivos.append({
            "nome": nome,
            "url": url,
            "bytes": bytes_baixados,
            "tratar": arquivo.get("tratar", True),
        })
        print(f"[coleta] {nome} — {bytes_baixados / 1024:.0f} KB")

    # IPCA (SGS 433) para a deflação da Etapa 3.
    resposta = requests.get(cfg["url_ipca"], timeout=timeout)
    resposta.raise_for_status()
    ipca = resposta.json()
    (pasta / "ipca_sgs433.json").write_text(
        json.dumps(ipca, ensure_ascii=False), encoding="utf-8"
    )
    print(f"[coleta] IPCA (SGS 433): {len(ipca)} meses")

    envelope = {
        "fonte": cfg["nome"],
        "url": cfg["url"],
        "coletado_em": datetime.now(timezone.utc).isoformat(),
        "arquivos": arquivos,
        "ipca": {"url": cfg["url_ipca"], "arquivo": "ipca_sgs433.json", "meses": len(ipca)},
    }
    destino = pasta / "_metadados.json"
    destino.write_text(json.dumps(envelope, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[coleta] metadados salvos em {destino}")
    return envelope


if __name__ == "__main__":
    coletar()

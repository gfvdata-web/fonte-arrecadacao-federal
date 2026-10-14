"""Carrega a série RFB de Arrecadação Federal (mensal) em formato tidy, pronta para análise.

Só usa a biblioteca padrão do Python, para rodar em qualquer ambiente.

Origem: CSV tratado publicado pelo projeto (arrecadacaofederal.gfvdata.com). A Receita
publica a série só em XLSX com várias abas e linhas somatórias; o CSV do site já vem
desempilhado, com rótulos amigáveis e a versão deflacionada pelo IPCA.
Se o download falhar, o script sai com código 2 — peça o CSV ao usuário e rode de novo
com --arquivo.

Saída: CSV com as colunas
  ano_mes, tributo, tipo, tributo_pai, valor, valor_constante

Uso:
  python carregar_dados.py                       # componentes, grava arrecadacao_federal.csv
  python carregar_dados.py --detalhes            # + aberturas (IRPF, IRPJ, IRRF...)
  python carregar_dados.py --arquivo anexo.csv   # usa um arquivo enviado pelo usuário
"""
from __future__ import annotations

import argparse
import csv
import io
import sys
import urllib.request
from collections import defaultdict
from pathlib import Path

URL_SITE = "https://arrecadacaofederal.gfvdata.com/dados/arrecadacao_federal_mensal.csv"
CABECALHO_UA = {"User-Agent": "skill-arrecadacao-federal-rfb/1.0"}
COLUNAS = ["ano_mes", "tributo", "tipo", "tributo_pai", "valor", "valor_constante"]


def _baixar(url: str, timeout: int = 60) -> bytes:
    req = urllib.request.Request(url, headers=CABECALHO_UA)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


def _ler(texto: str) -> list[dict]:
    """Lê o CSV do projeto (colunas ano_mes,tributo,rotulo,tributo_pai,nivel,tipo,valor,valor_constante)."""
    linhas = list(csv.DictReader(io.StringIO(texto.lstrip("﻿"))))
    if not linhas:
        raise ValueError("CSV vazio.")
    faltam = {"ano_mes", "tributo", "tipo", "valor", "valor_constante"} - set(linhas[0])
    if faltam:
        raise ValueError(f"Formato de CSV não reconhecido; faltam colunas {sorted(faltam)}")
    # O CSV do site traz o nome cru da RFB em `tributo` e o amigável em `rotulo`.
    rotulos = {l["tributo"]: (l.get("rotulo") or l["tributo"]) for l in linhas}
    return [{
        "ano_mes": l["ano_mes"],
        "tributo": rotulos[l["tributo"]],
        "tipo": l["tipo"],
        "tributo_pai": rotulos.get(l.get("tributo_pai") or "", l.get("tributo_pai") or ""),
        "valor": float(l["valor"] or 0),
        "valor_constante": float(l["valor_constante"] or 0),
    } for l in linhas]


def carregar(arquivo: str | None) -> tuple[list[dict], str]:
    if arquivo:
        caminho = Path(arquivo)
        if not caminho.is_file():
            print(f"Arquivo não encontrado: {caminho}", file=sys.stderr)
            sys.exit(1)
        return _ler(caminho.read_text(encoding="utf-8")), f"arquivo {caminho.name}"
    try:
        return _ler(_baixar(URL_SITE).decode("utf-8")), f"site do projeto ({URL_SITE})"
    except Exception as exc:  # rede bloqueada, timeout, formato inesperado
        print(f"Não foi possível baixar os dados: {type(exc).__name__}: {exc}", file=sys.stderr)
        print(
            "\nProvável bloqueio de rede no ambiente. Peça ao usuário para baixar o CSV em\n"
            f"  {URL_SITE}\n"
            "e anexá-lo à conversa; depois rode de novo com --arquivo <caminho>.",
            file=sys.stderr,
        )
        sys.exit(2)


def _bi(n: float) -> str:
    return f"R$ {n / 1000:,.1f} bi".replace(",", "X").replace(".", ",").replace("X", ".")


def resumir(linhas: list[dict], origem: str) -> None:
    comp = [l for l in linhas if l["tipo"] == "componente"]
    meses = sorted({l["ano_mes"] for l in comp})
    ult_ano = meses[-1][:4]
    if not meses[-1].endswith("-12"):
        ult_ano = str(int(ult_ano) - 1)  # último ano completo
    print(f"Origem: {origem}")
    print(f"Período: {meses[0]} a {meses[-1]} ({len(meses)} meses)")
    print("Unidades: valor = R$ milhões correntes; valor_constante = R$ milhões a preços "
          f"de {meses[-1]} (IPCA)")
    por_trib: dict[str, float] = defaultdict(float)
    for l in comp:
        if l["ano_mes"].startswith(ult_ano):
            por_trib[l["tributo"]] += l["valor"]
    total = sum(por_trib.values()) or 1
    print(f"\nTotal de {ult_ano}: {_bi(total)} (correntes, só componentes)")
    print(f"  {'tributo':<34} {'valor':>14} {'% total':>8}")
    for trib, v in sorted(por_trib.items(), key=lambda x: -x[1]):
        print(f"  {trib:<34} {_bi(v):>14} {f'{v / total * 100:.1f}%'.replace('.', ','):>8}")
    print("\nLembretes: Receita previdenciária = 0 em 1994 (lacuna da fonte); "
          "série termina em dez/2025.")


def gravar(linhas: list[dict], saida: Path) -> None:
    with saida.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=COLUNAS)
        w.writeheader()
        w.writerows(linhas)
    print(f"\nGravado: {saida} ({len(linhas)} linhas)")


def main() -> None:
    # Windows com console cp1252 quebra nos acentos do resumo.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--arquivo", help="CSV já baixado (o do site do projeto).")
    ap.add_argument("--detalhes", action="store_true",
                    help="Inclui as linhas de abertura (tipo=detalhe). Não some com componentes!")
    ap.add_argument("--saida", default="arrecadacao_federal.csv")
    args = ap.parse_args()

    linhas, origem = carregar(args.arquivo)
    tipos = {"componente", "detalhe"} if args.detalhes else {"componente"}
    filtradas = [l for l in linhas if l["tipo"] in tipos]
    resumir(filtradas, origem)
    gravar(filtradas, Path(args.saida))


if __name__ == "__main__":
    main()

"""Etapa 4 — Análise estatística da fonte RFB: Arrecadação das Receitas Federais.

Consome o CSV tidy da Etapa 3 e produz métricas analíticas: evolução da
arrecadação total, participação (%) de cada tributo, variação interanual (YoY),
CAGR, ranking por volume e estatística descritiva — sempre em duas bases,
**corrente** e **constante** (deflacionada pelo IPCA na Etapa 3).

Como a série é longa (1994→), além da série mensal é publicada uma agregação
**anual**, mais legível em gráficos de 30+ anos. Retorna um dicionário
serializável, usado pela Etapa 5 (publicação).
"""
from __future__ import annotations

import pandas as pd

from src import config

SLUG = "arrecadacao_federal"

# Bases de preço disponíveis no tidy (coluna do CSV -> chave no JSON).
BASES = {"valor": "corrente", "valor_constante": "constante"}


def _carregar_tidy(slug: str) -> pd.DataFrame:
    caminho = config.DIR_PROCESSADOS / f"{slug}.csv"
    if not caminho.exists():
        raise FileNotFoundError(
            f"Processado ausente: {caminho}. Rode a Etapa 3 (tratamento) antes da análise."
        )
    return pd.read_csv(caminho, dtype={"ano_mes": str})


def _num(valor) -> float | None:
    """Converte para float serializável, tratando NaN como None."""
    return None if valor is None or pd.isna(valor) else round(float(valor), 2)


def _cagr_aa(serie: pd.Series) -> float | None:
    """CAGR anual entre o primeiro e o último valor de uma série **anual**."""
    positivos = serie[serie > 0]
    if len(positivos) < 2:
        return None
    anos = len(positivos) - 1
    return ((positivos.iloc[-1] / positivos.iloc[0]) ** (1 / anos) - 1) * 100


def _yoy_pct(serie: pd.Series) -> float | None:
    """Variação % dos últimos 12 meses contra os 12 meses anteriores."""
    if len(serie) < 24:
        return None
    atual, anterior = serie.iloc[-12:].sum(), serie.iloc[-24:-12].sum()
    if not anterior:
        return None
    return (atual / anterior - 1) * 100


def _desc(serie: pd.Series) -> dict:
    """Estatística descritiva básica de uma série."""
    s = serie.dropna()
    media = float(s.mean()) if len(s) else None
    desvio = float(s.std()) if len(s) > 1 else None
    return {
        "media": _num(media),
        "mediana": _num(s.median()) if len(s) else None,
        "desvio_padrao": _num(desvio),
        "coef_variacao_pct": _num(desvio / media * 100) if (media and desvio) else None,
        "minimo": _num(s.min()) if len(s) else None,
        "maximo": _num(s.max()) if len(s) else None,
    }


def _pivotar(df: pd.DataFrame, indice: str, coluna_valor: str) -> pd.DataFrame:
    """Matriz período × tributo somando o valor da base escolhida."""
    return df.pivot_table(index=indice, columns="rotulo", values=coluna_valor,
                          aggfunc="sum").sort_index()


def analisar(slug: str = SLUG) -> dict:
    """Calcula todas as métricas e devolve um dicionário serializável."""
    cfg = config.fonte(slug)
    df = _carregar_tidy(slug)
    df["ano"] = df["ano_mes"].str.slice(0, 4)

    componentes = df[df["tipo"] == "componente"].copy()
    rotulo_total = cfg["rotulos"][cfg["linha_total"]]
    total = df[df["rotulo"] == rotulo_total].set_index("ano_mes").sort_index()

    meses = sorted(componentes["ano_mes"].unique())
    anos = sorted(componentes["ano"].unique())

    # Ordena os tributos pelo volume arrecadado (base corrente) no período todo.
    volume = componentes.groupby("rotulo")["valor"].sum().sort_values(ascending=False)
    tributos = list(volume.index)

    # Só a série mensal é publicada: a agregação anual do gráfico é feita no
    # front, sobre o período filtrado, evitando duplicar dados no JSON.
    series: dict[str, dict] = {t: {} for t in tributos}
    series_total: dict[str, list] = {}
    estatisticas: dict[str, dict] = {t: {} for t in tributos}

    for coluna, base in BASES.items():
        mensal = _pivotar(componentes, "ano_mes", coluna).reindex(meses)
        for tributo in tributos:
            series[tributo][base] = [_num(v) for v in mensal[tributo]]
            estatisticas[tributo][base] = _desc(mensal[tributo])
        series_total[base] = [_num(v) for v in total[coluna].reindex(meses)]

    # Ranking / KPIs por tributo, na base corrente (o front recalcula por período).
    mensal_corrente = _pivotar(componentes, "ano_mes", "valor").reindex(meses)
    anual_corrente = _pivotar(componentes, "ano", "valor").reindex(anos)
    total_periodo = float(mensal_corrente.to_numpy().sum())

    por_tributo = []
    for tributo in tributos:
        serie = mensal_corrente[tributo]
        acumulado = float(serie.sum())
        ult12 = float(serie.iloc[-12:].sum())
        por_tributo.append({
            "tributo": tributo,
            "valor_total": _num(acumulado),
            "part_pct": _num(acumulado / total_periodo * 100) if total_periodo else None,
            "valor_ult12m": _num(ult12),
            "yoy_pct": _num(_yoy_pct(serie)),
            "cagr_aa_pct": _num(_cagr_aa(anual_corrente[tributo])),
            "pico_mes": serie.idxmax() if serie.notna().any() else None,
            "pico_valor": _num(serie.max()),
        })

    # Composição interna de cada tributo (linhas "detalhe") nos últimos 12 meses.
    ult12_meses = meses[-12:]
    recorte = df[(df["tipo"] == "detalhe") & (df["ano_mes"].isin(ult12_meses))]
    detalhes: dict[str, list] = {}
    for pai, grupo in recorte.groupby("tributo_pai"):
        rotulo_pai = df.loc[df["tributo"] == pai, "rotulo"]
        if rotulo_pai.empty:
            continue
        soma = grupo.groupby("rotulo")["valor"].sum().sort_values(ascending=False)
        total_pai = float(soma.sum())
        detalhes[rotulo_pai.iloc[0]] = [
            {
                "rotulo": nome,
                "valor_ult12m": _num(valor),
                "part_pct": _num(valor / total_pai * 100) if total_pai else None,
            }
            for nome, valor in soma.items()
        ]

    serie_total_mensal = total["valor"].reindex(meses)
    lider = max(por_tributo, key=lambda x: x["valor_ult12m"] or 0)
    total_ult12m = float(serie_total_mensal.iloc[-12:].sum())
    lider_part_ult12m = (
        (lider["valor_ult12m"] / total_ult12m * 100) if total_ult12m else None
    )

    return {
        "labels": meses,
        "anos": anos,
        "tributos": tributos,
        "series": series,
        "total": series_total,
        "detalhes": detalhes,
        "kpis": {
            "por_tributo": por_tributo,
            "totais": {
                "mes_ref": meses[-1],
                "meses_cobertos": len(meses),
                "valor_ultimo_mes": _num(serie_total_mensal.iloc[-1]),
                "valor_ult12m": _num(serie_total_mensal.iloc[-12:].sum()),
                "yoy_pct": _num(_yoy_pct(serie_total_mensal)),
                "cagr_aa_pct": _num(_cagr_aa(
                    total.groupby(total.index.str.slice(0, 4))["valor"].sum().reindex(anos))),
                "tributo_lider": lider["tributo"],
                "tributo_lider_part_pct": _num(lider_part_ult12m),
            },
        },
        "estatisticas": estatisticas,
    }


if __name__ == "__main__":
    import json

    resultado = analisar()
    print(json.dumps(resultado["kpis"]["totais"], ensure_ascii=False, indent=2))

"""Configuração do repositório — fonte `arrecadacao_federal`.

Concentra caminhos de pastas e o registro da fonte usado por todas as etapas.
Este repositório cobre **uma única fonte**; o registro segue em formato de dicionário
por slug para manter o mesmo contrato de código das demais fontes do projeto.
"""
from __future__ import annotations

from pathlib import Path

# --- Caminhos base -----------------------------------------------------------
# src/config.py  ->  raiz do projeto = parent de src/
RAIZ = Path(__file__).resolve().parent.parent

DIR_DADOS = RAIZ / "dados"
DIR_BRUTOS = DIR_DADOS / "brutos"            # Etapa 2 (arquivos XLSX baixados)
DIR_PROCESSADOS = DIR_DADOS / "processados"  # Etapa 3 (CSV tidy)
DIR_PUBLICADOS = RAIZ / "docs" / "dados"     # Etapa 5 (JSON consumido pelo front)


def garantir_pastas() -> None:
    """Cria as pastas de dados caso ainda não existam."""
    for pasta in (DIR_BRUTOS, DIR_PROCESSADOS, DIR_PUBLICADOS):
        pasta.mkdir(parents=True, exist_ok=True)


# --- Registro da fonte -------------------------------------------------------
RFB_SERIE_HISTORICA = (
    "https://www.gov.br/receitafederal/pt-br/acesso-a-informacao/dados-abertos"
    "/receitadata/arrecadacao/serie-historica"
)

SLUG = "arrecadacao_federal"

FONTES: dict[str, dict] = {
    "arrecadacao_federal": {
        "nome": "RFB — Arrecadação das Receitas Federais (série histórica)",
        "descricao": (
            "Valor arrecadado mensal por tributo no Brasil, a preços correntes, "
            "publicado pela Receita Federal no portal ReceitaData."
        ),
        # Página de listagem: usada como fallback para descobrir os XLSX quando os
        # nomes de arquivo mudam de ano a ano (ex.: "1994 a 2025" -> "1994 a 2026").
        "url": f"{RFB_SERIE_HISTORICA}/",
        "arquivos": [
            {
                "nome": "arrecadacao-das-receitas-federais-1970-a-1993.xlsx",
                "url": f"{RFB_SERIE_HISTORICA}/arrecadacao-das-receitas-federais-1970-a-1993.xlsx",
                # Moedas diferentes por ano (Cr$, Cz$, NCz$, CR$) e a aba 1970-1985 é
                # anual: coletado para rastreabilidade, mas fora da série tratada.
                "tratar": False,
            },
            {
                "nome": "arrecadacao-das-receitas-federais-1994-a-2025.xlsx",
                "url": f"{RFB_SERIE_HISTORICA}/arrecadacao-das-receitas-federais-1994-a-2025.xlsx",
                "tratar": True,
            },
        ],
        # Etapa 2 também baixa o IPCA (SGS 433) para deflacionar na Etapa 3.
        "url_ipca": (
            "https://api.bcb.gov.br/dados/serie/bcdata.sgs.433/dados"
            "?formato=json&dataInicial=01/12/1993"
        ),
        # Rótulos amigáveis para as linhas do XLSX (chave = rótulo original, sem recuo).
        "rotulos": {
            "IMPOSTO SOBRE IMPORTAÇÃO": "Imposto de Importação",
            "IMPOSTO SOBRE EXPORTAÇÃO": "Imposto de Exportação",
            "I.P.I-TOTAL": "IPI",
            "IMPOSTO SOBRE A RENDA-TOTAL": "Imposto de Renda",
            "IOF - I. S/ OPERAÇÕES FINANCEIRAS": "IOF",
            "ITR - I. TERRITORIAL RURAL": "ITR",
            "COFINS - CONTRIB. P/ A SEGURIDADE SOCIAL": "COFINS",
            "CONTRIBUIÇÃO PARA O PIS/PASEP": "PIS/PASEP",
            "CSLL - CONTRIB. SOCIAL S/ LUCRO LÍQUIDO": "CSLL",
            "CIDE-COMBUSTÍVEIS": "CIDE-Combustíveis",
            "CONTRIBUIÇÃO PARA O FUNDAF": "FUNDAF",
            "PSS - CONTRIB. DO PLANO DE SEGURIDADE DO SERVIDOR": "PSS",
            "OUTRAS RECEITAS ADMINISTRADAS": "Outras receitas administradas",
            "RECEITA PREVIDENCIÁRIA [B]": "Receita previdenciária",
            "ADMINISTRADAS POR OUTROS ÓRGÃOS [D]": "Administradas por outros órgãos",
            "SUBTOTAL [A]": "Subtotal administradas (exceto previdenciária)",
            "ADMINISTRADAS PELA RFB [C]=[A]+[B]": "Administradas pela RFB",
            "TOTAL GERAL [E]=[C]+[D]": "Total geral",
        },
        # Linhas de nível 1 que somam exatamente o "TOTAL GERAL" (base das participações).
        "componentes_total": [
            "IMPOSTO SOBRE IMPORTAÇÃO",
            "IMPOSTO SOBRE EXPORTAÇÃO",
            "I.P.I-TOTAL",
            "IMPOSTO SOBRE A RENDA-TOTAL",
            "IOF - I. S/ OPERAÇÕES FINANCEIRAS",
            "ITR - I. TERRITORIAL RURAL",
            "COFINS - CONTRIB. P/ A SEGURIDADE SOCIAL",
            "CONTRIBUIÇÃO PARA O PIS/PASEP",
            "CSLL - CONTRIB. SOCIAL S/ LUCRO LÍQUIDO",
            "CIDE-COMBUSTÍVEIS",
            "CONTRIBUIÇÃO PARA O FUNDAF",
            "PSS - CONTRIB. DO PLANO DE SEGURIDADE DO SERVIDOR",
            "OUTRAS RECEITAS ADMINISTRADAS",
            "RECEITA PREVIDENCIÁRIA [B]",
            "ADMINISTRADAS POR OUTROS ÓRGÃOS [D]",
        ],
        # Linhas somatórias do próprio XLSX (não entram em participação/ranking).
        "agregados": [
            "SUBTOTAL [A]",
            "ADMINISTRADAS PELA RFB [C]=[A]+[B]",
            "TOTAL GERAL [E]=[C]+[D]",
        ],
        "linha_total": "TOTAL GERAL [E]=[C]+[D]",
        "unidades": {
            "valor": "R$ milhões (correntes)",
            "valor_constante": "R$ milhões (constantes, IPCA do último mês)",
        },
        "periodicidade": "mensal",
        "licenca": "CC-BY-ND 3.0 — Receita Federal do Brasil",
    },
}


def fonte(slug: str = SLUG) -> dict:
    """Retorna a configuração da fonte pelo slug, com erro claro se ausente."""
    if slug not in FONTES:
        disponiveis = ", ".join(FONTES) or "(nenhuma)"
        raise KeyError(f"Fonte '{slug}' não registrada. Disponíveis: {disponiveis}")
    return FONTES[slug]

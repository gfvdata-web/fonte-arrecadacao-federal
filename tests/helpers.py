"""Apoio dos testes: caminhos e um ambiente isolado em pasta temporária.

Nada aqui acessa a rede nem escreve dentro do repositório: a publicação roda com as pastas
de dados (src.config) e os caminhos da skill redirecionados para um diretório temporário.
"""
from __future__ import annotations

import contextlib
import io
import json
import shutil
import tempfile
from pathlib import Path
from unittest import mock

RAIZ = Path(__file__).resolve().parent.parent
DOCS = RAIZ / "docs"
DADOS_PUB = DOCS / "dados"
FIXTURE_TIDY = RAIZ / "tests" / "fixtures" / "tidy_minimo.csv"
SLUG = "arrecadacao_federal"
CSV_PUBLICO = DADOS_PUB / f"{SLUG}_mensal.csv"


def ler_json(caminho: Path):
    return json.loads(Path(caminho).read_text(encoding="utf-8"))


def ler_texto(caminho: Path) -> str:
    """Texto com quebras de linha normalizadas (o checkout no Windows converte para CRLF)."""
    return Path(caminho).read_text(encoding="utf-8").replace("\r\n", "\n")


@contextlib.contextmanager
def ambiente_isolado():
    """Redireciona dados/, docs/dados/ e a skill para uma pasta temporária; devolve a raiz dela."""
    from src import config
    from src.publicacao import skill

    with tempfile.TemporaryDirectory(prefix="af-teste-") as tmp:
        raiz = Path(tmp)
        proc, pub = raiz / "dados" / "processados", raiz / "docs" / "dados"
        brutos = raiz / "dados" / "brutos"
        for pasta in (proc, pub, brutos):
            pasta.mkdir(parents=True)
        shutil.copy(FIXTURE_TIDY, proc / f"{SLUG}.csv")
        shutil.copy(DADOS_PUB / "eventos_arrecadacao_federal.json", pub / "eventos_arrecadacao_federal.json")
        dir_skill = raiz / "skill" / skill.NOME_SKILL
        shutil.copytree(skill.DIR_SKILL, dir_skill, ignore=shutil.ignore_patterns("__pycache__"))
        with contextlib.ExitStack() as pilha:
            pilha.enter_context(mock.patch.object(config, "DIR_BRUTOS", brutos))
            pilha.enter_context(mock.patch.object(config, "DIR_PROCESSADOS", proc))
            pilha.enter_context(mock.patch.object(config, "DIR_PUBLICADOS", pub))
            pilha.enter_context(mock.patch.object(skill, "DIR_SKILL", dir_skill))
            pilha.enter_context(mock.patch.object(skill, "DESTINO_ZIP", raiz / "docs" / "skill" / "x.zip"))
            pilha.enter_context(mock.patch.object(skill, "ARQ_EVENTOS", pub / "eventos_arrecadacao_federal.json"))
            yield raiz


@contextlib.contextmanager
def sem_saida():
    """Silencia os print() do pipeline."""
    with contextlib.redirect_stdout(io.StringIO()):
        yield

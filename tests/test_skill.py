"""Skill do Claude (skill/arrecadacao-federal-rfb): estrutura, carga offline, zip e eventos.md em dia."""
from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import re
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

from src.publicacao import skill as empacotador

from tests.helpers import CSV_PUBLICO, DADOS_PUB, RAIZ, ler_json, ler_texto

NOME = "arrecadacao-federal-rfb"
DIR_SKILL = RAIZ / "skill" / NOME
ZIP_PUBLICO = RAIZ / "docs" / "skill" / f"{NOME}.zip"
SCRIPT = DIR_SKILL / "scripts" / "carregar_dados.py"

_spec = importlib.util.spec_from_file_location("carregar_dados", SCRIPT)
cd = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(cd)


def _arquivos_da_skill() -> list[Path]:
    return sorted(p for p in DIR_SKILL.rglob("*") if p.is_file() and "__pycache__" not in p.parts)


class TestEstruturaDaSkill(unittest.TestCase):
    def test_frontmatter(self):
        texto = ler_texto(DIR_SKILL / "SKILL.md")
        m = re.match(r"---\nname: (.+)\ndescription: (.+)\n---\n", texto)
        self.assertIsNotNone(m, "SKILL.md sem frontmatter name/description")
        self.assertEqual(m.group(1).strip(), NOME)
        self.assertEqual(NOME, empacotador.NOME_SKILL)
        self.assertGreater(len(m.group(2)), 80)
        self.assertLessEqual(len(m.group(2)), 1024)

    def test_referencias_citadas_no_skill_md_existem(self):
        texto = ler_texto(DIR_SKILL / "SKILL.md")
        citadas = set(re.findall(r"`?((?:references|scripts)/[\w.-]+)`?", texto))
        self.assertTrue(citadas)
        for ref in citadas:
            self.assertTrue((DIR_SKILL / ref).is_file(), f"SKILL.md cita {ref}, que não existe")

    def test_url_do_script_aponta_para_o_csv_publicado(self):
        self.assertTrue(cd.URL_SITE.startswith("https://arrecadacaofederal.gfvdata.com/"))
        self.assertTrue(cd.URL_SITE.endswith("/dados/arrecadacao_federal_mensal.csv"))
        self.assertTrue(CSV_PUBLICO.is_file())
        self.assertIn(cd.URL_SITE, ler_texto(DIR_SKILL / "SKILL.md"))

    def test_script_so_usa_biblioteca_padrao(self):
        fonte = ler_texto(SCRIPT)
        compile(fonte, "carregar_dados.py", "exec")
        importados = set(re.findall(r"^(?:import|from) (\w+)", fonte, re.M)) - {"__future__"}
        self.assertLessEqual(importados, set(sys.stdlib_module_names), "a skill roda em ambientes sem pip")


class TestCarregarDados(unittest.TestCase):
    def test_ler_csv_publico_usa_rotulos_amigaveis(self):
        linhas = cd._ler(CSV_PUBLICO.read_text(encoding="utf-8"))
        self.assertGreater(len(linhas), 10000)
        self.assertEqual(set(linhas[0]), set(cd.COLUNAS))
        componentes = {l["tributo"] for l in linhas if l["tipo"] == "componente"}
        self.assertEqual(componentes, set(ler_json(DADOS_PUB / "arrecadacao_federal.json")["tributos"]))
        self.assertIsInstance(linhas[0]["valor"], float)

    def test_ler_aceita_bom_e_rejeita_formato_invalido(self):
        self.assertTrue(cd._ler("﻿" + CSV_PUBLICO.read_text(encoding="utf-8")))
        with self.assertRaises(ValueError):
            cd._ler("")
        with self.assertRaises(ValueError):
            cd._ler("a,b\n1,2\n")

    def test_arquivo_inexistente_sai_com_codigo_1(self):
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as ctx:
            cd.carregar("nao_existe.csv")
        self.assertEqual(ctx.exception.code, 1)

    def test_falha_de_rede_sai_com_codigo_2(self):
        original = cd._baixar
        cd._baixar = lambda *a, **k: (_ for _ in ()).throw(OSError("sem rede"))
        try:
            with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as ctx:
                cd.carregar(None)
        finally:
            cd._baixar = original
        self.assertEqual(ctx.exception.code, 2)

    def test_script_com_arquivo_roda_offline_de_ponta_a_ponta(self):
        with tempfile.TemporaryDirectory() as tmp:
            saida = Path(tmp) / "saida.csv"
            r = subprocess.run(
                [sys.executable, "-X", "utf8", "-I", str(SCRIPT), "--arquivo", str(CSV_PUBLICO), "--saida", str(saida)],
                capture_output=True, text=True, encoding="utf-8", cwd=tmp,
            )
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn("Período: 1994-01 a 2025-12", r.stdout)
            self.assertIn("Total de 2025", r.stdout)
            linhas = saida.read_text(encoding="utf-8").splitlines()
            self.assertEqual(linhas[0], ",".join(cd.COLUNAS))
            self.assertEqual(len(linhas) - 1, 15 * 384)   # só componentes: 15 tributos x 384 meses

    def test_flag_detalhes_inclui_aberturas(self):
        with tempfile.TemporaryDirectory() as tmp:
            saida = Path(tmp) / "d.csv"
            r = subprocess.run(
                [sys.executable, "-X", "utf8", "-I", str(SCRIPT), "--arquivo", str(CSV_PUBLICO), "--detalhes", "--saida", str(saida)],
                capture_output=True, text=True, encoding="utf-8", cwd=tmp,
            )
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertGreater(len(saida.read_text(encoding="utf-8").splitlines()), 15 * 384 + 1)


class TestPacoteEEventos(unittest.TestCase):
    def test_zip_tem_a_pasta_da_skill_na_raiz(self):
        with zipfile.ZipFile(ZIP_PUBLICO) as zf:
            nomes = zf.namelist()
        self.assertTrue(nomes)
        self.assertTrue(all(n.startswith(f"{NOME}/") for n in nomes), nomes)
        self.assertIn(f"{NOME}/SKILL.md", nomes)
        self.assertFalse([n for n in nomes if "__pycache__" in n])

    def test_zip_em_sincronia_com_a_pasta_skill(self):
        esperados = {p.relative_to(DIR_SKILL.parent).as_posix(): p.read_bytes().replace(b"\r\n", b"\n")
                     for p in _arquivos_da_skill()}
        with zipfile.ZipFile(ZIP_PUBLICO) as zf:
            no_zip = {n: zf.read(n).replace(b"\r\n", b"\n") for n in zf.namelist() if not n.endswith("/")}
        self.assertEqual(set(no_zip), set(esperados), "arquivos do zip diferem de skill/ (rode run_pipeline.py)")
        for nome, conteudo in esperados.items():
            self.assertEqual(no_zip[nome], conteudo, f"{nome} está desatualizado no zip")

    def test_eventos_md_em_sincronia_com_o_json(self):
        eventos = sorted(ler_json(DADOS_PUB / "eventos_arrecadacao_federal.json"), key=lambda e: e["data"])
        texto = ler_texto(DIR_SKILL / "references" / "eventos.md")
        titulos = re.findall(r"^## .+? — (.+)$", texto, re.M)
        self.assertEqual(titulos, [e["titulo"] for e in eventos])
        for e in eventos:
            self.assertIn(e["descricao"], texto)
            self.assertIn(f"Fonte: {e['fonte']}", texto)

    def test_empacotar_gera_o_mesmo_conteudo_em_pasta_temporaria(self):
        from tests.helpers import ambiente_isolado, sem_saida
        from src.publicacao import skill

        with ambiente_isolado() as raiz:
            with sem_saida():
                skill.empacotar()
            destino = raiz / "docs" / "skill" / "x.zip"
            with zipfile.ZipFile(destino) as zf:
                nomes = sorted(zf.namelist())
                eventos_md = zf.read(f"{NOME}/references/eventos.md").decode("utf-8").replace("\r\n", "\n")
            self.assertEqual(nomes, sorted(p.relative_to(DIR_SKILL.parent).as_posix() for p in _arquivos_da_skill()))
            self.assertEqual(eventos_md, ler_texto(DIR_SKILL / "references" / "eventos.md"))


if __name__ == "__main__":
    unittest.main()

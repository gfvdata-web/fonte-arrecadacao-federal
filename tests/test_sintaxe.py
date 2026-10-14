"""Sintaxe: Python compila, JSON/CSV parseiam e todo JS (arquivos e <script> inline) passa no `node --check`."""
from __future__ import annotations

import csv
import json
import py_compile
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from tests.helpers import DOCS, RAIZ
from tests.test_paginas import Pagina

NODE = shutil.which("node")


def _arquivos(base: str, padrao: str) -> list[Path]:
    return sorted((RAIZ / base).rglob(padrao))


class TestSintaxe(unittest.TestCase):
    def test_python_compila(self):
        alvos = [RAIZ / "run_pipeline.py", *_arquivos("src", "*.py"), *_arquivos("tests", "*.py"),
                 *_arquivos("skill", "*.py")]
        self.assertGreater(len(alvos), 10)
        with tempfile.TemporaryDirectory() as tmp:
            for i, arq in enumerate(alvos):
                try:
                    py_compile.compile(str(arq), cfile=str(Path(tmp) / f"{i}.pyc"), doraise=True)
                except py_compile.PyCompileError as exc:
                    self.fail(f"{arq.relative_to(RAIZ)}: {exc.msg}")

    def test_json_valido(self):
        alvos = _arquivos("docs/dados", "*.json") + _arquivos("tests/fixtures", "*.json")
        self.assertGreaterEqual(len(alvos), 4)
        for arq in alvos:
            try:
                json.loads(arq.read_text(encoding="utf-8"))
            except ValueError as exc:
                self.fail(f"JSON inválido {arq.relative_to(RAIZ)}: {exc}")

    def test_csv_com_colunas_consistentes(self):
        for arq in (DOCS / "dados" / "arrecadacao_federal_mensal.csv", RAIZ / "tests" / "fixtures" / "tidy_minimo.csv"):
            with arq.open(encoding="utf-8", newline="") as f:
                linhas = list(csv.reader(f))
            self.assertTrue(all(len(l) == len(linhas[0]) for l in linhas), arq.name)

    @unittest.skipIf(NODE is None, "node não instalado")
    def test_js_dos_arquivos(self):
        alvos = _arquivos("docs", "*.js") + _arquivos("tests/js", "*.js")
        self.assertGreaterEqual(len(alvos), 4)     # app-v2, v1/app, v1/explorar, teste
        for arq in alvos:
            r = subprocess.run([NODE, "--check", str(arq)], capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, f"{arq.relative_to(RAIZ)}:\n{r.stderr.strip()}")

    @unittest.skipIf(NODE is None, "node não instalado")
    def test_js_inline_das_paginas(self):
        paginas = [p for p in sorted(DOCS.rglob("*.html"))]
        self.assertGreaterEqual(len(paginas), 4)
        with tempfile.TemporaryDirectory() as tmp:
            for pagina in paginas:
                pag = Pagina(pagina)
                inline = _scripts_inline(pag.texto_html)
                for i, codigo in enumerate(inline):
                    tmp_js = Path(tmp) / f"{pagina.stem}.{i}.js"
                    tmp_js.write_text(codigo, encoding="utf-8")
                    r = subprocess.run([NODE, "--check", str(tmp_js)], capture_output=True, text=True)
                    self.assertEqual(r.returncode, 0, f"<script> #{i} de {pagina.relative_to(RAIZ)}:\n{r.stderr.strip()}")


def _scripts_inline(html: str) -> list[str]:
    import re
    achados = re.findall(r"<script(?![^>]*\bsrc=)[^>]*>(.*?)</script>", html, re.S | re.I)
    return [c for c in achados if c.strip()]


if __name__ == "__main__":
    unittest.main()

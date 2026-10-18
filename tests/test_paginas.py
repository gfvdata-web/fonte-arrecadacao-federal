"""Páginas do site: V2 (index.html, skill.html) e V1 arquivada (docs/v1/)."""
from __future__ import annotations

import re
import unittest
from html.parser import HTMLParser
from pathlib import Path

from tests.helpers import DOCS, ler_texto


class Pagina(HTMLParser):
    def __init__(self, caminho: Path):
        super().__init__()
        self.caminho = caminho
        self.texto_html = ler_texto(caminho)
        self.ids, self.refs, self.links_nav, self.scripts, self.metas = set(), [], [], [], []
        self._nav = False
        self.feed(self.texto_html)

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if "id" in a:
            self.ids.add(a["id"])
        if tag == "nav" and "nav-paineis" in (a.get("class") or ""):
            self._nav = True
        if tag == "a" and self._nav:
            self.links_nav.append(a.get("href"))
        if tag in ("a", "link") and a.get("href"):
            self.refs.append(a["href"])
        if tag == "script":
            self.scripts.append(a)
            if a.get("src"):
                self.refs.append(a["src"])
        if tag == "meta":
            self.metas.append(a)

    def handle_endtag(self, tag):
        if tag == "nav":
            self._nav = False


def _locais(pag: Pagina):
    for ref in pag.refs:
        if re.match(r"^(https?:|//|#|mailto:|data:)", ref):
            continue
        yield ref.split("#")[0].split("?")[0]


V2 = {"index.html": Pagina(DOCS / "index.html"), "skill.html": Pagina(DOCS / "skill.html")}
V1 = {n: Pagina(DOCS / "v1" / n) for n in ("index.html", "explorar.html")}


class TestPaginasV2(unittest.TestCase):
    def test_links_locais_existem(self):
        for nome, pag in V2.items():
            for ref in _locais(pag):
                self.assertTrue((DOCS / ref).exists(), f"{nome}: {ref} não existe")

    def test_navegacao_so_painel_e_skill(self):
        for nome, pag in V2.items():
            self.assertEqual(pag.links_nav, ["index.html", "skill.html"], nome)

    def test_sem_link_para_v1_nem_explorar(self):
        for nome, pag in V2.items():
            for ref in pag.refs:
                self.assertNotIn("v1/", ref, nome)
                self.assertNotIn("explorar", ref, nome)

    def test_goatcounter_presente(self):
        for nome, pag in V2.items():
            gc = [s for s in pag.scripts if s.get("data-goatcounter")]
            self.assertEqual(len(gc), 1, nome)
            self.assertEqual(gc[0]["data-goatcounter"], "https://gfvdata.goatcounter.com/count")

    def test_goatcounter_com_prefixo_do_repo_antes_do_snippet(self):
        # Domínio próprio: sem o prefixo, o GoatCounter registra o caminho sem /fonte-arrecadacao-federal/
        # e o painel-status não conta as visitas.
        prefixo = 'window.goatcounter = { path: (p) => "/fonte-arrecadacao-federal" + p };'
        for html in sorted(DOCS.rglob("*.html")):
            texto = html.read_text(encoding="utf-8")
            nome = str(html.relative_to(DOCS))
            self.assertEqual(texto.count("data-goatcounter="), 1, nome)
            self.assertEqual(texto.count("window.goatcounter"), 1, nome)
            self.assertIn(prefixo, texto, f"{nome}: falta o prefixo /fonte-arrecadacao-federal do GoatCounter")
            self.assertLess(texto.index("window.goatcounter"), texto.index("data-goatcounter="), nome)
            self.assertLess(texto.index("data-goatcounter="), texto.index("</head>"), nome)

    def test_cdn_com_versao_fixa(self):
        cdns = [s["src"] for pag in V2.values() for s in pag.scripts if s.get("src", "").startswith("https://cdn")]
        self.assertGreaterEqual(len(cdns), 3)
        for src in cdns:
            self.assertRegex(src, r"/npm/[\w.-]+@\d+\.\d+\.\d+/", f"CDN sem versão fixada: {src}")

    def test_botao_de_tema_e_script_antecipado(self):
        for nome, pag in V2.items():
            self.assertIn("tema-switch-v2", pag.ids, nome)
            self.assertEqual(len(re.findall(r'data-tema="(?:light|dark)"', pag.texto_html)), 2, nome)
            self.assertIn('localStorage.getItem("tema-v2")', pag.texto_html, nome)
            self.assertIn("data-theme", pag.texto_html, nome)

    def test_ids_usados_pelo_js_existem_no_index(self):
        js = ler_texto(DOCS / "js" / "app-v2.js")
        usados = set(re.findall(r'getElementById\("([^"]+)"\)', js))
        usados |= set(re.findall(r'querySelector\("#([\w-]+)', js))
        self.assertGreater(len(usados), 12)
        faltam = usados - V2["index.html"].ids
        self.assertFalse(faltam, f"ids do JS ausentes em index.html: {faltam}")

    def test_index_carrega_o_js_v2_e_o_css_v2(self):
        refs = V2["index.html"].refs
        self.assertIn("js/app-v2.js", refs)
        self.assertIn("css/estilo-v2.css", refs)

    def test_skill_html_instrucao_e_zip(self):
        t = V2["skill.html"].texto_html
        self.assertIn("skill/arrecadacao-federal-rfb.zip", t)
        self.assertIn("dados/arrecadacao_federal_mensal.csv", t)
        self.assertIn("arrecadacao-federal-rfb", t)


class TestPaginasV1Arquivadas(unittest.TestCase):
    def test_existem_com_noindex(self):
        for nome, pag in V1.items():
            robots = [m for m in pag.metas if m.get("name") == "robots"]
            self.assertTrue(robots and "noindex" in robots[0].get("content", ""), f"v1/{nome} sem noindex")

    def test_links_locais_existem(self):
        for nome, pag in V1.items():
            for ref in _locais(pag):
                self.assertTrue((DOCS / "v1" / ref).resolve().exists(), f"v1/{nome}: {ref} não existe")

    def test_dados_vem_de_fora_da_pasta_v1(self):
        for js in ("app.js", "explorar.js"):
            texto = ler_texto(DOCS / "v1" / "js" / js)
            caminhos = re.findall(r'["\'`]((?:\.\./)*dados/[^"\'`]+)["\'`]', texto)
            self.assertTrue(caminhos, f"v1/js/{js} não lê nenhum dado")
            for c in caminhos:
                self.assertTrue(c.startswith("../dados/"), f"v1/js/{js}: {c}")
                self.assertTrue((DOCS / "v1" / c.replace("${SLUG}", "arrecadacao_federal")).resolve().exists(), f"v1/js/{js}: {c} não existe")


if __name__ == "__main__":
    unittest.main()

"""Contrato página <-> dados publicados em docs/dados/ (o que o app-v2.js lê)."""
from __future__ import annotations

import csv
import re
import unittest

from tests.helpers import CSV_PUBLICO, DADOS_PUB, ler_json

DADOS = ler_json(DADOS_PUB / "arrecadacao_federal.json")
EVENTOS = ler_json(DADOS_PUB / "eventos_arrecadacao_federal.json")
AAAA_MM = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")


class TestArrecadacaoJson(unittest.TestCase):
    def test_campos_de_topo(self):
        for campo in ("meta", "labels", "anos", "tributos", "series", "total", "kpis", "detalhes", "estatisticas"):
            self.assertIn(campo, DADOS, campo)

    def test_meta_e_periodo(self):
        meta = DADOS["meta"]
        for campo in ("fonte", "licenca", "gerado_em", "periodo", "mes_base_constante", "unidades"):
            self.assertTrue(meta.get(campo), campo)
        p = meta["periodo"]
        self.assertRegex(p["inicio"], AAAA_MM)
        self.assertRegex(p["fim"], AAAA_MM)
        self.assertEqual(p["inicio"], DADOS["labels"][0])
        self.assertEqual(p["fim"], DADOS["labels"][-1])
        self.assertEqual(meta["mes_base_constante"], p["fim"])

    def test_labels_mensais_continuos_e_anos(self):
        labels = DADOS["labels"]
        for l in labels:
            self.assertRegex(l, AAAA_MM)
        esperado = [f"{a}-{m:02d}" for a in range(int(labels[0][:4]), int(labels[-1][:4]) + 1) for m in range(1, 13)]
        self.assertEqual(labels, esperado[esperado.index(labels[0]):esperado.index(labels[-1]) + 1])
        self.assertEqual(DADOS["anos"], sorted({l[:4] for l in labels}))

    def test_quinze_tributos_e_series_do_tamanho_das_labels(self):
        n = len(DADOS["labels"])
        self.assertEqual(len(DADOS["tributos"]), 15)
        self.assertEqual(len(set(DADOS["tributos"])), 15)
        self.assertEqual(DADOS["tributos"], list(DADOS["series"]))
        self.assertEqual(set(DADOS["estatisticas"]), set(DADOS["tributos"]))
        for t in DADOS["tributos"]:
            for base in ("corrente", "constante"):
                self.assertEqual(len(DADOS["series"][t][base]), n, f"{t}/{base}")
        for base in ("corrente", "constante"):
            self.assertEqual(len(DADOS["total"][base]), n, base)

    def test_componentes_somam_o_total(self):
        for base in ("corrente", "constante"):
            for i, rotulo in enumerate(DADOS["labels"]):
                soma = sum(DADOS["series"][t][base][i] or 0 for t in DADOS["tributos"])
                total = DADOS["total"][base][i]
                self.assertIsNotNone(total, f"{rotulo}/{base}")
                self.assertLess(abs(soma - total), max(abs(total) * 1e-4, 0.5), f"{rotulo}/{base}: {soma} vs {total}")

    def test_kpis_cobrem_todos_os_tributos(self):
        por = DADOS["kpis"]["por_tributo"]
        self.assertEqual({x["tributo"] for x in por}, set(DADOS["tributos"]))
        for x in por:
            for campo in ("valor_total", "part_pct", "valor_ult12m", "yoy_pct", "cagr_aa_pct", "pico_mes", "pico_valor"):
                self.assertIn(campo, x)
        self.assertAlmostEqual(sum(x["part_pct"] for x in por), 100, delta=0.5)
        for campo in ("mes_ref", "valor_ult12m", "yoy_pct"):
            self.assertIn(campo, DADOS["kpis"]["totais"])
        self.assertEqual(DADOS["kpis"]["totais"]["mes_ref"], DADOS["labels"][-1])

    def test_kpi_ult12m_confere_com_a_serie(self):
        for x in DADOS["kpis"]["por_tributo"]:
            soma = sum(v or 0 for v in DADOS["series"][x["tributo"]]["corrente"][-12:])
            self.assertAlmostEqual(soma, x["valor_ult12m"], delta=0.5, msg=x["tributo"])


class TestEventos(unittest.TestCase):
    def test_schema(self):
        self.assertGreaterEqual(len(EVENTOS), 10)
        permitidos = set(DADOS["tributos"]) | {"Total"}
        for e in EVENTOS:
            self.assertEqual(set(e), {"data", "titulo", "descricao", "tributos", "fonte"}, e.get("titulo"))
            self.assertRegex(e["data"], AAAA_MM)
            self.assertTrue(e["titulo"].strip() and e["descricao"].strip())
            self.assertTrue(e["tributos"], e["titulo"])
            self.assertLessEqual(set(e["tributos"]), permitidos, f"{e['titulo']}: {set(e['tributos']) - permitidos}")
            self.assertRegex(e["fonte"], r"^https://\S+$", e["titulo"])

    def test_ordenado_por_data_e_sem_duplicata(self):
        datas = [e["data"] for e in EVENTOS]
        self.assertEqual(datas, sorted(datas))
        titulos = [(e["data"], e["titulo"]) for e in EVENTOS]
        self.assertEqual(len(titulos), len(set(titulos)))


class TestNotasEPerfil(unittest.TestCase):
    def test_notas_tem_o_comparativo_c3_que_o_painel_usa(self):
        notas = ler_json(DADOS_PUB / "notas_arrecadacao_federal.json")
        c3 = [c for c in notas["comparativos"] if c.get("id") == "C3"]
        self.assertEqual(len(c3), 1)
        self.assertTrue(c3[0].get("titulo") and c3[0].get("o_que_esperar"))
        self.assertTrue(notas["contexto_externo"])
        ctx = notas["contexto_externo"][0]
        self.assertRegex(ctx["url"], r"^https?://")
        self.assertTrue(ctx["fonte"])

    def test_perfil_e_json_nao_vazio(self):
        self.assertTrue(ler_json(DADOS_PUB / "perfil_arrecadacao_federal.json"))


class TestCsvPublico(unittest.TestCase):
    def test_colunas_e_cobertura(self):
        with CSV_PUBLICO.open(encoding="utf-8", newline="") as f:
            leitor = csv.DictReader(f)
            colunas = leitor.fieldnames
            linhas = list(leitor)
        self.assertEqual(colunas, ["ano_mes", "tributo", "rotulo", "tributo_pai", "nivel", "tipo", "valor", "valor_constante"])
        self.assertGreater(len(linhas), 10000)
        self.assertEqual({l["tipo"] for l in linhas}, {"agregado", "componente", "detalhe"})
        meses = sorted({l["ano_mes"] for l in linhas})
        self.assertEqual((meses[0], meses[-1]), (DADOS["labels"][0], DADOS["labels"][-1]))
        componentes = {l["rotulo"] for l in linhas if l["tipo"] == "componente"}
        self.assertEqual(componentes, set(DADOS["tributos"]))
        for l in linhas[:500]:
            float(l["valor"])
            float(l["valor_constante"])


if __name__ == "__main__":
    unittest.main()

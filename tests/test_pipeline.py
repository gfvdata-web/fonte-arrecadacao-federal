"""Pipeline: publicação (JSON + cópia do CSV), análise sobre um tidy mínimo e orquestrador. Sem rede e sem XLSX."""
from __future__ import annotations

import json
import unittest
from unittest import mock

import run_pipeline
from src import config
from src.analise import arrecadacao_federal as analise
from src.publicacao import arrecadacao_federal as publicacao

from tests.helpers import FIXTURE_TIDY, SLUG, ambiente_isolado, sem_saida


class TestAnalise(unittest.TestCase):
    def test_contrato_sobre_o_tidy_minimo(self):
        with ambiente_isolado():
            r = analise.analisar(SLUG)
        n = len(r["labels"])
        self.assertEqual(n, 26)
        self.assertEqual(r["labels"][0], "1994-01")
        self.assertEqual(r["anos"], ["1994", "1995", "1996"])
        self.assertGreater(len(r["tributos"]), 5)
        for t in r["tributos"]:
            for base in ("corrente", "constante"):
                self.assertEqual(len(r["series"][t][base]), n, f"{t}/{base}")
        for base in ("corrente", "constante"):
            self.assertEqual(len(r["total"][base]), n)
        self.assertEqual({x["tributo"] for x in r["kpis"]["por_tributo"]}, set(r["tributos"]))

    def test_componentes_somam_o_total_no_minimo(self):
        with ambiente_isolado():
            r = analise.analisar(SLUG)
        for i in range(len(r["labels"])):
            soma = sum(r["series"][t]["corrente"][i] or 0 for t in r["tributos"])
            self.assertAlmostEqual(soma, r["total"]["corrente"][i], delta=max(r["total"]["corrente"][i] * 1e-4, 1))

    def test_cagr_e_yoy_com_valores_conhecidos(self):
        import pandas as pd
        self.assertAlmostEqual(analise._cagr_aa(pd.Series([100.0, 121.0])), 21.0, places=6)
        self.assertIsNone(analise._cagr_aa(pd.Series([0.0, 5.0])))
        self.assertIsNone(analise._yoy_pct(pd.Series([1.0] * 12)))
        self.assertAlmostEqual(analise._yoy_pct(pd.Series([1.0] * 12 + [2.0] * 12)), 100.0)
        self.assertIsNone(analise._num(float("nan")))
        self.assertEqual(analise._num(1.2345), 1.23)

    def test_sem_processado_pede_a_etapa_3(self):
        with ambiente_isolado() as raiz:
            (raiz / "dados" / "processados" / f"{SLUG}.csv").unlink()
            with self.assertRaises(FileNotFoundError):
                analise.analisar(SLUG)


class TestPublicacao(unittest.TestCase):
    def test_grava_json_e_copia_do_csv_publico(self):
        with ambiente_isolado() as raiz, sem_saida():
            pacote = publicacao.publicar(SLUG)
            pub = raiz / "docs" / "dados"
            gravado = json.loads((pub / f"{SLUG}.json").read_text(encoding="utf-8"))
            self.assertEqual(gravado["meta"]["periodo"], {"inicio": "1994-01", "fim": "1996-02"})
            self.assertEqual(gravado["meta"]["fonte"], config.fonte(SLUG)["nome"])
            self.assertEqual(gravado["meta"]["mes_base_constante"], "1996-02")
            self.assertEqual(pacote["tributos"], gravado["tributos"])
            csv_pub = pub / f"{SLUG}_mensal.csv"
            self.assertTrue(csv_pub.is_file())
            self.assertEqual(csv_pub.read_bytes(), FIXTURE_TIDY.read_bytes())

    def test_nao_toca_notas_nem_perfil_escritos_a_mao(self):
        with ambiente_isolado() as raiz, sem_saida():
            notas = raiz / "docs" / "dados" / f"notas_{SLUG}.json"
            notas.write_text('{"a": 1}', encoding="utf-8")
            publicacao.publicar(SLUG)
            self.assertEqual(notas.read_text(encoding="utf-8"), '{"a": 1}')


class TestOrquestrador(unittest.TestCase):
    def test_flags_pulam_coleta_e_perfil(self):
        with ambiente_isolado(), sem_saida(), \
                mock.patch.object(run_pipeline.coleta, "coletar") as coletar, \
                mock.patch.object(run_pipeline.tratamento, "tratar") as tratar, \
                mock.patch.object(run_pipeline.perfil, "perfilar") as perfilar:
            run_pipeline.rodar(sem_coleta=True, sem_perfil=True)
            coletar.assert_not_called()
            perfilar.assert_not_called()
            tratar.assert_called_once_with(config.SLUG)

    def test_pipeline_completo_na_ordem_certa(self):
        ordem = []
        with ambiente_isolado() as raiz, sem_saida(), \
                mock.patch.object(run_pipeline.coleta, "coletar", side_effect=lambda s: ordem.append("coleta")), \
                mock.patch.object(run_pipeline.tratamento, "tratar", side_effect=lambda s: ordem.append("tratamento")), \
                mock.patch.object(run_pipeline.perfil, "perfilar", side_effect=lambda s: ordem.append("perfil")):
            run_pipeline.rodar()
            ordem.append("fim")
            self.assertTrue((raiz / "docs" / "dados" / f"{SLUG}.json").is_file())
            self.assertTrue((raiz / "docs" / "dados" / f"{SLUG}_mensal.csv").is_file())
            self.assertTrue((raiz / "docs" / "skill" / "x.zip").is_file())
        self.assertEqual(ordem, ["coleta", "tratamento", "perfil", "fim"])


if __name__ == "__main__":
    unittest.main()

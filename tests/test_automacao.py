"""Publicação: wrangler.jsonc, workflow de deploy na Cloudflare, requirements e .gitignore."""
from __future__ import annotations

import json
import re
import unittest

from tests.helpers import RAIZ, ler_texto


def _jsonc(texto: str) -> dict:
    """JSONC simples: remove comentários // de linha inteira (o arquivo não tem vírgulas finais)."""
    sem = "\n".join(l for l in texto.splitlines() if not l.lstrip().startswith("//"))
    return json.loads(sem)


WRANGLER = _jsonc(ler_texto(RAIZ / "wrangler.jsonc"))
DEPLOY = ler_texto(RAIZ / ".github" / "workflows" / "deploy.yml")


class TestWrangler(unittest.TestCase):
    def test_worker_de_assets_na_pasta_docs(self):
        self.assertEqual(WRANGLER["name"], "arrecadacao-federal")
        self.assertEqual(WRANGLER["assets"]["directory"], "./docs")
        self.assertTrue((RAIZ / "docs" / "index.html").is_file())
        self.assertNotIn("main", WRANGLER, "Worker só de assets não tem código")

    def test_dominio_proprio_sem_workers_dev(self):
        rotas = WRANGLER["routes"]
        self.assertEqual(len(rotas), 1)
        self.assertEqual(rotas[0]["pattern"], "arrecadacaofederal.gfvdata.com")
        self.assertIs(rotas[0]["custom_domain"], True)
        self.assertIs(WRANGLER["workers_dev"], False)
        self.assertRegex(WRANGLER["compatibility_date"], r"^\d{4}-\d{2}-\d{2}$")
        self.assertRegex(WRANGLER["account_id"], r"^[0-9a-f]{32}$")

    def test_sem_recurso_pago(self):
        for chave in ("r2_buckets", "durable_objects", "queues", "vectorize"):
            self.assertNotIn(chave, WRANGLER)


class TestDeployYml(unittest.TestCase):
    def test_dispara_na_main_e_manual(self):
        self.assertRegex(DEPLOY, r"on:\n  push:\n    branches: \[main\]")
        self.assertIn("workflow_dispatch:", DEPLOY)

    def test_usa_wrangler_4_fixo_com_segredo_e_conta_do_wrangler(self):
        # wrangler-action@v3 instala o wrangler 3, que recusa Worker só de assets.
        self.assertNotIn("uses: cloudflare/wrangler-action", DEPLOY)
        self.assertRegex(DEPLOY, r"npx --yes wrangler@4\.\d+\.\d+ deploy")
        self.assertIn("secrets.CLOUDFLARE_API_TOKEN", DEPLOY)
        self.assertIn(f"CLOUDFLARE_ACCOUNT_ID: {WRANGLER['account_id']}", DEPLOY)
        self.assertIn("actions/checkout@", DEPLOY)
        self.assertIn("actions/setup-node@", DEPLOY)

    def test_sem_token_so_avisa_e_nao_publica(self):
        self.assertRegex(DEPLOY, r"if: steps\.token\.outputs\.ok == 'sim'")
        self.assertIn("::warning::", DEPLOY)

    def test_permissao_minima_e_sem_execucao_concorrente(self):
        self.assertRegex(DEPLOY, r"permissions:\n  contents: read")
        self.assertIn("concurrency:", DEPLOY)


class TestDependenciasEGit(unittest.TestCase):
    def test_requirements(self):
        req = ler_texto(RAIZ / "requirements.txt")
        for pacote in ("requests", "pandas", "openpyxl"):
            self.assertRegex(req, rf"(?m)^{pacote}>=")

    def test_brutos_fora_do_git_e_pycache_ignorado(self):
        gi = ler_texto(RAIZ / ".gitignore")
        self.assertIn("dados/brutos/*", gi)
        self.assertIn("__pycache__/", gi)
        self.assertTrue(re.search(r"\.wrangler/", gi))


if __name__ == "__main__":
    unittest.main()

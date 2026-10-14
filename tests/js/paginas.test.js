// Testes do painel sem navegador: node --test tests/js
// Carrega docs/js/app-v2.js num contexto `vm` com um DOM falso, Chart.js falso e os JSON reais de docs/dados.
"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const DOCS = path.resolve(__dirname, "..", "..", "docs");
const lerJson = (rel) => JSON.parse(fs.readFileSync(path.join(DOCS, rel), "utf8"));
const lerTexto = (rel) => fs.readFileSync(path.join(DOCS, rel), "utf8");

// ---------- DOM falso ----------
function elemento() {
  const el = {
    hidden: false, innerHTML: "", textContent: "", value: "", dataset: {}, children: [], style: {},
    clientWidth: 1000,
    classList: { add() {}, remove() {}, toggle() {}, contains: () => false },
    addEventListener() {}, setAttribute() {}, getAttribute: () => null,
    querySelector: () => elemento(), querySelectorAll: () => [],
    closest: () => null,
  };
  el.parentElement = { clientWidth: 1000 };
  return el;
}
function documentoFalso() {
  const porId = new Map();
  return {
    porId,
    body: { dataset: {} },
    documentElement: elemento(),
    getElementById(id) {
      if (!porId.has(id)) porId.set(id, elemento());
      return porId.get(id);
    },
    querySelector: () => elemento(),
    querySelectorAll: () => [],
  };
}
class ChartFalso {
  static register() {}
  constructor(canvas, config) { this.config = config; ChartFalso.instancias.push(this); }
  destroy() {}
}
ChartFalso.instancias = [];
const esperar = () => new Promise((r) => setTimeout(r, 20));

// ---------- app-v2.js ----------
/** Carrega o script inteiro (inclusive iniciar()) com fetch lendo docs/; opções simulam arquivos ausentes. */
async function carregarPainel({ semEventos = false, semNotas = false, semDados = false } = {}) {
  const document = documentoFalso();
  const pedidos = [];
  const fetch = async (url) => {
    pedidos.push(url);
    const ausente = (semEventos && url.includes("eventos_")) || (semNotas && url.includes("notas_"))
      || (semDados && url.includes("arrecadacao_federal.json"));
    if (ausente || !fs.existsSync(path.join(DOCS, url))) return { ok: false, status: 404, json: async () => ({}) };
    return { ok: true, status: 200, json: async () => lerJson(url) };
  };
  ChartFalso.instancias = [];
  const erros = [];
  const ctx = vm.createContext({
    window: { innerWidth: 1200, matchMedia: () => ({ matches: false, addEventListener() {} }) },
    document, fetch, Chart: ChartFalso, console: { ...console, error: (...a) => erros.push(a), warn() {} },
    localStorage: { setItem() {}, getItem: () => null },
    Intl, Date, Math, Number, String, Array, Object, JSON, Promise, Set,
    getComputedStyle: () => ({ getPropertyValue: () => "#123456" }),
  });
  vm.runInContext(lerTexto("js/app-v2.js"), ctx, { filename: "app-v2.js" });
  for (let i = 0; i < 5; i++) await esperar();
  return {
    ctx, document, pedidos, erros,
    el: (id) => document.getElementById(id),
    rodar: (codigo) => JSON.parse(JSON.stringify(vm.runInContext(codigo, ctx) ?? null)),
  };
}

test("painel carrega os três JSON e renderiza narrativa, rodapé e gráficos sem lançar erro", async () => {
  const p = await carregarPainel();
  assert.deepEqual(p.erros, []);
  for (const f of ["dados/arrecadacao_federal.json", "dados/eventos_arrecadacao_federal.json", "dados/notas_arrecadacao_federal.json"]) {
    assert.ok(p.pedidos.includes(f), `não pediu ${f}`);
  }
  const dados = lerJson("dados/arrecadacao_federal.json");
  const abertura = p.el("txt-abertura").innerHTML;
  assert.match(abertura, /Nos 12 meses até dez\/2025/);
  assert.match(abertura, /<strong>R\$ \d+,\d+ tri<\/strong>/);
  assert.match(abertura, /<strong>Imposto de Renda<\/strong>/);   // maior tributo nos últimos 12 meses
  assert.ok(p.el("rodape-fonte-v2").textContent.includes(dados.meta.fonte));
  assert.match(p.el("rodape-fonte-v2").textContent, /jan\/1994 a dez\/2025/);
  assert.equal(ChartFalso.instancias.length, 2);
  assert.equal(ChartFalso.instancias[0].config.type, "bar");
  assert.equal(ChartFalso.instancias[1].config.type, "line");
});

test("composição: 6 principais + Demais e fatias somam 100% em cada ano", async () => {
  const p = await carregarPainel();
  const dados = lerJson("dados/arrecadacao_federal.json");
  const principais = p.rodar("principais");
  assert.equal(principais.length, 6);
  const maiores = [...dados.kpis.por_tributo].sort((a, b) => b.valor_total - a.valor_total).slice(0, 6).map((x) => x.tributo);
  assert.deepEqual(principais, maiores);
  const ultimo = dados.labels.length - 1;
  for (const precos of ["corrente", "constante"]) {
    const r = p.rodar(`participacaoPorAno(0, ${ultimo}, '${precos}')`);
    assert.equal(r.itens.length, 7);
    assert.equal(r.anos.length, dados.anos.length);
    r.anos.forEach((_, i) => {
      const soma = r.itens.reduce((s, t) => s + (r.share[t][i] ?? 0), 0);
      assert.ok(Math.abs(soma - 100) < 1e-6, `${precos} ${r.anos[i]}: ${soma}`);
    });
  }
  assert.match(p.el("txt-meio").innerHTML, /Entre \d{4} e 2025, a fatia de/);
});

test("formatação de valores (R$ milhões), percentuais e meses", async () => {
  const { rodar } = await carregarPainel();
  assert.equal(rodar("fmtMesAno('2025-12')"), "dez/2025");
  assert.equal(rodar("fmtValor(null)"), "—");
  assert.equal(rodar("fmtValor(2886874.8)"), "R$ 2,89 tri");
  assert.equal(rodar("fmtValor(292723.87)"), "R$ 292,7 bi");
  assert.equal(rodar("fmtValor(500)"), "R$ 500 mi");
  assert.equal(rodar("fmtPct(null)"), "—");
  assert.equal(rodar("fmtPct(28.48)"), "28,5%");
  assert.equal(rodar("fmtVezes(3.14)"), "3,1×");
  assert.equal(rodar("urlSegura('javascript:alert(1)')"), "#");
  assert.equal(rodar("urlSegura('https://exemplo.gov.br/a?b=1&c=2')"), "https://exemplo.gov.br/a?b=1&amp;c=2");
  assert.equal(rodar("esc('<b>\"x\"</b>')"), "&lt;b&gt;&quot;x&quot;&lt;/b&gt;");
});

test("períodos 10A/5A/1A/tudo viram índices sobre as labels", async () => {
  const { rodar } = await carregarPainel();
  const ultimo = lerJson("dados/arrecadacao_federal.json").labels.length - 1;
  assert.deepEqual(rodar("periodoParaIndices('tudo')"), [0, ultimo]);
  assert.deepEqual(rodar("periodoParaIndices('10a')"), [ultimo - 119, ultimo]);
  assert.deepEqual(rodar("periodoParaIndices('5a')"), [ultimo - 59, ultimo]);
  assert.deepEqual(rodar("periodoParaIndices('1a')"), [ultimo - 11, ultimo]);
});

test("CAGR e soma móvel: valores conhecidos e lacunas de tributo não registrado", async () => {
  const { rodar } = await carregarPainel();
  assert.ok(Math.abs(rodar("cagrAA([100, null, null, null, null, null, null, null, null, null, null, null, 121], 0, 12)") - 21) < 1e-9);
  assert.equal(rodar("cagrAA([0, 0, 5, null], 0, 3)"), null);
  const m = rodar("somaMovel12([1,1,1,1,1,1,1,1,1,1,1,1,2,0])");
  assert.equal(m[10], null);
  assert.equal(m[11], 12);
  assert.equal(m[12], 13);
  assert.equal(m[13], null);                       // janela com zero -> lacuna
});

test("eventos e narrativa de fechamento seguem o foco e o período", async () => {
  const p = await carregarPainel();
  const dados = lerJson("dados/arrecadacao_federal.json");
  const todos = JSON.stringify(dados.labels);
  p.rodar(`focoTributo = 'Total'; renderNarrativaEventos(${todos})`);
  const html = p.el("eventos-linha-tempo").innerHTML;
  assert.match(html, /class="evento-item"/);
  assert.match(html, /Plano Real/);
  assert.match(html, /Fonte ↗/);
  p.rodar("renderNarrativaEventos([])");
  assert.match(p.el("eventos-linha-tempo").innerHTML, /Nenhum marco catalogado/);

  const ultimo = dados.labels.length - 1;
  p.rodar(`focoTributo = 'Total'; renderNarrativaFechamento(${ultimo - 119}, ${ultimo})`);
  assert.match(p.el("txt-fechamento").innerHTML, /<strong>arrecadação total<\/strong> (cresceu|recuou)/);
  assert.match(p.el("txt-fechamento").innerHTML, /A série termina em dez\/2025/);
  p.rodar(`focoTributo = 'COFINS'; renderNarrativaFechamento(${ultimo - 119}, ${ultimo})`);
  assert.match(p.el("txt-fechamento").innerHTML, /<strong>COFINS<\/strong> (cresceu|recuou)/);
});

test("trocar foco, período, preços e visão re-renderiza sem lançar erro", async () => {
  const p = await carregarPainel();
  for (const foco of ["Total", ...p.rodar("principais")]) {
    for (const visao of ["12m", "mensal"]) {
      for (const periodo of ["tudo", "10a", "5a", "1a"]) {
        p.rodar(`focoTributo = ${JSON.stringify(foco)}; evoVisao = '${visao}'; evoPeriodo = '${periodo}'; renderGraficoEvolucao()`);
      }
    }
  }
  for (const precos of ["corrente", "constante"]) {
    for (const periodo of ["tudo", "10a", "5a", "1a"]) {
      p.rodar(`compPrecos = '${precos}'; compPeriodo = '${periodo}'; renderGraficoComposicao()`);
    }
  }
  p.rodar("aplicarTemaV2('dark'); aplicarTemaV2('light')");
  assert.deepEqual(p.erros, []);
  assert.match(p.el("desc-evolucao").textContent, /a preços constantes/);
});

test("nota da reforma tributária aparece a partir de notas_*.json e some se o arquivo faltar", async () => {
  const com = await carregarPainel();
  assert.equal(com.el("nota-reforma").hidden, false);
  assert.match(com.el("nota-reforma").innerHTML, /<strong>/);
  const sem = await carregarPainel({ semNotas: true });
  assert.equal(sem.el("nota-reforma").innerHTML, "");
  assert.deepEqual(sem.erros, []);
});

test("sem eventos o painel continua; sem dados mostra mensagem de erro", async () => {
  const semEv = await carregarPainel({ semEventos: true });
  assert.deepEqual(semEv.erros, []);
  assert.match(semEv.el("eventos-linha-tempo").innerHTML, /Nenhum marco catalogado/);
  const semDados = await carregarPainel({ semDados: true });
  assert.match(semDados.el("txt-abertura").textContent, /Não foi possível carregar os dados/);
  assert.equal(ChartFalso.instancias.length, 0);
});

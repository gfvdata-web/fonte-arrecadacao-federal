/* ===== Painel Arrecadação Federal — Etapa 6 =====
   Consome docs/dados/arrecadacao_federal.json (gerado pela Etapa 5).
   O JSON traz só a série mensal; participação, ranking, estatística e a
   agregação anual são recalculados aqui conforme o período selecionado. */

const ARQUIVO_DADOS = "dados/arrecadacao_federal.json";

// Paleta categórica: 15 tributos, na ordem de volume arrecadado.
const PALETA = [
  "#2563eb", "#0ea5a4", "#f59e0b", "#8b5cf6", "#ec4899",
  "#059669", "#ef4444", "#0891b2", "#a16207", "#7c3aed",
  "#db2777", "#65a30d", "#0369a1", "#c2410c", "#94a3b8",
];
const COR_TOTAL = "#0f172a";
const TRIBUTOS_VISIVEIS = 5; // demais séries começam ocultas na legenda

let dados = null;
let base = "corrente";        // "corrente" | "constante"
let granularidade = "anual";  // "anual" | "mensal"
let cores = {};
let graficoEvolucao = null;
let graficoParticipacao = null;

// Índices (em dados.labels) do filtro de período global.
let iInicio = 0, iFim = 0;

// ---------- Formatação ----------
const nf = (casas = 1) => new Intl.NumberFormat("pt-BR", {
  minimumFractionDigits: casas, maximumFractionDigits: casas,
});

/** valor em R$ milhões -> texto compacto. */
function fmtValor(x) {
  if (x == null) return "—";
  const abs = Math.abs(x);
  if (abs >= 1e6) return `R$ ${nf(2).format(x / 1e6)} tri`;
  if (abs >= 1e3) return `R$ ${nf(1).format(x / 1e3)} bi`;
  return `R$ ${nf(0).format(x)} mi`;
}

/** idem, mas sem achatar valores pequenos em "R$ 0 mi" (ex.: Imposto de Exportação). */
function fmtValorPreciso(x) {
  if (x == null) return "—";
  const abs = Math.abs(x);
  if (abs >= 1e3) return fmtValor(x);
  if (abs >= 1) return `R$ ${nf(0).format(x)} mi`;
  if (abs < 0.005) return "R$ 0 mi";
  return `R$ ${nf(2).format(x)} mi`;
}

function fmtPct(x, comSinal = false) {
  if (x == null) return "—";
  const s = comSinal && x > 0 ? "+" : "";
  return `${s}${nf(1).format(x)}%`;
}

const MESES = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"];

/** "2025-12" -> "dez/2025" */
function fmtMesAno(anoMes) {
  const [a, m] = anoMes.split("-");
  return `${MESES[Number(m) - 1]}/${a}`;
}

/** "2025-12" -> "dez/25" (usado nos filtros). */
function fmtMesAnoCurto(anoMes) {
  const [a, m] = anoMes.split("-");
  return `${MESES[Number(m) - 1]}/${a.slice(2)}`;
}

const cssVar = (nome) => getComputedStyle(document.body).getPropertyValue(nome).trim();

// ---------- Cálculos por período ----------
const num = (x) => (x == null ? 0 : x);
const serieDe = (tributo) => dados.series[tributo][base];
const serieTotal = () => dados.total[base];

function somar(serie, i0, i1) {
  let s = 0;
  for (let k = i0; k <= i1; k++) s += num(serie[k]);
  return s;
}

/** Agrega uma série mensal por ano dentro de [i0, i1]. Retorna {anos, valores}. */
function agregarAnual(serie, i0, i1) {
  const anos = [], valores = [];
  for (let k = i0; k <= i1; k++) {
    const ano = dados.labels[k].slice(0, 4);
    if (anos[anos.length - 1] !== ano) { anos.push(ano); valores.push(0); }
    valores[valores.length - 1] += num(serie[k]);
  }
  return { anos, valores };
}

/** Rótulos e séries do gráfico, já na granularidade escolhida. */
function pontosDe(serie) {
  if (granularidade === "mensal") {
    return dados.labels.slice(iInicio, iFim + 1).map((l, i) => ({
      x: fmtMesAno(l), y: serie[iInicio + i],
    }));
  }
  const { anos, valores } = agregarAnual(serie, iInicio, iFim);
  return anos.map((a, i) => ({ x: a, y: valores[i] }));
}

function rotulosGrafico() {
  return granularidade === "mensal"
    ? dados.labels.slice(iInicio, iFim + 1).map(fmtMesAno)
    : agregarAnual(serieTotal(), iInicio, iFim).anos;
}

/** YoY (%): 12 meses terminados em i1 vs. os 12 anteriores. */
function yoy(serie, i0, i1) {
  if (i1 - i0 < 23) return null;
  const atual = somar(serie, i1 - 11, i1);
  const anterior = somar(serie, i1 - 23, i1 - 12);
  return anterior ? (atual / anterior - 1) * 100 : null;
}

/** CAGR anual (%) entre o 1º e o último ano completo do intervalo. */
function cagrAA(serie, i0, i1) {
  const { valores } = agregarAnual(serie, i0, i1);
  const positivos = valores.filter((v) => v > 0);
  if (positivos.length < 2) return null;
  const anos = positivos.length - 1;
  return ((positivos[positivos.length - 1] / positivos[0]) ** (1 / anos) - 1) * 100;
}

/** Ranking por tributo no intervalo selecionado. */
function calcularRanking(i0, i1) {
  const geral = dados.tributos.reduce((s, t) => s + somar(serieDe(t), i0, i1), 0);
  const linhas = dados.tributos.map((tributo) => {
    const serie = serieDe(tributo);
    const acumulado = somar(serie, i0, i1);
    let pico = null, picoIdx = -1;
    for (let k = i0; k <= i1; k++) {
      if (serie[k] != null && (pico == null || serie[k] > pico)) { pico = serie[k]; picoIdx = k; }
    }
    return {
      tributo,
      valor_total: acumulado,
      part_pct: geral ? (acumulado / geral) * 100 : null,
      valor_ult12m: i1 - i0 >= 11 ? somar(serie, i1 - 11, i1) : acumulado,
      yoy_pct: yoy(serie, i0, i1),
      cagr_aa_pct: cagrAA(serie, i0, i1),
      pico_valor: pico,
      pico_mes: picoIdx >= 0 ? dados.labels[picoIdx] : null,
    };
  });
  linhas.sort((a, b) => b.valor_total - a.valor_total);
  return linhas;
}

/** Estatística descritiva da série mensal do tributo em [i0, i1]. */
function calcularEstatistica(tributo, i0, i1) {
  const serie = serieDe(tributo);
  const arr = [];
  for (let k = i0; k <= i1; k++) if (serie[k] != null) arr.push(serie[k]);
  const n = arr.length;
  if (!n) {
    return { media: null, mediana: null, desvio_padrao: null, coef_variacao_pct: null, minimo: null, maximo: null };
  }
  const media = arr.reduce((s, x) => s + x, 0) / n;
  const ord = [...arr].sort((a, b) => a - b);
  const mediana = n % 2 ? ord[(n - 1) / 2] : (ord[n / 2 - 1] + ord[n / 2]) / 2;
  let desvio = null;
  if (n > 1) {
    const soma2 = arr.reduce((s, x) => s + (x - media) ** 2, 0);
    desvio = Math.sqrt(soma2 / (n - 1)); // amostral (ddof=1), igual ao pandas
  }
  return {
    media,
    mediana,
    desvio_padrao: desvio,
    coef_variacao_pct: (media && desvio) ? (desvio / media) * 100 : null,
    minimo: ord[0],
    maximo: ord[n - 1],
  };
}

// ---------- Renderização ----------
const textoBase = () => (base === "corrente"
  ? "preços correntes"
  : `preços constantes de ${fmtMesAno(dados.meta.mes_base_constante)}`);

function periodoTexto() {
  return `${fmtMesAnoCurto(dados.labels[iInicio])}–${fmtMesAnoCurto(dados.labels[iFim])}`;
}

function renderCabecalho() {
  const meta = dados.meta;
  document.getElementById("descricao-fonte").textContent = meta.descricao;
  document.getElementById("meta-info").textContent =
    `Período: ${fmtMesAno(meta.periodo.inicio)} – ${fmtMesAno(meta.periodo.fim)} · `
    + `${dados.kpis.totais.meses_cobertos} meses · Atualizado em `
    + `${new Date(meta.gerado_em).toLocaleDateString("pt-BR")}`;
  document.getElementById("rodape-fonte").textContent =
    `Fonte: ${meta.fonte} · Licença ${meta.licenca}.`;
  document.getElementById("rodape-obs").textContent =
    "Valores em R$ milhões. Série mensal de 1994 em diante (antes disso a publicação da RFB "
    + `mistura quatro padrões monetários). Deflator: ${meta.deflator}. `
    + "Projeto de estudo — dados abertos da Receita Federal do Brasil.";
}

function renderKpis() {
  const ranking = calcularRanking(iInicio, iFim);
  const lider = ranking[0];
  const total = somar(serieTotal(), iInicio, iFim);
  const meses = iFim - iInicio + 1;
  const yoyTotal = yoy(serieTotal(), iInicio, iFim);
  const cartoes = [
    {
      rotulo: `Arrecadação no período`,
      valor: fmtValor(total),
      apoio: `${periodoTexto()} · ${meses} meses · ${textoBase()}`,
    },
    {
      rotulo: "Média mensal",
      valor: fmtValor(total / meses),
      apoio: `Média das ${meses} observações do período`,
    },
    {
      rotulo: "Tributo com maior participação",
      valor: lider.tributo,
      apoio: `${fmtPct(lider.part_pct)} do arrecadado no período`,
    },
    {
      rotulo: "Variação YoY do total",
      valor: fmtPct(yoyTotal, true),
      apoio: yoyTotal == null
        ? "Requer ao menos 24 meses no período"
        : `Últimos 12 meses vs. 12 anteriores (até ${fmtMesAnoCurto(dados.labels[iFim])})`,
      classe: yoyTotal == null ? "" : (yoyTotal >= 0 ? "pos" : "neg"),
    },
  ];
  document.getElementById("kpis").innerHTML = cartoes.map((c) => `
    <div class="kpi">
      <p class="rotulo">${c.rotulo}</p>
      <p class="valor">${c.valor}</p>
      <p class="apoio ${c.classe || ""}">${c.apoio}</p>
    </div>`).join("");
}

function renderEvolucao() {
  const passo = granularidade === "anual" ? "ano" : "mês";
  document.getElementById("titulo-evolucao").textContent =
    `Arrecadação por ${passo} (${textoBase()}). Clique na legenda para incluir ou remover séries.`;

  const datasets = [{
    label: "Total geral",
    data: pontosDe(serieTotal()).map((p) => p.y),
    borderColor: COR_TOTAL,
    backgroundColor: COR_TOTAL,
    borderWidth: 2.5,
    pointRadius: 0,
    pointHoverRadius: 4,
    tension: 0.25,
  }];
  dados.tributos.forEach((tributo, i) => {
    datasets.push({
      label: tributo,
      data: pontosDe(serieDe(tributo)).map((p) => p.y),
      borderColor: cores[tributo],
      backgroundColor: cores[tributo],
      borderWidth: 2,
      pointRadius: 0,
      pointHoverRadius: 4,
      tension: 0.25,
      hidden: i >= TRIBUTOS_VISIVEIS,
    });
  });

  if (graficoEvolucao) graficoEvolucao.destroy();
  graficoEvolucao = new Chart(document.getElementById("gEvolucao"), {
    type: "line",
    data: { labels: rotulosGrafico(), datasets },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: { mode: "index", intersect: false },
      plugins: {
        legend: { labels: { color: cssVar("--texto"), usePointStyle: true, boxWidth: 8 } },
        tooltip: { callbacks: { label: (i) => `${i.dataset.label}: ${fmtValorPreciso(i.parsed.y)}` } },
      },
      scales: {
        x: { ticks: { color: cssVar("--texto-suave"), maxTicksLimit: 14, autoSkip: true }, grid: { display: false } },
        y: { ticks: { color: cssVar("--texto-suave"), callback: (v) => fmtValor(v) }, grid: { color: cssVar("--borda") } },
      },
    },
  });
}

function renderParticipacao() {
  const itens = calcularRanking(iInicio, iFim);
  const total = itens.reduce((s, x) => s + x.valor_total, 0);
  document.getElementById("titulo-participacao").textContent =
    `Fatia de cada tributo no arrecadado de ${periodoTexto()} (${textoBase()}).`;

  if (graficoParticipacao) graficoParticipacao.destroy();
  graficoParticipacao = new Chart(document.getElementById("gParticipacao"), {
    type: "doughnut",
    data: {
      labels: itens.map((x) => x.tributo),
      datasets: [{
        data: itens.map((x) => x.valor_total),
        backgroundColor: itens.map((x) => cores[x.tributo]),
        borderColor: cssVar("--superficie"),
        borderWidth: 2,
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      cutout: "58%",
      plugins: {
        legend: { position: "bottom", labels: { color: cssVar("--texto"), usePointStyle: true, boxWidth: 8, font: { size: 10 } } },
        tooltip: {
          callbacks: {
            label: (i) => {
              const pct = total ? (i.parsed / total) * 100 : 0;
              return `${i.label}: ${fmtValorPreciso(i.parsed)} (${fmtPct(pct)})`;
            },
          },
        },
      },
    },
  });
}

function pilula(tributo) {
  return `<span class="pilula"><span class="ponto" style="background:${cores[tributo] || cssVar("--texto-suave")}"></span>${tributo}</span>`;
}

const cls = (x) => (x == null ? "nulo" : x >= 0 ? "pos" : "neg");

function renderTabelaRanking() {
  document.getElementById("desc-ranking").textContent =
    `Período ${periodoTexto()} · ${textoBase()}. Arrecadado e participação acumulam o período; `
    + "YoY compara os 12 meses finais com os 12 anteriores; CAGR usa os anos do intervalo.";

  document.querySelector("#tabela-ranking tbody").innerHTML =
    calcularRanking(iInicio, iFim).map((t) => `
      <tr>
        <td>${pilula(t.tributo)}</td>
        <td class="num">${fmtValorPreciso(t.valor_total)}</td>
        <td class="num">${fmtPct(t.part_pct)}</td>
        <td class="num">${fmtValorPreciso(t.valor_ult12m)}</td>
        <td class="num ${cls(t.yoy_pct)}">${fmtPct(t.yoy_pct, true)}</td>
        <td class="num ${cls(t.cagr_aa_pct)}">${fmtPct(t.cagr_aa_pct, true)}</td>
        <td class="num">${fmtValorPreciso(t.pico_valor)}${t.pico_mes ? ` <span class="nulo">(${fmtMesAnoCurto(t.pico_mes)})</span>` : ""}</td>
      </tr>`).join("");
}

function renderComposicao() {
  const sel = document.getElementById("composicao-tributo");
  const escolhido = sel.value;
  const itens = dados.detalhes[escolhido] || [];
  document.getElementById("desc-composicao").textContent = itens.length
    ? `Aberturas de ${escolhido} publicadas pela RFB — acumulado dos últimos 12 meses da série `
      + `(até ${fmtMesAno(dados.kpis.totais.mes_ref)}), a preços correntes.`
    : "Este tributo é publicado sem aberturas internas.";

  document.querySelector("#tabela-composicao tbody").innerHTML = itens.length
    ? itens.map((d) => `
        <tr>
          <td>${d.rotulo}</td>
          <td class="num">${fmtValorPreciso(d.valor_ult12m)}</td>
          <td class="num">${fmtPct(d.part_pct)}</td>
        </tr>`).join("")
    : `<tr><td colspan="3" class="nulo">Sem aberturas para ${escolhido}.</td></tr>`;
}

function renderTabelaEstatistica() {
  document.getElementById("titulo-estatistica").textContent =
    `Série mensal em ${periodoTexto()} — ${textoBase()}.`;
  document.querySelector("#tabela-estatistica tbody").innerHTML =
    dados.tributos.map((tributo) => {
      const e = calcularEstatistica(tributo, iInicio, iFim);
      return `
        <tr>
          <td>${pilula(tributo)}</td>
          <td class="num">${fmtValorPreciso(e.media)}</td>
          <td class="num">${fmtValorPreciso(e.mediana)}</td>
          <td class="num">${fmtValorPreciso(e.desvio_padrao)}</td>
          <td class="num">${fmtPct(e.coef_variacao_pct)}</td>
          <td class="num">${fmtValorPreciso(e.minimo)}</td>
          <td class="num">${fmtValorPreciso(e.maximo)}</td>
        </tr>`;
    }).join("");
}

function renderTudo() {
  renderKpis();
  renderEvolucao();
  renderParticipacao();
  renderTabelaRanking();
  renderTabelaEstatistica();
}

// ---------- Controles ----------
function ligarAlternadores() {
  document.querySelectorAll("[data-base]").forEach((btn) => {
    btn.addEventListener("click", () => {
      if (btn.dataset.base === base) return;
      document.querySelectorAll("[data-base]").forEach((b) => b.classList.remove("ativo"));
      btn.classList.add("ativo");
      base = btn.dataset.base;
      renderTudo();
    });
  });
  document.querySelectorAll("[data-granularidade]").forEach((btn) => {
    btn.addEventListener("click", () => {
      if (btn.dataset.granularidade === granularidade) return;
      document.querySelectorAll("[data-granularidade]").forEach((b) => b.classList.remove("ativo"));
      btn.classList.add("ativo");
      granularidade = btn.dataset.granularidade;
      renderEvolucao();
    });
  });
}

function preencherSelectMeses(sel, idxSelecionado) {
  sel.innerHTML = dados.labels
    .map((l, i) => `<option value="${i}">${fmtMesAnoCurto(l)}</option>`)
    .join("");
  sel.value = String(idxSelecionado);
}

function ligarFiltroPeriodo() {
  const selI = document.getElementById("periodo-inicio");
  const selF = document.getElementById("periodo-fim");
  preencherSelectMeses(selI, iInicio);
  preencherSelectMeses(selF, iFim);
  selI.addEventListener("change", () => {
    iInicio = Number(selI.value);
    if (iInicio > iFim) { iFim = iInicio; selF.value = String(iFim); }
    renderTudo();
  });
  selF.addEventListener("change", () => {
    iFim = Number(selF.value);
    if (iFim < iInicio) { iInicio = iFim; selI.value = String(iInicio); }
    renderTudo();
  });
}

function ligarSelectComposicao() {
  const sel = document.getElementById("composicao-tributo");
  const comAberturas = dados.tributos.filter((t) => dados.detalhes[t]);
  sel.innerHTML = comAberturas.map((t) => `<option value="${t}">${t}</option>`).join("");
  sel.addEventListener("change", renderComposicao);
}

async function iniciar() {
  try {
    const resp = await fetch(ARQUIVO_DADOS);
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    dados = await resp.json();
  } catch (erro) {
    document.getElementById("meta-info").textContent =
      "Não foi possível carregar os dados. Rode o pipeline "
      + `(python run_pipeline.py arrecadacao_federal) para gerar ${ARQUIVO_DADOS}.`;
    console.error(erro);
    return;
  }

  dados.tributos.forEach((t, i) => { cores[t] = PALETA[i % PALETA.length]; });
  iInicio = 0;
  iFim = dados.labels.length - 1;

  renderCabecalho();
  ligarFiltroPeriodo();
  ligarSelectComposicao();
  ligarAlternadores();
  renderComposicao();
  renderTudo();
}

iniciar();

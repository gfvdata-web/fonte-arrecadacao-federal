/* ===== Arrecadação Federal — painel =====
   Consome dados/arrecadacao_federal.json (Etapa 5), eventos_arrecadacao_federal.json e
   notas_arrecadacao_federal.json (reforma tributária). Só lê e desenha: nenhuma lista de
   tributos ou de números mora aqui. Os 6 maiores tributos vêm de kpis.por_tributo. */

const ARQUIVO_DADOS = "dados/arrecadacao_federal.json";
const ARQUIVO_EVENTOS = "dados/eventos_arrecadacao_federal.json";
const ARQUIVO_NOTAS = "dados/notas_arrecadacao_federal.json";
const N_PRINCIPAIS = 6;       // tributos separados na composição; o resto vira "Demais"
const ROTULO_TOTAL = "Total"; // mesmo valor usado em eventos[].tributos
const ROTULO_DEMAIS = "Demais";
const PERIODOS = [
  { codigo: "tudo", rotulo: "Desde sempre" },
  { codigo: "10a", rotulo: "10A" },
  { codigo: "5a", rotulo: "5A" },
  { codigo: "1a", rotulo: "1A" },
];

if (window.ChartDataLabels) Chart.register(window.ChartDataLabels);
if (window["chartjs-plugin-annotation"]) Chart.register(window["chartjs-plugin-annotation"]);

let dados = null;
let eventos = [];
let principais = [];   // nomes dos N maiores tributos, na ordem do JSON
let graficoComposicao = null;
let graficoEvolucao = null;

let compPrecos = "constante";  // "corrente" | "constante"
let compPeriodo = "10a";
let evoVisao = "12m";          // "12m" | "mensal"
let evoPeriodo = "tudo";
let focoTributo = ROTULO_TOTAL;

// ---------- Formatação ----------
const nf = (casas = 1) => new Intl.NumberFormat("pt-BR", { minimumFractionDigits: casas, maximumFractionDigits: casas });
const MESES = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"];
const fmtMesAno = (anoMes) => { const [a, m] = anoMes.split("-"); return `${MESES[Number(m) - 1]}/${a}`; };
const fmtPct = (x, casas = 1) => (x == null ? "—" : `${nf(casas).format(x)}%`);
const fmtVezes = (x) => `${nf(1).format(x)}×`;

/** Valores da fonte estão em R$ milhões. */
function fmtValor(x) {
  if (x == null) return "—";
  const abs = Math.abs(x);
  if (abs >= 1e6) return `R$ ${nf(2).format(x / 1e6)} tri`;
  if (abs >= 1e3) return `R$ ${nf(1).format(x / 1e3)} bi`;
  return `R$ ${nf(0).format(x)} mi`;
}
const cssVar = (nome) => getComputedStyle(document.body).getPropertyValue(nome).trim();
const num = (x) => (x == null ? 0 : x);

/** Texto vindo dos JSONs sempre passa por aqui antes de ir para innerHTML. */
function esc(texto) {
  return String(texto ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}
/** Só deixa passar links http(s) nos hrefs vindos do JSON. */
const urlSegura = (url) => (/^https?:\/\//.test(url) ? esc(url) : "#");

// ---------- Cores por tributo (variáveis CSS --c-1..--c-6, --c-demais, --c-total) ----------
function corTributo(nome) {
  if (nome === ROTULO_TOTAL) return cssVar("--c-total");
  if (nome === ROTULO_DEMAIS) return cssVar("--c-demais");
  const i = principais.indexOf(nome);
  return cssVar(i >= 0 ? `--c-${i + 1}` : "--c-demais");
}
function pilulaTributo(nome) {
  return `<span class="pilula-tributo"><span class="ponto-v2" style="background:${corTributo(nome)}"></span>${esc(nome)}</span>`;
}

// ---------- Séries ----------
const serieTributo = (nome, precos) => (nome === ROTULO_TOTAL ? dados.total[precos] : dados.series[nome][precos]);
const nomeFoco = () => (focoTributo === ROTULO_TOTAL ? "arrecadação total" : focoTributo);

/** Soma de uma série mensal dentro do ano indicado. */
function somaAno(serie, ano) {
  let s = 0;
  dados.labels.forEach((l, k) => { if (l.startsWith(ano)) s += num(serie[k]); });
  return s;
}

/** Soma móvel de 12 meses. Janela com algum mês nulo ou zero vira null: zero aqui significa
 *  "tributo ainda não registrado" (ex.: previdenciária em 1994) e entraria como valor falso. */
function somaMovel12(serie) {
  return serie.map((_, k) => {
    if (k < 11) return null;
    let s = 0;
    for (let j = k - 11; j <= k; j++) {
      if (serie[j] == null || serie[j] === 0) return null;
      s += serie[j];
    }
    return s;
  });
}

/** Converte um código de período em índices [i0, i1] sobre dados.labels. */
function periodoParaIndices(codigo) {
  const last = dados.labels.length - 1;
  if (codigo === "10a") return [Math.max(0, last - 119), last];
  if (codigo === "5a") return [Math.max(0, last - 59), last];
  if (codigo === "1a") return [Math.max(0, last - 11), last];
  return [0, last]; // "tudo"
}

/** CAGR anual (%) entre o 1º e o último valor positivo de uma série dentro de [i0, i1]. */
function cagrAA(serie, i0, i1) {
  let iPrim = -1, iUlt = -1;
  for (let k = i0; k <= i1; k++) {
    if (serie[k] != null && serie[k] > 0) { if (iPrim < 0) iPrim = k; iUlt = k; }
  }
  if (iPrim < 0 || iUlt === iPrim) return null;
  const anos = (iUlt - iPrim) / 12;
  return ((serie[iUlt] / serie[iPrim]) ** (1 / anos) - 1) * 100;
}

/** Anos (strings) que aparecem dentro de [i0, i1]. */
function anosDoPeriodo(i0, i1) {
  const anos = [];
  for (let k = i0; k <= i1; k++) {
    const a = dados.labels[k].slice(0, 4);
    if (!anos.includes(a)) anos.push(a);
  }
  return anos;
}

/** Participação (%) de cada item (principais + Demais) no total de cada ano do período. */
function participacaoPorAno(i0, i1, precos) {
  const anos = anosDoPeriodo(i0, i1);
  const itens = [...principais, ROTULO_DEMAIS];
  const share = {};
  itens.forEach((t) => { share[t] = []; });
  anos.forEach((ano) => {
    const total = somaAno(dados.total[precos], ano);
    let somaPrincipais = 0;
    principais.forEach((t) => {
      const v = somaAno(dados.series[t][precos], ano);
      somaPrincipais += v;
      share[t].push(total ? (v / total) * 100 : null);
    });
    share[ROTULO_DEMAIS].push(total ? ((total - somaPrincipais) / total) * 100 : null);
  });
  return { anos, itens, share };
}

// ---------- Rodapé ----------
function renderRodape() {
  const meta = dados.meta;
  document.getElementById("rodape-fonte-v2").textContent =
    `Fonte: ${meta.fonte}. Licença ${meta.licenca}. Dados gerados em ${new Date(meta.gerado_em).toLocaleDateString("pt-BR")}; `
    + `série de ${fmtMesAno(meta.periodo.inicio)} a ${fmtMesAno(meta.periodo.fim)}.`;
}

// ---------- Narrativa ----------
function renderNarrativaAbertura() {
  const last = dados.labels.length - 1;
  const ult12 = (serie) => serie.slice(last - 11, last + 1).reduce((s, v) => s + num(v), 0);
  const total12 = ult12(dados.total.corrente);
  const lider = dados.tributos
    .map((t) => ({ tributo: t, v: ult12(dados.series[t].corrente) }))
    .sort((a, b) => b.v - a.v)[0];
  const anoIni = dados.anos[1];                       // 1º ano inteiro depois do plano de estabilização
  const anoFim = dados.anos[dados.anos.length - 1];
  const vezes = somaAno(dados.total.constante, anoFim) / somaAno(dados.total.constante, anoIni);
  document.getElementById("txt-abertura").innerHTML =
    `Nos 12 meses até ${fmtMesAno(dados.labels[last])}, a Receita Federal arrecadou `
    + `<strong>${fmtValor(total12)}</strong>. Já descontada a inflação, isso é <strong>${fmtVezes(vezes)}</strong> `
    + `o que se arrecadava em ${anoIni}. O maior pedaço vem do <strong>${esc(lider.tributo)}</strong>: `
    + `<strong>${fmtPct((lider.v / total12) * 100)}</strong> de tudo.`;
}

function renderNarrativaMeio(anos, itens, share) {
  const alvo = document.getElementById("txt-meio");
  const iFim = anos.length - 1;
  let ganho = null, perda = null;
  itens.forEach((t) => {
    const ini = share[t][0], fim = share[t][iFim];
    if (ini == null || fim == null || ini <= 0) return; // fatia zero no início = tributo ainda não registrado
    const delta = fim - ini;
    if (!ganho || delta > ganho.delta) ganho = { t, ini, fim, delta };
    if (!perda || delta < perda.delta) perda = { t, ini, fim, delta };
  });
  if (!ganho || anos.length < 2) { alvo.textContent = "Sem dados suficientes no período selecionado."; return; }
  alvo.innerHTML =
    `Entre ${anos[0]} e ${anos[iFim]}, a fatia de <strong>${esc(ganho.t)}</strong> no total passou de ${fmtPct(ganho.ini)} para ${fmtPct(ganho.fim)}`
    + (perda.t !== ganho.t
      ? `, enquanto <strong>${esc(perda.t)}</strong> foi de ${fmtPct(perda.ini)} para ${fmtPct(perda.fim)}.`
      : ".");
}

/** Eventos do foco (ou do Total) dentro do período visível, em ordem de data. */
function eventosEmFoco(labelsPeriodo) {
  return eventos
    .filter((e) => (e.tributos.includes(focoTributo) || e.tributos.includes(ROTULO_TOTAL)) && labelsPeriodo.includes(e.data))
    .sort((a, b) => a.data.localeCompare(b.data));
}

function renderNarrativaEventos(labelsPeriodo) {
  const relevantes = eventosEmFoco(labelsPeriodo);
  const alvo = document.getElementById("eventos-linha-tempo");
  const titulo = `<p class="eventos-titulo">O que pode explicar a trajetória: ${esc(nomeFoco())}</p>`;
  if (!relevantes.length) {
    alvo.innerHTML = titulo
      + `<p class="eventos-vazio">Nenhum marco catalogado nesta janela de tempo — amplie o período para ver o contexto.</p>`;
    return;
  }
  alvo.innerHTML = titulo + relevantes.map((e, i) => `
    <div class="evento-item">
      <div class="evento-data">${fmtMesAno(e.data)}</div>
      <div class="evento-corpo">
        <h4><span class="evento-num">${i + 1}</span>${esc(e.titulo)}</h4>
        <p>${esc(e.descricao)} <a href="${urlSegura(e.fonte)}" target="_blank" rel="noopener">Fonte ↗</a></p>
      </div>
    </div>`).join("");
}

function renderNarrativaFechamento(i0, i1) {
  const alvo = document.getElementById("txt-fechamento");
  const rolagem = (nome) => somaMovel12(serieTributo(nome, "constante"));
  const fim = fmtMesAno(dados.labels[dados.labels.length - 1]);
  const aviso = ` A série termina em ${fim}, último mês da série histórica da Receita: 2026 ainda não aparece aqui.`;
  const foco = cagrAA(rolagem(focoTributo), i0, i1);
  const periodo = `${fmtMesAno(dados.labels[i0])} a ${fmtMesAno(dados.labels[i1])}`;
  if (foco == null) {
    alvo.textContent = "Não há variação suficiente no período selecionado para calcular o crescimento." + aviso;
    return;
  }
  const verbo = (x) => (x >= 0 ? "cresceu" : "recuou");
  let contraste = "";
  if (focoTributo === ROTULO_TOTAL) {
    const rank = principais
      .map((t) => ({ t, c: cagrAA(rolagem(t), i0, i1) }))
      .filter((x) => x.c != null)
      .sort((a, b) => b.c - a.c);
    if (rank.length > 1) {
      const topo = rank[0], base = rank[rank.length - 1];
      contraste = `; entre os maiores tributos, <strong>${esc(topo.t)}</strong> ${verbo(topo.c)} ${fmtPct(Math.abs(topo.c))} ao ano e `
        + `<strong>${esc(base.t)}</strong> ${verbo(base.c)} ${fmtPct(Math.abs(base.c))}`;
    }
  } else {
    const tot = cagrAA(rolagem(ROTULO_TOTAL), i0, i1);
    if (tot != null) contraste = `, contra ${fmtPct(Math.abs(tot))} ao ano ${tot >= 0 ? "de alta" : "de queda"} do total`;
  }
  alvo.innerHTML =
    `De ${periodo}, a <strong>${esc(nomeFoco())}</strong> ${verbo(foco)} <strong>${fmtPct(Math.abs(foco))} ao ano</strong> `
    + `acima da inflação (soma de 12 meses, a preços constantes)${contraste}.` + aviso;
}

/** Aviso da reforma tributária (2027), lido de notas_arrecadacao_federal.json. */
async function renderNotaReforma() {
  const alvo = document.getElementById("nota-reforma");
  try {
    const resp = await fetch(ARQUIVO_NOTAS);
    if (!resp.ok) return;
    const notas = await resp.json();
    const c3 = (notas.comparativos || []).find((c) => c.id === "C3");
    const ctx = (notas.contexto_externo || [])[0];
    if (!c3) return;
    alvo.innerHTML = `<strong>${esc(c3.titulo)}.</strong> ${esc(c3.o_que_esperar).replace(/\*/g, "")}`
      + (ctx ? ` <a href="${urlSegura(ctx.url)}" target="_blank" rel="noopener">${esc(ctx.fonte)} ↗</a>` : "");
    alvo.hidden = false;
  } catch (erro) {
    console.warn("Notas não carregadas:", erro);
  }
}

// ---------- Gráfico 1: composição por ano (colunas empilhadas, % do total) ----------
function renderGraficoComposicao() {
  const [i0, i1] = periodoParaIndices(compPeriodo);
  const { anos, itens, share } = participacaoPorAno(i0, i1, compPrecos);

  document.getElementById("desc-composicao").textContent =
    `Fatia de cada tributo no total arrecadado por ano, a preços ${compPrecos === "constante" ? "constantes" : "correntes"} `
    + `(${anos[0]} a ${anos[anos.length - 1]}).`;

  const datasets = itens.map((t) => ({
    label: t,
    data: share[t],
    backgroundColor: corTributo(t),
    maxBarThickness: 46,
    datalabels: {
      color: "#fff",
      font: { family: "IBM Plex Sans", weight: 700, size: 10 },
      backgroundColor: "rgba(0,0,0,.28)",
      borderRadius: 3,
      padding: { top: 2, bottom: 2, left: 4, right: 4 },
      formatter: (v) => (v != null && v >= 7 ? `${Math.round(v)}%` : ""),
    },
  }));

  // Uma coluna por ano; abaixo de PX_POR_GRUPO por coluna a área cresce e vira scroll interno.
  const PX_POR_GRUPO = 40;
  const wrapper = document.getElementById("composicaoScrollInner");
  const larguraMinima = anos.length * PX_POR_GRUPO;
  wrapper.style.width = larguraMinima > wrapper.parentElement.clientWidth ? `${larguraMinima}px` : "100%";

  if (graficoComposicao) graficoComposicao.destroy();
  graficoComposicao = new Chart(document.getElementById("gComposicao"), {
    type: "bar",
    data: { labels: anos, datasets },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { position: "bottom", labels: { color: cssVar("--texto"), usePointStyle: true, boxWidth: 8, font: { family: "IBM Plex Sans" } } },
        tooltip: {
          mode: "index", intersect: false,
          callbacks: { label: (i) => `${i.dataset.label}: ${fmtPct(i.parsed.y)}` },
        },
      },
      interaction: { mode: "index", intersect: false },
      scales: {
        x: { stacked: true, ticks: { color: cssVar("--texto-suave"), autoSkip: true, maxRotation: 0 }, grid: { display: false } },
        y: {
          stacked: true, beginAtZero: true, max: 100,
          ticks: { color: cssVar("--texto-suave"), callback: (v) => `${v}%` },
          grid: { color: cssVar("--borda") },
        },
      },
    },
  });

  renderTabelaComposicao(anos, itens, share);
  renderNarrativaMeio(anos, itens, share);
}

function renderTabelaComposicao(anos, itens, share) {
  document.querySelector("#tabela-composicao thead").innerHTML =
    `<tr><th>Tributo</th>${anos.map((a) => `<th>${a}</th>`).join("")}</tr>`;
  document.querySelector("#tabela-composicao tbody").innerHTML = itens.map((t) => `
    <tr><td>${pilulaTributo(t)}</td>${share[t].map((v) => `<td>${fmtPct(v)}</td>`).join("")}</tr>
  `).join("");
}

// ---------- Gráfico 2: linha do tempo (preços constantes) ----------
/** Linhas verticais tracejadas, numeradas como a lista de marcos abaixo do gráfico. */
function construirAnotacoesEventos(labelsPeriodo) {
  const anotacoes = {};
  eventosEmFoco(labelsPeriodo).forEach((e, idx) => {
    const posicao = labelsPeriodo.indexOf(e.data);
    anotacoes[`evento${idx}`] = {
      type: "line", xMin: posicao, xMax: posicao,
      borderColor: cssVar("--evento-linha"), borderWidth: 1, borderDash: [4, 4],
      label: {
        display: true, content: String(idx + 1), position: "start", rotation: 0,
        backgroundColor: cssVar("--texto"), color: cssVar("--bg"),
        font: { size: 10, family: "IBM Plex Sans", weight: 700 }, padding: 3,
      },
    };
  });
  return anotacoes;
}

function renderGraficoEvolucao() {
  const [i0, i1] = periodoParaIndices(evoPeriodo);
  const bruta = serieTributo(focoTributo, "constante");
  // Mensal: zero vira lacuna (tributo ainda não registrado). 12 meses: ver somaMovel12.
  const serie = evoVisao === "12m" ? somaMovel12(bruta) : bruta.map((v) => (v ? v : null));
  const labelsPeriodo = dados.labels.slice(i0, i1 + 1);
  const cor = corTributo(focoTributo);

  document.getElementById("desc-evolucao").textContent =
    `${evoVisao === "12m" ? "Soma móvel de 12 meses" : "Valor mensal"} de ${nomeFoco()}, a preços constantes (dez/2025), `
    + `de ${fmtMesAno(dados.labels[i0])} a ${fmtMesAno(dados.labels[i1])}.`;

  if (graficoEvolucao) graficoEvolucao.destroy();
  graficoEvolucao = new Chart(document.getElementById("gEvolucao"), {
    type: "line",
    data: {
      labels: labelsPeriodo.map(fmtMesAno),
      datasets: [{
        label: nomeFoco(), data: serie.slice(i0, i1 + 1),
        borderColor: cor, backgroundColor: cor, borderWidth: 3,
        pointRadius: 0, pointHoverRadius: 4, tension: 0.25,
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: { mode: "index", intersect: false },
      plugins: {
        legend: { display: false },
        tooltip: { callbacks: { label: (i) => `${i.dataset.label}: ${fmtValor(i.parsed.y)}` } },
        datalabels: { display: false },
        annotation: { annotations: construirAnotacoesEventos(labelsPeriodo) },
      },
      scales: {
        x: { ticks: { color: cssVar("--texto-suave"), maxTicksLimit: 10, autoSkip: true, maxRotation: 0 }, grid: { display: false } },
        y: { ticks: { color: cssVar("--texto-suave"), callback: (v) => fmtValor(v) }, grid: { color: cssVar("--borda") } },
      },
    },
  });

  renderTabelaEvolucao(i0, i1);
  renderNarrativaFechamento(i0, i1);
  renderNarrativaEventos(labelsPeriodo);
}

/** Tabela anual do tributo em foco: valor constante, valor corrente e variação real sobre o ano anterior. */
function renderTabelaEvolucao(i0, i1) {
  const anos = anosDoPeriodo(i0, i1);
  const cons = serieTributo(focoTributo, "constante"), corr = serieTributo(focoTributo, "corrente");
  document.querySelector("#tabela-evolucao thead").innerHTML =
    `<tr><th>Ano</th><th>Constante (dez/2025)</th><th>Corrente</th><th>Var. real</th></tr>`;
  document.querySelector("#tabela-evolucao tbody").innerHTML = anos.map((a) => {
    const v = somaAno(cons, a), anterior = somaAno(cons, String(Number(a) - 1));
    const c = somaAno(corr, a);
    const variacao = anterior > 0 && v > 0 ? (v / anterior - 1) * 100 : null;
    return `<tr><td>${a}</td><td>${v ? fmtValor(v) : "—"}</td><td>${c ? fmtValor(c) : "—"}</td><td>${fmtPct(variacao)}</td></tr>`;
  }).join("");
}

// ---------- Filtros / interação ----------
function montarPilulasPeriodo(container, estadoAtual, aoClicar) {
  container.innerHTML = PERIODOS.map((p) => `
    <button class="pilula-btn ${p.codigo === estadoAtual ? "ativo" : ""}" data-periodo="${p.codigo}">${p.rotulo}</button>
  `).join("");
  container.querySelectorAll(".pilula-btn").forEach((btn) => {
    btn.addEventListener("click", () => aoClicar(btn.dataset.periodo, container));
  });
}

/** Pílulas de "contar a história de": Total + os maiores tributos. */
function montarPilulasTributo() {
  const cont = document.getElementById("foco-tributo");
  cont.innerHTML = [ROTULO_TOTAL, ...principais].map((t) => `
    <button class="pilula-btn pilula-btn-tributo ${t === focoTributo ? "ativo" : ""}" data-tributo="${esc(t)}">
      <span class="ponto-v2" style="background:${corTributo(t)}"></span>${esc(t)}
    </button>
  `).join("");
  cont.querySelectorAll(".pilula-btn-tributo").forEach((btn) => {
    btn.addEventListener("click", () => {
      if (btn.dataset.tributo === focoTributo) return;
      focoTributo = btn.dataset.tributo;
      cont.querySelectorAll(".pilula-btn-tributo").forEach((b) => b.classList.toggle("ativo", b.dataset.tributo === focoTributo));
      renderGraficoEvolucao();
    });
  });
}

function ligarFiltros() {
  document.querySelectorAll("[data-precos-comp]").forEach((btn) => {
    btn.addEventListener("click", () => {
      if (btn.dataset.precosComp === compPrecos) return;
      document.querySelectorAll("[data-precos-comp]").forEach((b) => b.classList.remove("ativo"));
      btn.classList.add("ativo");
      compPrecos = btn.dataset.precosComp;
      renderGraficoComposicao();
    });
  });
  document.querySelectorAll("[data-visao-evo]").forEach((btn) => {
    btn.addEventListener("click", () => {
      if (btn.dataset.visaoEvo === evoVisao) return;
      document.querySelectorAll("[data-visao-evo]").forEach((b) => b.classList.remove("ativo"));
      btn.classList.add("ativo");
      evoVisao = btn.dataset.visaoEvo;
      renderGraficoEvolucao();
    });
  });

  montarPilulasPeriodo(document.getElementById("periodo-composicao"), compPeriodo, (codigo, cont) => {
    compPeriodo = codigo;
    cont.querySelectorAll(".pilula-btn").forEach((b) => b.classList.toggle("ativo", b.dataset.periodo === codigo));
    renderGraficoComposicao();
  });
  montarPilulasPeriodo(document.getElementById("periodo-evolucao"), evoPeriodo, (codigo, cont) => {
    evoPeriodo = codigo;
    cont.querySelectorAll(".pilula-btn").forEach((b) => b.classList.toggle("ativo", b.dataset.periodo === codigo));
    renderGraficoEvolucao();
  });
}

// ---------- Tema claro/escuro ----------
function temaEfetivoV2() {
  const attr = document.documentElement.getAttribute("data-theme");
  if (attr === "dark" || attr === "light") return attr;
  return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}

function sincronizarSwitchTemaV2() {
  const efetivo = temaEfetivoV2();
  document.querySelectorAll("#tema-switch-v2 .tema-switch-v2__btn").forEach((botao) => {
    const ativo = botao.dataset.tema === efetivo;
    botao.classList.toggle("tema-switch-v2__btn--ativo", ativo);
    botao.setAttribute("aria-pressed", ativo ? "true" : "false");
  });
}

/** Canvas (Chart.js) não reage sozinho à troca de tema. Redesenha os gráficos e as pílulas com ponto colorido. */
function rerenderizarAposTrocaTema() {
  if (!dados) return;
  montarPilulasTributo();
  renderGraficoComposicao();
  renderGraficoEvolucao();
}

function aplicarTemaV2(tema) {
  document.documentElement.setAttribute("data-theme", tema);
  try { localStorage.setItem("tema-v2", tema); } catch (e) { /* modo privado / storage bloqueado */ }
  sincronizarSwitchTemaV2();
  rerenderizarAposTrocaTema();
}

function configurarTemaV2() {
  sincronizarSwitchTemaV2();
  document.querySelectorAll("#tema-switch-v2 .tema-switch-v2__btn").forEach((botao) => {
    botao.addEventListener("click", () => aplicarTemaV2(botao.dataset.tema));
  });
  // Sem escolha explícita, acompanha a mudança de tema do sistema.
  window.matchMedia("(prefers-color-scheme: dark)").addEventListener("change", () => {
    if (!document.documentElement.getAttribute("data-theme")) {
      sincronizarSwitchTemaV2();
      rerenderizarAposTrocaTema();
    }
  });
}

async function iniciar() {
  configurarTemaV2();
  try {
    const resp = await fetch(ARQUIVO_DADOS);
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    dados = await resp.json();
  } catch (erro) {
    document.getElementById("txt-abertura").textContent =
      `Não foi possível carregar os dados (${ARQUIVO_DADOS}). Rode o pipeline (python run_pipeline.py) para gerá-los.`;
    console.error(erro);
    return;
  }

  try {
    const respEventos = await fetch(ARQUIVO_EVENTOS);
    eventos = respEventos.ok ? await respEventos.json() : [];
  } catch (erro) {
    eventos = [];
    console.warn("Eventos não carregados:", erro);
  }

  principais = [...dados.kpis.por_tributo]
    .sort((a, b) => b.valor_total - a.valor_total)
    .slice(0, N_PRINCIPAIS)
    .map((x) => x.tributo);

  renderRodape();
  renderNarrativaAbertura();
  ligarFiltros();
  montarPilulasTributo();
  renderGraficoComposicao();
  renderGraficoEvolucao();
  renderNotaReforma();
}

iniciar();

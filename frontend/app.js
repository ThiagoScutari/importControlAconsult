"use strict";

// Campos do processo exibidos para conferência (chave -> rótulo).
const CAMPOS_PROCESSO = [
  ["processo", "Processo"],
  ["tipo_importacao", "Tipo Importação"],
  ["di_duimp", "DI/DUIMP"],
  ["data_nf", "Data NF"],
  ["numero_nf", "Nº NF"],
  ["valor_nf", "Valor NF"],
  ["despachante", "Despachante"],
  ["fornecedor_estrangeiro", "Fornecedor Estrangeiro"],
  ["fabricante", "Fabricante"],
  ["pais_origem", "País Origem"],
  ["pais_aquisicao", "País Aquisição"],
  ["invoice", "Invoice"],
  ["invoice_usd", "Invoice USD"],
  ["tx_di", "TX DI"],
  ["resultado_rs", "Resultado R$ (provisão fornecedor)"],
  ["cotacao", "Cotação"],
  ["fob_rs", "FOB R$"],
  ["frete_rs", "Frete R$"],
  ["valor_aduaneiro_rs", "Valor Aduaneiro R$"],
  ["ii", "II"],
  ["ipi", "IPI"],
  ["pis", "PIS"],
  ["cofins", "COFINS"],
  ["cbs", "CBS"],
  ["ibs_uf", "IBS-UF"],
  ["ibs_mun", "IBS-MUN"],
  ["siscomex", "Siscomex"],
  ["afrmm", "AFRMM"],
  ["icms", "ICMS"],
  ["armazenagem", "Armazenagem"],
  ["total_tributos", "Total Tributos"],
  ["peso_liquido", "Peso Líquido"],
  ["volumes", "Volumes"],
  ["navio", "Navio"],
  ["bl", "BL"],
  ["chegada", "Chegada"],
  ["chave_nfe", "Chave NF-e"],
];

// Campos do middleware: [chave, rótulo, tipo, opções?]
const CAMPOS_MIDDLEWARE = [
  ["conta_processo_nome", "Conta do Processo — nome", "text"],
  ["conta_processo_numero", "Conta do Processo — número", "text"],
  ["entidade_contabil", "Entidade Contábil (trading × adquirente)", "text"],
  ["data_lancamento", "Data Lançamento", "text"],
  ["vlr_usd_pg_cambio", "Câmbio — USD pago (campo 4)", "text"],
  ["tx_cambio", "Câmbio — taxa (campo 5)", "text"],
  ["tratamento_cbs_ibs", "Tratamento CBS/IBS", "select", ["reservar", "lancar"]],
  ["inicia_lote", "Inicia Lote", "text"],
  ["matriz_filial", "Matriz/Filial", "text"],
];

// Rótulos amigáveis das categorias de linha do fechamento.
const CATEGORIA_LABEL = {
  despesa_processo: "Despesa do processo (entra no lançamento)",
  tributo_federal_na_nf: "Tributo federal (já na NF — não relança)",
  icms_importacao: "ICMS importação (DARE/diferido)",
  retencao: "Retenção (crédito)",
  adiantamento: "Adiantamento (crédito)",
};

let estado = { processo: null, sugestoes: null, arquivos: [] };

// ----- helpers DOM -----
const $ = (sel) => document.querySelector(sel);
const el = (tag, attrs = {}, ...filhos) => {
  const n = document.createElement(tag);
  Object.entries(attrs).forEach(([k, v]) => {
    if (k === "class") n.className = v;
    else if (k === "value") n.value = v == null ? "" : v;
    else n.setAttribute(k, v);
  });
  filhos.forEach((f) => n.append(f));
  return n;
};

// ----- Upload (drag & drop) -----
const dropzone = $("#dropzone");
const fileInput = $("#file-input");

["dragover", "dragenter"].forEach((ev) =>
  dropzone.addEventListener(ev, (e) => { e.preventDefault(); dropzone.classList.add("dragover"); })
);
["dragleave", "drop"].forEach((ev) =>
  dropzone.addEventListener(ev, (e) => { e.preventDefault(); dropzone.classList.remove("dragover"); })
);
dropzone.addEventListener("drop", (e) => adicionarArquivos(e.dataTransfer.files));
fileInput.addEventListener("change", (e) => adicionarArquivos(e.target.files));

function adicionarArquivos(fileList) {
  for (const f of fileList) {
    if (f.type === "application/pdf" || f.name.toLowerCase().endsWith(".pdf")) {
      estado.arquivos.push(f);
    }
  }
  renderListaArquivos();
}

function renderListaArquivos() {
  const ul = $("#file-list");
  ul.innerHTML = "";
  estado.arquivos.forEach((f, i) => {
    const li = el("li", {}, `📄 ${f.name} `);
    const x = el("span", { class: "link", title: "remover" }, "✕");
    x.style.float = "right";
    x.onclick = () => { estado.arquivos.splice(i, 1); renderListaArquivos(); };
    li.append(x);
    ul.append(li);
  });
  $("#btn-extrair").disabled = estado.arquivos.length === 0;
}

// ----- Extrair -----
$("#btn-extrair").addEventListener("click", extrair);

async function extrair() {
  const status = $("#extrair-status");
  status.textContent = "Extraindo…";
  const fd = new FormData();
  estado.arquivos.forEach((f) => fd.append("arquivos", f));
  try {
    const resp = await fetch("/extract", { method: "POST", body: fd });
    if (!resp.ok) throw new Error("Falha na extração (" + resp.status + ")");
    const dados = await resp.json();
    estado.processo = dados;
    estado.sugestoes = dados.sugestoes_middleware || {};
    status.textContent = "✓ extraído";
    renderConferencia(dados);
  } catch (err) {
    status.textContent = "✕ " + err.message;
  }
}

// ----- Conferência -----
function renderConferencia(dados) {
  $("#passo-conferencia").classList.remove("hidden");
  const sug = estado.sugestoes || {};

  // Campos do processo (extraídos)
  const grid = $("#campos-processo");
  grid.innerHTML = "";
  CAMPOS_PROCESSO.forEach(([chave, rotulo]) => {
    grid.append(campoInput("proc__" + chave, rotulo, valorTexto(dados[chave])));
  });

  // Middleware (campos a completar)
  const mid = $("#campos-middleware");
  mid.innerHTML = "";
  CAMPOS_MIDDLEWARE.forEach(([chave, rotulo, tipo, opcoes]) => {
    let valor = "";
    if (chave === "conta_processo_nome") valor = sug.conta_processo_nome || "";
    if (chave === "data_lancamento") valor = sug.data_lancamento || dados.data_nf || "";
    if (chave === "tratamento_cbs_ibs") valor = "reservar";
    if (tipo === "select") mid.append(campoSelect("mid__" + chave, rotulo, opcoes, valor));
    else mid.append(campoInput("mid__" + chave, rotulo, valor));
  });

  renderContas(sug.papeis || {});
  renderClassificacao(sug.despesas || []);
  renderAvisos(dados.avisos, dados.nao_reconhecidos);

  $("#passo-conferencia").scrollIntoView({ behavior: "smooth" });
}

function campoInput(id, rotulo, valor) {
  return el("div", { class: "campo" },
    el("label", { for: id }, rotulo),
    el("input", { id, type: "text", value: valor })
  );
}
function campoSelect(id, rotulo, opcoes, valor) {
  const sel = el("select", { id });
  (opcoes || []).forEach((o) => {
    const opt = el("option", { value: o }, o);
    if (o === valor) opt.selected = true;
    sel.append(opt);
  });
  return el("div", { class: "campo" }, el("label", { for: id }, rotulo), sel);
}

// Plano de contas (papel -> código), editável -> contas_override
function renderContas(papeis) {
  const tbody = $("#tabela-contas tbody");
  tbody.innerHTML = "";
  const chaves = Object.keys(papeis);
  chaves.forEach((papel) => {
    const tr = el("tr");
    tr.append(el("td", {}, papel));
    tr.append(el("td", {}, el("input", { id: "conta__" + papel, type: "text", value: papeis[papel] || "" })));
    tbody.append(tr);
  });
  tbody.dataset.papeis = JSON.stringify(chaves);
}

// Classificação das linhas do fechamento (dropdown por linha) -> classificacao_override
function renderClassificacao(despesas) {
  const tbody = $("#tabela-classificacao tbody");
  tbody.innerHTML = "";
  const cats = Object.keys(CATEGORIA_LABEL);
  despesas.forEach((d, i) => {
    const tr = el("tr");
    tr.append(el("td", {}, el("input", { id: `cls__${i}__desc`, type: "text", value: d.descricao || "" })));
    tr.append(el("td", {}, valorTexto(d.valor)));
    const sel = el("select", { id: `cls__${i}__cat` });
    cats.forEach((c) => {
      const opt = el("option", { value: c }, CATEGORIA_LABEL[c]);
      if (c === d.categoria) opt.selected = true;
      sel.append(opt);
    });
    // realce visual do que entra no lançamento
    sel.classList.add("cat-" + (d.categoria || ""));
    tr.append(el("td", {}, sel));
    tbody.append(tr);
  });
  tbody.dataset.linhas = despesas.length;
}

function valorTexto(v) {
  if (v === null || v === undefined) return "";
  return String(v);
}

function renderAvisos(avisos, naoReconhecidos) {
  const box = $("#avisos");
  const itens = [];
  (avisos || []).forEach((a) => itens.push({ tipo: a.tipo, msg: a.mensagem }));
  (naoReconhecidos || []).forEach((n) => itens.push({ tipo: "ausente", msg: `Arquivo ignorado: ${n.arquivo} (${n.motivo})` }));
  if (itens.length === 0) { box.classList.add("hidden"); return; }
  box.classList.remove("hidden");
  box.innerHTML = "";
  box.append(el("h4", {}, `⚠ ${itens.length} aviso(s)`));
  const ul = el("ul");
  itens.forEach((i) => ul.append(el("li", { class: i.tipo }, i.msg)));
  box.append(ul);
}

// ----- Gerar -----
$("#btn-gerar").addEventListener("click", gerar);
$("#btn-recomecar").addEventListener("click", () => location.reload());

// Contrato de número na fronteira: o front NÃO parseia número. Envia o valor
// bruto do campo (string); o backend (coerta_valor) coage com segurança,
// tolerando tanto "382358.58" (float exibido) quanto "382.358,58" (edição BR).
function coletarProcesso() {
  const p = Object.assign({}, estado.processo);
  CAMPOS_PROCESSO.forEach(([chave]) => {
    const inp = $("#proc__" + chave);
    if (inp) p[chave] = inp.value === "" ? null : inp.value;
  });
  return p;
}

function coletarMiddleware() {
  const m = { contas_override: {}, classificacao_override: {}, lancamentos: [] };

  CAMPOS_MIDDLEWARE.forEach(([chave]) => {
    const inp = $("#mid__" + chave);
    if (!inp) return;
    m[chave] = inp.value === "" ? null : inp.value;  // câmbio incluso: string bruta
  });

  // Plano de contas (papel -> código)
  const papeis = JSON.parse($("#tabela-contas tbody").dataset.papeis || "[]");
  papeis.forEach((papel) => {
    const v = $("#conta__" + papel);
    if (v && v.value.trim()) m.contas_override[papel] = v.value.trim();
  });

  // Classificação por linha (descrição -> categoria)
  const n = parseInt($("#tabela-classificacao tbody").dataset.linhas || "0", 10);
  for (let i = 0; i < n; i++) {
    const desc = $(`#cls__${i}__desc`).value;
    const cat = $(`#cls__${i}__cat`).value;
    if (desc) m.classificacao_override[desc] = cat;
  }

  m.incluir_saida_c = $("#incluir-c").checked;
  return m;
}

async function gerar() {
  const status = $("#gerar-status");
  status.textContent = "Gerando…";
  try {
    const body = JSON.stringify({ processo: coletarProcesso(), middleware: coletarMiddleware() });
    const resp = await fetch("/generate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body,
    });
    if (!resp.ok) throw new Error("Falha ao gerar (" + resp.status + ")");
    const blob = await resp.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `saidas_processo_${(coletarProcesso().processo || "sem_ref").replace(/\W+/g, "_")}.zip`;
    document.body.append(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
    status.textContent = "✓ arquivos baixados";
  } catch (err) {
    status.textContent = "✕ " + err.message;
  }
}

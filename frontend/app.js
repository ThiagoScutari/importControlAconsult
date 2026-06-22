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
  ["cotacao", "Cotação"],
  ["fob_rs", "FOB R$"],
  ["frete_rs", "Frete R$"],
  ["valor_aduaneiro_rs", "Valor Aduaneiro R$"],
  ["ii", "II"],
  ["ipi", "IPI"],
  ["pis", "PIS"],
  ["cofins", "COFINS"],
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

const CAMPOS_MIDDLEWARE = [
  ["tipo_importacao", "Tipo Importação", "select", ["Própria", "Conta e ordem", "Encomenda"]],
  ["entidade_contabil", "Entidade Contábil", "text"],
  ["data_lancamento", "Data Lançamento", "text"],
  ["complemento_historico", "Complemento Histórico", "text"],
  ["inicia_lote", "Inicia Lote", "text"],
  ["matriz_filial", "Matriz/Filial", "text"],
];

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

  // Campos do processo
  const grid = $("#campos-processo");
  grid.innerHTML = "";
  CAMPOS_PROCESSO.forEach(([chave, rotulo]) => {
    grid.append(campoInput("proc__" + chave, rotulo, valorTexto(dados[chave])));
  });

  // Middleware
  const mid = $("#campos-middleware");
  mid.innerHTML = "";
  const sug = estado.sugestoes || {};
  CAMPOS_MIDDLEWARE.forEach(([chave, rotulo, tipo, opcoes]) => {
    let valor = "";
    if (chave === "tipo_importacao") valor = sug.tipo_importacao || dados.tipo_importacao || "";
    if (chave === "data_lancamento") valor = sug.data_lancamento || dados.data_nf || "";
    if (chave === "complemento_historico") valor = complementoPadrao(dados);
    if (tipo === "select") mid.append(campoSelect("mid__" + chave, rotulo, opcoes, valor));
    else mid.append(campoInput("mid__" + chave, rotulo, valor));
  });

  renderAvisos(dados.avisos, dados.nao_reconhecidos);
  renderLancamentos(sug.despesas || [], dados);

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
  opcoes.forEach((o) => {
    const opt = el("option", { value: o }, o);
    if (o === valor) opt.selected = true;
    sel.append(opt);
  });
  return el("div", { class: "campo" }, el("label", { for: id }, rotulo), sel);
}

function valorTexto(v) {
  if (v === null || v === undefined) return "";
  return String(v);
}

function complementoPadrao(d) {
  const partes = [];
  if (d.processo) partes.push("PROCESSO " + d.processo);
  if (d.di_duimp) partes.push("DI/DUIMP " + d.di_duimp);
  if (d.numero_nf) partes.push("NF " + d.numero_nf);
  return partes.join(" ");
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

function renderLancamentos(despesas, dados) {
  const tbody = $("#tabela-lancamentos tbody");
  tbody.innerHTML = "";
  const linhas = despesas.length
    ? despesas
    : [{ descricao: "(sem fechamento) Valor da NF", valor: dados.valor_nf, conta_debito: "", conta_credito: "", cod_historico: "" }];
  linhas.forEach((d, i) => {
    const tr = el("tr");
    tr.append(tdInput(`lc__${i}__descricao`, d.descricao || ""));
    tr.append(tdInput(`lc__${i}__valor`, valorTexto(d.valor)));
    tr.append(tdInput(`lc__${i}__conta_debito`, d.conta_debito || ""));
    tr.append(tdInput(`lc__${i}__conta_credito`, d.conta_credito || ""));
    tr.append(tdInput(`lc__${i}__cod_historico`, d.cod_historico || ""));
    tbody.append(tr);
  });
  tbody.dataset.linhas = linhas.length;
}
function tdInput(id, valor) {
  return el("td", {}, el("input", { id, type: "text", value: valor }));
}

// ----- Gerar -----
$("#btn-gerar").addEventListener("click", gerar);
$("#btn-recomecar").addEventListener("click", () => location.reload());

function coletarProcesso() {
  const p = Object.assign({}, estado.processo);
  CAMPOS_PROCESSO.forEach(([chave]) => {
    const inp = $("#proc__" + chave);
    if (inp) p[chave] = converteNumero(chave, inp.value);
  });
  return p;
}

const NUMERICOS = new Set(["valor_nf", "invoice_usd", "cotacao", "fob_rs", "frete_rs",
  "valor_aduaneiro_rs", "ii", "ipi", "pis", "cofins", "siscomex", "afrmm", "icms",
  "armazenagem", "total_tributos", "peso_liquido", "volumes"]);

function converteNumero(chave, valor) {
  if (!NUMERICOS.has(chave)) return valor === "" ? null : valor;
  if (valor === "" || valor == null) return null;
  // aceita formato BR ou US
  const n = parseFloat(String(valor).replace(/\./g, "").replace(",", "."));
  return isNaN(n) ? null : n;
}

function coletarMiddleware() {
  const m = {};
  CAMPOS_MIDDLEWARE.forEach(([chave]) => {
    const inp = $("#mid__" + chave);
    if (inp) m[chave] = inp.value || null;
  });
  m.incluir_saida_c = $("#incluir-c").checked;
  m.lancamentos = coletarLancamentos(m);
  return m;
}

function coletarLancamentos(m) {
  const tbody = $("#tabela-lancamentos tbody");
  const n = parseInt(tbody.dataset.linhas || "0", 10);
  const out = [];
  for (let i = 0; i < n; i++) {
    const valorTxt = $(`#lc__${i}__valor`).value;
    const valor = parseFloat(String(valorTxt).replace(/\./g, "").replace(",", ".")) || 0;
    out.push({
      data: m.data_lancamento || "",
      conta_debito: $(`#lc__${i}__conta_debito`).value || "",
      conta_credito: $(`#lc__${i}__conta_credito`).value || "",
      valor: valor,
      cod_historico: $(`#lc__${i}__cod_historico`).value || "",
      complemento_historico: `${m.complemento_historico || ""} - ${$(`#lc__${i}__descricao`).value}`.replace(/^ - /, ""),
      inicia_lote: m.inicia_lote || "",
      matriz_filial: m.matriz_filial || "",
      cc_debito: "",
      cc_credito: "",
    });
  }
  return out;
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
    a.download = `saidas_processo_${coletarProcesso().processo || "sem_ref"}.zip`;
    document.body.append(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
    status.textContent = "✓ arquivos baixados";
  } catch (err) {
    status.textContent = "✕ " + err.message;
  }
}

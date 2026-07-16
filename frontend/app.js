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

// Rótulo amigável por campo (para as divergências). Base = campos do formulário;
// extras cobrem campos fora do form (ex.: importador_nome).
const ROTULO_CAMPO = Object.fromEntries(CAMPOS_PROCESSO);
Object.assign(ROTULO_CAMPO, {
  importador_nome: "Importador (nome)",
  importador_cnpj: "Importador (CNPJ)",
  adquirente_nome: "Adquirente (nome)",
  adquirente_cnpj: "Adquirente (CNPJ)",
});

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

  renderDivergencias(dados.divergencias);
  renderContas(sug.papeis || {});
  renderClassificacao(sug.despesas || []);
  renderAvisos(dados.avisos, dados.nao_reconhecidos, dados.anexos, {
    total: dados.adiantamento_total,
    linhas: dados.adiantamentos,
  });

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
    // [R3] contas sem default (ex.: conta do processo/fornecedor) vêm em branco —
    // o operador informa; o placeholder sinaliza a obrigatoriedade.
    const attrs = { id: "conta__" + papel, type: "text", value: papeis[papel] || "" };
    if (!papeis[papel]) attrs.placeholder = "informe o código";
    tr.append(el("td", {}, el("input", attrs)));
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

function renderAvisos(avisos, naoReconhecidos, anexos, adiantamento) {
  const box = $("#avisos");
  box.innerHTML = "";
  const problemas = [];
  const infos = [];
  (avisos || []).forEach((a) =>
    (a.tipo === "info" ? infos : problemas).push({ tipo: a.tipo, msg: a.mensagem })
  );
  (naoReconhecidos || []).forEach((n) =>
    problemas.push({ tipo: "ausente", msg: `Arquivo ignorado: ${n.arquivo} (${n.motivo})` })
  );
  // Anexos/referência: reconhecidos e ignorados com calma — NÃO são avisos.
  const refs = (anexos || []).map((n) => `${n.arquivo} — ${n.motivo}`);

  // Adiantamento capturado (crédito do Passo 6.2) — validação na conferência.
  if (adiantamento && adiantamento.total != null && adiantamento.total !== "") {
    const linhas = (adiantamento.linhas || [])
      .map((a) => `${a.descricao}: ${valorTexto(a.valor)}`)
      .join(" + ");
    infos.push({
      tipo: "info",
      msg: `Adiantamento capturado: R$ ${valorTexto(adiantamento.total)}${linhas ? " (" + linhas + ")" : ""}`,
    });
  }

  if (problemas.length === 0 && refs.length === 0 && infos.length === 0) {
    box.classList.add("hidden");
    return;
  }
  box.classList.remove("hidden");

  if (problemas.length) {
    box.append(el("h4", {}, `⚠ ${problemas.length} aviso(s)`));
    const ul = el("ul");
    problemas.forEach((i) => ul.append(el("li", { class: i.tipo }, i.msg)));
    box.append(ul);
  }
  if (infos.length) {
    const ul = el("ul");
    infos.forEach((i) => ul.append(el("li", { class: "info" }, i.msg)));
    box.append(ul);
  }
  if (refs.length) {
    box.append(el("h4", { class: "info" }, `ℹ ${refs.length} anexo(s)/referência (reconhecidos, ignorados)`));
    const ul = el("ul");
    refs.forEach((r) => ul.append(el("li", { class: "anexo" }, r)));
    box.append(ul);
  }
}

// ----- Conferência navegável de divergências (diff + seleção) -----
// Quando os documentos discordam de um campo, o operador vê os valores lado a
// lado e ESCOLHE qual usar; a escolha vai para o campo de saída e para a Saída A
// rastreável. Não há correção automática (spec §3 [R2]/[R3]).
function renderDivergencias(divs) {
  const box = $("#divergencias");
  box.innerHTML = "";
  if (!divs || divs.length === 0) { box.classList.add("hidden"); return; }
  box.classList.remove("hidden");
  box.append(el("h3", {}, `⚖ Divergências entre documentos (${divs.length})`));
  box.append(el("p", { class: "sub" },
    "Os documentos discordam nestes campos. Selecione qual valor usar — ele vai para o campo abaixo e para a Saída A rastreável."));
  divs.forEach((d, i) => box.append(cardDivergencia(d, i)));
}

function cardDivergencia(d, idx) {
  const card = el("div", { class: "diverg-card" });
  card.append(el("h4", {}, ROTULO_CAMPO[d.campo] || d.campo));
  const opcoes = el("div", { class: "diverg-opcoes" });
  (d.candidatos || []).forEach((c, j) => {
    const opt = el("label", { class: "diverg-opt" });
    const radio = el("input", { type: "radio", name: `div__${idx}` });
    if (j === 0) radio.checked = true; // candidato[0] = escolhido por prioridade
    radio.addEventListener("change", () => aplicarEscolha(d.campo, c.fonte, c.valor, opt));
    opt.append(
      radio,
      el("span", { class: "diverg-fonte" }, c.fonte),
      el("span", { class: "diverg-valor" }, valorTexto(c.valor))
    );
    opcoes.append(opt);
  });
  card.append(opcoes);
  return card;
}

function aplicarEscolha(campo, fonte, valor, optEl) {
  // 1) escreve no campo de saída do formulário (quando existe input p/ o campo)
  const inp = $("#proc__" + campo);
  if (inp) inp.value = valorTexto(valor);
  // 2) atualiza o objeto do processo — cobre campos fora do formulário (ex.: importador_nome)
  if (estado.processo) estado.processo[campo] = valor;
  // 3) registra a escolha na rastreabilidade (Saída A rastreável)
  atualizarRastreamento(campo, fonte, valor);
  // 4) realce visual do card e do campo escolhido
  if (optEl && optEl.parentElement) {
    [...optEl.parentElement.children].forEach((o) => o.classList.remove("escolhido"));
    optEl.classList.add("escolhido");
  }
  if (inp) {
    inp.classList.add("campo-destacado");
    inp.scrollIntoView({ behavior: "smooth", block: "center" });
    setTimeout(() => inp.classList.remove("campo-destacado"), 1500);
  }
}

function atualizarRastreamento(campo, fonte, valor) {
  if (!estado.processo) return;
  const r = estado.processo.rastreamento || (estado.processo.rastreamento = []);
  const marca = `${fonte} (escolha do operador)`;
  const ent = r.find((x) => x.campo === campo);
  if (ent) { ent.valor = valor; ent.fonte = marca; }
  else r.push({ campo, valor, fonte: marca });
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

// ----- Saída D: atualizar a Relação das Importações (.xlsx) -----
$("#relacao-file").addEventListener("change", (e) => {
  $("#btn-relacao").disabled = !(e.target.files && e.target.files.length);
});
$("#btn-relacao").addEventListener("click", atualizarRelacao);

async function atualizarRelacao() {
  const status = $("#relacao-status");
  const arquivo = $("#relacao-file").files[0];
  if (!arquivo) { status.textContent = "✕ selecione o .xlsx da Relação"; return; }
  status.textContent = "Atualizando…";
  try {
    // mesmo contrato do /generate (processo + middleware editados), como campo de form
    const payload = JSON.stringify({ processo: coletarProcesso(), middleware: coletarMiddleware() });
    const fd = new FormData();
    fd.append("arquivo", arquivo);
    fd.append("payload", payload);
    const resp = await fetch("/relacao", { method: "POST", body: fd });
    if (!resp.ok) {
      let msg = "Falha ao atualizar (" + resp.status + ")";
      try { const j = await resp.json(); if (j.erro) msg = j.erro; } catch (_) {}
      throw new Error(msg);
    }
    baixarBlob(await resp.blob(),
      `relacao_atualizada_${(coletarProcesso().processo || "sem_ref").replace(/\W+/g, "_")}.xlsx`);
    status.textContent = "✓ Relação atualizada baixada";
  } catch (err) {
    status.textContent = "✕ " + err.message;
  }
}

// download utilitário compartilhado (zip das saídas e xlsx da Relação)
function baixarBlob(blob, nome) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = nome;
  document.body.append(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
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
    baixarBlob(await resp.blob(),
      `saidas_processo_${(coletarProcesso().processo || "sem_ref").replace(/\W+/g, "_")}.zip`);
    status.textContent = "✓ arquivos baixados";
  } catch (err) {
    status.textContent = "✕ " + err.message;
  }
}

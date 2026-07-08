"""App FastAPI: rotas de extração/geração + serve o front-end estático."""
from __future__ import annotations

import io
import os
import zipfile
from typing import List

from fastapi import FastAPI, File, UploadFile
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles

from backend.consolidador import consolidar
from backend.contabilizador import gerar_partidas, montar_nome_conta_processo
from backend.depara import (
    CategoriaLinha,
    PapelConta,
    classificar_linha,
    codigo_conta,
    sugerir_despesa,
    sugerir_fornecedor,
)
from backend.detector import TipoDocumento, detectar_tipo
from backend.extractors import (
    di,
    duimp,
    fechamento_syndex,
    fechamento_terra,
    fechamento_win,
    nota_fiscal,
)
from backend.models import GerarRequest
from backend.outputs import (
    gerar_saida_a,
    gerar_saida_a_rastreavel,
    gerar_saida_b,
    gerar_saida_c,
)
from backend.pdf_utils import extract_text

# Mapa tipo -> módulo extrator
EXTRATORES = {
    TipoDocumento.DUIMP: duimp,
    TipoDocumento.DI: di,
    TipoDocumento.NOTA_FISCAL: nota_fiscal,
    TipoDocumento.FECHAMENTO_TERRA: fechamento_terra,
    TipoDocumento.FECHAMENTO_WIN: fechamento_win,
    TipoDocumento.FECHAMENTO_SYNDEX: fechamento_syndex,
}

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FRONTEND = os.path.join(ROOT, "frontend")

app = FastAPI(title="Extrator de Importação — Aconsult (mockup)")


@app.post("/extract")
async def extract(arquivos: List[UploadFile] = File(...)):
    """Recebe 1..N PDFs de um processo: detecta, extrai e consolida."""
    documentos = []
    nao_reconhecidos = []
    for arq in arquivos:
        conteudo = await arq.read()
        try:
            texto = extract_text(conteudo)
        except Exception as exc:  # PDF ilegível / corrompido
            nao_reconhecidos.append({"arquivo": arq.filename, "motivo": str(exc)})
            continue
        tipo = detectar_tipo(texto)
        if tipo == TipoDocumento.DESCONHECIDO:
            nao_reconhecidos.append({"arquivo": arq.filename, "motivo": "tipo não reconhecido"})
            continue
        dados = EXTRATORES[tipo].extrair(texto)
        dados["_arquivo"] = arq.filename
        documentos.append(dados)

    processo = consolidar(documentos)
    sugestoes = _sugestoes_middleware(processo)

    payload = processo.model_dump()
    payload["nao_reconhecidos"] = nao_reconhecidos
    payload["sugestoes_middleware"] = sugestoes
    return JSONResponse(payload)


def _sugestoes_middleware(processo) -> dict:
    """Pré-preenchimento do middleware: de-para + nome da conta + classificação.

    A classificação por linha (categoria) alimenta o dropdown da demo — o guard
    §3 já vem sugerido, e o operador reclassifica se preciso.
    """
    forn = sugerir_fornecedor(processo.fornecedor_estrangeiro) or {}
    despesas = []
    for d in processo.despesas:
        cat = classificar_linha(d.get("descricao"), d.get("tipo"))
        despesas.append({
            "descricao": d.get("descricao"),
            "valor": d.get("valor"),
            "tipo": d.get("tipo"),
            "categoria": cat.value,
            **sugerir_despesa(d.get("descricao")),
        })
    return {
        "tipo_importacao": processo.tipo_importacao,
        "conta_processo_nome": montar_nome_conta_processo(processo),
        "resultado_rs": processo.resultado_rs,
        "papeis": {p.value: codigo_conta(p) for p in PapelConta},
        "categorias_possiveis": [c.value for c in CategoriaLinha],
        "conta_debito": forn.get("conta", ""),
        "cod_historico": forn.get("cod_historico", ""),
        "data_lancamento": processo.data_nf or "",
        "despesas": despesas,
    }


@app.post("/generate")
async def generate(req: GerarRequest):
    """Gera os arquivos A, B (e C, se marcado) e devolve em um .zip."""
    processo = req.processo
    middleware = req.middleware

    # Atualiza tipo de importação confirmado pelo operador, se enviado.
    if middleware.tipo_importacao:
        processo.tipo_importacao = middleware.tipo_importacao

    # Saída B: partidas do POP (motor). Se o operador editou a tabela e enviou
    # lançamentos prontos, respeita-os; senão, gera pelo algoritmo 1.5.
    lancamentos = middleware.lancamentos or gerar_partidas(processo, middleware)

    arquivos = {
        "saida_A_extracao.csv": gerar_saida_a([processo]),
        "saida_A_rastreavel.csv": gerar_saida_a_rastreavel([processo]),
        "saida_B_lancamentos_dominio.csv": gerar_saida_b(lancamentos),
        "saida_B_lancamentos_dominio.txt": gerar_saida_b(lancamentos),
    }
    if middleware.incluir_saida_c:
        arquivos["saida_C_fornecedores.csv"] = gerar_saida_c([processo])

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for nome, conteudo in arquivos.items():
            # BOM para abrir certinho no Excel PT-BR
            zf.writestr(nome, "﻿" + conteudo)
    buf.seek(0)

    nome_zip = f"saidas_processo_{processo.processo or 'sem_ref'}.zip"
    return Response(
        content=buf.getvalue(),
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{nome_zip}"'},
    )


@app.get("/")
async def index():
    return FileResponse(os.path.join(FRONTEND, "index.html"))


# Arquivos estáticos do front-end (app.js, styles.css)
app.mount("/static", StaticFiles(directory=FRONTEND), name="static")

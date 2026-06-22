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
from backend.depara import sugerir_despesa, sugerir_fornecedor
from backend.detector import TipoDocumento, detectar_tipo
from backend.extractors import (
    di,
    duimp,
    fechamento_terra,
    fechamento_win,
    nota_fiscal,
)
from backend.models import GerarRequest
from backend.outputs import (
    gerar_lancamentos_sugeridos,
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
    """Pré-preenchimento do middleware via de-para (fornecedor/despesa)."""
    forn = sugerir_fornecedor(processo.fornecedor_estrangeiro) or {}
    return {
        "tipo_importacao": processo.tipo_importacao,
        "conta_debito": forn.get("conta", ""),
        "cod_historico": forn.get("cod_historico", ""),
        "data_lancamento": processo.data_nf or "",
        "despesas": [
            {"descricao": d.get("descricao"), "valor": d.get("valor"), **sugerir_despesa(d.get("descricao"))}
            for d in processo.despesas
        ],
    }


@app.post("/generate")
async def generate(req: GerarRequest):
    """Gera os arquivos A, B (e C, se marcado) e devolve em um .zip."""
    processo = req.processo
    middleware = req.middleware

    # Atualiza tipo de importação confirmado pelo operador, se enviado.
    if middleware.tipo_importacao:
        processo.tipo_importacao = middleware.tipo_importacao

    lancamentos = middleware.lancamentos or gerar_lancamentos_sugeridos(processo, middleware)

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

"""App FastAPI: rotas de extração/geração + serve o front-end estático."""
from __future__ import annotations

import io
import os
import re
import zipfile
from typing import List

from fastapi import FastAPI, File, Form, UploadFile
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles

from backend.consolidador import consolidar
from backend.contabilizador import (
    gerar_partidas,
    montar_nome_conta_processo,
    validar_partidas,
)
from backend.depara import (
    CategoriaLinha,
    PapelConta,
    classificar_linha,
    codigo_conta,
    sugerir_despesa,
    sugerir_fornecedor,
)
from backend.detector import LIMIAR_TEXTO_MINIMO, TipoDocumento, detectar_tipo
from backend.extractors import (
    di,
    duimp,
    fechamento_alltime,
    fechamento_connecta,
    fechamento_syndex,
    fechamento_terra,
    fechamento_win,
    nota_fiscal,
)
from backend.models import GerarRequest
from backend.outputs import (
    append_relacao,
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
    TipoDocumento.FECHAMENTO_ALLTIME: fechamento_alltime,
    TipoDocumento.FECHAMENTO_CONNECTA: fechamento_connecta,
}

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FRONTEND = os.path.join(ROOT, "frontend")

app = FastAPI(title="Extrator de Importação — Aconsult (mockup)")

# Limite de upload no app (defesa em profundidade; spec §13). O nginx já corta
# uploads grandes (client_max_body_size), mas o app também recusa por conta —
# útil no Docker sem proxy. Responde 413 quando o Content-Length passa do teto;
# uploads chunked (sem Content-Length) ficam a cargo do proxy (ok p/ o mockup).
MAX_UPLOAD_BYTES = 25 * 1024 * 1024  # 25 MB (alinhar com o client_max_body_size do nginx)


@app.middleware("http")
async def limite_tamanho_upload(request, call_next):
    cl = request.headers.get("content-length")
    if cl is not None:
        try:
            if int(cl) > MAX_UPLOAD_BYTES:
                return JSONResponse(
                    status_code=413,
                    content={"erro": f"upload excede o limite de {MAX_UPLOAD_BYTES // (1024 * 1024)} MB"},
                )
        except ValueError:
            pass  # header malformado: segue e falha adiante normalmente
    return await call_next(request)


@app.post("/extract")
async def extract(arquivos: List[UploadFile] = File(...)):
    """Recebe 1..N PDFs de um processo: detecta, extrai e consolida."""
    documentos = []
    nao_reconhecidos = []
    anexos = []  # anexos/referência reconhecidos e ignorados com calma (spec §3 [R3])
    for arq in arquivos:
        conteudo = await arq.read()
        try:
            texto = extract_text(conteudo)
        except Exception as exc:  # PDF ilegível / corrompido
            nao_reconhecidos.append({"arquivo": arq.filename, "motivo": f"PDF ilegível: {exc}"})
            continue

        # Detectar/extrair blindados: uma exceção em um arquivo não pode derrubar
        # o /extract inteiro — o arquivo problemático é isolado e reportado.
        try:
            tipo = detectar_tipo(texto)
        except Exception as exc:
            nao_reconhecidos.append({"arquivo": arq.filename, "motivo": f"falha ao classificar: {exc}"})
            continue

        if tipo == TipoDocumento.ANEXO_REFERENCIA:
            eh_imagem = len((texto or "").strip()) < LIMIAR_TEXTO_MINIMO
            anexos.append({
                "arquivo": arq.filename,
                "motivo": "anexo/referência (imagem)" if eh_imagem else "anexo/referência",
            })
            continue
        if tipo == TipoDocumento.DESCONHECIDO:
            nao_reconhecidos.append({"arquivo": arq.filename, "motivo": "tipo não reconhecido"})
            continue

        extrator = EXTRATORES.get(tipo)
        if extrator is None:  # tipo suportado sem extrator registrado (defensivo)
            nao_reconhecidos.append({"arquivo": arq.filename, "motivo": f"sem extrator para {tipo.value}"})
            continue
        try:
            dados = extrator.extrair(texto)
        except Exception as exc:  # regex/parse quebrou neste arquivo — isola e segue
            nao_reconhecidos.append({"arquivo": arq.filename, "motivo": f"falha na extração ({tipo.value}): {exc}"})
            continue
        dados["_arquivo"] = arq.filename
        documentos.append(dados)

    processo = consolidar(documentos)
    sugestoes = _sugestoes_middleware(processo)

    payload = processo.model_dump()
    payload["nao_reconhecidos"] = nao_reconhecidos
    payload["anexos"] = anexos
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


def _slug(ref: str | None) -> str:
    """Referência do processo em slug seguro para nome de arquivo."""
    return re.sub(r"\W+", "_", (ref or "sem_ref").strip()).strip("_") or "sem_ref"


def _formatar_avisos(avisos) -> str:
    """Texto legível dos Avisos para o AVISOS.txt do zip."""
    linhas = ["AVISOS DA GERAÇÃO (confira/complete no middleware)", ""]
    for a in avisos:
        linhas.append(f"- [{a.tipo}] {a.campo}: {a.mensagem}")
    return "\n".join(linhas) + "\n"


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

    # Bug 2: nunca deixar partida incompleta / lote desbalanceado passar em
    # silêncio — sinaliza (sem bloquear) para o operador completar a conta.
    processo.avisos.extend(validar_partidas(lancamentos))

    ref = _slug(processo.processo)
    arquivos = {
        f"{ref}_saida_A_extracao.csv": gerar_saida_a([processo]),
        f"{ref}_saida_A_rastreavel.csv": gerar_saida_a_rastreavel([processo]),
        f"{ref}_saida_B_lancamentos_dominio.csv": gerar_saida_b(lancamentos),
        f"{ref}_saida_B_lancamentos_dominio.txt": gerar_saida_b(lancamentos),
    }
    if middleware.incluir_saida_c:
        arquivos[f"{ref}_saida_C_fornecedores.csv"] = gerar_saida_c([processo])
    if processo.avisos:
        arquivos[f"{ref}_AVISOS.txt"] = _formatar_avisos(processo.avisos)

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for nome, conteudo in arquivos.items():
            # BOM para abrir certinho no Excel PT-BR
            zf.writestr(nome, "﻿" + conteudo)
    buf.seek(0)

    nome_zip = f"{ref}_saidas.zip"
    # O corpo é um .zip, então o front não consegue ler os avisos da geração. Estes
    # headers (ASCII) carregam o essencial para a tela: quantas partidas a Saída B
    # tem e quais contas obrigatórias continuam em branco. Sem isso, uma Saída B
    # vazia era baixada com um "✓ arquivos baixados" — o bug relatado.
    return Response(
        content=buf.getvalue(),
        media_type="application/zip",
        headers={
            "Content-Disposition": f'attachment; filename="{nome_zip}"',
            "X-Saida-B-Partidas": str(len(lancamentos)),
            "X-Contas-Pendentes": ",".join(_contas_pendentes(processo.avisos)),
            "Access-Control-Expose-Headers": "X-Saida-B-Partidas, X-Contas-Pendentes",
        },
    )


def _contas_pendentes(avisos) -> List[str]:
    """Papéis de conta sem código, extraídos dos Avisos ``conta:<papel>`` do motor."""
    pendentes = []
    for a in avisos:
        if a.campo.startswith("conta:"):
            papel = a.campo.split(":", 1)[1]
            if papel not in pendentes:
                pendentes.append(papel)
    return pendentes


XLSX_MEDIA = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


@app.post("/relacao")
async def relacao(arquivo: UploadFile = File(...), payload: str = Form(...)):
    """Saída D (spec §6.4): recebe a Relação atual da empresa (.xlsx), insere UMA
    linha do processo sob o bloco do ano e devolve o arquivo atualizado.

    O ``payload`` é o mesmo ``GerarRequest`` (processo + middleware) do /generate,
    enviado como campo de formulário ao lado do upload da planilha.
    """
    try:
        req = GerarRequest.model_validate_json(payload)
    except Exception as exc:
        return JSONResponse(status_code=422, content={"erro": f"payload inválido: {exc}"})

    processo = req.processo
    if req.middleware.tipo_importacao:
        processo.tipo_importacao = req.middleware.tipo_importacao

    conteudo = await arquivo.read()
    try:
        atualizado = append_relacao(conteudo, processo, req.middleware)
    except Exception as exc:  # planilha inesperada / corrompida — não derruba a rota
        return JSONResponse(
            status_code=400,
            content={"erro": f"não foi possível atualizar a Relação: {exc}"},
        )

    nome = f"{_slug(processo.processo)}_relacao_atualizada.xlsx"
    return Response(
        content=atualizado,
        media_type=XLSX_MEDIA,
        headers={"Content-Disposition": f'attachment; filename="{nome}"'},
    )


@app.get("/")
async def index():
    return FileResponse(os.path.join(FRONTEND, "index.html"))


# Arquivos estáticos do front-end (app.js, styles.css)
app.mount("/static", StaticFiles(directory=FRONTEND), name="static")

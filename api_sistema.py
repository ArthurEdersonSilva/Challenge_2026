from __future__ import annotations

from datetime import datetime
import os
from typing import Any, Dict, Optional
from uuid import uuid4

import cv2
import numpy as np
from flask import jsonify, request
from flask_cors import CORS

from api_evidencias import app

from services.camera_service import (
    buscar_cameras,
    testar_camera_manual,
    testar_camera_descoberta,
    cadastrar_camera_rede,
    editar_camera_rede,
    buscar_cameras_usb,
    testar_camera_usb,
    cadastrar_camera_usb,
    editar_camera_usb,
    listar_cameras_com_status,
    obter_camera,
    obter_status_camera,
    verificar_vinculos_camera,
    remover_camera,
    iniciar_preview,
    obter_frame_preview,
    parar_preview,
    reconectar_preview,
    listar_previews_ativos,
)

from services.ambiente_service import (
    listar_ambientes_consulta,
    obter_ambiente,
    criar_ambiente,
    editar_ambiente_basico,
    remover_ambiente,
    listar_rois,
    obter_roi,
    definir_roi,
    remover_roi,
    previsualizar_area_monitoramento,
    obter_area_monitoramento,
    analisar_area_selecionada,
    analisar_roi_salva,
    preparar_selecao_maquinario,
    salvar_selecao_maquinario,
    listar_objetos_ambiente,
    listar_maquinarios_ambiente,
    descartar_analise_maquinario,
    listar_epis_disponiveis,
    obter_epis_obrigatorios,
    definir_epis_obrigatorios,
    listar_colaboradores_para_ambiente,
    obter_colaboradores_vinculados,
    definir_colaboradores_vinculados,
    vincular_colaborador,
    desvincular_colaborador,
    obter_revisao_ambiente,
    obter_status_ambiente,
    atualizar_status_ambientes,
    obter_detalhes_ambiente_consulta,
    finalizar_ambiente,
)

from services.colaborador_service import (
    consultar_colaboradores,
    obter_detalhes_colaborador,
    obter_imagem_colaborador,
    validar_captura_facial,
    cadastrar_colaborador,
    editar_colaborador,
    remover_colaborador,
    obter_status_biometria,
    atualizar_biometria_colaborador,
)

from services.colaborador_consulta_service import (
    consultar_colaboradores_gerencial,
    listar_opcoes_filtros_colaboradores,
    obter_detalhes_colaborador_gerencial,
)

from services.monitoramento_colaborador_service import (
    obter_monitoramento_colaborador,
)

from services.dashboard_gerencial_service import (
    obter_dashboard_gerencial,
)


# ============================================================
# ALIASES PÚBLICOS ESPERADOS PELOS TESTES HTTP
# ============================================================

consultar_ambientes = listar_ambientes_consulta


# ============================================================
# CORS
# ============================================================

_ORIGENS_PADRAO = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]

_ORIGENS_CONFIG = os.getenv(
    "CHALLENGE_FRONTEND_ORIGINS",
    "",
).strip()

_ORIGENS = (
    [
        item.strip()
        for item in _ORIGENS_CONFIG.split(",")
        if item.strip()
    ]
    if _ORIGENS_CONFIG
    else _ORIGENS_PADRAO
)

CORS(
    app,
    resources={r"/api/*": {"origins": _ORIGENS}},
)


# ============================================================
# CONTEXTO DE AUTENTICAÇÃO
# ============================================================

_estado_sistema_atual = None

# Sessões seguras de preview destinadas à tela de Monitoramento do Colaborador.
# O frontend recebe somente o token desta camada; o session_id interno do
# camera_service não é exposto ao OPERADOR.
_monitoramento_previews: Dict[str, Dict[str, Any]] = {}


def definir_estado_sistema(estado_sistema: Any) -> None:
    """
    Injeta a instância runtime real usada pelo monitoramento.

    Não cria um segundo EstadoSistema.
    """
    global _estado_sistema_atual
    _estado_sistema_atual = estado_sistema


def obter_estado_sistema():
    return _estado_sistema_atual


def obter_contexto_autenticacao() -> Dict[str, Any]:
    """
    Adaptador local inicial de autenticação.

    Enquanto o projeto não possuir um provedor de login/token fechado,
    aceita cabeçalhos locais:
        X-Perfil: GERENCIAL | GESTOR | OPERADOR
        X-Matricula: matrícula do usuário autenticado

    IMPORTANTE:
    isto representa somente o contrato de transporte local.
    O frontend não deve escolher livremente o próprio perfil em produção.
    """
    perfil = str(
        request.headers.get("X-Perfil") or ""
    ).strip().upper()

    matricula = str(
        request.headers.get("X-Matricula") or ""
    ).strip() or None

    if perfil not in {
        "GERENCIAL",
        "GESTOR",
        "OPERADOR",
        "COLABORADOR",
    }:
        return {
            "autenticado": False,
            "perfil": None,
            "matricula": None,
        }

    if perfil == "GESTOR":
        perfil = "GERENCIAL"

    if perfil == "COLABORADOR":
        perfil = "OPERADOR"

    return {
        "autenticado": True,
        "perfil": perfil,
        "matricula": matricula,
    }


# ============================================================
# HELPERS HTTP
# ============================================================

def _json(
    dados: Dict[str, Any],
    status: int = 200,
):
    return jsonify(dados), status


def _erro(
    codigo: str,
    status: int,
    **extras,
):
    payload = {
        "sucesso": False,
        "erro": codigo,
    }
    payload.update(extras)
    return _json(payload, status)


def _exigir_autenticacao(
    apenas_gerencial: bool = False,
):
    contexto = obter_contexto_autenticacao()

    if not contexto.get("autenticado"):
        return None, _erro(
            "NAO_AUTENTICADO",
            401,
        )

    if (
        apenas_gerencial
        and contexto.get("perfil") != "GERENCIAL"
    ):
        return contexto, _erro(
            "ACESSO_NEGADO",
            403,
        )

    return contexto, None


def _status_por_erro(
    erro: Optional[str],
) -> int:
    if erro in {
        "CAMERA_NAO_ENCONTRADA",
        "CAMERA_USB_NAO_ENCONTRADA",
        "AMBIENTE_NAO_ENCONTRADO",
        "COLABORADOR_NAO_ENCONTRADO",
        "ROI_NAO_DEFINIDA",
        "PREVIEW_NAO_ENCONTRADO",
        "ANALISE_MAQUINARIO_NAO_ENCONTRADA",
        "OBJETO_GLOBAL_NAO_ENCONTRADO",
        "COLABORADOR_NAO_VINCULADO",
        "IMAGEM_COLABORADOR_NAO_ENCONTRADA",
        "MONITORAMENTO_PREVIEW_NAO_ENCONTRADO",
    }:
        return 404

    if erro in {
        "NOME_AMBIENTE_JA_EXISTE",
        "MATRICULA_JA_CADASTRADA",
        "CAMERA_POSSUI_VINCULOS",
        "COLABORADOR_POSSUI_VINCULOS",
        "CAMERA_VINCULADA_A_AMBIENTE",
        "BIOMETRIA_JA_EXISTENTE",
        "ANALISE_DE_OUTRO_AMBIENTE",
        "PREVIEW_DE_OUTRA_CAMERA",
    }:
        return 409

    if erro in {
        "CAMERA_INDISPONIVEL",
        "CAMERA_USB_INDISPONIVEL",
        "FRAME_USB_NAO_RECEBIDO",
        "STREAM_INDISPONIVEL",
        "STREAM_NAO_DESCOBERTO",
        "MONITORAMENTO_INDISPONIVEL",
        "ESTADO_SISTEMA_INDISPONIVEL",
        "NENHUM_FRAME_VALIDO_PARA_ANALISE",
        "MONITORAMENTO_CAMERA_INDISPONIVEL",
    }:
        return 503

    if erro in {
        "ERRO_LISTAR_CAMERAS",
        "ERRO_LISTAR_AMBIENTES",
        "ERRO_LISTAR_COLABORADORES",
        "ERRO_CARREGAR_INCIDENTES",
        "ERRO_SALVAR_CAMERA",
        "ERRO_SALVAR_AMBIENTE",
        "ERRO_SALVAR_COLABORADOR",
        "ERRO_ATUALIZAR_COLABORADOR",
        "ERRO_REMOVER_COLABORADOR",
        "ERRO_VERIFICAR_VINCULOS_COLABORADOR",
        "ERRO_LER_IMAGEM_COLABORADOR",
        "ERRO_REMOVER_AMBIENTE",
        "ERRO_CODIFICAR_ANALISE_AMBIENTE",
        "ERRO_CODIFICAR_AREA_MONITORAMENTO",
        "ERRO_INTERNO",
    }:
        return 500

    return 400


def _responder_service(
    resultado: Dict[str, Any],
    sucesso_status: int = 200,
):
    if resultado.get("sucesso"):
        return _json(resultado, sucesso_status)

    erro = resultado.get("erro") or "ERRO_INTERNO"
    return _json(
        resultado,
        _status_por_erro(erro),
    )


def _json_body() -> Dict[str, Any]:
    dados = request.get_json(silent=True)
    return dados if isinstance(dados, dict) else {}


def _inteiro_query(
    nome: str,
    padrao: int,
) -> int:
    valor = request.args.get(nome)

    if valor is None:
        return padrao

    try:
        return int(valor)
    except Exception:
        return padrao


def _data_valida(valor: Optional[str]) -> bool:
    if not valor:
        return True

    try:
        datetime.strptime(
            valor,
            "%Y-%m-%d",
        )
        return True
    except ValueError:
        return False


def _decodificar_upload_imagem(
    campo: str = "imagem_biometrica",
):
    arquivo = request.files.get(campo)

    if arquivo is None:
        return None

    dados = arquivo.read()

    if not dados:
        return None

    array = np.frombuffer(
        dados,
        dtype=np.uint8,
    )

    return cv2.imdecode(
        array,
        cv2.IMREAD_COLOR,
    )


# ============================================================
# ERRO INTERNO GLOBAL
# ============================================================

@app.errorhandler(Exception)
def _erro_interno_global(erro):
    return _erro(
        "ERRO_INTERNO",
        500,
    )


# ============================================================
# CÂMERAS
# ============================================================

@app.get("/api/cameras")
def api_listar_cameras():
    _, falha = _exigir_autenticacao(
        apenas_gerencial=True
    )
    if falha:
        return falha

    return _responder_service(
        listar_cameras_com_status()
    )


@app.get("/api/cameras/status")
def api_status_cameras():
    _, falha = _exigir_autenticacao(
        apenas_gerencial=True
    )
    if falha:
        return falha

    return _responder_service(
        listar_cameras_com_status()
    )


@app.get("/api/cameras/<camera_uid>")
def api_obter_camera(camera_uid: str):
    _, falha = _exigir_autenticacao(
        apenas_gerencial=True
    )
    if falha:
        return falha

    return _responder_service(
        obter_camera(camera_uid)
    )


@app.get("/api/cameras/<camera_uid>/status")
def api_status_camera(camera_uid: str):
    _, falha = _exigir_autenticacao(
        apenas_gerencial=True
    )
    if falha:
        return falha

    return _responder_service(
        obter_status_camera(camera_uid)
    )


@app.get("/api/cameras/<camera_uid>/vinculos")
def api_vinculos_camera(camera_uid: str):
    _, falha = _exigir_autenticacao(
        apenas_gerencial=True
    )
    if falha:
        return falha

    return _responder_service(
        verificar_vinculos_camera(camera_uid)
    )


@app.post("/api/cameras/rede/buscar")
def api_buscar_cameras_rede():
    _, falha = _exigir_autenticacao(
        apenas_gerencial=True
    )
    if falha:
        return falha

    resultado = buscar_cameras()

    if (
        resultado.get("sucesso")
        and "candidatos" not in resultado
        and "cameras" in resultado
    ):
        resultado = dict(resultado)
        resultado["candidatos"] = resultado.get(
            "cameras",
            [],
        )

    return _responder_service(resultado)


@app.post("/api/cameras/rede/testar")
def api_testar_camera_rede():
    _, falha = _exigir_autenticacao(
        apenas_gerencial=True
    )
    if falha:
        return falha

    dados = _json_body()

    candidato = dados.get("candidato")
    fonte = str(
        dados.get("fonte") or ""
    ).strip()
    usuario = dados.get("usuario")
    senha = dados.get("senha")

    if isinstance(candidato, dict):
        resultado = testar_camera_descoberta(
            candidato,
            usuario=usuario,
            senha=senha,
        )
    elif fonte:
        resultado = testar_camera_manual(
            fonte,
            usuario=usuario,
            senha=senha,
        )
    else:
        return _erro(
            "FONTE_OU_CANDIDATO_OBRIGATORIO",
            400,
        )

    return _responder_service(resultado)


@app.post("/api/cameras/rede")
def api_cadastrar_camera_rede():
    _, falha = _exigir_autenticacao(
        apenas_gerencial=True
    )
    if falha:
        return falha

    dados = _json_body()

    nome = str(
        dados.get("nome") or ""
    ).strip()

    if not nome:
        return _erro(
            "NOME_OBRIGATORIO",
            400,
        )

    fonte = str(
        dados.get("fonte") or ""
    ).strip()

    if not fonte:
        return _erro(
            "URL_STREAM_OBRIGATORIA",
            400,
        )

    resultado = cadastrar_camera_rede(
        nome=nome,
        fonte=fonte,
        onvif=bool(
            dados.get("onvif", False)
        ),
        portas_detectadas=dados.get(
            "portas_detectadas"
        ),
        camera_uid=dados.get("camera_uid"),
    )

    return _responder_service(
        resultado,
        sucesso_status=201,
    )


@app.put("/api/cameras/<camera_uid>")
def api_editar_camera(camera_uid: str):
    _, falha = _exigir_autenticacao(
        apenas_gerencial=True
    )
    if falha:
        return falha

    atual = obter_camera(camera_uid)

    if not atual.get("sucesso"):
        return _responder_service(atual)

    dados = _json_body()
    camera = atual.get("camera") or {}
    tipo = str(
        camera.get("tipo") or ""
    ).lower()

    nome = dados.get(
        "nome",
        camera.get("nome"),
    )

    if tipo == "usb":
        resultado = editar_camera_usb(
            camera_uid,
            nome,
        )
    else:
        fonte = dados.get("fonte")

        if fonte is None:
            fonte = (
                camera.get("conexao")
                or {}
            ).get("fonte")

        resultado = editar_camera_rede(
            camera_uid=camera_uid,
            nome=nome,
            fonte=fonte,
            onvif=dados.get("onvif"),
        )

    return _responder_service(resultado)


@app.delete("/api/cameras/<camera_uid>")
def api_remover_camera(camera_uid: str):
    _, falha = _exigir_autenticacao(
        apenas_gerencial=True
    )
    if falha:
        return falha

    vinculos = verificar_vinculos_camera(
        camera_uid
    )

    if not vinculos.get("sucesso"):
        return _responder_service(vinculos)

    possui = bool(
        vinculos.get("possui_vinculos")
        or vinculos.get("vinculada")
    )

    if possui:
        itens = (
            vinculos.get("vinculos")
            or vinculos.get("ambientes")
            or []
        )
        return _erro(
            "CAMERA_POSSUI_VINCULOS",
            409,
            vinculos=itens,
        )

    return _responder_service(
        remover_camera(camera_uid)
    )


@app.post("/api/cameras/usb/buscar")
def api_buscar_cameras_usb():
    _, falha = _exigir_autenticacao(
        apenas_gerencial=True
    )
    if falha:
        return falha

    return _responder_service(
        buscar_cameras_usb()
    )


@app.post("/api/cameras/usb/testar")
def api_testar_camera_usb():
    _, falha = _exigir_autenticacao(
        apenas_gerencial=True
    )
    if falha:
        return falha

    dados = _json_body()

    if "indice" not in dados:
        return _erro(
            "INDICE_USB_OBRIGATORIO",
            400,
        )

    try:
        indice = int(dados["indice"])
    except Exception:
        return _erro(
            "INDICE_USB_INVALIDO",
            400,
        )

    return _responder_service(
        testar_camera_usb(indice)
    )


@app.post("/api/cameras/usb")
def api_cadastrar_camera_usb():
    _, falha = _exigir_autenticacao(
        apenas_gerencial=True
    )
    if falha:
        return falha

    dados = _json_body()

    nome = str(
        dados.get("nome") or ""
    ).strip()

    if not nome:
        return _erro(
            "NOME_OBRIGATORIO",
            400,
        )

    try:
        indice = int(dados.get("indice"))
    except Exception:
        return _erro(
            "INDICE_USB_INVALIDO",
            400,
        )

    resultado = cadastrar_camera_usb(
        indice=indice,
        nome=nome,
        camera_uid=dados.get("camera_uid"),
    )

    return _responder_service(
        resultado,
        sucesso_status=201,
    )


@app.post("/api/cameras/<camera_uid>/preview")
def api_iniciar_preview(camera_uid: str):
    _, falha = _exigir_autenticacao(
        apenas_gerencial=True
    )
    if falha:
        return falha

    return _responder_service(
        iniciar_preview(camera_uid)
    )


@app.get("/api/cameras/preview/<session_id>/frame")
def api_obter_frame_preview(session_id: str):
    _, falha = _exigir_autenticacao(
        apenas_gerencial=True
    )
    if falha:
        return falha

    return _responder_service(
        obter_frame_preview(session_id)
    )


@app.post("/api/cameras/preview/<session_id>/reconectar")
def api_reconectar_preview(session_id: str):
    _, falha = _exigir_autenticacao(
        apenas_gerencial=True
    )
    if falha:
        return falha

    return _responder_service(
        reconectar_preview(session_id)
    )


@app.delete("/api/cameras/preview/<session_id>")
def api_parar_preview(session_id: str):
    _, falha = _exigir_autenticacao(
        apenas_gerencial=True
    )
    if falha:
        return falha

    return _responder_service(
        parar_preview(session_id)
    )


@app.get("/api/cameras/previews")
def api_listar_previews():
    _, falha = _exigir_autenticacao(
        apenas_gerencial=True
    )
    if falha:
        return falha

    return _responder_service(
        listar_previews_ativos()
    )


# ============================================================
# AMBIENTES
# ============================================================

@app.get("/api/ambientes")
def api_consultar_ambientes():
    _, falha = _exigir_autenticacao(
        apenas_gerencial=True
    )
    if falha:
        return falha

    resultado = consultar_ambientes(
        busca=request.args.get("busca"),
        status=request.args.get("status"),
        camera_uid=request.args.get(
            "camera_uid"
        ),
        epi=request.args.get("epi"),
        pagina=_inteiro_query(
            "pagina",
            1,
        ),
        por_pagina=_inteiro_query(
            "por_pagina",
            20,
        ),
    )

    return _responder_service(resultado)


@app.get("/api/ambientes/<ambiente_id>")
def api_obter_ambiente(ambiente_id: str):
    _, falha = _exigir_autenticacao(
        apenas_gerencial=True
    )
    if falha:
        return falha

    return _responder_service(
        obter_ambiente(ambiente_id)
    )


@app.post("/api/ambientes")
def api_criar_ambiente():
    _, falha = _exigir_autenticacao(
        apenas_gerencial=True
    )
    if falha:
        return falha

    dados = _json_body()

    nome = str(
        dados.get("nome") or ""
    ).strip()

    if not nome:
        return _erro(
            "NOME_AMBIENTE_OBRIGATORIO",
            400,
        )

    camera_uids = (
        dados.get("camera_uids")
        if "camera_uids" in dados
        else dados.get("cameras")
    )

    resultado = criar_ambiente(
        nome=nome,
        camera_uids=camera_uids or [],
        epis_obrigatorios=dados.get(
            "epis_obrigatorios"
        ),
        descricao=str(
            dados.get("descricao") or ""
        ),
    )

    return _responder_service(
        resultado,
        sucesso_status=201,
    )


@app.put("/api/ambientes/<ambiente_id>")
def api_editar_ambiente(
    ambiente_id: str,
):
    _, falha = _exigir_autenticacao(
        apenas_gerencial=True
    )
    if falha:
        return falha

    dados = _json_body()

    camera_uids = None
    if "camera_uids" in dados:
        camera_uids = dados.get(
            "camera_uids"
        )
    elif "cameras" in dados:
        camera_uids = dados.get(
            "cameras"
        )

    resultado = editar_ambiente_basico(
        ambiente_id=ambiente_id,
        nome=dados.get("nome"),
        camera_uids=camera_uids,
        epis_obrigatorios=dados.get(
            "epis_obrigatorios"
        ),
        calibrado=dados.get(
            "calibrado"
        ),
        descricao=dados.get(
            "descricao"
        ),
    )

    return _responder_service(resultado)


@app.delete("/api/ambientes/<ambiente_id>")
def api_remover_ambiente(
    ambiente_id: str,
):
    _, falha = _exigir_autenticacao(
        apenas_gerencial=True
    )
    if falha:
        return falha

    return _responder_service(
        remover_ambiente(ambiente_id)
    )


@app.get("/api/ambientes/status")
def api_status_ambientes():
    _, falha = _exigir_autenticacao(
        apenas_gerencial=True
    )
    if falha:
        return falha

    return _responder_service(
        atualizar_status_ambientes()
    )


@app.post("/api/ambientes/<ambiente_id>/finalizar")
def api_finalizar_ambiente(
    ambiente_id: str,
):
    _, falha = _exigir_autenticacao(
        apenas_gerencial=True
    )
    if falha:
        return falha

    return _responder_service(
        finalizar_ambiente(ambiente_id)
    )


# ------------------------------------------------------------
# AMBIENTES — DETALHES / STATUS INDIVIDUAL
# ------------------------------------------------------------

@app.get("/api/ambientes/<ambiente_id>/detalhes")
def api_detalhes_ambiente(ambiente_id: str):
    _, falha = _exigir_autenticacao(
        apenas_gerencial=True
    )
    if falha:
        return falha

    return _responder_service(
        obter_detalhes_ambiente_consulta(ambiente_id)
    )


@app.get("/api/ambientes/<ambiente_id>/status")
def api_status_ambiente(ambiente_id: str):
    _, falha = _exigir_autenticacao(
        apenas_gerencial=True
    )
    if falha:
        return falha

    return _responder_service(
        obter_status_ambiente(ambiente_id)
    )


# ------------------------------------------------------------
# AMBIENTES — ROI
# ------------------------------------------------------------

@app.get("/api/ambientes/<ambiente_id>/rois")
def api_listar_rois_ambiente(ambiente_id: str):
    _, falha = _exigir_autenticacao(
        apenas_gerencial=True
    )
    if falha:
        return falha

    return _responder_service(
        listar_rois(ambiente_id)
    )


@app.get("/api/ambientes/<ambiente_id>/rois/<camera_uid>")
def api_obter_roi_ambiente(
    ambiente_id: str,
    camera_uid: str,
):
    _, falha = _exigir_autenticacao(
        apenas_gerencial=True
    )
    if falha:
        return falha

    return _responder_service(
        obter_roi(ambiente_id, camera_uid)
    )


@app.put("/api/ambientes/<ambiente_id>/rois/<camera_uid>")
def api_definir_roi_ambiente(
    ambiente_id: str,
    camera_uid: str,
):
    _, falha = _exigir_autenticacao(
        apenas_gerencial=True
    )
    if falha:
        return falha

    dados = _json_body()

    return _responder_service(
        definir_roi(
            ambiente_id=ambiente_id,
            camera_uid=camera_uid,
            x1=dados.get("x1"),
            y1=dados.get("y1"),
            x2=dados.get("x2"),
            y2=dados.get("y2"),
        )
    )


@app.delete("/api/ambientes/<ambiente_id>/rois/<camera_uid>")
def api_remover_roi_ambiente(
    ambiente_id: str,
    camera_uid: str,
):
    _, falha = _exigir_autenticacao(
        apenas_gerencial=True
    )
    if falha:
        return falha

    return _responder_service(
        remover_roi(ambiente_id, camera_uid)
    )


# ------------------------------------------------------------
# AMBIENTES — PREVIEW/CROP DA ÁREA DE MONITORAMENTO
# ------------------------------------------------------------

@app.post("/api/ambientes/area-monitoramento/previsualizar")
def api_previsualizar_area_monitoramento():
    _, falha = _exigir_autenticacao(
        apenas_gerencial=True
    )
    if falha:
        return falha

    dados = _json_body()

    return _responder_service(
        previsualizar_area_monitoramento(
            session_id=dados.get("session_id"),
            camera_uid=dados.get("camera_uid"),
            x1=dados.get("x1"),
            y1=dados.get("y1"),
            x2=dados.get("x2"),
            y2=dados.get("y2"),
            qualidade_jpeg=dados.get("qualidade_jpeg", 90),
        )
    )


@app.post("/api/ambientes/<ambiente_id>/rois/<camera_uid>/preview")
def api_preview_roi_salva(
    ambiente_id: str,
    camera_uid: str,
):
    _, falha = _exigir_autenticacao(
        apenas_gerencial=True
    )
    if falha:
        return falha

    dados = _json_body()

    return _responder_service(
        obter_area_monitoramento(
            ambiente_id=ambiente_id,
            camera_uid=camera_uid,
            session_id=dados.get("session_id"),
            qualidade_jpeg=dados.get("qualidade_jpeg", 90),
        )
    )


# ------------------------------------------------------------
# AMBIENTES — ANÁLISE DA ÁREA
# ------------------------------------------------------------

@app.post("/api/ambientes/area-monitoramento/analisar")
def api_analisar_area_monitoramento():
    _, falha = _exigir_autenticacao(
        apenas_gerencial=True
    )
    if falha:
        return falha

    dados = _json_body()

    return _responder_service(
        analisar_area_selecionada(
            session_id=dados.get("session_id"),
            camera_uid=dados.get("camera_uid"),
            x1=dados.get("x1"),
            y1=dados.get("y1"),
            x2=dados.get("x2"),
            y2=dados.get("y2"),
            qualidade_jpeg=dados.get("qualidade_jpeg", 90),
            quantidade_frames=dados.get("quantidade_frames", 10),
        )
    )


@app.post("/api/ambientes/<ambiente_id>/rois/<camera_uid>/analisar")
def api_analisar_roi_salva(
    ambiente_id: str,
    camera_uid: str,
):
    _, falha = _exigir_autenticacao(
        apenas_gerencial=True
    )
    if falha:
        return falha

    dados = _json_body()

    return _responder_service(
        analisar_roi_salva(
            ambiente_id=ambiente_id,
            camera_uid=camera_uid,
            session_id=dados.get("session_id"),
            qualidade_jpeg=dados.get("qualidade_jpeg", 90),
            quantidade_frames=dados.get("quantidade_frames", 10),
        )
    )


# ------------------------------------------------------------
# AMBIENTES — MAQUINÁRIO
# ------------------------------------------------------------

@app.post("/api/ambientes/<ambiente_id>/maquinario/preparar")
def api_preparar_maquinario(ambiente_id: str):
    _, falha = _exigir_autenticacao(
        apenas_gerencial=True
    )
    if falha:
        return falha

    dados = _json_body()

    return _responder_service(
        preparar_selecao_maquinario(
            ambiente_id=ambiente_id,
            sessoes_por_camera=dados.get("sessoes_por_camera"),
            qualidade_jpeg=dados.get("qualidade_jpeg", 90),
        )
    )


@app.put("/api/ambientes/<ambiente_id>/maquinario")
def api_salvar_maquinario(ambiente_id: str):
    _, falha = _exigir_autenticacao(
        apenas_gerencial=True
    )
    if falha:
        return falha

    dados = _json_body()

    return _responder_service(
        salvar_selecao_maquinario(
            ambiente_id=ambiente_id,
            analise_id=dados.get("analise_id"),
            ids_maquinario=dados.get("ids_maquinario"),
        )
    )


@app.get("/api/ambientes/<ambiente_id>/objetos")
def api_listar_objetos_ambiente(ambiente_id: str):
    _, falha = _exigir_autenticacao(
        apenas_gerencial=True
    )
    if falha:
        return falha

    return _responder_service(
        listar_objetos_ambiente(ambiente_id)
    )


@app.get("/api/ambientes/<ambiente_id>/maquinarios")
def api_listar_maquinarios_ambiente(ambiente_id: str):
    _, falha = _exigir_autenticacao(
        apenas_gerencial=True
    )
    if falha:
        return falha

    return _responder_service(
        listar_maquinarios_ambiente(ambiente_id)
    )


@app.delete("/api/ambientes/analises-maquinario/<analise_id>")
def api_descartar_analise_maquinario(analise_id: str):
    _, falha = _exigir_autenticacao(
        apenas_gerencial=True
    )
    if falha:
        return falha

    return _responder_service(
        descartar_analise_maquinario(analise_id)
    )


# ------------------------------------------------------------
# AMBIENTES — EPIs
# ------------------------------------------------------------

@app.get("/api/ambientes/epis/disponiveis")
def api_listar_epis_disponiveis():
    _, falha = _exigir_autenticacao(
        apenas_gerencial=True
    )
    if falha:
        return falha

    return _responder_service(
        listar_epis_disponiveis()
    )


@app.get("/api/ambientes/<ambiente_id>/epis")
def api_obter_epis_ambiente(ambiente_id: str):
    _, falha = _exigir_autenticacao(
        apenas_gerencial=True
    )
    if falha:
        return falha

    return _responder_service(
        obter_epis_obrigatorios(ambiente_id)
    )


@app.put("/api/ambientes/<ambiente_id>/epis")
def api_definir_epis_ambiente(ambiente_id: str):
    _, falha = _exigir_autenticacao(
        apenas_gerencial=True
    )
    if falha:
        return falha

    dados = _json_body()

    return _responder_service(
        definir_epis_obrigatorios(
            ambiente_id=ambiente_id,
            epis_obrigatorios=dados.get("epis_obrigatorios"),
        )
    )


# ------------------------------------------------------------
# AMBIENTES — COLABORADORES VINCULADOS
# ------------------------------------------------------------

@app.get("/api/ambientes/colaboradores/disponiveis")
def api_colaboradores_disponiveis_ambiente():
    _, falha = _exigir_autenticacao(
        apenas_gerencial=True
    )
    if falha:
        return falha

    return _responder_service(
        listar_colaboradores_para_ambiente()
    )


@app.get("/api/ambientes/<ambiente_id>/colaboradores")
def api_obter_colaboradores_ambiente(ambiente_id: str):
    _, falha = _exigir_autenticacao(
        apenas_gerencial=True
    )
    if falha:
        return falha

    return _responder_service(
        obter_colaboradores_vinculados(ambiente_id)
    )


@app.put("/api/ambientes/<ambiente_id>/colaboradores")
def api_definir_colaboradores_ambiente(ambiente_id: str):
    _, falha = _exigir_autenticacao(
        apenas_gerencial=True
    )
    if falha:
        return falha

    dados = _json_body()

    return _responder_service(
        definir_colaboradores_vinculados(
            ambiente_id=ambiente_id,
            matriculas=dados.get("matriculas"),
        )
    )


@app.post("/api/ambientes/<ambiente_id>/colaboradores/<matricula>")
def api_vincular_colaborador_ambiente(
    ambiente_id: str,
    matricula: str,
):
    _, falha = _exigir_autenticacao(
        apenas_gerencial=True
    )
    if falha:
        return falha

    return _responder_service(
        vincular_colaborador(ambiente_id, matricula)
    )


@app.delete("/api/ambientes/<ambiente_id>/colaboradores/<matricula>")
def api_desvincular_colaborador_ambiente(
    ambiente_id: str,
    matricula: str,
):
    _, falha = _exigir_autenticacao(
        apenas_gerencial=True
    )
    if falha:
        return falha

    return _responder_service(
        desvincular_colaborador(ambiente_id, matricula)
    )


# ------------------------------------------------------------
# AMBIENTES — REVISÃO
# ------------------------------------------------------------

@app.get("/api/ambientes/<ambiente_id>/revisao")
def api_revisao_ambiente(ambiente_id: str):
    _, falha = _exigir_autenticacao(
        apenas_gerencial=True
    )
    if falha:
        return falha

    return _responder_service(
        obter_revisao_ambiente(ambiente_id)
    )


# ============================================================
# COLABORADORES
# ============================================================

@app.post("/api/colaboradores/biometria/validar")
def api_validar_captura_facial():
    _, falha = _exigir_autenticacao(
        apenas_gerencial=True
    )
    if falha:
        return falha

    imagem = _decodificar_upload_imagem()

    if imagem is None:
        return _erro(
            "IMAGEM_BIOMETRICA_OBRIGATORIA",
            400,
        )

    return _responder_service(
        validar_captura_facial(imagem)
    )


@app.get("/api/colaboradores")
def api_consultar_colaboradores():
    _, falha = _exigir_autenticacao(
        apenas_gerencial=True
    )
    if falha:
        return falha

    resultado = consultar_colaboradores(
        busca=request.args.get("busca"),
        pagina=_inteiro_query(
            "pagina",
            1,
        ),
        por_pagina=_inteiro_query(
            "por_pagina",
            20,
        ),
        setor=request.args.get("setor"),
    )

    return _responder_service(resultado)


@app.get("/api/colaboradores/consulta-gerencial/filtros")
def api_filtros_consulta_colaboradores_gerencial():
    _, falha = _exigir_autenticacao(
        apenas_gerencial=True
    )
    if falha:
        return falha

    return _responder_service(
        listar_opcoes_filtros_colaboradores()
    )


@app.get("/api/colaboradores/consulta-gerencial")
def api_consulta_colaboradores_gerencial():
    _, falha = _exigir_autenticacao(
        apenas_gerencial=True
    )
    if falha:
        return falha

    resultado = consultar_colaboradores_gerencial(
        data_inicio=request.args.get("data_inicio"),
        data_fim=request.args.get("data_fim"),
        setor=request.args.get("setor"),
        ambiente=request.args.get("ambiente"),
        situacao_infracoes=request.args.get("situacao_infracoes"),
        busca=request.args.get("busca"),
        pagina=_inteiro_query("pagina", 1),
        por_pagina=_inteiro_query("por_pagina", 20),
    )

    return _responder_service(resultado)


@app.get("/api/colaboradores/<matricula>/detalhes-gerenciais")
def api_detalhes_colaborador_gerencial(matricula: str):
    _, falha = _exigir_autenticacao(
        apenas_gerencial=True
    )
    if falha:
        return falha

    resultado = obter_detalhes_colaborador_gerencial(
        matricula=matricula,
        data_inicio=request.args.get("data_inicio"),
        data_fim=request.args.get("data_fim"),
        limite_historico=_inteiro_query("limite_historico", 20),
    )

    return _responder_service(resultado)


@app.get("/api/colaboradores/<matricula>")
def api_detalhes_colaborador(
    matricula: str,
):
    _, falha = _exigir_autenticacao(
        apenas_gerencial=True
    )
    if falha:
        return falha

    return _responder_service(
        obter_detalhes_colaborador(
            matricula
        )
    )


@app.get("/api/colaboradores/<matricula>/imagem")
def api_imagem_colaborador(matricula: str):
    _, falha = _exigir_autenticacao(
        apenas_gerencial=True
    )
    if falha:
        return falha

    return _responder_service(
        obter_imagem_colaborador(matricula)
    )


@app.post("/api/colaboradores")
def api_cadastrar_colaborador():
    _, falha = _exigir_autenticacao(
        apenas_gerencial=True
    )
    if falha:
        return falha

    matricula = str(
        request.form.get("matricula")
        or ""
    ).strip()
    nome = str(
        request.form.get("nome")
        or ""
    ).strip()
    cargo = str(
        request.form.get("cargo")
        or ""
    ).strip()
    setor = str(
        request.form.get("setor")
        or ""
    ).strip() or None

    if not matricula:
        return _erro(
            "MATRICULA_OBRIGATORIA",
            400,
        )

    if not nome:
        return _erro(
            "NOME_OBRIGATORIO",
            400,
        )

    if not cargo:
        return _erro(
            "CARGO_OBRIGATORIO",
            400,
        )

    imagem = _decodificar_upload_imagem()

    if imagem is None:
        return _erro(
            "IMAGEM_BIOMETRICA_OBRIGATORIA",
            400,
        )

    resultado = cadastrar_colaborador(
        matricula=matricula,
        nome=nome,
        cargo=cargo,
        imagem_biometrica=imagem,
        setor=setor,
    )

    return _responder_service(
        resultado,
        sucesso_status=201,
    )


@app.put("/api/colaboradores/<matricula>")
def api_editar_colaborador(
    matricula: str,
):
    _, falha = _exigir_autenticacao(
        apenas_gerencial=True
    )
    if falha:
        return falha

    dados = _json_body()

    return _responder_service(
        editar_colaborador(
            matricula=matricula,
            nome=dados.get("nome"),
            cargo=dados.get("cargo"),
            setor=dados.get("setor"),
        )
    )



def _verificar_vinculos_colaborador_http(
    matricula: str,
) -> Dict[str, Any]:
    """
    Verifica se a matrícula está vinculada a algum ambiente.

    Fica na camada HTTP para evitar dependência circular entre
    colaborador_service e ambiente_service.
    """
    matricula = str(matricula or "").strip()
    vinculos = []
    pagina = 1
    por_pagina = 100

    try:
        while True:
            resultado = listar_ambientes_consulta(
                pagina=pagina,
                por_pagina=por_pagina,
                atualizar_status=False,
            )

            if not resultado.get("sucesso"):
                return {
                    "sucesso": False,
                    "erro": "ERRO_VERIFICAR_VINCULOS_COLABORADOR",
                    "detalhe": resultado.get("erro"),
                    "vinculos": [],
                }

            ambientes = resultado.get("ambientes") or []

            for ambiente in ambientes:
                ambiente_id = str(
                    ambiente.get("ambiente_id") or ""
                ).strip()

                if not ambiente_id:
                    continue

                vinculados = obter_colaboradores_vinculados(
                    ambiente_id
                )

                if not vinculados.get("sucesso"):
                    # Um ambiente removido entre as duas leituras não deve
                    # transformar a exclusão em falso positivo.
                    if vinculados.get("erro") == "AMBIENTE_NAO_ENCONTRADO":
                        continue

                    return {
                        "sucesso": False,
                        "erro": "ERRO_VERIFICAR_VINCULOS_COLABORADOR",
                        "detalhe": vinculados.get("erro"),
                        "vinculos": [],
                    }

                colaboradores = vinculados.get("colaboradores") or []
                matriculas_ausentes = {
                    str(item or "").strip()
                    for item in (
                        vinculados.get("matriculas_ausentes") or []
                    )
                }

                esta_vinculado = any(
                    str(item.get("matricula") or "").strip() == matricula
                    for item in colaboradores
                    if isinstance(item, dict)
                ) or matricula in matriculas_ausentes

                if esta_vinculado:
                    vinculos.append({
                        "ambiente_id": ambiente_id,
                        "nome": ambiente.get("nome"),
                    })

            paginacao = resultado.get("paginacao") or {}
            try:
                total_paginas = int(
                    paginacao.get("total_paginas") or 1
                )
            except (TypeError, ValueError):
                total_paginas = 1

            if pagina >= total_paginas or not ambientes:
                break

            pagina += 1

    except Exception as erro:
        return {
            "sucesso": False,
            "erro": "ERRO_VERIFICAR_VINCULOS_COLABORADOR",
            "detalhe": str(erro),
            "vinculos": [],
        }

    return {
        "sucesso": True,
        "erro": None,
        "matricula": matricula,
        "possui_vinculos": bool(vinculos),
        "quantidade_vinculos": len(vinculos),
        "vinculos": vinculos,
    }


@app.delete("/api/colaboradores/<matricula>")
def api_remover_colaborador(matricula: str):
    _, falha = _exigir_autenticacao(
        apenas_gerencial=True
    )
    if falha:
        return falha

    existente = obter_detalhes_colaborador(matricula)
    if not existente.get("sucesso"):
        return _responder_service(existente)

    verificacao = _verificar_vinculos_colaborador_http(
        matricula
    )
    if not verificacao.get("sucesso"):
        return _responder_service(verificacao)

    vinculos = verificacao.get("vinculos") or []
    if vinculos:
        return _erro(
            "COLABORADOR_POSSUI_VINCULOS",
            409,
            matricula=matricula,
            quantidade_vinculos=len(vinculos),
            vinculos=vinculos,
        )

    return _responder_service(
        remover_colaborador(matricula)
    )

@app.get("/api/colaboradores/<matricula>/biometria/status")
def api_status_biometria(
    matricula: str,
):
    _, falha = _exigir_autenticacao(
        apenas_gerencial=True
    )
    if falha:
        return falha

    return _responder_service(
        obter_status_biometria(
            matricula
        )
    )


@app.put("/api/colaboradores/<matricula>/biometria")
def api_atualizar_biometria(
    matricula: str,
):
    _, falha = _exigir_autenticacao(
        apenas_gerencial=True
    )
    if falha:
        return falha

    imagem = _decodificar_upload_imagem()

    if imagem is None:
        return _erro(
            "IMAGEM_BIOMETRICA_OBRIGATORIA",
            400,
        )

    return _responder_service(
        atualizar_biometria_colaborador(
            matricula=matricula,
            imagem_biometrica=imagem,
        )
    )


# ============================================================
# MONITORAMENTO DO COLABORADOR
# ============================================================

def _executar_monitoramento(
    matricula: str,
):
    estado = obter_estado_sistema()

    if estado is None:
        return _erro(
            "ESTADO_SISTEMA_INDISPONIVEL",
            503,
        )

    resultado = obter_monitoramento_colaborador(
        matricula,
        estado,
    )

    return _responder_service(resultado)


@app.get("/api/monitoramento/me")
def api_monitoramento_me():
    contexto, falha = _exigir_autenticacao(
        apenas_gerencial=False
    )
    if falha:
        return falha

    matricula = str(
        contexto.get("matricula")
        or ""
    ).strip()

    if not matricula:
        return _erro(
            "ACESSO_NEGADO",
            403,
        )

    return _executar_monitoramento(
        matricula
    )


@app.get("/api/monitoramento/colaboradores/<matricula>")
def api_monitoramento_colaborador(
    matricula: str,
):
    contexto, falha = _exigir_autenticacao(
        apenas_gerencial=False
    )
    if falha:
        return falha

    if (
        contexto.get("perfil") == "OPERADOR"
        and str(
            contexto.get("matricula")
            or ""
        ).strip()
        != str(matricula).strip()
    ):
        return _erro(
            "ACESSO_NEGADO",
            403,
        )

    return _executar_monitoramento(
        matricula
    )


# ============================================================
# PREVIEW SEGURO — MONITORAMENTO DO COLABORADOR
# ============================================================

def _matricula_contexto_obrigatoria():
    contexto, falha = _exigir_autenticacao(
        apenas_gerencial=False
    )
    if falha:
        return None, falha

    matricula = str(
        contexto.get("matricula") or ""
    ).strip()

    if not matricula:
        return None, _erro(
            "ACESSO_NEGADO",
            403,
        )

    return matricula, None


def _camera_monitoramento_atual(
    matricula: str,
):
    estado = obter_estado_sistema()

    if estado is None:
        return None, _erro(
            "ESTADO_SISTEMA_INDISPONIVEL",
            503,
        )

    resultado = obter_monitoramento_colaborador(
        matricula,
        estado,
    )

    if not resultado.get("sucesso"):
        return None, _json(
            resultado,
            _status_por_erro(
                resultado.get("erro")
            ),
        )

    monitoramento = resultado.get("monitoramento") or {}
    camera = monitoramento.get("camera") or {}
    camera_uid = str(
        camera.get("camera_uid") or ""
    ).strip()

    if (
        not monitoramento.get("presente")
        or not camera_uid
    ):
        return None, _erro(
            "MONITORAMENTO_CAMERA_INDISPONIVEL",
            503,
        )

    return {
        "camera_uid": camera_uid,
        "nome": camera.get("nome"),
        "tipo": camera.get("tipo"),
        "status": camera.get("status"),
    }, None


def _obter_preview_monitoramento_autorizado(
    token: str,
    matricula: str,
):
    sessao = _monitoramento_previews.get(token)

    if sessao is None:
        return None, _erro(
            "MONITORAMENTO_PREVIEW_NAO_ENCONTRADO",
            404,
        )

    if str(sessao.get("matricula") or "") != matricula:
        return None, _erro(
            "ACESSO_NEGADO",
            403,
        )

    return sessao, None


@app.post("/api/monitoramento/me/preview")
def api_monitoramento_me_iniciar_preview():
    matricula, falha = _matricula_contexto_obrigatoria()
    if falha:
        return falha

    camera, falha = _camera_monitoramento_atual(
        matricula
    )
    if falha:
        return falha

    resultado = iniciar_preview(
        camera["camera_uid"]
    )

    if not resultado.get("sucesso"):
        return _responder_service(resultado)

    token = str(uuid4())

    _monitoramento_previews[token] = {
        "matricula": matricula,
        "camera_uid": camera["camera_uid"],
        "preview_session_id": resultado.get("session_id"),
        "preview_reutilizado": bool(
            resultado.get("reutilizada", False)
        ),
    }

    # Resposta propositalmente sanitizada: não contém fonte, URL,
    # usuário, senha ou demais dados administrativos da câmera.
    return _json({
        "sucesso": True,
        "erro": None,
        "session_id": token,
        "camera": {
            "camera_uid": camera["camera_uid"],
            "nome": camera.get("nome"),
            "tipo": camera.get("tipo"),
            "status": camera.get("status"),
        },
        "status": "PREVIEW_ATIVO",
    })


@app.get("/api/monitoramento/me/preview/<session_id>/frame")
def api_monitoramento_me_frame_preview(
    session_id: str,
):
    matricula, falha = _matricula_contexto_obrigatoria()
    if falha:
        return falha

    sessao, falha = _obter_preview_monitoramento_autorizado(
        session_id,
        matricula,
    )
    if falha:
        return falha

    resultado = obter_frame_preview(
        sessao["preview_session_id"]
    )

    if not resultado.get("sucesso"):
        if resultado.get("erro") == "PREVIEW_NAO_ENCONTRADO":
            _monitoramento_previews.pop(
                session_id,
                None,
            )
        return _responder_service(resultado)

    return _json({
        "sucesso": True,
        "erro": None,
        "session_id": session_id,
        "camera_uid": sessao.get("camera_uid"),
        "mime_type": resultado.get("mime_type"),
        "frame_base64": resultado.get("frame_base64"),
        "largura": resultado.get("largura"),
        "altura": resultado.get("altura"),
    })


@app.delete("/api/monitoramento/me/preview/<session_id>")
def api_monitoramento_me_parar_preview(
    session_id: str,
):
    matricula, falha = _matricula_contexto_obrigatoria()
    if falha:
        return falha

    sessao, falha = _obter_preview_monitoramento_autorizado(
        session_id,
        matricula,
    )
    if falha:
        return falha

    _monitoramento_previews.pop(
        session_id,
        None,
    )

    # Se a sessão interna já existia, ela pode pertencer a outro consumidor
    # administrativo. Nesse caso apenas removemos o vínculo do OPERADOR.
    if not sessao.get("preview_reutilizado"):
        resultado = parar_preview(
            sessao["preview_session_id"]
        )
        if not resultado.get("sucesso"):
            return _responder_service(resultado)

    return _json({
        "sucesso": True,
        "erro": None,
        "session_id": session_id,
        "status": "PREVIEW_ENCERRADO",
    })


# ============================================================
# DASHBOARD GERENCIAL
# ============================================================

@app.get("/api/dashboard-gerencial")
def api_dashboard_gerencial():
    _, falha = _exigir_autenticacao(
        apenas_gerencial=True
    )
    if falha:
        return falha

    data_inicio = request.args.get(
        "data_inicio"
    )
    data_fim = request.args.get(
        "data_fim"
    )

    if not _data_valida(
        data_inicio
    ) or not _data_valida(
        data_fim
    ):
        return _erro(
            "DATA_INVALIDA",
            400,
        )

    if (
        data_inicio
        and data_fim
        and data_inicio > data_fim
    ):
        return _erro(
            "DATA_INVALIDA",
            400,
        )

    resultado = obter_dashboard_gerencial(
        data_inicio=data_inicio,
        data_fim=data_fim,
    )

    return _responder_service(resultado)


# ============================================================
# EXECUÇÃO LOCAL
# ============================================================

if __name__ == "__main__":
    app.run(
        host="127.0.0.1",
        port=5000,
        debug=False,
    )

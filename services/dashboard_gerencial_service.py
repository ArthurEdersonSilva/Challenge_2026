from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, List, Optional

from services.camera_service import listar_cameras_com_status
from services.ambiente_service import atualizar_status_ambientes
from services.colaborador_service import listar_colaboradores
from services.dashboard_infracoes_service import obter_dashboard_infracoes


def _falha(resultado: Dict[str, Any], erro_padrao: str) -> Optional[Dict[str, Any]]:
    if resultado.get("sucesso"):
        return None

    return {
        "sucesso": False,
        "erro": resultado.get("erro") or erro_padrao,
        "detalhe": resultado.get("detalhe"),
    }


def _montar_alertas(
    cameras: List[Dict[str, Any]],
    ambientes: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    alertas: List[Dict[str, Any]] = []

    for camera in cameras:
        if bool(camera.get("online")):
            continue

        alertas.append({
            "tipo": "CAMERA_OFFLINE",
            "camera_uid": camera.get("camera_uid"),
            "camera_nome": camera.get("nome"),
            "motivo": camera.get("motivo"),
        })

    for ambiente in ambientes:
        if str(ambiente.get("status") or "").upper() != "COM_PROBLEMA":
            continue

        alertas.append({
            "tipo": "AMBIENTE_COM_PROBLEMA",
            "ambiente_id": ambiente.get("ambiente_id"),
            "ambiente_nome": ambiente.get("nome"),
            "motivo": ambiente.get("motivo"),
        })

    return alertas


def _total_infracoes(indicadores: Dict[str, Any]) -> int:
    total = indicadores.get("total_infracoes")

    if isinstance(total, dict):
        try:
            return int(total.get("atual") or 0)
        except (TypeError, ValueError):
            return 0

    try:
        return int(total or 0)
    except (TypeError, ValueError):
        return 0


def obter_dashboard_gerencial(
    data_inicio: Any = None,
    data_fim: Any = None,
) -> Dict[str, Any]:
    """
    Agrega dados já produzidos pelos serviços do backend para o Dashboard Gerencial.

    O serviço é somente-leitura:
    - não persiste dados;
    - não acessa JSON/CSV diretamente;
    - não executa OpenCV, YOLO ou biometria;
    - não altera os retornos recebidos das dependências.
    """
    cameras_resultado = listar_cameras_com_status()
    falha = _falha(cameras_resultado, "ERRO_LISTAR_CAMERAS")
    if falha:
        return falha

    ambientes_resultado = atualizar_status_ambientes()
    falha = _falha(ambientes_resultado, "ERRO_LISTAR_AMBIENTES")
    if falha:
        return falha

    colaboradores_resultado = listar_colaboradores()
    falha = _falha(
        colaboradores_resultado,
        "ERRO_LISTAR_COLABORADORES",
    )
    if falha:
        return falha

    infracoes_resultado = obter_dashboard_infracoes(
        data_inicio=data_inicio,
        data_fim=data_fim,
    )
    falha = _falha(
        infracoes_resultado,
        "ERRO_CARREGAR_INCIDENTES",
    )
    if falha:
        return falha

    cameras = deepcopy(
        cameras_resultado.get("cameras") or []
    )
    ambientes = deepcopy(
        ambientes_resultado.get("ambientes") or []
    )
    colaboradores = deepcopy(
        colaboradores_resultado.get("colaboradores") or []
    )

    indicadores = deepcopy(
        infracoes_resultado.get("indicadores") or {}
    )
    serie_temporal = deepcopy(
        infracoes_resultado.get("serie_temporal") or []
    )
    ambientes_com_mais_infracoes = deepcopy(
        infracoes_resultado.get("infracoes_por_ambiente") or []
    )

    cameras_total = len(cameras)
    cameras_online = sum(
        1
        for camera in cameras
        if bool(camera.get("online"))
    )
    cameras_offline = cameras_total - cameras_online

    ambientes_total = len(ambientes)
    ambientes_ativos = sum(
        1
        for ambiente in ambientes
        if str(ambiente.get("status") or "").upper() == "ATIVO"
    )
    ambientes_com_problema = sum(
        1
        for ambiente in ambientes
        if str(ambiente.get("status") or "").upper()
        == "COM_PROBLEMA"
    )
    ambientes_inativos = sum(
        1
        for ambiente in ambientes
        if str(ambiente.get("status") or "").upper() == "INATIVO"
    )

    periodo_fonte = infracoes_resultado.get("filtros")
    if not isinstance(periodo_fonte, dict):
        periodo_fonte = {}

    periodo = {
        "data_inicio": (
            data_inicio
            if data_inicio is not None
            else periodo_fonte.get("data_inicio")
        ),
        "data_fim": (
            data_fim
            if data_fim is not None
            else periodo_fonte.get("data_fim")
        ),
    }

    return {
        "sucesso": True,
        "erro": None,
        "resumo": {
            "cameras_total": cameras_total,
            "cameras_online": cameras_online,
            "cameras_offline": cameras_offline,
            "ambientes_total": ambientes_total,
            "ambientes_ativos": ambientes_ativos,
            "ambientes_com_problema": ambientes_com_problema,
            "ambientes_inativos": ambientes_inativos,
            "colaboradores_total": len(colaboradores),
            "infracoes_periodo": _total_infracoes(indicadores),
        },
        "alertas": _montar_alertas(
            cameras=cameras,
            ambientes=ambientes,
        ),
        "ambientes_com_mais_infracoes": ambientes_com_mais_infracoes,
        "serie_temporal": serie_temporal,
        "status_cameras": cameras,
        "periodo": periodo,
    }

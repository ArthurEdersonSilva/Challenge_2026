from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional

from services.evidencia_service import (
    TIPO_ABERTURA,
    _carregar_eventos,
    _eventos_por_incidente,
    _parse_timestamp,
    _rotulo_infracao,
    _valor_identidade,
)
from services.relatorio_service import gerar_relatorio_geral


def _corresponde_filtro_exato(valor: Any, filtro: Optional[str]) -> bool:
    filtro_q = str(filtro or "").strip().casefold()

    if not filtro_q:
        return True

    return str(valor or "").strip().casefold() == filtro_q


def _incidente_corresponde_filtros(
    abertura: Dict[str, Any],
    eventos: list[Dict[str, Any]],
    data_inicio: str,
    data_fim: str,
    ambiente: Optional[str],
    colaborador: Optional[str],
    epi: Optional[str],
) -> tuple[bool, Dict[str, str], Optional[datetime]]:
    dt = _parse_timestamp(abertura.get("timestamp", ""))

    if dt is None:
        return False, {}, None

    data_iso = dt.date().isoformat()

    if data_iso < str(data_inicio) or data_iso > str(data_fim):
        return False, {}, dt

    ambiente_q = str(ambiente or "").strip().casefold()

    if ambiente_q:
        candidatos = {
            str(abertura.get("ambiente_id") or "").strip().casefold(),
            str(abertura.get("ambiente_nome") or "").strip().casefold(),
        }

        if ambiente_q not in candidatos:
            return False, {}, dt

    identidade = {
        "matricula": _valor_identidade(
            eventos,
            "matricula",
            "--",
        ),
        "nome": _valor_identidade(
            eventos,
            "nome",
            "DESCONHECIDO",
        ),
        "cargo": _valor_identidade(
            eventos,
            "cargo",
            "--",
        ),
    }

    colaborador_q = str(colaborador or "").strip().casefold()

    if colaborador_q:
        candidatos = {
            identidade["matricula"].casefold(),
            identidade["nome"].casefold(),
        }

        if colaborador_q not in candidatos:
            return False, identidade, dt

    epi_q = str(epi or "").strip().casefold()

    if epi_q:
        candidatos = {
            str(abertura.get("epi") or "").strip().casefold(),
            str(
                abertura.get("tipo_irregularidade") or ""
            ).strip().casefold(),
        }

        if epi_q not in candidatos:
            return False, identidade, dt

    return True, identidade, dt



def listar_opcoes_filtros_dashboard() -> Dict[str, Any]:
    carregado = _carregar_eventos()

    if not carregado.get("sucesso"):
        return {
            "sucesso": False,
            "erro": carregado.get("erro"),
            "detalhe": carregado.get("detalhe"),
            "ambientes": [],
            "colaboradores": [],
            "epis": [],
            "tipos_irregularidade": [],
            "epi_infracao": [],
        }

    agrupados = _eventos_por_incidente(
        carregado["eventos"]
    )

    ambientes: Dict[str, Dict[str, Any]] = {}
    colaboradores: Dict[str, Dict[str, Any]] = {}
    epis = set()
    tipos_irregularidade = set()

    for incidente_id, eventos in agrupados.items():
        abertura = next(
            (
                evento
                for evento in eventos
                if str(
                    evento.get("tipo_registro") or ""
                ).strip() == TIPO_ABERTURA
            ),
            None,
        )

        if abertura is None:
            continue

        ambiente_id = str(
            abertura.get("ambiente_id") or ""
        ).strip()
        ambiente_nome = str(
            abertura.get("ambiente_nome") or ""
        ).strip()

        if ambiente_id or ambiente_nome:
            chave_ambiente = ambiente_id or ambiente_nome

            ambientes[chave_ambiente] = {
                "ambiente_id": ambiente_id or None,
                "nome": ambiente_nome,
            }

        matricula = _valor_identidade(
            eventos,
            "matricula",
            "--",
        )
        nome = _valor_identidade(
            eventos,
            "nome",
            "DESCONHECIDO",
        )
        cargo = _valor_identidade(
            eventos,
            "cargo",
            "--",
        )

        if matricula and matricula != "--":
            colaboradores[matricula] = {
                "matricula": matricula,
                "nome": nome,
                "cargo": cargo,
            }

        epi = str(
            abertura.get("epi") or ""
        ).strip()

        if epi:
            epis.add(epi)

        tipo = str(
            abertura.get("tipo_irregularidade") or ""
        ).strip()

        if tipo:
            tipos_irregularidade.add(tipo)

    epis_ordenados = sorted(
        epis,
        key=str.casefold,
    )
    tipos_ordenados = sorted(
        tipos_irregularidade,
        key=str.casefold,
    )

    epi_infracao = [
        {
            "tipo": "EPI",
            "valor": valor,
            "rotulo": valor,
        }
        for valor in epis_ordenados
    ] + [
        {
            "tipo": "INFRACAO",
            "valor": valor,
            "rotulo": valor,
        }
        for valor in tipos_ordenados
    ]

    return {
        "sucesso": True,
        "erro": None,
        "ambientes": sorted(
            ambientes.values(),
            key=lambda item: (
                item.get("nome") or ""
            ).casefold(),
        ),
        "colaboradores": sorted(
            colaboradores.values(),
            key=lambda item: (
                item.get("nome") or ""
            ).casefold(),
        ),
        "epis": epis_ordenados,
        "tipos_irregularidade": tipos_ordenados,
        "epi_infracao": epi_infracao,
    }

def obter_dashboard_infracoes(
    data_inicio: Any = None,
    data_fim: Any = None,
    ambiente: Optional[str] = None,
    colaborador: Optional[str] = None,
    epi: Optional[str] = None,
    limite_recentes: int = 20,
) -> Dict[str, Any]:
    relatorio = gerar_relatorio_geral(
        data_inicio=data_inicio,
        data_fim=data_fim,
        ambiente=ambiente,
        colaborador=colaborador,
        epi=epi,
        granularidade="DIARIO",
    )

    if not relatorio.get("sucesso"):
        return relatorio

    carregado = _carregar_eventos()

    if not carregado.get("sucesso"):
        return {
            "sucesso": False,
            "erro": carregado.get("erro"),
            "detalhe": carregado.get("detalhe"),
        }

    agrupados = _eventos_por_incidente(
        carregado["eventos"]
    )

    estado_contagem = {
        "ATIVO": 0,
        "OBSERVACAO_SUSPENSA": 0,
        "ENCERRADO": 0,
    }

    recentes = []

    filtros_relatorio = relatorio["filtros"]
    inicio = filtros_relatorio["data_inicio"]
    fim = filtros_relatorio["data_fim"]

    for incidente_id, eventos in agrupados.items():
        if not eventos:
            continue

        abertura = next(
            (
                evento
                for evento in eventos
                if str(
                    evento.get("tipo_registro") or ""
                ).strip() == TIPO_ABERTURA
            ),
            None,
        )

        if abertura is None:
            continue

        corresponde, identidade, dt = _incidente_corresponde_filtros(
            abertura=abertura,
            eventos=eventos,
            data_inicio=inicio,
            data_fim=fim,
            ambiente=ambiente,
            colaborador=colaborador,
            epi=epi,
        )

        if not corresponde:
            continue

        ultimo = eventos[-1]

        estado = str(
            ultimo.get("estado_incidente") or ""
        ).strip()

        if estado in estado_contagem:
            estado_contagem[estado] += 1

        recentes.append({
            "incidente_id": incidente_id,
            "timestamp": (
                None
                if dt is None
                else dt.isoformat()
            ),
            "ambiente_id": abertura.get("ambiente_id"),
            "ambiente_nome": abertura.get("ambiente_nome"),
            "camera_id": abertura.get("camera_id"),
            "camera_nome": abertura.get("camera_nome"),
            "epi": abertura.get("epi"),
            "tipo_irregularidade": abertura.get(
                "tipo_irregularidade"
            ),
            "infracao": _rotulo_infracao(
                abertura.get("epi", ""),
                abertura.get(
                    "tipo_irregularidade",
                    "",
                ),
            ),
            "estado_incidente": estado,
            **identidade,
        })

    recentes.sort(
        key=lambda item: item.get("timestamp") or "",
        reverse=True,
    )

    try:
        limite_recentes = max(
            1,
            min(200, int(limite_recentes)),
        )
    except Exception:
        limite_recentes = 20

    return {
        "sucesso": True,
        "erro": None,
        "indicadores": relatorio["indicadores"],
        "serie_temporal": relatorio["serie_temporal"],
        "infracoes_por_ambiente": relatorio[
            "infracoes_por_ambiente"
        ],
        "infracoes_por_epi": relatorio[
            "infracoes_por_epi"
        ],
        "infracoes_por_colaborador": relatorio[
            "resumo_por_colaborador"
        ],
        "estado_incidentes_historico": {
            "ativos": estado_contagem["ATIVO"],
            "observacao_suspensa": estado_contagem[
                "OBSERVACAO_SUSPENSA"
            ],
            "encerrados": estado_contagem["ENCERRADO"],
        },
        "ocorrencias_recentes": recentes[:limite_recentes],
        "filtros": filtros_relatorio,
    }

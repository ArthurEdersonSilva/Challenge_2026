from __future__ import annotations

from typing import Any, Dict, Iterable, Mapping, Optional, Tuple

from services.colaborador_service import obter_detalhes_colaborador

try:
    from avaliacao_ergonomia import obter_estado_ergonomia
except Exception:  # pragma: no cover - fallback defensivo de integração
    obter_estado_ergonomia = None


STATUS_CONFORME = "CONFORME"
STATUS_NAO_CONFORME = "NAO_CONFORME"
STATUS_INDETERMINADO = "INDETERMINADO"


def _snapshot_estado(estado_sistema: Any) -> Dict[str, Any]:
    """
    Obtém um snapshot somente-leitura do estado atual.

    Aceita o EstadoSistema real (método snapshot) e também um mapping,
    facilitando testes sem alterar o runtime.
    """
    if estado_sistema is None:
        return {}

    snapshot = getattr(estado_sistema, "snapshot", None)
    if callable(snapshot):
        resultado = snapshot()
        return dict(resultado or {})

    if isinstance(estado_sistema, Mapping):
        return dict(estado_sistema)

    return {}


def _normalizar_matricula(valor: Any) -> str:
    return str(valor or "").strip()


def _epis_obrigatorios(snapshot: Mapping[str, Any]) -> Tuple[str, ...]:
    ambiente = snapshot.get("ambiente") or {}
    epis = ambiente.get("epis_obrigatorios") or ()

    resultado = []
    for epi in epis:
        nome = str(epi or "").strip()
        if nome and nome not in resultado:
            resultado.append(nome)

    return tuple(resultado)


def _encontrar_pessoa(
    snapshot: Mapping[str, Any],
    matricula: str,
) -> Tuple[Optional[Any], Optional[Dict[str, Any]]]:
    pessoas = snapshot.get("pessoas") or {}

    if isinstance(pessoas, Mapping):
        itens: Iterable = pessoas.items()
    else:
        return None, None

    for chave, pessoa in itens:
        if not isinstance(pessoa, Mapping):
            continue

        identidade = pessoa.get("identidade") or {}
        matricula_identidade = _normalizar_matricula(
            identidade.get("matricula")
        )

        if matricula_identidade != matricula:
            continue

        ativo = bool(pessoa.get("ativo", False))
        detectado = bool(pessoa.get("detectado_no_frame", False))

        if not ativo or not detectado:
            continue

        return chave, dict(pessoa)

    return None, None


def _pessoa_identificada(
    pessoa: Optional[Mapping[str, Any]],
    matricula: str,
) -> bool:
    if not pessoa:
        return False

    identidade = pessoa.get("identidade") or {}

    return bool(
        _normalizar_matricula(identidade.get("matricula")) == matricula
        and bool(identidade.get("conhecida", False))
        and str(identidade.get("status_identidade") or "").upper()
        == "IDENTIFICADO"
    )


def _camera_da_pessoa(
    snapshot: Mapping[str, Any],
    pessoa: Optional[Mapping[str, Any]],
) -> Optional[Dict[str, Any]]:
    if not pessoa:
        return None

    camera_id = pessoa.get("camera_id")
    cameras = snapshot.get("cameras") or {}

    camera = None

    if isinstance(cameras, Mapping):
        camera = cameras.get(camera_id)

        if camera is None:
            camera = cameras.get(str(camera_id))

    if not isinstance(camera, Mapping):
        return None

    return {
        "camera_id": camera.get("camera_id", camera_id),
        "camera_uid": camera.get("camera_uid"),
        "nome": camera.get("nome"),
        "tipo": camera.get("tipo"),
        "status": camera.get("status"),
        "ativa": bool(camera.get("ativa", False)),
    }


def _ambiente_atual(
    snapshot: Mapping[str, Any],
) -> Optional[Dict[str, Any]]:
    ambiente = snapshot.get("ambiente")

    if not isinstance(ambiente, Mapping):
        return None

    return {
        "ambiente_id": ambiente.get("ambiente_id"),
        "nome": ambiente.get("nome"),
        "calibrado": bool(ambiente.get("calibrado", False)),
    }


def _chave_track(
    chave_pessoa: Any,
    pessoa: Optional[Mapping[str, Any]],
) -> Tuple[Any, Any]:
    if pessoa:
        camera_id = pessoa.get("camera_id")
        track_instance_id = pessoa.get("track_instance_id")

        if camera_id is not None and track_instance_id is not None:
            return camera_id, track_instance_id

    if (
        isinstance(chave_pessoa, tuple)
        and len(chave_pessoa) >= 2
    ):
        return chave_pessoa[0], chave_pessoa[1]

    return None, None


def _estado_epi_confirmado(
    snapshot: Mapping[str, Any],
    chave_pessoa: Any,
    pessoa: Optional[Mapping[str, Any]],
    epi: str,
) -> str:
    """
    Usa somente estado temporal confirmado.

    Estado instantâneo isolado não é suficiente para classificar conformidade.
    """
    camera_id, track_instance_id = _chave_track(
        chave_pessoa,
        pessoa,
    )

    estados_temporais = snapshot.get("estados_epi_temporais") or {}

    estado_temporal = None
    if isinstance(estados_temporais, Mapping):
        estado_temporal = estados_temporais.get(
            (camera_id, track_instance_id, epi)
        )

    if isinstance(estado_temporal, Mapping):
        confirmado = estado_temporal.get("estado_confirmado")
        if confirmado is not None:
            valor = str(confirmado).strip().upper()
            if valor:
                return valor

    return STATUS_INDETERMINADO


def _montar_epis(
    snapshot: Mapping[str, Any],
    chave_pessoa: Any,
    pessoa: Optional[Mapping[str, Any]],
) -> list[Dict[str, str]]:
    itens = []

    for epi in _epis_obrigatorios(snapshot):
        itens.append({
            "epi": epi,
            "estado": _estado_epi_confirmado(
                snapshot=snapshot,
                chave_pessoa=chave_pessoa,
                pessoa=pessoa,
                epi=epi,
            ),
        })

    return itens


def _status_geral(
    presente: bool,
    epis: list[Dict[str, str]],
) -> str:
    if not presente:
        return STATUS_INDETERMINADO

    if not epis:
        return STATUS_INDETERMINADO

    estados = {
        str(item.get("estado") or "").upper()
        for item in epis
    }

    if "AUSENTE" in estados or "INCORRETO" in estados:
        return STATUS_NAO_CONFORME

    if estados and estados == {"CORRETO"}:
        return STATUS_CONFORME

    return STATUS_INDETERMINADO


def _ergonomia_indisponivel() -> Dict[str, Any]:
    return {
        "disponivel": False,
        "estado": None,
        "postura": None,
        "problemas": [],
    }


def _ergonomia_da_pessoa(
    pessoa: Optional[Mapping[str, Any]],
) -> Dict[str, Any]:
    """
    Lê somente o resultado estabilizado já produzido por avaliacao_ergonomia.

    Não executa Pose nem recalcula ergonomia. A fonte runtime existente é
    consultada apenas quando o track atual possui keypoints, evitando
    apresentar ergonomia como disponível em snapshots artificiais/legados
    que não carregam informação de pose.
    """
    if not pessoa:
        return _ergonomia_indisponivel()

    camera_id = pessoa.get("camera_id")
    track_instance_id = pessoa.get("track_instance_id")
    keypoints = pessoa.get("keypoints") or {}

    if (
        camera_id is None
        or not track_instance_id
        or not isinstance(keypoints, Mapping)
        or not keypoints
        or not callable(obter_estado_ergonomia)
    ):
        return _ergonomia_indisponivel()

    try:
        resultado = obter_estado_ergonomia(
            camera_id,
            track_instance_id,
        )
    except Exception:
        return _ergonomia_indisponivel()

    if not isinstance(resultado, Mapping):
        return _ergonomia_indisponivel()

    estado = str(
        resultado.get("estado") or "INDETERMINADA"
    ).strip().upper()
    postura = str(
        resultado.get("modo") or "INDETERMINADA"
    ).strip().upper()

    problemas_brutos = resultado.get("problemas") or []
    problemas = []
    if isinstance(problemas_brutos, (list, tuple)):
        for problema in problemas_brutos:
            if isinstance(problema, Mapping):
                problemas.append({
                    "regiao": problema.get("regiao"),
                    "descricao": problema.get("descricao"),
                })
            else:
                problemas.append(problema)

    return {
        "disponivel": True,
        "estado": estado,
        "postura": postura,
        "problemas": problemas,
    }


def obter_monitoramento_colaborador(
    matricula: str,
    estado_sistema: Any,
) -> Dict[str, Any]:
    """
    Projeta o estado runtime de um colaborador para a tela de monitoramento.

    Esta função:
    - não executa biometria;
    - não executa YOLO;
    - não executa ergonomia; apenas lê o resultado runtime já estabilizado;
    - não altera EstadoSistema;
    - não altera CSV ou imagens biométricas.
    """
    matricula = _normalizar_matricula(matricula)

    detalhes = obter_detalhes_colaborador(matricula)

    if not detalhes.get("sucesso"):
        return {
            "sucesso": False,
            "erro": detalhes.get("erro"),
            "colaborador": None,
            "monitoramento": None,
        }

    cadastro = detalhes["colaborador"]
    snapshot = _snapshot_estado(estado_sistema)

    chave_pessoa, pessoa = _encontrar_pessoa(
        snapshot=snapshot,
        matricula=matricula,
    )

    identificado = _pessoa_identificada(
        pessoa=pessoa,
        matricula=matricula,
    )
    presente = pessoa is not None and identificado

    epis = (
        _montar_epis(
            snapshot=snapshot,
            chave_pessoa=chave_pessoa,
            pessoa=pessoa,
        )
        if presente
        else [
            {
                "epi": epi,
                "estado": STATUS_INDETERMINADO,
            }
            for epi in _epis_obrigatorios(snapshot)
        ]
    )

    colaborador = {
        "matricula": cadastro.get("matricula"),
        "nome": cadastro.get("nome"),
        "cargo": cadastro.get("cargo"),
        "identificado": identificado,
    }

    monitoramento = {
        "presente": presente,
        "camera": (
            _camera_da_pessoa(snapshot, pessoa)
            if presente
            else None
        ),
        "ambiente": _ambiente_atual(snapshot),
        "status_geral": _status_geral(
            presente=presente,
            epis=epis,
        ),
        "epis_obrigatorios": epis,
        "ergonomia": (
            _ergonomia_da_pessoa(pessoa)
            if presente
            else _ergonomia_indisponivel()
        ),
        "atualizado_em": snapshot.get("atualizado_em"),
    }

    return {
        "sucesso": True,
        "erro": None,
        "colaborador": colaborador,
        "monitoramento": monitoramento,
    }

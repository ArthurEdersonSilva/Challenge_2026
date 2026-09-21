from __future__ import annotations

from collections import Counter, defaultdict
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from services.colaborador_service import (
    listar_colaboradores,
    obter_detalhes_colaborador,
    obter_status_biometria,
)
from services.ambiente_service import (
    listar_ambientes,
    obter_colaboradores_vinculados,
)
from services.evidencia_service import (
    TIPO_ABERTURA,
    TIPO_EVIDENCIA,
    _carregar_eventos,
    _eventos_por_incidente,
    _parse_timestamp,
    _rotulo_infracao,
    _valor_identidade,
)


def _normalizar_texto(valor: Any) -> str:
    return str(valor or "").strip()


def _parse_data(valor: Any) -> Optional[date]:
    texto = _normalizar_texto(valor)
    if not texto:
        return None
    try:
        return datetime.strptime(texto, "%Y-%m-%d").date()
    except ValueError:
        raise ValueError("DATA_INVALIDA")


def _resolver_periodo(
    data_inicio: Any = None,
    data_fim: Any = None,
) -> Tuple[date, date]:
    fim = _parse_data(data_fim)
    if fim is None:
        fim = datetime.now().astimezone().date()

    inicio = _parse_data(data_inicio)
    if inicio is None:
        inicio = fim - timedelta(days=29)

    if inicio > fim:
        raise ValueError("PERIODO_INVALIDO")

    return inicio, fim


def _mapa_ambientes_por_matricula() -> Tuple[Dict[str, List[Dict[str, Any]]], bool]:
    resultado = listar_ambientes()
    if not resultado.get("sucesso"):
        return {}, False

    mapa: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    disponivel = True

    for ambiente in resultado.get("ambientes") or []:
        if not isinstance(ambiente, dict):
            continue

        ambiente_id = _normalizar_texto(ambiente.get("ambiente_id"))
        if not ambiente_id:
            continue

        vinculados = obter_colaboradores_vinculados(ambiente_id)
        if not vinculados.get("sucesso"):
            # Ambiente removido durante a leitura não deve derrubar toda a consulta.
            if vinculados.get("erro") == "AMBIENTE_NAO_ENCONTRADO":
                continue
            disponivel = False
            continue

        dados_ambiente = {
            "ambiente_id": ambiente_id,
            "nome": ambiente.get("nome"),
        }

        for colaborador in vinculados.get("colaboradores") or []:
            if not isinstance(colaborador, dict):
                continue
            matricula = _normalizar_texto(colaborador.get("matricula"))
            if matricula:
                mapa[matricula].append(dict(dados_ambiente))

        # Matrículas ausentes do cadastro ainda representam vínculo persistido.
        for matricula in vinculados.get("matriculas_ausentes") or []:
            matricula = _normalizar_texto(matricula)
            if matricula:
                mapa[matricula].append(dict(dados_ambiente))

    for matricula in list(mapa):
        mapa[matricula].sort(
            key=lambda item: _normalizar_texto(item.get("nome")).casefold()
        )

    return dict(mapa), disponivel


def _carregar_infracoes() -> Dict[str, Any]:
    carregado = _carregar_eventos()
    if not carregado.get("sucesso"):
        return {
            "sucesso": False,
            "erro": carregado.get("erro") or "ERRO_CARREGAR_INCIDENTES",
            "detalhe": carregado.get("detalhe"),
            "infracoes": [],
        }

    eventos = carregado.get("eventos") or []
    por_incidente = _eventos_por_incidente(eventos)
    vistos = set()
    infracoes: List[Dict[str, Any]] = []

    for evento in eventos:
        if _normalizar_texto(evento.get("tipo_registro")) != TIPO_ABERTURA:
            continue

        incidente_id = _normalizar_texto(evento.get("incidente_id"))
        if not incidente_id or incidente_id in vistos:
            continue
        vistos.add(incidente_id)

        grupo = por_incidente.get(incidente_id, [evento])
        dt = _parse_timestamp(evento.get("timestamp", ""))
        if dt is None:
            continue

        matricula = _valor_identidade(grupo, "matricula", "--")
        nome = _valor_identidade(grupo, "nome", "DESCONHECIDO")
        cargo = _valor_identidade(grupo, "cargo", "--")
        epi = _normalizar_texto(evento.get("epi"))
        tipo_irregularidade = _normalizar_texto(evento.get("tipo_irregularidade"))

        evidencia_id = None
        for item in grupo:
            if _normalizar_texto(item.get("tipo_registro")) != TIPO_EVIDENCIA:
                continue
            candidato = _normalizar_texto(item.get("evidencia_id"))
            if candidato:
                evidencia_id = candidato
                break

        infracoes.append({
            "incidente_id": incidente_id,
            "evidencia_id": evidencia_id,
            "timestamp": dt.isoformat(),
            "data": dt.date().isoformat(),
            "horario": dt.strftime("%H:%M:%S"),
            "ambiente_id": _normalizar_texto(evento.get("ambiente_id")) or None,
            "ambiente_nome": _normalizar_texto(evento.get("ambiente_nome")) or None,
            "camera_id": _normalizar_texto(evento.get("camera_id")) or None,
            "camera_nome": _normalizar_texto(evento.get("camera_nome")) or None,
            "matricula": matricula,
            "nome": nome,
            "cargo": cargo,
            "epi": epi or None,
            "tipo_irregularidade": tipo_irregularidade or None,
            "infracao": _rotulo_infracao(epi, tipo_irregularidade),
        })

    infracoes.sort(
        key=lambda item: _normalizar_texto(item.get("timestamp")),
        reverse=True,
    )

    return {
        "sucesso": True,
        "erro": None,
        "fonte": carregado.get("fonte"),
        "infracoes": infracoes,
    }


def _filtrar_infracoes(
    infracoes: List[Dict[str, Any]],
    inicio: Optional[date] = None,
    fim: Optional[date] = None,
    matricula: Optional[str] = None,
    ambiente: Optional[str] = None,
) -> List[Dict[str, Any]]:
    matricula_q = _normalizar_texto(matricula).casefold()
    ambiente_q = _normalizar_texto(ambiente).casefold()
    saida = []

    for item in infracoes:
        try:
            data_item = datetime.strptime(
                _normalizar_texto(item.get("data")), "%Y-%m-%d"
            ).date()
        except ValueError:
            continue

        if inicio is not None and data_item < inicio:
            continue
        if fim is not None and data_item > fim:
            continue

        if matricula_q and _normalizar_texto(item.get("matricula")).casefold() != matricula_q:
            continue

        if ambiente_q:
            candidatos = {
                _normalizar_texto(item.get("ambiente_id")).casefold(),
                _normalizar_texto(item.get("ambiente_nome")).casefold(),
            }
            if ambiente_q not in candidatos:
                continue

        saida.append(item)

    return saida


def listar_opcoes_filtros_colaboradores() -> Dict[str, Any]:
    colaboradores = listar_colaboradores()
    if not colaboradores.get("sucesso"):
        return {
            "sucesso": False,
            "erro": colaboradores.get("erro") or "ERRO_LISTAR_COLABORADORES",
        }

    ambientes = listar_ambientes()
    if not ambientes.get("sucesso"):
        return {
            "sucesso": False,
            "erro": ambientes.get("erro") or "ERRO_LISTAR_AMBIENTES",
        }

    setores = sorted(
        {
            _normalizar_texto(item.get("setor"))
            for item in colaboradores.get("colaboradores") or []
            if _normalizar_texto(item.get("setor"))
        },
        key=str.casefold,
    )

    opcoes_ambientes = [
        {
            "ambiente_id": item.get("ambiente_id"),
            "nome": item.get("nome"),
        }
        for item in ambientes.get("ambientes") or []
        if isinstance(item, dict)
    ]
    opcoes_ambientes.sort(key=lambda item: _normalizar_texto(item.get("nome")).casefold())

    return {
        "sucesso": True,
        "erro": None,
        "setores": setores,
        "ambientes": opcoes_ambientes,
        "situacoes_infracoes": [
            "COM_INFRACOES",
            "SEM_INFRACOES",
        ],
    }


def consultar_colaboradores_gerencial(
    data_inicio: Any = None,
    data_fim: Any = None,
    setor: Optional[str] = None,
    ambiente: Optional[str] = None,
    situacao_infracoes: Optional[str] = None,
    busca: Optional[str] = None,
    pagina: int = 1,
    por_pagina: int = 20,
) -> Dict[str, Any]:
    try:
        inicio, fim = _resolver_periodo(data_inicio, data_fim)
    except ValueError as erro:
        return {
            "sucesso": False,
            "erro": str(erro),
            "colaboradores": [],
        }

    try:
        pagina = int(pagina)
        por_pagina = int(por_pagina)
    except (TypeError, ValueError):
        return {"sucesso": False, "erro": "PAGINACAO_INVALIDA", "colaboradores": []}

    if pagina < 1:
        return {"sucesso": False, "erro": "PAGINA_INVALIDA", "colaboradores": []}
    if por_pagina < 1:
        return {"sucesso": False, "erro": "POR_PAGINA_INVALIDO", "colaboradores": []}
    por_pagina = min(200, por_pagina)

    base = listar_colaboradores()
    if not base.get("sucesso"):
        return {
            "sucesso": False,
            "erro": base.get("erro") or "ERRO_LISTAR_COLABORADORES",
            "detalhe": base.get("detalhe"),
            "colaboradores": [],
        }

    incidentes = _carregar_infracoes()
    if not incidentes.get("sucesso"):
        return incidentes

    mapa_ambientes, ambientes_disponiveis = _mapa_ambientes_por_matricula()
    infracoes_periodo = _filtrar_infracoes(
        incidentes.get("infracoes") or [],
        inicio=inicio,
        fim=fim,
        ambiente=ambiente,
    )

    por_matricula: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for item in infracoes_periodo:
        matricula_item = _normalizar_texto(item.get("matricula"))
        if matricula_item and matricula_item != "--":
            por_matricula[matricula_item].append(item)

    busca_q = _normalizar_texto(busca).casefold()
    setor_q = _normalizar_texto(setor).casefold()
    ambiente_q = _normalizar_texto(ambiente).casefold()

    itens: List[Dict[str, Any]] = []
    for colaborador in base.get("colaboradores") or []:
        matricula = _normalizar_texto(colaborador.get("matricula"))
        if not matricula:
            continue

        if busca_q and not any(
            busca_q in _normalizar_texto(valor).casefold()
            for valor in (
                colaborador.get("matricula"),
                colaborador.get("nome"),
                colaborador.get("cargo"),
                colaborador.get("setor"),
            )
        ):
            continue

        if setor_q and _normalizar_texto(colaborador.get("setor")).casefold() != setor_q:
            continue

        ambientes_vinculados = mapa_ambientes.get(matricula, [])
        if ambiente_q:
            if not any(
                ambiente_q
                in {
                    _normalizar_texto(item.get("ambiente_id")).casefold(),
                    _normalizar_texto(item.get("nome")).casefold(),
                }
                for item in ambientes_vinculados
            ):
                continue

        ocorrencias = por_matricula.get(matricula, [])
        ultima = ocorrencias[0] if ocorrencias else None

        itens.append({
            "matricula": matricula,
            "nome": colaborador.get("nome"),
            "cargo": colaborador.get("cargo"),
            "setor": colaborador.get("setor"),
            "biometria_cadastrada": bool(colaborador.get("biometria_cadastrada")),
            "imagem_disponivel": bool(colaborador.get("biometria_cadastrada")),
            "ambientes": ambientes_vinculados,
            "quantidade_ambientes": len(ambientes_vinculados),
            "infracoes_periodo": len(ocorrencias),
            "ultima_infracao": None if ultima is None else ultima.get("timestamp"),
        })

    resumo_base = {
        "colaboradores_cadastrados": len(itens),
        "com_infracoes_periodo": sum(1 for item in itens if item["infracoes_periodo"] > 0),
        "sem_infracoes_periodo": sum(1 for item in itens if item["infracoes_periodo"] == 0),
        "total_infracoes_periodo": sum(item["infracoes_periodo"] for item in itens),
    }

    situacao = _normalizar_texto(situacao_infracoes).upper()
    if situacao and situacao != "TODOS":
        if situacao == "COM_INFRACOES":
            itens = [item for item in itens if item["infracoes_periodo"] > 0]
        elif situacao == "SEM_INFRACOES":
            itens = [item for item in itens if item["infracoes_periodo"] == 0]
        else:
            return {
                "sucesso": False,
                "erro": "SITUACAO_INFRACOES_INVALIDA",
                "colaboradores": [],
            }

    itens.sort(
        key=lambda item: (
            -int(item.get("infracoes_periodo") or 0),
            _normalizar_texto(item.get("nome")).casefold(),
            _normalizar_texto(item.get("matricula")).casefold(),
        )
    )

    total = len(itens)
    total_paginas = max(1, (total + por_pagina - 1) // por_pagina)
    if pagina > total_paginas:
        pagina = total_paginas

    inicio_idx = (pagina - 1) * por_pagina
    fim_idx = inicio_idx + por_pagina

    return {
        "sucesso": True,
        "erro": None,
        "periodo": {
            "data_inicio": inicio.isoformat(),
            "data_fim": fim.isoformat(),
        },
        "filtros": {
            "setor": setor,
            "ambiente": ambiente,
            "situacao_infracoes": situacao_infracoes,
            "busca": busca,
        },
        "resumo": resumo_base,
        "paginacao": {
            "pagina": pagina,
            "por_pagina": por_pagina,
            "total_itens": total,
            "total_paginas": total_paginas,
        },
        "ambientes_fonte_disponivel": ambientes_disponiveis,
        "colaboradores": itens[inicio_idx:fim_idx],
    }


def obter_detalhes_colaborador_gerencial(
    matricula: str,
    data_inicio: Any = None,
    data_fim: Any = None,
    limite_historico: int = 20,
) -> Dict[str, Any]:
    detalhe = obter_detalhes_colaborador(matricula)
    if not detalhe.get("sucesso"):
        return detalhe

    try:
        inicio, fim = _resolver_periodo(data_inicio, data_fim)
    except ValueError as erro:
        return {
            "sucesso": False,
            "erro": str(erro),
            "colaborador": None,
        }

    try:
        limite_historico = max(1, min(200, int(limite_historico)))
    except (TypeError, ValueError):
        limite_historico = 20

    incidentes = _carregar_infracoes()
    if not incidentes.get("sucesso"):
        return incidentes

    todas = _filtrar_infracoes(
        incidentes.get("infracoes") or [],
        matricula=matricula,
    )
    periodo = _filtrar_infracoes(
        todas,
        inicio=inicio,
        fim=fim,
    )

    mapa_ambientes, ambientes_disponiveis = _mapa_ambientes_por_matricula()
    ambientes = mapa_ambientes.get(_normalizar_texto(matricula), [])

    contador_epi = Counter(
        _normalizar_texto(item.get("epi")) or "Não informado"
        for item in periodo
    )
    infracoes_por_epi = [
        {"epi": epi, "infracoes": quantidade}
        for epi, quantidade in sorted(
            contador_epi.items(),
            key=lambda par: (-par[1], par[0].casefold()),
        )
    ]

    historico = [
        {
            "incidente_id": item.get("incidente_id"),
            "evidencia_id": item.get("evidencia_id"),
            "timestamp": item.get("timestamp"),
            "data": item.get("data"),
            "horario": item.get("horario"),
            "ambiente_id": item.get("ambiente_id"),
            "ambiente_nome": item.get("ambiente_nome"),
            "epi": item.get("epi"),
            "tipo_irregularidade": item.get("tipo_irregularidade"),
            "infracao": item.get("infracao"),
        }
        for item in periodo[:limite_historico]
    ]

    status_biometria = obter_status_biometria(matricula)
    if not status_biometria.get("sucesso"):
        status_biometria = {
            "sucesso": False,
            "erro": status_biometria.get("erro"),
            "biometria_cadastrada": bool(
                (detalhe.get("colaborador") or {}).get("biometria_cadastrada")
            ),
        }

    ultima_historica = todas[0] if todas else None

    return {
        "sucesso": True,
        "erro": None,
        "colaborador": detalhe.get("colaborador"),
        "periodo": {
            "data_inicio": inicio.isoformat(),
            "data_fim": fim.isoformat(),
        },
        "biometria": status_biometria,
        "imagem_disponivel": bool(
            (detalhe.get("colaborador") or {}).get("biometria_cadastrada")
        ),
        "ambientes_vinculados": ambientes,
        "ambientes_fonte_disponivel": ambientes_disponiveis,
        "indicadores": {
            "infracoes_periodo": len(periodo),
            "total_historico_infracoes": len(todas),
            "ambientes_vinculados": len(ambientes),
            "ultima_infracao": None if ultima_historica is None else ultima_historica.get("timestamp"),
        },
        "infracoes_por_epi": infracoes_por_epi,
        "historico_infracoes": historico,
        "historico_total_itens_periodo": len(periodo),
    }

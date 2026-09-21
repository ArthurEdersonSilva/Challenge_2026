from __future__ import annotations

from collections import Counter, defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from services.evidencia_service import (
    TIPO_ABERTURA,
    TIPO_EVIDENCIA,
    _carregar_eventos,
    _eventos_por_incidente,
    _parse_data,
    _parse_timestamp,
    _rotulo_infracao,
    _valor_identidade,
)


def _periodo(
    data_inicio: Any,
    data_fim: Any,
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


def _filtro_texto_exato(
    valor: str,
    filtro: Optional[str],
) -> bool:
    filtro_q = str(
        filtro or ""
    ).strip().casefold()

    if not filtro_q:
        return True

    return str(
        valor or ""
    ).strip().casefold() == filtro_q


def _identidade_incidente(
    eventos_incidente: List[Dict[str, Any]],
) -> Dict[str, str]:
    return {
        "matricula": _valor_identidade(
            eventos_incidente,
            "matricula",
            "--",
        ),
        "nome": _valor_identidade(
            eventos_incidente,
            "nome",
            "DESCONHECIDO",
        ),
        "cargo": _valor_identidade(
            eventos_incidente,
            "cargo",
            "--",
        ),
    }


def _aberturas_filtradas(
    eventos: List[Dict[str, Any]],
    inicio: date,
    fim: date,
    ambiente: Optional[str],
    colaborador: Optional[str],
    epi: Optional[str],
) -> List[Dict[str, Any]]:
    por_incidente = _eventos_por_incidente(
        eventos
    )

    saida = []
    vistos = set()

    for evento in eventos:
        if str(
            evento.get("tipo_registro") or ""
        ).strip() != TIPO_ABERTURA:
            continue

        incidente_id = str(
            evento.get("incidente_id") or ""
        ).strip()

        if not incidente_id or incidente_id in vistos:
            continue

        dt = _parse_timestamp(
            evento.get("timestamp", "")
        )

        if dt is None:
            continue

        if not (
            inicio
            <= dt.date()
            <= fim
        ):
            continue

        identidade = _identidade_incidente(
            por_incidente.get(
                incidente_id,
                [evento],
            )
        )

        ambiente_filtro = str(
            ambiente or ""
        ).strip().casefold()

        if ambiente_filtro:
            candidatos = {
                str(
                    evento.get(
                        "ambiente_id"
                    ) or ""
                ).strip().casefold(),
                str(
                    evento.get(
                        "ambiente_nome"
                    ) or ""
                ).strip().casefold(),
            }

            if ambiente_filtro not in candidatos:
                continue

        colaborador_filtro = str(
            colaborador or ""
        ).strip().casefold()

        if colaborador_filtro:
            candidatos = {
                identidade[
                    "matricula"
                ].casefold(),
                identidade[
                    "nome"
                ].casefold(),
            }

            if (
                colaborador_filtro
                not in candidatos
            ):
                continue

        epi_filtro = str(
            epi or ""
        ).strip().casefold()

        if epi_filtro:
            candidatos = {
                str(
                    evento.get("epi") or ""
                ).strip().casefold(),
                str(
                    evento.get(
                        "tipo_irregularidade"
                    ) or ""
                ).strip().casefold(),
            }

            if epi_filtro not in candidatos:
                continue

        vistos.add(incidente_id)

        saida.append({
            **evento,
            "_timestamp": dt,
            "_identidade": identidade,
        })

    return saida


def _evidencias_filtradas(
    eventos: List[Dict[str, Any]],
    inicio: date,
    fim: date,
    ambiente: Optional[str],
    colaborador: Optional[str],
    epi: Optional[str],
) -> List[Dict[str, Any]]:
    por_incidente = _eventos_por_incidente(
        eventos
    )

    saida = []

    for evento in eventos:
        if str(
            evento.get("tipo_registro") or ""
        ).strip() != TIPO_EVIDENCIA:
            continue

        if not str(
            evento.get("evidencia_id") or ""
        ).strip():
            continue

        dt = _parse_timestamp(
            evento.get("timestamp", "")
        )

        if dt is None or not (
            inicio
            <= dt.date()
            <= fim
        ):
            continue

        incidente_id = str(
            evento.get("incidente_id") or ""
        ).strip()

        identidade = _identidade_incidente(
            por_incidente.get(
                incidente_id,
                [evento],
            )
        )

        ambiente_q = str(
            ambiente or ""
        ).strip().casefold()

        if ambiente_q:
            candidatos = {
                str(
                    evento.get(
                        "ambiente_id"
                    ) or ""
                ).strip().casefold(),
                str(
                    evento.get(
                        "ambiente_nome"
                    ) or ""
                ).strip().casefold(),
            }

            if ambiente_q not in candidatos:
                continue

        colaborador_q = str(
            colaborador or ""
        ).strip().casefold()

        if colaborador_q:
            candidatos = {
                identidade[
                    "matricula"
                ].casefold(),
                identidade[
                    "nome"
                ].casefold(),
            }

            if colaborador_q not in candidatos:
                continue

        epi_q = str(
            epi or ""
        ).strip().casefold()

        if epi_q:
            candidatos = {
                str(
                    evento.get("epi") or ""
                ).strip().casefold(),
                str(
                    evento.get(
                        "tipo_irregularidade"
                    ) or ""
                ).strip().casefold(),
            }

            if epi_q not in candidatos:
                continue

        saida.append({
            **evento,
            "_timestamp": dt,
            "_identidade": identidade,
        })

    return saida


def _variacao(
    atual: int,
    anterior: int,
) -> Dict[str, Any]:
    atual = int(atual)
    anterior = int(anterior)

    if anterior == 0:
        if atual == 0:
            percentual = 0.0
            sem_base = False
        else:
            percentual = None
            sem_base = True
    else:
        percentual = round(
            (
                (atual - anterior)
                / anterior
            )
            * 100.0,
            2,
        )
        sem_base = False

    return {
        "atual": atual,
        "anterior": anterior,
        "variacao_percentual": percentual,
        "sem_base_comparacao": sem_base,
    }


def _chave_periodo(
    dt: datetime,
    granularidade: str,
) -> str:
    granularidade = str(
        granularidade or "DIARIO"
    ).strip().upper()

    if granularidade == "MENSAL":
        return dt.strftime("%Y-%m")

    if granularidade == "SEMANAL":
        ano, semana, _ = (
            dt.isocalendar()
        )
        return f"{ano}-W{semana:02d}"

    return dt.date().isoformat()


def _serie_temporal(
    aberturas: List[Dict[str, Any]],
    granularidade: str,
) -> List[Dict[str, Any]]:
    contador = Counter(
        _chave_periodo(
            item["_timestamp"],
            granularidade,
        )
        for item in aberturas
    )

    return [
        {
            "periodo": chave,
            "infracoes": contador[chave],
        }
        for chave in sorted(contador)
    ]


def _resumo_ambientes(
    aberturas: List[Dict[str, Any]],
    evidencias: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    dados = defaultdict(
        lambda: {
            "ambiente_id": "",
            "ambiente_nome": "",
            "colaboradores": set(),
            "infracoes": 0,
            "evidencias": 0,
        }
    )

    for item in aberturas:
        chave = str(
            item.get("ambiente_id")
            or item.get("ambiente_nome")
            or "--"
        )

        atual = dados[chave]
        atual["ambiente_id"] = str(
            item.get("ambiente_id") or ""
        )
        atual["ambiente_nome"] = str(
            item.get("ambiente_nome") or ""
        )
        atual["infracoes"] += 1

        matricula = item[
            "_identidade"
        ]["matricula"]

        if matricula != "--":
            atual[
                "colaboradores"
            ].add(matricula)

    for item in evidencias:
        chave = str(
            item.get("ambiente_id")
            or item.get("ambiente_nome")
            or "--"
        )

        atual = dados[chave]
        atual["ambiente_id"] = str(
            item.get("ambiente_id") or ""
        )
        atual["ambiente_nome"] = str(
            item.get("ambiente_nome") or ""
        )
        atual["evidencias"] += 1

    total = len(aberturas)

    saida = []

    for item in dados.values():
        percentual = (
            0.0
            if total == 0
            else round(
                item["infracoes"]
                * 100.0
                / total,
                2,
            )
        )

        saida.append({
            "ambiente_id": item[
                "ambiente_id"
            ],
            "ambiente_nome": item[
                "ambiente_nome"
            ],
            "colaboradores": len(
                item["colaboradores"]
            ),
            "infracoes": item[
                "infracoes"
            ],
            "evidencias": item[
                "evidencias"
            ],
            "percentual_total": percentual,
        })

    saida.sort(
        key=lambda item: (
            -item["infracoes"],
            item[
                "ambiente_nome"
            ].casefold(),
        )
    )

    return saida


def _resumo_colaboradores(
    aberturas: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    dados = defaultdict(
        lambda: {
            "matricula": "",
            "nome": "",
            "cargo": "",
            "ambientes": Counter(),
            "infracoes": 0,
            "ultima_ocorrencia": None,
        }
    )

    for item in aberturas:
        ident = item["_identidade"]
        matricula = ident["matricula"]

        if matricula == "--":
            continue

        atual = dados[matricula]
        atual["matricula"] = matricula
        atual["nome"] = ident["nome"]
        atual["cargo"] = ident["cargo"]
        atual["infracoes"] += 1

        ambiente_nome = str(
            item.get("ambiente_nome") or ""
        )

        if ambiente_nome:
            atual[
                "ambientes"
            ][ambiente_nome] += 1

        dt = item["_timestamp"]

        if (
            atual[
                "ultima_ocorrencia"
            ] is None
            or dt
            > atual[
                "ultima_ocorrencia"
            ]
        ):
            atual[
                "ultima_ocorrencia"
            ] = dt

    total = len(aberturas)

    saida = []

    for atual in dados.values():
        principal = (
            atual["ambientes"].most_common(1)[0][0]
            if atual["ambientes"]
            else None
        )

        percentual = (
            0.0
            if total == 0
            else round(
                atual["infracoes"]
                * 100.0
                / total,
                2,
            )
        )

        saida.append({
            "matricula": atual[
                "matricula"
            ],
            "nome": atual["nome"],
            "cargo": atual["cargo"],
            "ambiente_principal": principal,
            "ambientes": sorted(
                atual["ambientes"].keys()
            ),
            "infracoes": atual[
                "infracoes"
            ],
            "ultima_ocorrencia": (
                None
                if atual[
                    "ultima_ocorrencia"
                ] is None
                else atual[
                    "ultima_ocorrencia"
                ].isoformat()
            ),
            "percentual_total": percentual,
        })

    saida.sort(
        key=lambda item: (
            -item["infracoes"],
            item["nome"].casefold(),
        )
    )

    return saida


def _gerar_periodo(
    eventos: List[Dict[str, Any]],
    inicio: date,
    fim: date,
    ambiente: Optional[str],
    colaborador: Optional[str],
    epi: Optional[str],
    granularidade: str,
) -> Dict[str, Any]:
    aberturas = _aberturas_filtradas(
        eventos,
        inicio,
        fim,
        ambiente,
        colaborador,
        epi,
    )

    evidencias = _evidencias_filtradas(
        eventos,
        inicio,
        fim,
        ambiente,
        colaborador,
        epi,
    )

    colaboradores = {
        item["_identidade"]["matricula"]
        for item in aberturas
        if item["_identidade"]["matricula"]
        != "--"
    }

    ambientes = {
        str(
            item.get("ambiente_id")
            or item.get("ambiente_nome")
            or ""
        )
        for item in aberturas
        if (
            item.get("ambiente_id")
            or item.get("ambiente_nome")
        )
    }

    por_ambiente = Counter(
        str(
            item.get("ambiente_nome")
            or item.get("ambiente_id")
            or "--"
        )
        for item in aberturas
    )

    por_epi = Counter(
        str(
            item.get("epi") or "EPI"
        )
        for item in aberturas
    )

    return {
        "periodo": {
            "inicio": inicio.isoformat(),
            "fim": fim.isoformat(),
        },
        "total_infracoes": len(
            aberturas
        ),
        "colaboradores_envolvidos": len(
            colaboradores
        ),
        "ambientes_com_ocorrencias": len(
            ambientes
        ),
        "total_evidencias": len(
            evidencias
        ),
        "serie_temporal": _serie_temporal(
            aberturas,
            granularidade,
        ),
        "infracoes_por_ambiente": [
            {
                "ambiente": chave,
                "infracoes": valor,
            }
            for chave, valor in (
                por_ambiente.most_common()
            )
        ],
        "infracoes_por_epi": [
            {
                "epi": chave,
                "infracoes": valor,
            }
            for chave, valor in (
                por_epi.most_common()
            )
        ],
        "resumo_por_ambiente": (
            _resumo_ambientes(
                aberturas,
                evidencias,
            )
        ),
        "resumo_por_colaborador": (
            _resumo_colaboradores(
                aberturas
            )
        ),
    }


def gerar_relatorio_geral(
    data_inicio: Any = None,
    data_fim: Any = None,
    ambiente: Optional[str] = None,
    colaborador: Optional[str] = None,
    epi: Optional[str] = None,
    granularidade: str = "DIARIO",
) -> Dict[str, Any]:
    carregado = _carregar_eventos()

    if not carregado.get("sucesso"):
        return {
            "sucesso": False,
            "erro": carregado.get("erro"),
            "detalhe": carregado.get("detalhe"),
        }

    try:
        inicio, fim = _periodo(
            data_inicio,
            data_fim,
        )
    except ValueError as erro:
        return {
            "sucesso": False,
            "erro": str(erro),
        }

    atual = _gerar_periodo(
        carregado["eventos"],
        inicio,
        fim,
        ambiente,
        colaborador,
        epi,
        granularidade,
    )

    quantidade_dias = (
        fim - inicio
    ).days + 1

    fim_anterior = (
        inicio - timedelta(days=1)
    )
    inicio_anterior = (
        fim_anterior
        - timedelta(
            days=quantidade_dias - 1
        )
    )

    anterior = _gerar_periodo(
        carregado["eventos"],
        inicio_anterior,
        fim_anterior,
        ambiente,
        colaborador,
        epi,
        granularidade,
    )

    return {
        "sucesso": True,
        "erro": None,
        "fonte": carregado.get("fonte"),
        "filtros": {
            "data_inicio": inicio.isoformat(),
            "data_fim": fim.isoformat(),
            "ambiente": ambiente,
            "colaborador": colaborador,
            "epi": epi,
            "granularidade": str(
                granularidade
                or "DIARIO"
            ).upper(),
        },
        "indicadores": {
            "total_infracoes": _variacao(
                atual[
                    "total_infracoes"
                ],
                anterior[
                    "total_infracoes"
                ],
            ),
            "colaboradores_envolvidos": _variacao(
                atual[
                    "colaboradores_envolvidos"
                ],
                anterior[
                    "colaboradores_envolvidos"
                ],
            ),
            "ambientes_com_ocorrencias": _variacao(
                atual[
                    "ambientes_com_ocorrencias"
                ],
                anterior[
                    "ambientes_com_ocorrencias"
                ],
            ),
            "total_evidencias": _variacao(
                atual[
                    "total_evidencias"
                ],
                anterior[
                    "total_evidencias"
                ],
            ),
        },
        "serie_temporal": atual[
            "serie_temporal"
        ],
        "infracoes_por_ambiente": atual[
            "infracoes_por_ambiente"
        ],
        "infracoes_por_epi": atual[
            "infracoes_por_epi"
        ],
        "resumo_por_ambiente": atual[
            "resumo_por_ambiente"
        ],
        "resumo_por_colaborador": atual[
            "resumo_por_colaborador"
        ],
        "periodo_anterior": anterior[
            "periodo"
        ],
    }


def _pdf_escape(texto: str) -> bytes:
    texto = str(texto)

    texto = (
        texto.replace("\\", "\\\\")
        .replace("(", "\\(")
        .replace(")", "\\)")
    )

    return texto.encode(
        "cp1252",
        errors="replace",
    )


def _quebrar_linha(
    texto: str,
    largura: int = 90,
) -> List[str]:
    palavras = str(texto).split()

    if not palavras:
        return [""]

    linhas = []
    atual = ""

    for palavra in palavras:
        candidato = (
            palavra
            if not atual
            else f"{atual} {palavra}"
        )

        if len(candidato) <= largura:
            atual = candidato
        else:
            linhas.append(atual)
            atual = palavra

    if atual:
        linhas.append(atual)

    return linhas


def _gerar_pdf_texto(
    caminho: Path,
    paginas: List[List[str]],
) -> None:
    objetos = []

    # Objeto 1: catálogo
    # 2: páginas
    # 3: fonte
    objetos.append(None)
    objetos.append(None)
    objetos.append(
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"
    )

    pagina_ids = []

    for linhas in paginas:
        comandos = [
            b"BT",
            b"/F1 10 Tf",
            b"50 800 Td",
            b"14 TL",
        ]

        primeira = True

        for linha in linhas:
            if not primeira:
                comandos.append(b"T*")
            primeira = False
            comandos.append(
                b"("
                + _pdf_escape(linha)
                + b") Tj"
            )

        comandos.append(b"ET")

        stream = b"\n".join(comandos)

        conteudo_id = len(objetos) + 1
        objetos.append(
            b"<< /Length "
            + str(len(stream)).encode()
            + b" >>\nstream\n"
            + stream
            + b"\nendstream"
        )

        pagina_id = len(objetos) + 1
        pagina_ids.append(pagina_id)
        objetos.append(
            (
                b"<< /Type /Page /Parent 2 0 R "
                b"/MediaBox [0 0 595 842] "
                b"/Resources << /Font << /F1 3 0 R >> >> "
                b"/Contents "
                + str(conteudo_id).encode()
                + b" 0 R >>"
            )
        )

    filhos = b" ".join(
        f"{pid} 0 R".encode()
        for pid in pagina_ids
    )

    objetos[1] = (
        b"<< /Type /Pages /Kids ["
        + filhos
        + b"] /Count "
        + str(len(pagina_ids)).encode()
        + b" >>"
    )

    objetos[0] = (
        b"<< /Type /Catalog /Pages 2 0 R >>"
    )

    conteudo = bytearray(
        b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n"
    )

    offsets = [0]

    for indice, objeto in enumerate(
        objetos,
        start=1,
    ):
        offsets.append(len(conteudo))
        conteudo.extend(
            f"{indice} 0 obj\n".encode()
        )
        conteudo.extend(objeto)
        conteudo.extend(b"\nendobj\n")

    xref = len(conteudo)

    conteudo.extend(
        f"xref\n0 {len(objetos)+1}\n".encode()
    )
    conteudo.extend(
        b"0000000000 65535 f \n"
    )

    for offset in offsets[1:]:
        conteudo.extend(
            f"{offset:010d} 00000 n \n".encode()
        )

    conteudo.extend(
        (
            f"trailer\n<< /Size {len(objetos)+1} "
            f"/Root 1 0 R >>\n"
            f"startxref\n{xref}\n%%EOF\n"
        ).encode()
    )

    caminho.write_bytes(conteudo)


def exportar_relatorio_pdf(
    destino: str,
    data_inicio: Any = None,
    data_fim: Any = None,
    ambiente: Optional[str] = None,
    colaborador: Optional[str] = None,
    epi: Optional[str] = None,
    granularidade: str = "DIARIO",
) -> Dict[str, Any]:
    relatorio = gerar_relatorio_geral(
        data_inicio=data_inicio,
        data_fim=data_fim,
        ambiente=ambiente,
        colaborador=colaborador,
        epi=epi,
        granularidade=granularidade,
    )

    if not relatorio.get("sucesso"):
        return relatorio

    caminho = Path(destino)

    if caminho.suffix.lower() != ".pdf":
        caminho = (
            caminho
            / "relatorio_geral.pdf"
        )

    linhas = [
        "RELATORIO GERAL - CHALLENGE EPI",
        "",
        (
            "Periodo: "
            f"{relatorio['filtros']['data_inicio']} "
            "a "
            f"{relatorio['filtros']['data_fim']}"
        ),
        f"Ambiente: {ambiente or 'Todos'}",
        f"Colaborador: {colaborador or 'Todos'}",
        f"EPI / Infracao: {epi or 'Todos'}",
        "",
        "INDICADORES",
    ]

    for chave, titulo in (
        (
            "total_infracoes",
            "Total de infracoes",
        ),
        (
            "colaboradores_envolvidos",
            "Colaboradores envolvidos",
        ),
        (
            "ambientes_com_ocorrencias",
            "Ambientes com ocorrencias",
        ),
        (
            "total_evidencias",
            "Total de evidencias",
        ),
    ):
        item = relatorio[
            "indicadores"
        ][chave]

        linhas.append(
            f"{titulo}: {item['atual']}"
        )

    linhas.extend(
        [
            "",
            "INFRACOES POR AMBIENTE",
        ]
    )

    for item in relatorio[
        "infracoes_por_ambiente"
    ]:
        linhas.append(
            f"- {item['ambiente']}: "
            f"{item['infracoes']}"
        )

    linhas.extend(
        [
            "",
            "INFRACOES POR EPI",
        ]
    )

    for item in relatorio[
        "infracoes_por_epi"
    ]:
        linhas.append(
            f"- {item['epi']}: "
            f"{item['infracoes']}"
        )

    linhas.extend(
        [
            "",
            "RESUMO POR AMBIENTE",
        ]
    )

    for item in relatorio[
        "resumo_por_ambiente"
    ]:
        linhas.append(
            (
                f"- {item['ambiente_nome']}: "
                f"{item['infracoes']} infracoes, "
                f"{item['evidencias']} evidencias, "
                f"{item['colaboradores']} colaboradores"
            )
        )

    linhas.extend(
        [
            "",
            "RESUMO POR COLABORADOR",
        ]
    )

    for item in relatorio[
        "resumo_por_colaborador"
    ]:
        linhas.append(
            (
                f"- {item['nome']} "
                f"({item['matricula']}): "
                f"{item['infracoes']} infracoes"
            )
        )

    expandido = []

    for linha in linhas:
        expandido.extend(
            _quebrar_linha(linha)
        )

    paginas = []

    por_pagina = 50

    for indice in range(
        0,
        len(expandido),
        por_pagina,
    ):
        paginas.append(
            expandido[
                indice:indice
                + por_pagina
            ]
        )

    if not paginas:
        paginas = [["RELATORIO SEM DADOS"]]

    try:
        caminho.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        _gerar_pdf_texto(
            caminho,
            paginas,
        )
    except Exception as erro:
        return {
            "sucesso": False,
            "erro": "ERRO_EXPORTAR_RELATORIO_PDF",
            "detalhe": str(erro),
        }

    return {
        "sucesso": True,
        "erro": None,
        "arquivo": str(
            caminho.resolve()
        ),
        "relatorio": relatorio,
    }

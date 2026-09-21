from __future__ import annotations

import base64
import csv
import json
import mimetypes
import os
import shutil
import zipfile
from collections import defaultdict
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

import config


TIPO_ABERTURA = "ABERTURA"
TIPO_EVIDENCIA = "EVIDENCIA"

TIPO_AUSENCIA_EPI = "AUSENCIA_EPI"
TIPO_USO_INCORRETO_EPI = "USO_INCORRETO_EPI"


def _caminho_csv() -> Path:
    return Path(
        str(
            getattr(
                config,
                "PATH_INCIDENTES_EPI_CSV",
                "incidentes_epi.csv",
            )
        )
    )


def _resolver_caminho_arquivo(valor: str) -> Optional[Path]:
    texto = str(valor or "").strip()

    if not texto:
        return None

    caminho = Path(texto)

    if not caminho.is_absolute():
        caminho = Path.cwd() / caminho

    try:
        return caminho.resolve()
    except Exception:
        return caminho


def _parse_timestamp(valor: str) -> Optional[datetime]:
    texto = str(valor or "").strip()

    if not texto:
        return None

    if texto.endswith("Z"):
        texto = texto[:-1] + "+00:00"

    try:
        dt = datetime.fromisoformat(texto)
    except Exception:
        return None

    if dt.tzinfo is not None:
        try:
            dt = dt.astimezone()
        except Exception:
            pass

    return dt


def _parse_data(valor: Any) -> Optional[date]:
    if valor is None or valor == "":
        return None

    if isinstance(valor, datetime):
        return valor.date()

    if isinstance(valor, date):
        return valor

    texto = str(valor).strip()

    if not texto:
        return None

    for formato in ("%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(texto, formato).date()
        except Exception:
            pass

    raise ValueError("DATA_INVALIDA")


def _carregar_eventos() -> Dict[str, Any]:
    caminho = _caminho_csv()

    if not caminho.exists():
        return {
            "sucesso": True,
            "erro": None,
            "fonte": str(caminho),
            "eventos": [],
        }

    try:
        with caminho.open(
            "r",
            encoding="utf-8",
            newline="",
        ) as arquivo:
            eventos = list(csv.DictReader(arquivo))
    except Exception as erro:
        return {
            "sucesso": False,
            "erro": "ERRO_LER_HISTORICO_INCIDENTES",
            "detalhe": str(erro),
            "fonte": str(caminho),
            "eventos": [],
        }

    return {
        "sucesso": True,
        "erro": None,
        "fonte": str(caminho),
        "eventos": eventos,
    }


def _eventos_por_incidente(
    eventos: Iterable[Dict[str, Any]],
) -> Dict[str, List[Dict[str, Any]]]:
    agrupados: Dict[str, List[Dict[str, Any]]] = defaultdict(list)

    for evento in eventos:
        incidente_id = str(
            evento.get("incidente_id") or ""
        ).strip()

        if incidente_id:
            agrupados[incidente_id].append(evento)

    for itens in agrupados.values():
        itens.sort(
            key=lambda item: (
                _parse_timestamp(item.get("timestamp", ""))
                or datetime.min
            )
        )

    return dict(agrupados)


def _valor_identidade(
    eventos_incidente: List[Dict[str, Any]],
    campo: str,
    padrao: str,
) -> str:
    valor = padrao

    for evento in eventos_incidente:
        candidato = str(evento.get(campo) or "").strip()

        if not candidato:
            continue

        if campo == "matricula" and candidato == "--":
            continue

        if campo == "nome" and candidato == "DESCONHECIDO":
            continue

        if campo == "cargo" and candidato == "--":
            continue

        valor = candidato

    return valor


def _estado_incidente_atual(
    eventos_incidente: List[Dict[str, Any]],
) -> Dict[str, Any]:
    if not eventos_incidente:
        return {
            "estado_incidente": None,
            "motivo_encerramento": None,
            "ultimo_evento": None,
        }

    ultimo = eventos_incidente[-1]

    return {
        "estado_incidente": str(
            ultimo.get("estado_incidente") or ""
        ).strip() or None,
        "motivo_encerramento": str(
            ultimo.get("motivo_encerramento") or ""
        ).strip() or None,
        "ultimo_evento": str(
            ultimo.get("tipo_registro") or ""
        ).strip() or None,
    }


def _rotulo_infracao(
    epi: str,
    tipo_irregularidade: str,
) -> str:
    epi = str(epi or "EPI").strip() or "EPI"
    tipo = str(tipo_irregularidade or "").strip()

    if tipo == TIPO_AUSENCIA_EPI:
        return f"Sem {epi.lower()}"

    if tipo == TIPO_USO_INCORRETO_EPI:
        return f"Uso incorreto de {epi.lower()}"

    return tipo or epi


def _dados_base_evidencia(
    evento: Dict[str, Any],
    eventos_incidente: List[Dict[str, Any]],
) -> Dict[str, Any]:
    dt = _parse_timestamp(evento.get("timestamp", ""))

    matricula = _valor_identidade(
        eventos_incidente,
        "matricula",
        "--",
    )
    nome = _valor_identidade(
        eventos_incidente,
        "nome",
        "DESCONHECIDO",
    )
    cargo = _valor_identidade(
        eventos_incidente,
        "cargo",
        "--",
    )

    status_identidade = str(
        evento.get("status_identidade") or ""
    ).strip()

    for item in eventos_incidente:
        candidato = str(
            item.get("status_identidade") or ""
        ).strip()

        if candidato:
            status_identidade = candidato

    frame = _resolver_caminho_arquivo(
        evento.get("caminho_frame", "")
    )
    crop = _resolver_caminho_arquivo(
        evento.get("caminho_crop", "")
    )

    frame_existe = bool(
        frame is not None and frame.exists()
    )
    crop_existe = bool(
        crop is not None and crop.exists()
    )

    epi = str(evento.get("epi") or "").strip()
    tipo_irregularidade = str(
        evento.get("tipo_irregularidade") or ""
    ).strip()

    estado = _estado_incidente_atual(
        eventos_incidente
    )

    return {
        "evidencia_id": str(
            evento.get("evidencia_id") or ""
        ).strip(),
        "incidente_id": str(
            evento.get("incidente_id") or ""
        ).strip(),
        "registro_id": str(
            evento.get("registro_id") or ""
        ).strip(),
        "timestamp": (
            None if dt is None else dt.isoformat()
        ),
        "data": (
            None if dt is None else dt.date().isoformat()
        ),
        "horario": (
            None
            if dt is None
            else dt.strftime("%H:%M:%S")
        ),
        "ambiente_id": str(
            evento.get("ambiente_id") or ""
        ).strip(),
        "ambiente_nome": str(
            evento.get("ambiente_nome") or ""
        ).strip(),
        "camera_id": str(
            evento.get("camera_id") or ""
        ).strip(),
        "camera_nome": str(
            evento.get("camera_nome") or ""
        ).strip(),
        "track_id": str(
            evento.get("track_id") or ""
        ).strip(),
        "track_instance_id": str(
            evento.get("track_instance_id") or ""
        ).strip(),
        "epi": epi,
        "tipo_irregularidade": tipo_irregularidade,
        "infracao": _rotulo_infracao(
            epi,
            tipo_irregularidade,
        ),
        "matricula": matricula,
        "nome": nome,
        "cargo": cargo,
        "status_identidade": status_identidade or None,
        "pessoa_identificada": (
            bool(matricula and matricula != "--")
            and nome != "DESCONHECIDO"
        ),
        "caminho_frame": (
            None if frame is None else str(frame)
        ),
        "caminho_crop": (
            None if crop is None else str(crop)
        ),
        "frame_disponivel": frame_existe,
        "crop_disponivel": crop_existe,
        "imagem_disponivel": (
            frame_existe or crop_existe
        ),
        **estado,
    }


def _selecionar_evidencias(
    eventos: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    por_incidente = _eventos_por_incidente(
        eventos
    )

    evidencias = []

    for evento in eventos:
        if str(
            evento.get("tipo_registro") or ""
        ).strip() != TIPO_EVIDENCIA:
            continue

        evidencia_id = str(
            evento.get("evidencia_id") or ""
        ).strip()

        if not evidencia_id:
            continue

        incidente_id = str(
            evento.get("incidente_id") or ""
        ).strip()

        evidencias.append(
            _dados_base_evidencia(
                evento,
                por_incidente.get(
                    incidente_id,
                    [evento],
                ),
            )
        )

    evidencias.sort(
        key=lambda item: (
            item.get("timestamp") or ""
        ),
        reverse=True,
    )

    return evidencias


def _aplicar_filtros(
    evidencias: List[Dict[str, Any]],
    data_inicio: Any = None,
    data_fim: Any = None,
    ambiente: Optional[str] = None,
    colaborador: Optional[str] = None,
    epi: Optional[str] = None,
    busca: Optional[str] = None,
) -> List[Dict[str, Any]]:
    inicio = _parse_data(data_inicio)
    fim = _parse_data(data_fim)

    if inicio and fim and inicio > fim:
        raise ValueError("PERIODO_INVALIDO")

    ambiente_q = str(
        ambiente or ""
    ).strip().casefold()
    colaborador_q = str(
        colaborador or ""
    ).strip().casefold()
    epi_q = str(
        epi or ""
    ).strip().casefold()
    busca_q = str(
        busca or ""
    ).strip().casefold()

    filtradas = []

    for item in evidencias:
        data_item = _parse_data(item.get("data"))

        if (
            inicio
            and data_item
            and data_item < inicio
        ):
            continue

        if (
            fim
            and data_item
            and data_item > fim
        ):
            continue

        if ambiente_q:
            candidatos = {
                str(
                    item.get("ambiente_id") or ""
                ).casefold(),
                str(
                    item.get("ambiente_nome") or ""
                ).casefold(),
            }

            if ambiente_q not in candidatos:
                continue

        if colaborador_q:
            candidatos = {
                str(
                    item.get("matricula") or ""
                ).casefold(),
                str(
                    item.get("nome") or ""
                ).casefold(),
            }

            if colaborador_q not in candidatos:
                continue

        if epi_q:
            candidatos = {
                str(
                    item.get("epi") or ""
                ).casefold(),
                str(
                    item.get(
                        "tipo_irregularidade"
                    ) or ""
                ).casefold(),
                str(
                    item.get("infracao") or ""
                ).casefold(),
            }

            if epi_q not in candidatos:
                continue

        if busca_q:
            campos = (
                "nome",
                "matricula",
                "ambiente_nome",
                "ambiente_id",
                "camera_nome",
                "camera_id",
                "incidente_id",
                "evidencia_id",
                "epi",
                "infracao",
            )

            if not any(
                busca_q
                in str(
                    item.get(campo) or ""
                ).casefold()
                for campo in campos
            ):
                continue

        filtradas.append(item)

    return filtradas


def listar_evidencias(
    data_inicio: Any = None,
    data_fim: Any = None,
    ambiente: Optional[str] = None,
    colaborador: Optional[str] = None,
    epi: Optional[str] = None,
    busca: Optional[str] = None,
    pagina: int = 1,
    por_pagina: int = 20,
) -> Dict[str, Any]:
    carregado = _carregar_eventos()

    if not carregado.get("sucesso"):
        return {
            "sucesso": False,
            "erro": carregado.get("erro"),
            "detalhe": carregado.get("detalhe"),
            "total": 0,
            "evidencias": [],
        }

    try:
        evidencias = _aplicar_filtros(
            _selecionar_evidencias(
                carregado["eventos"]
            ),
            data_inicio=data_inicio,
            data_fim=data_fim,
            ambiente=ambiente,
            colaborador=colaborador,
            epi=epi,
            busca=busca,
        )
    except ValueError as erro:
        return {
            "sucesso": False,
            "erro": str(erro),
            "total": 0,
            "evidencias": [],
        }

    try:
        pagina = max(1, int(pagina))
    except Exception:
        pagina = 1

    try:
        por_pagina = max(
            1,
            min(200, int(por_pagina)),
        )
    except Exception:
        por_pagina = 20

    total = len(evidencias)
    total_paginas = max(
        1,
        (total + por_pagina - 1)
        // por_pagina,
    )

    if pagina > total_paginas:
        pagina = total_paginas

    inicio = (pagina - 1) * por_pagina
    fim = inicio + por_pagina

    return {
        "sucesso": True,
        "erro": None,
        "fonte": carregado.get("fonte"),
        "total": total,
        "paginacao": {
            "pagina": pagina,
            "por_pagina": por_pagina,
            "total_itens": total,
            "total_paginas": total_paginas,
        },
        "evidencias": evidencias[inicio:fim],
    }


def listar_opcoes_filtros_evidencias() -> Dict[str, Any]:
    carregado = _carregar_eventos()

    if not carregado.get("sucesso"):
        return {
            "sucesso": False,
            "erro": carregado.get("erro"),
        }

    evidencias = _selecionar_evidencias(
        carregado["eventos"]
    )

    ambientes = {}
    colaboradores = {}
    epis = set()

    for item in evidencias:
        ambiente_id = str(
            item.get("ambiente_id") or ""
        ).strip()
        ambiente_nome = str(
            item.get("ambiente_nome") or ""
        ).strip()

        if ambiente_id or ambiente_nome:
            ambientes[
                ambiente_id or ambiente_nome
            ] = {
                "ambiente_id": (
                    ambiente_id or None
                ),
                "nome": ambiente_nome,
            }

        matricula = str(
            item.get("matricula") or ""
        ).strip()
        nome = str(
            item.get("nome") or ""
        ).strip()

        if (
            matricula
            and matricula != "--"
        ):
            colaboradores[matricula] = {
                "matricula": matricula,
                "nome": nome,
            }

        epi = str(
            item.get("epi") or ""
        ).strip()

        if epi:
            epis.add(epi)

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
        "epis": sorted(
            epis,
            key=str.casefold,
        ),
    }


def _buscar_evidencia(
    evidencia_id: str,
) -> Tuple[
    Optional[Dict[str, Any]],
    Optional[List[Dict[str, Any]]],
]:
    evidencia_id = str(
        evidencia_id or ""
    ).strip()

    if not evidencia_id:
        return None, None

    carregado = _carregar_eventos()

    if not carregado.get("sucesso"):
        return None, None

    por_incidente = _eventos_por_incidente(
        carregado["eventos"]
    )

    for evento in carregado["eventos"]:
        if (
            str(
                evento.get("tipo_registro") or ""
            ).strip()
            != TIPO_EVIDENCIA
        ):
            continue

        if str(
            evento.get("evidencia_id") or ""
        ).strip() != evidencia_id:
            continue

        incidente_id = str(
            evento.get("incidente_id") or ""
        ).strip()

        eventos_incidente = (
            por_incidente.get(
                incidente_id,
                [evento],
            )
        )

        return (
            _dados_base_evidencia(
                evento,
                eventos_incidente,
            ),
            eventos_incidente,
        )

    return None, None


def _dimensoes_imagem(
    caminho: Optional[str],
) -> Dict[str, Optional[int]]:
    if not caminho:
        return {
            "largura": None,
            "altura": None,
        }

    path = Path(caminho)

    if not path.exists():
        return {
            "largura": None,
            "altura": None,
        }

    try:
        import cv2

        imagem = cv2.imread(
            str(path),
            cv2.IMREAD_UNCHANGED,
        )

        if imagem is None:
            raise ValueError

        altura, largura = imagem.shape[:2]

        return {
            "largura": int(largura),
            "altura": int(altura),
        }
    except Exception:
        return {
            "largura": None,
            "altura": None,
        }


def _caminho_metadata_evidencia(
    evidencia: Dict[str, Any],
) -> Optional[Path]:
    evidencia_id = str(
        evidencia.get("evidencia_id") or ""
    ).strip()
    incidente_id = str(
        evidencia.get("incidente_id") or ""
    ).strip()

    if not evidencia_id:
        return None

    for chave in ("caminho_frame", "caminho_crop"):
        caminho = evidencia.get(chave)

        if caminho:
            path = Path(caminho)
            return (
                path.parent
                / f"{evidencia_id}_metadata.json"
            )

    pasta_base = str(
        getattr(
            config,
            "PASTA_PROVAS_INCIDENTES",
            "provas_incidentes",
        )
    ).strip()

    if not pasta_base or not incidente_id:
        return None

    base = Path(pasta_base)

    if not base.is_absolute():
        base = Path.cwd() / base

    return (
        base
        / incidente_id
        / f"{evidencia_id}_metadata.json"
    )


def _carregar_metadata_evidencia(
    evidencia: Dict[str, Any],
) -> Dict[str, Any]:
    caminho = _caminho_metadata_evidencia(
        evidencia
    )

    if caminho is None or not caminho.exists():
        return {
            "disponivel": False,
            "caminho": (
                None
                if caminho is None
                else str(caminho)
            ),
            "dados": None,
            "erro": None,
        }

    try:
        dados = json.loads(
            caminho.read_text(
                encoding="utf-8"
            )
        )
    except Exception as erro:
        return {
            "disponivel": False,
            "caminho": str(caminho),
            "dados": None,
            "erro": (
                "METADATA_EVIDENCIA_INVALIDO:"
                + str(erro)
            ),
        }

    if not isinstance(dados, dict):
        return {
            "disponivel": False,
            "caminho": str(caminho),
            "dados": None,
            "erro": "METADATA_EVIDENCIA_INVALIDO",
        }

    if str(
        dados.get("evidencia_id") or ""
    ).strip() != str(
        evidencia.get("evidencia_id") or ""
    ).strip():
        return {
            "disponivel": False,
            "caminho": str(caminho),
            "dados": None,
            "erro": "METADATA_EVIDENCIA_ID_DIVERGENTE",
        }

    if str(
        dados.get("incidente_id") or ""
    ).strip() != str(
        evidencia.get("incidente_id") or ""
    ).strip():
        return {
            "disponivel": False,
            "caminho": str(caminho),
            "dados": None,
            "erro": "METADATA_INCIDENTE_ID_DIVERGENTE",
        }

    epis = dados.get("epis_analisados")

    if not isinstance(epis, list):
        epis = []

    maquinario = dados.get(
        "maquinario_relacionado"
    )

    return {
        "disponivel": True,
        "caminho": str(caminho),
        "dados": {
            "schema_version": dados.get(
                "schema_version"
            ),
            "confianca_deteccao": dados.get(
                "confianca_deteccao"
            ),
            "epis_analisados": epis,
            "maquinario_relacionado": maquinario,
        },
        "erro": None,
    }


def obter_detalhes_evidencia(
    evidencia_id: str,
) -> Dict[str, Any]:
    evidencia, eventos_incidente = (
        _buscar_evidencia(evidencia_id)
    )

    if evidencia is None:
        return {
            "sucesso": False,
            "erro": "EVIDENCIA_NAO_ENCONTRADA",
        }

    caminho_preferido = (
        evidencia.get("caminho_frame")
        if evidencia.get(
            "frame_disponivel"
        )
        else evidencia.get("caminho_crop")
    )

    dimensoes = _dimensoes_imagem(
        caminho_preferido
    )

    historico = []

    for evento in eventos_incidente or []:
        dt = _parse_timestamp(
            evento.get("timestamp", "")
        )

        historico.append({
            "tipo_registro": str(
                evento.get(
                    "tipo_registro"
                ) or ""
            ).strip(),
            "timestamp": (
                None
                if dt is None
                else dt.isoformat()
            ),
            "estado_incidente": str(
                evento.get(
                    "estado_incidente"
                ) or ""
            ).strip() or None,
            "motivo_encerramento": str(
                evento.get(
                    "motivo_encerramento"
                ) or ""
            ).strip() or None,
            "detalhe": str(
                evento.get("detalhe") or ""
            ).strip() or None,
        })

    metadata = _carregar_metadata_evidencia(
        evidencia
    )
    dados_metadata = (
        metadata.get("dados") or {}
    )

    maquinario_relacionado = (
        dados_metadata.get(
            "maquinario_relacionado"
        )
        if metadata.get("disponivel")
        else None
    )

    limitacoes = []

    if not metadata.get("disponivel"):
        limitacoes.append(
            "Evidência sem metadata enriquecido; valores históricos não foram reconstruídos."
        )

    if metadata.get("erro"):
        limitacoes.append(
            metadata["erro"]
        )

    if maquinario_relacionado is None:
        limitacoes.append(
            "Não existe associação real persistida entre esta evidência e um maquinário específico."
        )

    return {
        "sucesso": True,
        "erro": None,
        "evidencia": {
            **evidencia,
            "imagem_preferida": caminho_preferido,
            "largura_imagem": dimensoes[
                "largura"
            ],
            "altura_imagem": dimensoes[
                "altura"
            ],
            "metadata_enriquecido_disponivel": bool(
                metadata.get("disponivel")
            ),
            "caminho_metadata": metadata.get(
                "caminho"
            ),
            "epis_analisados": (
                list(
                    dados_metadata.get(
                        "epis_analisados"
                    ) or []
                )
                if metadata.get("disponivel")
                else []
            ),
            "historico_epi_completo_disponivel": bool(
                metadata.get("disponivel")
            ),
            "confianca_deteccao": (
                dados_metadata.get(
                    "confianca_deteccao"
                )
                if metadata.get("disponivel")
                else None
            ),
            "maquinario_relacionado": maquinario_relacionado,
            "maquinario_relacionado_disponivel": (
                maquinario_relacionado is not None
            ),
            "historico_incidente": historico,
        },
        "limitacoes": limitacoes,
    }


def obter_imagem_evidencia(
    evidencia_id: str,
    tipo: str = "frame",
) -> Dict[str, Any]:
    evidencia, _ = _buscar_evidencia(
        evidencia_id
    )

    if evidencia is None:
        return {
            "sucesso": False,
            "erro": "EVIDENCIA_NAO_ENCONTRADA",
        }

    tipo = str(
        tipo or "frame"
    ).strip().lower()

    if tipo not in {"frame", "crop"}:
        return {
            "sucesso": False,
            "erro": "TIPO_IMAGEM_INVALIDO",
        }

    caminho = evidencia.get(
        "caminho_frame"
        if tipo == "frame"
        else "caminho_crop"
    )

    if not caminho or not Path(caminho).exists():
        return {
            "sucesso": False,
            "erro": "IMAGEM_EVIDENCIA_INDISPONIVEL",
            "tipo": tipo,
        }

    path = Path(caminho)

    try:
        conteudo = path.read_bytes()
    except Exception as erro:
        return {
            "sucesso": False,
            "erro": "ERRO_LER_IMAGEM_EVIDENCIA",
            "detalhe": str(erro),
        }

    mime = (
        mimetypes.guess_type(
            str(path)
        )[0]
        or "image/jpeg"
    )

    dimensoes = _dimensoes_imagem(
        str(path)
    )

    return {
        "sucesso": True,
        "erro": None,
        "evidencia_id": evidencia_id,
        "tipo": tipo,
        "mime_type": mime,
        "imagem_base64": base64.b64encode(
            conteudo
        ).decode("ascii"),
        **dimensoes,
    }


def exportar_evidencia(
    evidencia_id: str,
    destino: str,
) -> Dict[str, Any]:
    detalhes = obter_detalhes_evidencia(
        evidencia_id
    )

    if not detalhes.get("sucesso"):
        return detalhes

    evidencia = detalhes["evidencia"]

    destino_path = Path(destino)

    if destino_path.suffix.lower() != ".zip":
        destino_path = (
            destino_path
            / f"evidencia_{evidencia_id}.zip"
        )

    try:
        destino_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        with zipfile.ZipFile(
            destino_path,
            "w",
            compression=zipfile.ZIP_DEFLATED,
        ) as arquivo_zip:
            for chave in (
                "caminho_frame",
                "caminho_crop",
            ):
                caminho = evidencia.get(chave)

                if (
                    caminho
                    and Path(caminho).exists()
                ):
                    arquivo_zip.write(
                        caminho,
                        arcname=Path(
                            caminho
                        ).name,
                    )

            metadata = json.dumps(
                evidencia,
                ensure_ascii=False,
                indent=2,
                default=str,
            ).encode("utf-8")

            arquivo_zip.writestr(
                "metadata.json",
                metadata,
            )

    except Exception as erro:
        return {
            "sucesso": False,
            "erro": "ERRO_EXPORTAR_EVIDENCIA",
            "detalhe": str(erro),
        }

    return {
        "sucesso": True,
        "erro": None,
        "evidencia_id": evidencia_id,
        "arquivo": str(
            destino_path.resolve()
        ),
    }

import base64
import os
import tempfile
import threading
import uuid

from copy import deepcopy
from types import SimpleNamespace
from typing import Any, Dict, List, Optional

import cv2
import numpy as np

import ambientes
import config
import objetos_globais as objetos_globais_modulo

from analise_ambiente import (
    analisar_frame,
    desenhar_objetos,
    criar_resumo_objetos,
)

from services.colaborador_service import (
    listar_colaboradores,
    obter_colaborador,
)

from services.camera_service import (
    listar_cameras,
    obter_camera,
    obter_frame_preview,
    listar_cameras_com_status,
)

from services.incidente_service import (
    contar_infracoes_hoje_por_ambiente,
)


# ============================================================
# FOTO DO AMBIENTE
# ============================================================

_RAIZ_PROJETO = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__),
        "..",
    )
)

_PASTA_IMAGENS_AMBIENTES = os.path.join(
    _RAIZ_PROJETO,
    "ambientes",
    "imagens",
)


def _foto_relativa_ambiente(
    ambiente_id: str,
) -> str:
    return (
        f"ambientes/imagens/"
        f"{ambiente_id}.jpg"
    )


def _foto_absoluta_ambiente(
    ambiente_id: str,
) -> str:
    return os.path.join(
        _PASTA_IMAGENS_AMBIENTES,
        f"{ambiente_id}.jpg",
    )


# ============================================================
# NORMALIZAÇÃO / BUSCAS INTERNAS
# ============================================================


def _normalizar_lista_texto(valores: Optional[List[str]]) -> List[str]:
    resultado: List[str] = []
    vistos = set()

    for valor in valores or []:
        texto = str(valor or "").strip()

        if not texto:
            continue

        chave = texto.casefold()

        if chave in vistos:
            continue

        vistos.add(chave)
        resultado.append(texto)

    return resultado


def _buscar_perfil_por_id(ambiente_id: str) -> Optional[Dict[str, Any]]:
    ambiente_id = str(ambiente_id or "").strip()

    if not ambiente_id:
        return None

    for perfil in ambientes.listar_perfis():
        if str(perfil.get("ambiente_id") or "").strip() == ambiente_id:
            return deepcopy(perfil)

    return None


def _nome_disponivel_para_edicao(
    nome: str,
    ambiente_id_atual: Optional[str] = None,
) -> bool:
    nome_normalizado = str(nome or "").strip().casefold()

    if not nome_normalizado:
        return False

    for perfil in ambientes.listar_perfis():
        perfil_id = str(perfil.get("ambiente_id") or "").strip()

        if ambiente_id_atual and perfil_id == ambiente_id_atual:
            continue

        nome_existente = str(perfil.get("nome") or "").strip().casefold()

        if nome_existente == nome_normalizado:
            return False

    return True


def _montar_referencia_camera(camera: Dict[str, Any]) -> Dict[str, Any]:
    """
    Monta a referência persistente da câmera para o perfil do ambiente.

    camera_uid é a referência principal. A referência legada é preservada
    somente quando existe informação real no cadastro atual.
    """
    camera_uid = str(camera.get("camera_uid") or "").strip()
    tipo = str(camera.get("tipo") or "").strip().lower()
    nome = str(camera.get("nome") or "").strip()

    referencia: Dict[str, Any] = {
        "camera_uid": camera_uid,
        "tipo": tipo,
        "nome": nome,
    }

    if tipo == "usb":
        indice = (camera.get("ultimo_runtime") or {}).get("indice_usb")

        if isinstance(indice, int):
            referencia["referencia_legada"] = {
                "indice": indice,
            }

    else:
        config_index = (camera.get("compatibilidade") or {}).get(
            "config_index_legado"
        )

        if isinstance(config_index, int):
            referencia["referencia_legada"] = {
                "config_index": config_index,
            }

    return referencia


def _resolver_cameras_para_perfil(
    camera_uids: List[str],
) -> Dict[str, Any]:
    referencias: List[Dict[str, Any]] = []
    vistos = set()

    for camera_uid in camera_uids or []:
        uid = str(camera_uid or "").strip()

        if not uid or uid in vistos:
            continue

        vistos.add(uid)

        resultado = obter_camera(uid)

        if not resultado.get("sucesso"):
            return {
                "sucesso": False,
                "erro": "CAMERA_NAO_ENCONTRADA",
                "camera_uid": uid,
                "cameras": [],
            }

        camera = resultado.get("camera")

        if not isinstance(camera, dict):
            return {
                "sucesso": False,
                "erro": "CAMERA_INVALIDA",
                "camera_uid": uid,
                "cameras": [],
            }

        referencias.append(_montar_referencia_camera(camera))

    # Ambiente pode existir sem câmera vinculada.
    # Se camera_uids vier vazio, o perfil é criado normalmente.
    return {
        "sucesso": True,
        "erro": None,
        "cameras": referencias,
    }


# ============================================================
# CONSULTA
# ============================================================


def listar_ambientes() -> Dict[str, Any]:
    perfis = ambientes.listar_perfis()
    resultado: List[Dict[str, Any]] = []

    for perfil in perfis:
        cameras = perfil.get("cameras")
        epis = perfil.get("epis_obrigatorios")
        objetos = perfil.get("objetos_globais")

        resultado.append(
            {
                "ambiente_id": perfil.get("ambiente_id"),
                "nome": perfil.get("nome"),
                "descricao": str(
                    perfil.get("descricao") or ""
                ),
                "foto_ambiente": str(
                    perfil.get("foto_ambiente") or ""
                ),
                "possui_foto": bool(
                    str(
                        perfil.get("foto_ambiente")
                        or ""
                    ).strip()
                ),
                "calibrado": perfil.get("calibrado", False),
                "quantidade_cameras": len(cameras) if isinstance(cameras, list) else 0,
                "quantidade_epis": len(epis) if isinstance(epis, list) else 0,
                "quantidade_objetos": len(objetos) if isinstance(objetos, dict) else 0,
                "schema_version": perfil.get("schema_version"),
                "metadata": deepcopy(perfil.get("metadata") or {}),
            }
        )

    return {
        "sucesso": True,
        "erro": None,
        "quantidade": len(resultado),
        "ambientes": resultado,
    }


def obter_ambiente(ambiente_id: str) -> Dict[str, Any]:
    perfil = _buscar_perfil_por_id(ambiente_id)

    if perfil is None:
        return {
            "sucesso": False,
            "erro": "AMBIENTE_NAO_ENCONTRADO",
            "ambiente": None,
        }

    return {
        "sucesso": True,
        "erro": None,
        "ambiente": perfil,
    }


def listar_cameras_para_ambiente() -> Dict[str, Any]:
    """
    Expõe ao fluxo de Ambiente as câmeras já cadastradas.

    Não descobre nem cadastra câmeras novas.
    """
    resultado = listar_cameras()

    if not resultado.get("sucesso"):
        return resultado

    cameras_front: List[Dict[str, Any]] = []

    for camera in resultado.get("cameras", []):
        if not isinstance(camera, dict):
            continue

        cameras_front.append(
            {
                "camera_uid": camera.get("camera_uid"),
                "nome": camera.get("nome"),
                "tipo": camera.get("tipo"),
            }
        )

    return {
        "sucesso": True,
        "erro": None,
        "quantidade": len(cameras_front),
        "cameras": cameras_front,
    }


# ============================================================
# CRIAÇÃO
# ============================================================


def criar_ambiente(
    nome: str,
    camera_uids: Optional[List[str]] = None,
    epis_obrigatorios: Optional[List[str]] = None,
    descricao: str = "",
) -> Dict[str, Any]:
    """
    Cria o perfil persistente inicial do ambiente.

    Nesta primeira versão do service são persistidos somente campos já
    suportados pelo schema atual de ambientes.py.

    ROI e colaboradores serão adicionados em uma evolução compatível do
    schema, sem quebrar ambientes antigos.
    """
    nome_normalizado = str(nome or "").strip()
    descricao_normalizada = str(descricao or "").strip()

    if len(descricao_normalizada) > 500:
        return {
            "sucesso": False,
            "erro": "DESCRICAO_AMBIENTE_MUITO_LONGA",
            "limite": 500,
        }

    if not nome_normalizado:
        return {
            "sucesso": False,
            "erro": "NOME_AMBIENTE_OBRIGATORIO",
        }

    if not ambientes.nome_ambiente_disponivel(nome_normalizado):
        return {
            "sucesso": False,
            "erro": "NOME_AMBIENTE_JA_EXISTE",
        }

    cameras = _resolver_cameras_para_perfil(camera_uids)

    if not cameras.get("sucesso"):
        return cameras

    perfil = ambientes.criar_perfil(
        nome=nome_normalizado,
        cameras=cameras["cameras"],
        epis_obrigatorios=_normalizar_lista_texto(epis_obrigatorios),
        objetos_globais={},
        calibrado=False,
        origem=ambientes.ORIGEM_NOVO,
        descricao=descricao_normalizada,
    )

    try:
        ambientes.salvar_perfil(perfil)
    except ValueError as erro:
        return {
            "sucesso": False,
            "erro": "PERFIL_AMBIENTE_INVALIDO",
            "detalhe": str(erro),
        }
    except Exception:
        return {
            "sucesso": False,
            "erro": "ERRO_SALVAR_AMBIENTE",
        }

    return {
        "sucesso": True,
        "erro": None,
        "ambiente": deepcopy(perfil),
    }


# ============================================================
# EDIÇÃO BÁSICA
# ============================================================


def editar_ambiente_basico(
    ambiente_id: str,
    nome: Optional[str] = None,
    camera_uids: Optional[List[str]] = None,
    epis_obrigatorios: Optional[List[str]] = None,
    calibrado: Optional[bool] = None,
    descricao: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Atualiza somente dados já pertencentes ao schema atual.

    Preserva objetos_globais, metadata de criação e ambiente_id.
    """
    perfil = _buscar_perfil_por_id(ambiente_id)

    if perfil is None:
        return {
            "sucesso": False,
            "erro": "AMBIENTE_NAO_ENCONTRADO",
            "ambiente": None,
        }

    if nome is not None:
        nome_normalizado = str(nome or "").strip()

        if not nome_normalizado:
            return {
                "sucesso": False,
                "erro": "NOME_AMBIENTE_OBRIGATORIO",
            }

        if not _nome_disponivel_para_edicao(
            nome_normalizado,
            ambiente_id_atual=ambiente_id,
        ):
            return {
                "sucesso": False,
                "erro": "NOME_AMBIENTE_JA_EXISTE",
            }

        perfil["nome"] = nome_normalizado

    if descricao is not None:
        descricao_normalizada = str(descricao or "").strip()

        if len(descricao_normalizada) > 500:
            return {
                "sucesso": False,
                "erro": "DESCRICAO_AMBIENTE_MUITO_LONGA",
                "limite": 500,
            }

        perfil["descricao"] = descricao_normalizada

    if camera_uids is not None:
        cameras = _resolver_cameras_para_perfil(camera_uids)

        if not cameras.get("sucesso"):
            return cameras

        perfil["cameras"] = cameras["cameras"]

    if epis_obrigatorios is not None:
        perfil["epis_obrigatorios"] = _normalizar_lista_texto(
            epis_obrigatorios
        )

    if calibrado is not None:
        perfil["calibrado"] = bool(calibrado)

    if descricao is not None and perfil.get("schema_version") != ambientes.SCHEMA_VERSION:
        perfil["schema_version"] = ambientes.SCHEMA_VERSION
        perfil.setdefault("descricao", "")
        perfil.setdefault("rois", {})
        perfil.setdefault("colaboradores_vinculados", [])
    perfil.setdefault("foto_ambiente", "")

    try:
        ambientes.salvar_perfil(perfil)
    except ValueError as erro:
        return {
            "sucesso": False,
            "erro": "PERFIL_AMBIENTE_INVALIDO",
            "detalhe": str(erro),
        }
    except Exception:
        return {
            "sucesso": False,
            "erro": "ERRO_SALVAR_AMBIENTE",
        }

    return {
        "sucesso": True,
        "erro": None,
        "ambiente": deepcopy(perfil),
    }


# ============================================================
# REMOÇÃO
# ============================================================

def remover_ambiente(
    ambiente_id: str,
) -> Dict[str, Any]:
    """
    Remove somente o perfil persistente do ambiente.

    Não remove câmeras cadastradas.
    Não remove incidentes.
    Não remove evidências.
    Não remove outros históricos.
    """
    perfil = _buscar_perfil_por_id(ambiente_id)

    if perfil is None:
        return {
            "sucesso": False,
            "erro": "AMBIENTE_NAO_ENCONTRADO",
        }

    foto_ambiente = str(
        perfil.get("foto_ambiente")
        or ""
    ).strip()

    removido = ambientes.remover_perfil(ambiente_id)

    if not removido:
        return {
            "sucesso": False,
            "erro": "ERRO_REMOVER_AMBIENTE",
        }

    if foto_ambiente:
        caminho_foto = _foto_absoluta_ambiente(
            ambiente_id
        )

        try:
            if os.path.exists(caminho_foto):
                os.remove(caminho_foto)
        except Exception:
            # O ambiente já foi removido. Falha ao limpar a imagem
            # não recria o perfil nem interrompe a remoção.
            pass

    return {
        "sucesso": True,
        "erro": None,
        "ambiente_id": ambiente_id,
        "nome": perfil.get("nome"),
    }


# ============================================================
# FOTO DO AMBIENTE
# ============================================================

def salvar_foto_ambiente(
    ambiente_id: str,
    imagem_base64: str,
    qualidade_jpeg: int = 90,
) -> Dict[str, Any]:
    """
    Salva uma foto física do ambiente e persiste somente
    o caminho relativo no JSON do ambiente.

    Aceita Base64 puro ou Data URL:
        data:image/jpeg;base64,...
    """
    perfil = _buscar_perfil_por_id(
        ambiente_id
    )

    if perfil is None:
        return {
            "sucesso": False,
            "erro": "AMBIENTE_NAO_ENCONTRADO",
        }

    if not isinstance(
        imagem_base64,
        str,
    ) or not imagem_base64.strip():
        return {
            "sucesso": False,
            "erro": "FOTO_AMBIENTE_OBRIGATORIA",
        }

    conteudo = imagem_base64.strip()

    if conteudo.lower().startswith(
        "data:image/"
    ):
        partes = conteudo.split(
            ",",
            1,
        )

        if len(partes) != 2:
            return {
                "sucesso": False,
                "erro": "FOTO_AMBIENTE_BASE64_INVALIDA",
            }

        conteudo = partes[1]

    try:
        dados = base64.b64decode(
            conteudo,
            validate=True,
        )
        buffer = np.frombuffer(
            dados,
            dtype=np.uint8,
        )
        frame = cv2.imdecode(
            buffer,
            cv2.IMREAD_COLOR,
        )
    except Exception:
        frame = None

    if frame is None or frame.size == 0:
        return {
            "sucesso": False,
            "erro": "FOTO_AMBIENTE_INVALIDA",
        }

    try:
        qualidade = int(
            qualidade_jpeg
        )
    except (TypeError, ValueError):
        qualidade = 90

    qualidade = max(
        1,
        min(100, qualidade),
    )

    ok, jpeg = cv2.imencode(
        ".jpg",
        frame,
        [
            cv2.IMWRITE_JPEG_QUALITY,
            qualidade,
        ],
    )

    if not ok:
        return {
            "sucesso": False,
            "erro": "ERRO_CODIFICAR_FOTO_AMBIENTE",
        }

    os.makedirs(
        _PASTA_IMAGENS_AMBIENTES,
        exist_ok=True,
    )

    caminho_final = (
        _foto_absoluta_ambiente(
            ambiente_id
        )
    )

    fd, temporario = tempfile.mkstemp(
        prefix=f".{ambiente_id}.",
        suffix=".jpg.tmp",
        dir=_PASTA_IMAGENS_AMBIENTES,
    )

    try:
        with os.fdopen(
            fd,
            "wb",
        ) as arquivo:
            arquivo.write(
                jpeg.tobytes()
            )
            arquivo.flush()
            os.fsync(
                arquivo.fileno()
            )

        caminho_relativo = (
            _foto_relativa_ambiente(
                ambiente_id
            )
        )

        perfil["schema_version"] = (
            ambientes.SCHEMA_VERSION
        )
        perfil.setdefault(
            "descricao",
            "",
        )
        perfil.setdefault(
            "rois",
            {},
        )
        perfil.setdefault(
            "colaboradores_vinculados",
            [],
        )
        perfil["foto_ambiente"] = (
            caminho_relativo
        )

        ambientes.salvar_perfil(
            perfil
        )

        os.replace(
            temporario,
            caminho_final,
        )

    except ValueError as erro:
        try:
            if os.path.exists(
                temporario
            ):
                os.remove(
                    temporario
                )
        except Exception:
            pass

        return {
            "sucesso": False,
            "erro": "PERFIL_AMBIENTE_INVALIDO",
            "detalhe": str(erro),
        }

    except Exception as erro:
        try:
            if os.path.exists(
                temporario
            ):
                os.remove(
                    temporario
                )
        except Exception:
            pass

        return {
            "sucesso": False,
            "erro": "ERRO_SALVAR_FOTO_AMBIENTE",
            "detalhe": str(erro),
        }

    altura, largura = frame.shape[:2]

    return {
        "sucesso": True,
        "erro": None,
        "ambiente_id": ambiente_id,
        "foto_ambiente": caminho_relativo,
        "largura": int(largura),
        "altura": int(altura),
        "mime_type": "image/jpeg",
    }


def capturar_foto_ambiente(
    ambiente_id: str,
    session_id: str,
    qualidade_jpeg: int = 90,
) -> Dict[str, Any]:
    """
    Usa um frame da sessão de preview já aberta e salva
    esse frame como foto do ambiente.
    """
    session_id = str(
        session_id or ""
    ).strip()

    if not session_id:
        return {
            "sucesso": False,
            "erro": "SESSION_ID_OBRIGATORIO",
        }

    frame = obter_frame_preview(
        session_id
    )

    if not frame.get("sucesso"):
        return {
            "sucesso": False,
            "erro": (
                frame.get("erro")
                or "ERRO_OBTER_FRAME_PREVIEW"
            ),
        }

    return salvar_foto_ambiente(
        ambiente_id=ambiente_id,
        imagem_base64=frame.get(
            "frame_base64"
        ),
        qualidade_jpeg=qualidade_jpeg,
    )


def obter_foto_ambiente(
    ambiente_id: str,
) -> Dict[str, Any]:
    perfil = _buscar_perfil_por_id(
        ambiente_id
    )

    if perfil is None:
        return {
            "sucesso": False,
            "erro": "AMBIENTE_NAO_ENCONTRADO",
        }

    foto_relativa = str(
        perfil.get("foto_ambiente")
        or ""
    ).strip()

    if not foto_relativa:
        return {
            "sucesso": False,
            "erro": "FOTO_AMBIENTE_NAO_DEFINIDA",
            "ambiente_id": ambiente_id,
        }

    caminho = _foto_absoluta_ambiente(
        ambiente_id
    )

    if not os.path.exists(
        caminho
    ):
        return {
            "sucesso": False,
            "erro": "ARQUIVO_FOTO_AMBIENTE_NAO_ENCONTRADO",
            "ambiente_id": ambiente_id,
            "foto_ambiente": foto_relativa,
        }

    return {
        "sucesso": True,
        "erro": None,
        "ambiente_id": ambiente_id,
        "foto_ambiente": foto_relativa,
        "caminho_absoluto": caminho,
        "mime_type": "image/jpeg",
    }


def remover_foto_ambiente(
    ambiente_id: str,
) -> Dict[str, Any]:
    perfil = _buscar_perfil_por_id(
        ambiente_id
    )

    if perfil is None:
        return {
            "sucesso": False,
            "erro": "AMBIENTE_NAO_ENCONTRADO",
        }

    caminho = _foto_absoluta_ambiente(
        ambiente_id
    )

    try:
        if os.path.exists(
            caminho
        ):
            os.remove(
                caminho
            )
    except Exception as erro:
        return {
            "sucesso": False,
            "erro": "ERRO_REMOVER_FOTO_AMBIENTE",
            "detalhe": str(erro),
        }

    perfil["schema_version"] = (
        ambientes.SCHEMA_VERSION
    )
    perfil.setdefault(
        "descricao",
        "",
    )
    perfil.setdefault(
        "rois",
        {},
    )
    perfil.setdefault(
        "colaboradores_vinculados",
        [],
    )
    perfil["foto_ambiente"] = ""

    try:
        ambientes.salvar_perfil(
            perfil
        )
    except Exception as erro:
        return {
            "sucesso": False,
            "erro": "ERRO_SALVAR_AMBIENTE",
            "detalhe": str(erro),
        }

    return {
        "sucesso": True,
        "erro": None,
        "ambiente_id": ambiente_id,
    }


# ============================================================
# ROI
# ============================================================

def _normalizar_coordenada_roi(valor: Any, campo: str) -> float:
    """
    Normaliza e valida uma coordenada de ROI no intervalo 0..1.
    """
    if isinstance(valor, bool) or not isinstance(valor, (int, float)):
        raise ValueError(f"{campo} deve ser numérico.")

    valor_float = float(valor)

    if not (0.0 <= valor_float <= 1.0):
        raise ValueError(f"{campo} deve estar entre 0 e 1.")

    return valor_float


def _camera_pertence_ao_ambiente(
    perfil: Dict[str, Any],
    camera_uid: str,
) -> bool:
    camera_uid = str(camera_uid or "").strip()

    for camera in perfil.get("cameras", []):
        if not isinstance(camera, dict):
            continue

        if str(camera.get("camera_uid") or "").strip() == camera_uid:
            return True

    return False


def listar_rois(
    ambiente_id: str,
) -> Dict[str, Any]:
    """
    Lista as ROIs persistidas do ambiente.

    Perfis antigos (schema 1/2) sem o campo 'rois' são tratados
    como ambientes com zero ROIs, sem migração automática.
    """
    perfil = _buscar_perfil_por_id(ambiente_id)

    if perfil is None:
        return {
            "sucesso": False,
            "erro": "AMBIENTE_NAO_ENCONTRADO",
            "rois": {},
            "quantidade": 0,
        }

    rois = perfil.get("rois", {})

    if not isinstance(rois, dict):
        rois = {}

    return {
        "sucesso": True,
        "erro": None,
        "ambiente_id": perfil.get("ambiente_id"),
        "rois": deepcopy(rois),
        "quantidade": len(rois),
    }


def obter_roi(
    ambiente_id: str,
    camera_uid: str,
) -> Dict[str, Any]:
    """
    Retorna a ROI de uma câmera vinculada ao ambiente.
    """
    perfil = _buscar_perfil_por_id(ambiente_id)

    if perfil is None:
        return {
            "sucesso": False,
            "erro": "AMBIENTE_NAO_ENCONTRADO",
        }

    camera_uid = str(camera_uid or "").strip()

    if not camera_uid:
        return {
            "sucesso": False,
            "erro": "CAMERA_UID_OBRIGATORIO",
        }

    if not _camera_pertence_ao_ambiente(perfil, camera_uid):
        return {
            "sucesso": False,
            "erro": "CAMERA_NAO_VINCULADA_AO_AMBIENTE",
            "camera_uid": camera_uid,
        }

    rois = perfil.get("rois", {})
    if not isinstance(rois, dict):
        rois = {}

    roi = rois.get(camera_uid)

    if not isinstance(roi, dict):
        return {
            "sucesso": False,
            "erro": "ROI_NAO_DEFINIDA",
            "camera_uid": camera_uid,
        }

    return {
        "sucesso": True,
        "erro": None,
        "ambiente_id": perfil.get("ambiente_id"),
        "camera_uid": camera_uid,
        "roi": deepcopy(roi),
    }


def definir_roi(
    ambiente_id: str,
    camera_uid: str,
    x1: float,
    y1: float,
    x2: float,
    y2: float,
) -> Dict[str, Any]:
    """
    Define ou substitui a ROI de uma câmera do ambiente.

    Coordenadas normalizadas:
        0.0 <= x1 < x2 <= 1.0
        0.0 <= y1 < y2 <= 1.0

    Ao persistir a primeira ROI, um perfil antigo é promovido
    para o schema atual sem alterar os demais dados.
    """
    perfil = _buscar_perfil_por_id(ambiente_id)

    if perfil is None:
        return {
            "sucesso": False,
            "erro": "AMBIENTE_NAO_ENCONTRADO",
        }

    camera_uid = str(camera_uid or "").strip()

    if not camera_uid:
        return {
            "sucesso": False,
            "erro": "CAMERA_UID_OBRIGATORIO",
        }

    if not _camera_pertence_ao_ambiente(perfil, camera_uid):
        return {
            "sucesso": False,
            "erro": "CAMERA_NAO_VINCULADA_AO_AMBIENTE",
            "camera_uid": camera_uid,
        }

    try:
        x1_n = _normalizar_coordenada_roi(x1, "x1")
        y1_n = _normalizar_coordenada_roi(y1, "y1")
        x2_n = _normalizar_coordenada_roi(x2, "x2")
        y2_n = _normalizar_coordenada_roi(y2, "y2")
    except ValueError as erro:
        return {
            "sucesso": False,
            "erro": "ROI_INVALIDA",
            "detalhe": str(erro),
        }

    if x1_n >= x2_n:
        return {
            "sucesso": False,
            "erro": "ROI_INVALIDA",
            "detalhe": "x1 deve ser menor que x2.",
        }

    if y1_n >= y2_n:
        return {
            "sucesso": False,
            "erro": "ROI_INVALIDA",
            "detalhe": "y1 deve ser menor que y2.",
        }

    perfil["schema_version"] = ambientes.SCHEMA_VERSION

    rois = perfil.get("rois")
    if not isinstance(rois, dict):
        rois = {}

    rois[camera_uid] = {
        "x1": x1_n,
        "y1": y1_n,
        "x2": x2_n,
        "y2": y2_n,
    }
    perfil["rois"] = rois

    try:
        ambientes.salvar_perfil(perfil)
    except ValueError as erro:
        return {
            "sucesso": False,
            "erro": "PERFIL_AMBIENTE_INVALIDO",
            "detalhe": str(erro),
        }
    except Exception:
        return {
            "sucesso": False,
            "erro": "ERRO_SALVAR_AMBIENTE",
        }

    return {
        "sucesso": True,
        "erro": None,
        "ambiente_id": perfil.get("ambiente_id"),
        "camera_uid": camera_uid,
        "roi": deepcopy(rois[camera_uid]),
        "schema_version": perfil.get("schema_version"),
    }


def remover_roi(
    ambiente_id: str,
    camera_uid: str,
) -> Dict[str, Any]:
    """
    Remove somente a ROI da câmera informada.
    Não remove a câmera nem outros dados do ambiente.
    """
    perfil = _buscar_perfil_por_id(ambiente_id)

    if perfil is None:
        return {
            "sucesso": False,
            "erro": "AMBIENTE_NAO_ENCONTRADO",
        }

    camera_uid = str(camera_uid or "").strip()

    if not camera_uid:
        return {
            "sucesso": False,
            "erro": "CAMERA_UID_OBRIGATORIO",
        }

    if not _camera_pertence_ao_ambiente(perfil, camera_uid):
        return {
            "sucesso": False,
            "erro": "CAMERA_NAO_VINCULADA_AO_AMBIENTE",
            "camera_uid": camera_uid,
        }

    rois = perfil.get("rois", {})
    if not isinstance(rois, dict) or camera_uid not in rois:
        return {
            "sucesso": False,
            "erro": "ROI_NAO_DEFINIDA",
            "camera_uid": camera_uid,
        }

    del rois[camera_uid]

    perfil["schema_version"] = ambientes.SCHEMA_VERSION
    perfil["rois"] = rois

    try:
        ambientes.salvar_perfil(perfil)
    except ValueError as erro:
        return {
            "sucesso": False,
            "erro": "PERFIL_AMBIENTE_INVALIDO",
            "detalhe": str(erro),
        }
    except Exception:
        return {
            "sucesso": False,
            "erro": "ERRO_SALVAR_AMBIENTE",
        }

    return {
        "sucesso": True,
        "erro": None,
        "ambiente_id": perfil.get("ambiente_id"),
        "camera_uid": camera_uid,
    }


# ============================================================
# ÁREA DE MONITORAMENTO — FRAME / CROP / ZOOM
# ============================================================

def _validar_roi_em_memoria(
    roi: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Valida uma ROI sem persistir nada.
    """
    if not isinstance(roi, dict):
        return {
            "sucesso": False,
            "erro": "ROI_INVALIDA",
            "detalhe": "ROI deve ser um objeto.",
        }

    try:
        x1 = _normalizar_coordenada_roi(roi.get("x1"), "x1")
        y1 = _normalizar_coordenada_roi(roi.get("y1"), "y1")
        x2 = _normalizar_coordenada_roi(roi.get("x2"), "x2")
        y2 = _normalizar_coordenada_roi(roi.get("y2"), "y2")
    except ValueError as erro:
        return {
            "sucesso": False,
            "erro": "ROI_INVALIDA",
            "detalhe": str(erro),
        }

    if x1 >= x2:
        return {
            "sucesso": False,
            "erro": "ROI_INVALIDA",
            "detalhe": "x1 deve ser menor que x2.",
        }

    if y1 >= y2:
        return {
            "sucesso": False,
            "erro": "ROI_INVALIDA",
            "detalhe": "y1 deve ser menor que y2.",
        }

    return {
        "sucesso": True,
        "erro": None,
        "roi": {
            "x1": x1,
            "y1": y1,
            "x2": x2,
            "y2": y2,
        },
    }


def converter_roi_para_pixels(
    roi: Dict[str, Any],
    largura: int,
    altura: int,
) -> Dict[str, Any]:
    """
    Converte coordenadas normalizadas 0..1 para pixels do frame.
    """
    validacao = _validar_roi_em_memoria(roi)

    if not validacao.get("sucesso"):
        return validacao

    try:
        largura = int(largura)
        altura = int(altura)
    except (TypeError, ValueError):
        return {
            "sucesso": False,
            "erro": "DIMENSAO_FRAME_INVALIDA",
        }

    if largura <= 0 or altura <= 0:
        return {
            "sucesso": False,
            "erro": "DIMENSAO_FRAME_INVALIDA",
        }

    roi_n = validacao["roi"]

    x1 = max(0, min(largura - 1, int(round(roi_n["x1"] * largura))))
    y1 = max(0, min(altura - 1, int(round(roi_n["y1"] * altura))))
    x2 = max(1, min(largura, int(round(roi_n["x2"] * largura))))
    y2 = max(1, min(altura, int(round(roi_n["y2"] * altura))))

    if x1 >= x2 or y1 >= y2:
        return {
            "sucesso": False,
            "erro": "ROI_SEM_AREA_UTIL",
        }

    return {
        "sucesso": True,
        "erro": None,
        "roi_normalizada": deepcopy(roi_n),
        "roi_pixels": {
            "x1": x1,
            "y1": y1,
            "x2": x2,
            "y2": y2,
            "largura": x2 - x1,
            "altura": y2 - y1,
        },
    }


def recortar_frame_por_roi(
    frame_base64: str,
    roi: Dict[str, Any],
    qualidade_jpeg: int = 90,
) -> Dict[str, Any]:
    """
    Recorta um frame JPEG/Base64 usando uma ROI normalizada.

    Não salva imagem em disco.
    Não altera a ROI persistida.
    """
    if not isinstance(frame_base64, str) or not frame_base64.strip():
        return {
            "sucesso": False,
            "erro": "FRAME_BASE64_INVALIDO",
        }

    try:
        dados = base64.b64decode(frame_base64, validate=True)
        buffer = np.frombuffer(dados, dtype=np.uint8)
        frame = cv2.imdecode(buffer, cv2.IMREAD_COLOR)
    except Exception:
        frame = None

    if frame is None or frame.size == 0:
        return {
            "sucesso": False,
            "erro": "FRAME_NAO_DECODIFICADO",
        }

    altura_original, largura_original = frame.shape[:2]

    conversao = converter_roi_para_pixels(
        roi,
        largura_original,
        altura_original,
    )

    if not conversao.get("sucesso"):
        return conversao

    pixels = conversao["roi_pixels"]

    recorte = frame[
        pixels["y1"]:pixels["y2"],
        pixels["x1"]:pixels["x2"],
    ]

    if recorte is None or recorte.size == 0:
        return {
            "sucesso": False,
            "erro": "RECORTE_ROI_VAZIO",
        }

    try:
        qualidade = int(qualidade_jpeg)
    except (TypeError, ValueError):
        qualidade = 90

    qualidade = max(1, min(100, qualidade))

    ok, jpeg = cv2.imencode(
        ".jpg",
        recorte,
        [cv2.IMWRITE_JPEG_QUALITY, qualidade],
    )

    if not ok:
        return {
            "sucesso": False,
            "erro": "ERRO_CODIFICAR_AREA_MONITORAMENTO",
        }

    altura_recorte, largura_recorte = recorte.shape[:2]

    return {
        "sucesso": True,
        "erro": None,
        "mime_type": "image/jpeg",
        "frame_base64": base64.b64encode(
            jpeg.tobytes()
        ).decode("ascii"),
        "largura_original": int(largura_original),
        "altura_original": int(altura_original),
        "largura": int(largura_recorte),
        "altura": int(altura_recorte),
        "roi_normalizada": conversao["roi_normalizada"],
        "roi_pixels": pixels,
    }


def previsualizar_area_monitoramento(
    session_id: str,
    camera_uid: str,
    x1: float,
    y1: float,
    x2: float,
    y2: float,
    qualidade_jpeg: int = 90,
) -> Dict[str, Any]:
    """
    Gera o zoom/crop da área que o usuário acabou de selecionar.

    IMPORTANTE:
    - não salva a ROI;
    - usa a sessão de preview já aberta pelo camera_service;
    - devolve a imagem original e o recorte ampliado para a interface.
    """
    camera_uid = str(camera_uid or "").strip()

    if not camera_uid:
        return {
            "sucesso": False,
            "erro": "CAMERA_UID_OBRIGATORIO",
        }

    roi = {
        "x1": x1,
        "y1": y1,
        "x2": x2,
        "y2": y2,
    }

    validacao = _validar_roi_em_memoria(roi)

    if not validacao.get("sucesso"):
        return validacao

    frame = obter_frame_preview(session_id)

    if not frame.get("sucesso"):
        return {
            "sucesso": False,
            "erro": frame.get("erro") or "ERRO_OBTER_FRAME_PREVIEW",
        }

    camera_preview = str(frame.get("camera_uid") or "").strip()

    if camera_preview != camera_uid:
        return {
            "sucesso": False,
            "erro": "PREVIEW_DE_OUTRA_CAMERA",
            "camera_uid_esperado": camera_uid,
            "camera_uid_preview": camera_preview,
        }

    recorte = recortar_frame_por_roi(
        frame_base64=frame.get("frame_base64"),
        roi=validacao["roi"],
        qualidade_jpeg=qualidade_jpeg,
    )

    if not recorte.get("sucesso"):
        return recorte

    return {
        "sucesso": True,
        "erro": None,
        "session_id": session_id,
        "camera_uid": camera_uid,
        "imagem_original": {
            "mime_type": frame.get("mime_type"),
            "frame_base64": frame.get("frame_base64"),
            "largura": frame.get("largura"),
            "altura": frame.get("altura"),
        },
        "area_selecionada": {
            "mime_type": recorte.get("mime_type"),
            "frame_base64": recorte.get("frame_base64"),
            "largura": recorte.get("largura"),
            "altura": recorte.get("altura"),
            "roi_normalizada": recorte.get("roi_normalizada"),
            "roi_pixels": recorte.get("roi_pixels"),
        },
    }


def obter_area_monitoramento(
    ambiente_id: str,
    camera_uid: str,
    session_id: str,
    qualidade_jpeg: int = 90,
) -> Dict[str, Any]:
    """
    Obtém a ROI já salva no ambiente e gera o recorte atual da câmera.

    Esse é o método que poderá ser reutilizado depois pelo fluxo de análise
    de objetos e pelo monitoramento do ambiente.
    """
    roi_resultado = obter_roi(
        ambiente_id=ambiente_id,
        camera_uid=camera_uid,
    )

    if not roi_resultado.get("sucesso"):
        return roi_resultado

    roi = roi_resultado["roi"]

    preview = previsualizar_area_monitoramento(
        session_id=session_id,
        camera_uid=camera_uid,
        x1=roi["x1"],
        y1=roi["y1"],
        x2=roi["x2"],
        y2=roi["y2"],
        qualidade_jpeg=qualidade_jpeg,
    )

    if not preview.get("sucesso"):
        return preview

    preview["ambiente_id"] = ambiente_id
    return preview


# ============================================================
# ANÁLISE DE OBJETOS DENTRO DA ROI
# ============================================================

def _decodificar_jpeg_base64(
    frame_base64: str,
):
    """
    Converte JPEG/Base64 em frame OpenCV (BGR).
    """
    if not isinstance(frame_base64, str) or not frame_base64.strip():
        return None

    try:
        dados = base64.b64decode(frame_base64, validate=True)
        buffer = np.frombuffer(dados, dtype=np.uint8)
        frame = cv2.imdecode(buffer, cv2.IMREAD_COLOR)
    except Exception:
        return None

    if frame is None or frame.size == 0:
        return None

    return frame


def _codificar_frame_jpeg_base64(
    frame,
    qualidade_jpeg: int = 90,
) -> Optional[str]:
    """
    Converte um frame OpenCV (BGR) para JPEG/Base64.
    """
    if frame is None or frame.size == 0:
        return None

    try:
        qualidade = int(qualidade_jpeg)
    except (TypeError, ValueError):
        qualidade = 90

    qualidade = max(1, min(100, qualidade))

    ok, jpeg = cv2.imencode(
        ".jpg",
        frame,
        [cv2.IMWRITE_JPEG_QUALITY, qualidade],
    )

    if not ok:
        return None

    return base64.b64encode(
        jpeg.tobytes()
    ).decode("ascii")


def _enriquecer_objetos_com_coordenadas_frame(
    objetos: List[Dict[str, Any]],
    roi_pixels: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """
    Mantém as coordenadas retornadas pelo FastSAM relativas à ROI
    e acrescenta as coordenadas equivalentes no frame completo.

    Isso evita perder compatibilidade com o monitoramento que trabalha
    com coordenadas da imagem completa.
    """
    offset_x = int(roi_pixels.get("x1", 0))
    offset_y = int(roi_pixels.get("y1", 0))

    resultado: List[Dict[str, Any]] = []

    for objeto in objetos or []:
        item = deepcopy(objeto)

        bbox = item.get("bbox")
        centro = item.get("centro")

        if (
            isinstance(bbox, list)
            and len(bbox) == 4
        ):
            x1, y1, x2, y2 = [int(v) for v in bbox]

            item["bbox_roi"] = [
                x1,
                y1,
                x2,
                y2,
            ]

            item["bbox_frame"] = [
                x1 + offset_x,
                y1 + offset_y,
                x2 + offset_x,
                y2 + offset_y,
            ]

        if (
            isinstance(centro, list)
            and len(centro) == 2
        ):
            cx, cy = [int(v) for v in centro]

            item["centro_roi"] = [
                cx,
                cy,
            ]

            item["centro_frame"] = [
                cx + offset_x,
                cy + offset_y,
            ]

        resultado.append(item)

    return resultado


def analisar_area_selecionada(
    session_id: str,
    camera_uid: str,
    x1: float,
    y1: float,
    x2: float,
    y2: float,
    qualidade_jpeg: int = 90,
) -> Dict[str, Any]:
    """
    Analisa SOMENTE a área que o usuário acabou de selecionar.

    Fluxo:
        preview da câmera
        -> ROI
        -> crop/zoom
        -> analise_ambiente.analisar_frame()
        -> Objeto 1, Objeto 2, ...

    A ROI NÃO é persistida por esta função.
    Nenhum threshold ou modelo de IA é alterado.
    """
    preview = previsualizar_area_monitoramento(
        session_id=session_id,
        camera_uid=camera_uid,
        x1=x1,
        y1=y1,
        x2=x2,
        y2=y2,
        qualidade_jpeg=qualidade_jpeg,
    )

    if not preview.get("sucesso"):
        return preview

    area = preview.get("area_selecionada") or {}

    frame_roi = _decodificar_jpeg_base64(
        area.get("frame_base64")
    )

    if frame_roi is None:
        return {
            "sucesso": False,
            "erro": "AREA_MONITORAMENTO_NAO_DECODIFICADA",
        }

    # Reutiliza exatamente o código atual do projeto.
    objetos = analisar_frame(
        frame_roi,
        camera_uid,
    )

    objetos_enriquecidos = (
        _enriquecer_objetos_com_coordenadas_frame(
            objetos,
            area.get("roi_pixels") or {},
        )
    )

    frame_anotado = desenhar_objetos(
        frame_roi,
        objetos,
    )

    frame_anotado_base64 = (
        _codificar_frame_jpeg_base64(
            frame_anotado,
            qualidade_jpeg=qualidade_jpeg,
        )
    )

    if frame_anotado_base64 is None:
        return {
            "sucesso": False,
            "erro": "ERRO_CODIFICAR_ANALISE_AMBIENTE",
        }

    return {
        "sucesso": True,
        "erro": None,
        "session_id": session_id,
        "camera_uid": camera_uid,
        "roi_normalizada": deepcopy(
            area.get("roi_normalizada")
        ),
        "roi_pixels": deepcopy(
            area.get("roi_pixels")
        ),
        "largura_area": area.get("largura"),
        "altura_area": area.get("altura"),
        "quantidade_objetos": len(
            objetos_enriquecidos
        ),
        "objetos": objetos_enriquecidos,
        "resumo_objetos": criar_resumo_objetos(
            objetos
        ),
        "imagem_analisada": {
            "mime_type": "image/jpeg",
            "frame_base64": frame_anotado_base64,
            "largura": area.get("largura"),
            "altura": area.get("altura"),
        },
    }


def analisar_roi_salva(
    ambiente_id: str,
    camera_uid: str,
    session_id: str,
    qualidade_jpeg: int = 90,
) -> Dict[str, Any]:
    """
    Executa a mesma análise usando a ROI já persistida no ambiente.
    """
    roi_resultado = obter_roi(
        ambiente_id=ambiente_id,
        camera_uid=camera_uid,
    )

    if not roi_resultado.get("sucesso"):
        return roi_resultado

    roi = roi_resultado["roi"]

    resultado = analisar_area_selecionada(
        session_id=session_id,
        camera_uid=camera_uid,
        x1=roi["x1"],
        y1=roi["y1"],
        x2=roi["x2"],
        y2=roi["y2"],
        qualidade_jpeg=qualidade_jpeg,
    )

    if resultado.get("sucesso"):
        resultado["ambiente_id"] = ambiente_id

    return resultado


# ============================================================
# MAQUINÁRIO — PREPARAÇÃO / SELEÇÃO / PERSISTÊNCIA
# ============================================================

_ANALISES_MAQUINARIO: Dict[str, Dict[str, Any]] = {}
_ANALISES_MAQUINARIO_LOCK = threading.RLock()


def _ordenar_objetos_globais(
    objetos_globais: Dict[str, Dict[str, Any]],
) -> List[Dict[str, Any]]:
    objetos = [
        deepcopy(objeto)
        for objeto in (objetos_globais or {}).values()
        if isinstance(objeto, dict)
    ]

    objetos.sort(
        key=lambda item: (
            int(item.get("numero", 10**9)),
            str(item.get("id", "")),
        )
    )

    return objetos


def _analisar_camera_para_maquinario(
    ambiente_id: str,
    camera_uid: str,
    session_id: str,
    qualidade_jpeg: int = 90,
) -> Dict[str, Any]:
    """
    Analisa uma câmera usando SOMENTE a ROI já salva do ambiente.

    Retorna também o frame ROI em memória para associação visual entre câmeras.
    Esse frame não é persistido.
    """
    area = obter_area_monitoramento(
        ambiente_id=ambiente_id,
        camera_uid=camera_uid,
        session_id=session_id,
        qualidade_jpeg=qualidade_jpeg,
    )

    if not area.get("sucesso"):
        return area

    area_selecionada = area.get("area_selecionada") or {}

    frame_roi = _decodificar_jpeg_base64(
        area_selecionada.get("frame_base64")
    )

    if frame_roi is None:
        return {
            "sucesso": False,
            "erro": "AREA_MONITORAMENTO_NAO_DECODIFICADA",
            "camera_uid": camera_uid,
        }

    objetos = analisar_frame(
        frame_roi,
        camera_uid,
    )

    objetos_enriquecidos = _enriquecer_objetos_com_coordenadas_frame(
        objetos,
        area_selecionada.get("roi_pixels") or {},
    )

    frame_anotado = desenhar_objetos(
        frame_roi,
        objetos,
    )

    frame_anotado_base64 = _codificar_frame_jpeg_base64(
        frame_anotado,
        qualidade_jpeg=qualidade_jpeg,
    )

    if frame_anotado_base64 is None:
        return {
            "sucesso": False,
            "erro": "ERRO_CODIFICAR_ANALISE_AMBIENTE",
            "camera_uid": camera_uid,
        }

    return {
        "sucesso": True,
        "erro": None,
        "camera_uid": camera_uid,
        "session_id": session_id,
        "roi_normalizada": deepcopy(
            area_selecionada.get("roi_normalizada")
        ),
        "roi_pixels": deepcopy(
            area_selecionada.get("roi_pixels")
        ),
        "largura_area": area_selecionada.get("largura"),
        "altura_area": area_selecionada.get("altura"),
        "quantidade_objetos": len(objetos_enriquecidos),
        "objetos": objetos_enriquecidos,
        "imagem_analisada": {
            "mime_type": "image/jpeg",
            "frame_base64": frame_anotado_base64,
            "largura": area_selecionada.get("largura"),
            "altura": area_selecionada.get("altura"),
        },
        # Uso interno somente durante esta chamada.
        "_frame_roi": frame_roi,
    }


def preparar_selecao_maquinario(
    ambiente_id: str,
    sessoes_por_camera: Dict[str, str],
    qualidade_jpeg: int = 90,
) -> Dict[str, Any]:
    """
    Executa a análise das ROIs e prepara os objetos para a tela de Maquinário.

    Entrada:
        sessoes_por_camera = {
            "<camera_uid>": "<session_id>",
            ...
        }

    Pode receber uma ou várias câmeras.

    A função:
        1. valida se as câmeras pertencem ao ambiente;
        2. usa a ROI salva de cada câmera;
        3. roda FastSAM somente dentro da ROI;
        4. reutiliza objetos_globais.py para consolidar os objetos;
        5. cria uma análise temporária em memória;
        6. NÃO salva maquinário ainda.

    O usuário decide quais objetos são máquinas na etapa seguinte.
    """
    perfil = _buscar_perfil_por_id(ambiente_id)

    if perfil is None:
        return {
            "sucesso": False,
            "erro": "AMBIENTE_NAO_ENCONTRADO",
        }

    if not isinstance(sessoes_por_camera, dict) or not sessoes_por_camera:
        return {
            "sucesso": False,
            "erro": "SESSOES_CAMERA_OBRIGATORIAS",
        }

    cameras_perfil = {
        str(camera.get("camera_uid") or "").strip()
        for camera in perfil.get("cameras", [])
        if isinstance(camera, dict)
        and str(camera.get("camera_uid") or "").strip()
    }

    analises_publicas: Dict[str, Dict[str, Any]] = {}
    frames_originais = []
    objetos_por_camera: Dict[str, List[Dict[str, Any]]] = {}

    for camera_uid, session_id in sessoes_por_camera.items():
        camera_uid = str(camera_uid or "").strip()
        session_id = str(session_id or "").strip()

        if not camera_uid:
            return {
                "sucesso": False,
                "erro": "CAMERA_UID_OBRIGATORIO",
            }

        if camera_uid not in cameras_perfil:
            return {
                "sucesso": False,
                "erro": "CAMERA_NAO_VINCULADA_AO_AMBIENTE",
                "camera_uid": camera_uid,
            }

        if not session_id:
            return {
                "sucesso": False,
                "erro": "SESSION_ID_OBRIGATORIO",
                "camera_uid": camera_uid,
            }

        analise = _analisar_camera_para_maquinario(
            ambiente_id=ambiente_id,
            camera_uid=camera_uid,
            session_id=session_id,
            qualidade_jpeg=qualidade_jpeg,
        )

        if not analise.get("sucesso"):
            return {
                "sucesso": False,
                "erro": analise.get("erro") or "ERRO_ANALISE_CAMERA",
                "camera_uid": camera_uid,
                "detalhe": analise.get("detalhe"),
            }

        frame_roi = analise.pop("_frame_roi")

        objetos_camera = analise.get("objetos", [])
        objetos_por_camera[camera_uid] = objetos_camera

        camera_runtime = SimpleNamespace(
            camera_id=camera_uid,
            objetos=objetos_camera,
        )

        frames_originais.append(
            (camera_runtime, frame_roi)
        )

        analises_publicas[camera_uid] = deepcopy(analise)

    # Reutiliza integralmente a lógica existente de associação entre câmeras.
    objetos_globais_runtime = (
        objetos_globais_modulo.criar_objetos_globais(
            frames_originais
        )
    )

    objetos_para_salvar = (
        objetos_globais_modulo.preparar_objetos_para_salvar(
            objetos_globais_runtime
        )
    )

    # objetos_globais.py trabalha com o frame ROI.
    # Antes de persistir, convertemos as detecções para coordenadas
    # da imagem COMPLETA para manter compatibilidade com o monitoramento.
    for camera_uid, objetos_camera in objetos_por_camera.items():
        for objeto in objetos_camera:
            global_id = objeto.get("id_global")

            if not global_id or global_id not in objetos_para_salvar:
                continue

            bbox_frame = objeto.get("bbox_frame")
            bbox_roi = objeto.get("bbox_roi") or objeto.get("bbox")

            if isinstance(bbox_frame, list) and len(bbox_frame) == 4:
                objetos_para_salvar[global_id].setdefault(
                    "deteccoes",
                    {},
                )[str(camera_uid)] = [
                    int(valor)
                    for valor in bbox_frame
                ]

            # Informação extra apenas para a tela de configuração.
            objeto["bbox_roi"] = deepcopy(bbox_roi)

    analise_id = str(uuid.uuid4())

    with _ANALISES_MAQUINARIO_LOCK:
        _ANALISES_MAQUINARIO[analise_id] = {
            "analise_id": analise_id,
            "ambiente_id": ambiente_id,
            "objetos_globais": deepcopy(objetos_para_salvar),
            "cameras_analisadas": sorted(
                analises_publicas.keys()
            ),
        }

    return {
        "sucesso": True,
        "erro": None,
        "analise_id": analise_id,
        "ambiente_id": ambiente_id,
        "cameras_analisadas": sorted(
            analises_publicas.keys()
        ),
        "quantidade_objetos": len(objetos_para_salvar),
        "objetos": _ordenar_objetos_globais(
            objetos_para_salvar
        ),
        "analises_cameras": analises_publicas,
    }


def salvar_selecao_maquinario(
    ambiente_id: str,
    analise_id: str,
    ids_maquinario: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Salva a decisão humana sobre quais objetos detectados são maquinários.

    Todos os objetos selecionados recebem:
        maquinario = True

    Todos os demais objetos da MESMA análise recebem:
        maquinario = False

    Nenhum objeto é classificado automaticamente como máquina.
    """
    perfil = _buscar_perfil_por_id(ambiente_id)

    if perfil is None:
        return {
            "sucesso": False,
            "erro": "AMBIENTE_NAO_ENCONTRADO",
        }

    analise_id = str(analise_id or "").strip()

    if not analise_id:
        return {
            "sucesso": False,
            "erro": "ANALISE_ID_OBRIGATORIO",
        }

    with _ANALISES_MAQUINARIO_LOCK:
        analise = deepcopy(
            _ANALISES_MAQUINARIO.get(analise_id)
        )

    if analise is None:
        return {
            "sucesso": False,
            "erro": "ANALISE_MAQUINARIO_NAO_ENCONTRADA",
        }

    if analise.get("ambiente_id") != ambiente_id:
        return {
            "sucesso": False,
            "erro": "ANALISE_DE_OUTRO_AMBIENTE",
        }

    objetos = deepcopy(
        analise.get("objetos_globais") or {}
    )

    ids_existentes = set(objetos.keys())

    selecionados = {
        str(objeto_id or "").strip()
        for objeto_id in (ids_maquinario or [])
        if str(objeto_id or "").strip()
    }

    ids_invalidos = sorted(
        selecionados - ids_existentes
    )

    if ids_invalidos:
        return {
            "sucesso": False,
            "erro": "OBJETO_GLOBAL_NAO_ENCONTRADO",
            "ids_invalidos": ids_invalidos,
        }

    for global_id, objeto in objetos.items():
        objeto["maquinario"] = (
            global_id in selecionados
        )

    perfil["schema_version"] = ambientes.SCHEMA_VERSION
    perfil.setdefault("descricao", "")
    perfil.setdefault("rois", {})
    perfil["objetos_globais"] = objetos

    try:
        ambientes.salvar_perfil(perfil)
    except ValueError as erro:
        return {
            "sucesso": False,
            "erro": "PERFIL_AMBIENTE_INVALIDO",
            "detalhe": str(erro),
        }
    except Exception:
        return {
            "sucesso": False,
            "erro": "ERRO_SALVAR_AMBIENTE",
        }

    with _ANALISES_MAQUINARIO_LOCK:
        _ANALISES_MAQUINARIO.pop(
            analise_id,
            None,
        )

    return {
        "sucesso": True,
        "erro": None,
        "ambiente_id": ambiente_id,
        "quantidade_objetos": len(objetos),
        "quantidade_maquinarios": len(selecionados),
        "objetos": _ordenar_objetos_globais(objetos),
    }


def listar_objetos_ambiente(
    ambiente_id: str,
) -> Dict[str, Any]:
    """
    Lista os objetos persistidos no ambiente.
    """
    perfil = _buscar_perfil_por_id(ambiente_id)

    if perfil is None:
        return {
            "sucesso": False,
            "erro": "AMBIENTE_NAO_ENCONTRADO",
            "objetos": [],
            "quantidade": 0,
        }

    objetos_globais = perfil.get(
        "objetos_globais",
        {},
    )

    if not isinstance(objetos_globais, dict):
        objetos_globais = {}

    objetos = _ordenar_objetos_globais(
        objetos_globais
    )

    return {
        "sucesso": True,
        "erro": None,
        "ambiente_id": ambiente_id,
        "objetos": objetos,
        "quantidade": len(objetos),
    }


def listar_maquinarios_ambiente(
    ambiente_id: str,
) -> Dict[str, Any]:
    """
    Lista somente os objetos confirmados manualmente como maquinário.
    """
    resultado = listar_objetos_ambiente(
        ambiente_id
    )

    if not resultado.get("sucesso"):
        return resultado

    maquinarios = [
        objeto
        for objeto in resultado.get("objetos", [])
        if objeto.get("maquinario") is True
    ]

    return {
        "sucesso": True,
        "erro": None,
        "ambiente_id": ambiente_id,
        "maquinarios": maquinarios,
        "quantidade": len(maquinarios),
    }


def descartar_analise_maquinario(
    analise_id: str,
) -> Dict[str, Any]:
    """
    Descarta uma análise temporária sem alterar o ambiente.
    Usado quando o usuário cancelar/refizer a etapa de Maquinário.
    """
    analise_id = str(analise_id or "").strip()

    if not analise_id:
        return {
            "sucesso": False,
            "erro": "ANALISE_ID_OBRIGATORIO",
        }

    with _ANALISES_MAQUINARIO_LOCK:
        removida = _ANALISES_MAQUINARIO.pop(
            analise_id,
            None,
        )

    if removida is None:
        return {
            "sucesso": False,
            "erro": "ANALISE_MAQUINARIO_NAO_ENCONTRADA",
        }

    return {
        "sucesso": True,
        "erro": None,
        "analise_id": analise_id,
    }


# ============================================================
# ANÁLISE MULTI-FRAME DA ROI
# ============================================================
#
# Este bloco substitui, por sobrescrita das funções abaixo,
# somente a forma como o ambiente_service escolhe o frame
# usado na análise da ROI.
#
# NÃO altera:
# - analise_ambiente.py
# - FastSAM-s.pt
# - thresholds/filtros da detecção
# - objetos_globais.py
#
# Regra:
# - captura vários frames consecutivos;
# - aplica a mesma ROI em todos;
# - executa analisar_frame() exatamente como já existe;
# - escolhe o frame com MAIOR quantidade de objetos válidos;
# - mantém o restante do fluxo igual.
# ============================================================


def _normalizar_quantidade_frames(
    quantidade_frames: Any,
) -> int:
    """
    Mantém a análise multi-frame controlada.
    Padrão: 10 frames.
    Limite de segurança local: 1..10.
    """
    try:
        quantidade = int(quantidade_frames)
    except (TypeError, ValueError):
        quantidade = 10

    return max(1, min(10, quantidade))


def _analisar_multiplos_frames_roi(
    session_id: str,
    camera_uid: str,
    roi: Dict[str, Any],
    quantidade_frames: int = 10,
    qualidade_jpeg: int = 90,
    incluir_frame_interno: bool = False,
    frames_aquecimento: int = 3,
) -> Dict[str, Any]:
    """
    Descarta alguns frames iniciais da sessão já aberta, depois
    captura vários frames consecutivos, recorta a mesma ROI em cada
    frame e executa a detecção atual.

    Critério de escolha:
        maior quantidade de objetos válidos retornados por analisar_frame().

    Em empate, mantém o primeiro frame que atingiu aquela quantidade.
    """
    session_id = str(session_id or "").strip()
    camera_uid = str(camera_uid or "").strip()

    if not session_id:
        return {
            "sucesso": False,
            "erro": "SESSION_ID_OBRIGATORIO",
        }

    if not camera_uid:
        return {
            "sucesso": False,
            "erro": "CAMERA_UID_OBRIGATORIO",
        }

    validacao_roi = _validar_roi_em_memoria(roi)

    if not validacao_roi.get("sucesso"):
        return validacao_roi

    roi_normalizada = validacao_roi["roi"]
    quantidade = _normalizar_quantidade_frames(
        quantidade_frames
    )

    try:
        quantidade_aquecimento = int(frames_aquecimento)
    except (TypeError, ValueError):
        quantidade_aquecimento = 3

    quantidade_aquecimento = max(
        0,
        min(10, quantidade_aquecimento),
    )

    # Aquecimento da câmera:
    # descarta alguns frames iniciais sem executar FastSAM neles.
    # Isso reduz a chance de analisar frames imediatamente após abrir
    # a sessão, quando exposição/foco ainda podem estar se estabilizando.
    frames_aquecimento_descartados = 0
    erros_aquecimento: List[Dict[str, Any]] = []

    for indice_aquecimento in range(
        1,
        quantidade_aquecimento + 1,
    ):
        frame_aquecimento = obter_frame_preview(
            session_id
        )

        if frame_aquecimento.get("sucesso"):
            frames_aquecimento_descartados += 1
        else:
            erros_aquecimento.append({
                "frame_indice": indice_aquecimento,
                "erro": (
                    frame_aquecimento.get("erro")
                    or "ERRO_OBTER_FRAME_AQUECIMENTO"
                ),
            })

    melhor = None
    contagens_objetos: List[int] = []
    erros_frames: List[Dict[str, Any]] = []

    for indice in range(1, quantidade + 1):
        frame_preview = obter_frame_preview(
            session_id
        )

        if not frame_preview.get("sucesso"):
            contagens_objetos.append(0)
            erros_frames.append({
                "frame_indice": indice,
                "erro": (
                    frame_preview.get("erro")
                    or "ERRO_OBTER_FRAME_PREVIEW"
                ),
            })
            continue

        camera_preview = str(
            frame_preview.get("camera_uid") or ""
        ).strip()

        if camera_preview != camera_uid:
            return {
                "sucesso": False,
                "erro": "PREVIEW_DE_OUTRA_CAMERA",
                "camera_uid_esperado": camera_uid,
                "camera_uid_preview": camera_preview,
            }

        recorte = recortar_frame_por_roi(
            frame_base64=frame_preview.get(
                "frame_base64"
            ),
            roi=roi_normalizada,
            qualidade_jpeg=qualidade_jpeg,
        )

        if not recorte.get("sucesso"):
            contagens_objetos.append(0)
            erros_frames.append({
                "frame_indice": indice,
                "erro": (
                    recorte.get("erro")
                    or "ERRO_RECORTAR_ROI"
                ),
            })
            continue

        frame_roi = _decodificar_jpeg_base64(
            recorte.get("frame_base64")
        )

        if frame_roi is None:
            contagens_objetos.append(0)
            erros_frames.append({
                "frame_indice": indice,
                "erro": (
                    "AREA_MONITORAMENTO_NAO_DECODIFICADA"
                ),
            })
            continue

        # Usa exatamente a detecção atual do projeto.
        objetos = analisar_frame(
            frame_roi,
            camera_uid,
        )

        objetos_enriquecidos = (
            _enriquecer_objetos_com_coordenadas_frame(
                objetos,
                recorte.get("roi_pixels") or {},
            )
        )

        quantidade_objetos = len(
            objetos_enriquecidos
        )

        contagens_objetos.append(
            quantidade_objetos
        )

        candidato = {
            "frame_indice": indice,
            "frame_roi": frame_roi,
            "objetos_originais": objetos,
            "objetos": objetos_enriquecidos,
            "quantidade_objetos": quantidade_objetos,
            "roi_normalizada": deepcopy(
                recorte.get("roi_normalizada")
            ),
            "roi_pixels": deepcopy(
                recorte.get("roi_pixels")
            ),
            "largura_area": recorte.get("largura"),
            "altura_area": recorte.get("altura"),
        }

        if (
            melhor is None
            or quantidade_objetos
            > melhor["quantidade_objetos"]
        ):
            melhor = candidato

    if melhor is None:
        return {
            "sucesso": False,
            "erro": "NENHUM_FRAME_VALIDO_PARA_ANALISE",
            "camera_uid": camera_uid,
            "frames_solicitados": quantidade,
            "erros_frames": erros_frames,
        }

    frame_anotado = desenhar_objetos(
        melhor["frame_roi"],
        melhor["objetos_originais"],
    )

    frame_anotado_base64 = (
        _codificar_frame_jpeg_base64(
            frame_anotado,
            qualidade_jpeg=qualidade_jpeg,
        )
    )

    if frame_anotado_base64 is None:
        return {
            "sucesso": False,
            "erro": "ERRO_CODIFICAR_ANALISE_AMBIENTE",
            "camera_uid": camera_uid,
        }

    resultado = {
        "sucesso": True,
        "erro": None,
        "session_id": session_id,
        "camera_uid": camera_uid,
        "frames_aquecimento_solicitados": quantidade_aquecimento,
        "frames_aquecimento_descartados": frames_aquecimento_descartados,
        "frames_solicitados": quantidade,
        "frames_analisados": len(
            contagens_objetos
        ),
        "contagens_objetos_por_frame": (
            contagens_objetos
        ),
        "melhor_frame_indice": melhor[
            "frame_indice"
        ],
        "roi_normalizada": melhor[
            "roi_normalizada"
        ],
        "roi_pixels": melhor[
            "roi_pixels"
        ],
        "largura_area": melhor[
            "largura_area"
        ],
        "altura_area": melhor[
            "altura_area"
        ],
        "quantidade_objetos": melhor[
            "quantidade_objetos"
        ],
        "objetos": melhor["objetos"],
        "resumo_objetos": criar_resumo_objetos(
            melhor["objetos_originais"]
        ),
        "imagem_analisada": {
            "mime_type": "image/jpeg",
            "frame_base64": frame_anotado_base64,
            "largura": melhor["largura_area"],
            "altura": melhor["altura_area"],
        },
    }

    if erros_aquecimento:
        resultado["erros_aquecimento"] = (
            deepcopy(erros_aquecimento)
        )

    if erros_frames:
        resultado["erros_frames"] = (
            deepcopy(erros_frames)
        )

    if incluir_frame_interno:
        resultado["_frame_roi"] = melhor[
            "frame_roi"
        ]

    return resultado


def analisar_area_selecionada(
    session_id: str,
    camera_uid: str,
    x1: float,
    y1: float,
    x2: float,
    y2: float,
    qualidade_jpeg: int = 90,
    quantidade_frames: int = 10,
) -> Dict[str, Any]:
    """
    Analisa a ROI recém-selecionada usando vários frames consecutivos.

    A ROI NÃO é persistida por esta função.
    O FastSAM, seus thresholds e filtros permanecem inalterados.
    """
    roi = {
        "x1": x1,
        "y1": y1,
        "x2": x2,
        "y2": y2,
    }

    return _analisar_multiplos_frames_roi(
        session_id=session_id,
        camera_uid=camera_uid,
        roi=roi,
        quantidade_frames=quantidade_frames,
        qualidade_jpeg=qualidade_jpeg,
        incluir_frame_interno=False,
    )


def analisar_roi_salva(
    ambiente_id: str,
    camera_uid: str,
    session_id: str,
    qualidade_jpeg: int = 90,
    quantidade_frames: int = 10,
) -> Dict[str, Any]:
    """
    Analisa a ROI persistida do ambiente usando vários frames consecutivos.
    """
    roi_resultado = obter_roi(
        ambiente_id=ambiente_id,
        camera_uid=camera_uid,
    )

    if not roi_resultado.get("sucesso"):
        return roi_resultado

    resultado = _analisar_multiplos_frames_roi(
        session_id=session_id,
        camera_uid=camera_uid,
        roi=roi_resultado["roi"],
        quantidade_frames=quantidade_frames,
        qualidade_jpeg=qualidade_jpeg,
        incluir_frame_interno=False,
    )

    if resultado.get("sucesso"):
        resultado["ambiente_id"] = ambiente_id

    return resultado


def _analisar_camera_para_maquinario(
    ambiente_id: str,
    camera_uid: str,
    session_id: str,
    qualidade_jpeg: int = 90,
    quantidade_frames: int = 10,
) -> Dict[str, Any]:
    """
    Versão multi-frame usada pelo fluxo existente de Maquinário.

    A interface com preparar_selecao_maquinario() permanece compatível:
    a função continua devolvendo um único melhor frame ROI e os objetos
    correspondentes, apenas escolhidos entre vários frames consecutivos.
    """
    roi_resultado = obter_roi(
        ambiente_id=ambiente_id,
        camera_uid=camera_uid,
    )

    if not roi_resultado.get("sucesso"):
        return roi_resultado

    return _analisar_multiplos_frames_roi(
        session_id=session_id,
        camera_uid=camera_uid,
        roi=roi_resultado["roi"],
        quantidade_frames=quantidade_frames,
        qualidade_jpeg=qualidade_jpeg,
        incluir_frame_interno=True,
    )


# ============================================================
# EPIs DO AMBIENTE
# ============================================================

def listar_epis_disponiveis() -> Dict[str, Any]:
    """
    Retorna o catálogo oficial de EPIs definido em config.EPIS_DISPONIVEIS.

    Não altera config.py e não cria catálogo paralelo.
    """
    epis = [
        str(epi).strip()
        for epi in getattr(config, "EPIS_DISPONIVEIS", [])
        if str(epi).strip()
    ]

    return {
        "sucesso": True,
        "erro": None,
        "epis": epis,
        "quantidade": len(epis),
    }


def obter_epis_obrigatorios(
    ambiente_id: str,
) -> Dict[str, Any]:
    """
    Retorna os EPIs obrigatórios atualmente persistidos no ambiente.
    """
    perfil = _buscar_perfil_por_id(ambiente_id)

    if perfil is None:
        return {
            "sucesso": False,
            "erro": "AMBIENTE_NAO_ENCONTRADO",
            "epis_obrigatorios": [],
            "quantidade": 0,
        }

    epis = perfil.get("epis_obrigatorios", [])

    if not isinstance(epis, list):
        epis = []

    epis = [
        str(epi).strip()
        for epi in epis
        if str(epi).strip()
    ]

    return {
        "sucesso": True,
        "erro": None,
        "ambiente_id": ambiente_id,
        "epis_obrigatorios": epis,
        "quantidade": len(epis),
    }


def definir_epis_obrigatorios(
    ambiente_id: str,
    epis_obrigatorios: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Define a lista de EPIs obrigatórios do ambiente.

    Regras:
    - usa somente itens existentes em config.EPIS_DISPONIVEIS;
    - aceita lista vazia como escolha manual válida;
    - remove duplicados;
    - persiste os nomes canônicos do catálogo oficial;
    - não altera o estado 'calibrado' do ambiente.
    """
    perfil = _buscar_perfil_por_id(ambiente_id)

    if perfil is None:
        return {
            "sucesso": False,
            "erro": "AMBIENTE_NAO_ENCONTRADO",
        }

    if epis_obrigatorios is None:
        epis_obrigatorios = []

    if not isinstance(epis_obrigatorios, list):
        return {
            "sucesso": False,
            "erro": "EPIS_OBRIGATORIOS_INVALIDOS",
            "detalhe": "epis_obrigatorios deve ser uma lista.",
        }

    catalogo = [
        str(epi).strip()
        for epi in getattr(config, "EPIS_DISPONIVEIS", [])
        if str(epi).strip()
    ]

    catalogo_por_nome = {
        epi.casefold(): epi
        for epi in catalogo
    }

    selecionados: List[str] = []
    vistos = set()
    invalidos: List[str] = []

    for item in epis_obrigatorios:
        nome = str(item or "").strip()

        if not nome:
            continue

        canonico = catalogo_por_nome.get(
            nome.casefold()
        )

        if canonico is None:
            invalidos.append(nome)
            continue

        chave = canonico.casefold()

        if chave in vistos:
            continue

        vistos.add(chave)
        selecionados.append(canonico)

    if invalidos:
        return {
            "sucesso": False,
            "erro": "EPI_NAO_DISPONIVEL",
            "epis_invalidos": invalidos,
            "epis_disponiveis": catalogo,
        }

    perfil["schema_version"] = ambientes.SCHEMA_VERSION
    perfil.setdefault("descricao", "")
    perfil.setdefault("rois", {})
    perfil["epis_obrigatorios"] = selecionados

    try:
        ambientes.salvar_perfil(perfil)
    except ValueError as erro:
        return {
            "sucesso": False,
            "erro": "PERFIL_AMBIENTE_INVALIDO",
            "detalhe": str(erro),
        }
    except Exception:
        return {
            "sucesso": False,
            "erro": "ERRO_SALVAR_AMBIENTE",
        }

    return {
        "sucesso": True,
        "erro": None,
        "ambiente_id": ambiente_id,
        "epis_obrigatorios": deepcopy(selecionados),
        "quantidade": len(selecionados),
    }


# ============================================================
# COLABORADORES DO AMBIENTE
# ============================================================

def listar_colaboradores_para_ambiente() -> Dict[str, Any]:
    """
    Lista colaboradores existentes que podem ser vinculados ao ambiente.
    """
    return listar_colaboradores()


def obter_colaboradores_vinculados(
    ambiente_id: str,
) -> Dict[str, Any]:
    """
    Retorna os colaboradores vinculados ao ambiente,
    enriquecidos com nome/cargo atuais do cadastro.
    """
    perfil = _buscar_perfil_por_id(ambiente_id)

    if perfil is None:
        return {
            "sucesso": False,
            "erro": "AMBIENTE_NAO_ENCONTRADO",
            "colaboradores": [],
            "quantidade": 0,
        }

    matriculas = perfil.get(
        "colaboradores_vinculados",
        [],
    )

    if not isinstance(matriculas, list):
        matriculas = []

    colaboradores = []
    ausentes = []

    for matricula in matriculas:
        resultado = obter_colaborador(matricula)

        if resultado.get("sucesso"):
            colaboradores.append(
                resultado["colaborador"]
            )
        else:
            ausentes.append(
                str(matricula)
            )

    return {
        "sucesso": True,
        "erro": None,
        "ambiente_id": ambiente_id,
        "colaboradores": colaboradores,
        "quantidade": len(colaboradores),
        "matriculas_ausentes": ausentes,
    }


def definir_colaboradores_vinculados(
    ambiente_id: str,
    matriculas: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Substitui a lista de colaboradores vinculados ao ambiente.

    Regras:
    - somente matrículas já cadastradas podem ser vinculadas;
    - duplicados são removidos;
    - lista vazia é válida;
    - não altera nem apaga cadastro/biometria do colaborador.
    """
    perfil = _buscar_perfil_por_id(ambiente_id)

    if perfil is None:
        return {
            "sucesso": False,
            "erro": "AMBIENTE_NAO_ENCONTRADO",
        }

    if matriculas is None:
        matriculas = []

    if not isinstance(matriculas, list):
        return {
            "sucesso": False,
            "erro": "MATRICULAS_INVALIDAS",
        }

    normalizadas = []
    vistas = set()
    inexistentes = []

    for matricula in matriculas:
        matricula_normalizada = str(
            matricula or ""
        ).strip()

        if not matricula_normalizada:
            continue

        if matricula_normalizada in vistas:
            continue

        resultado = obter_colaborador(
            matricula_normalizada
        )

        if not resultado.get("sucesso"):
            inexistentes.append(
                matricula_normalizada
            )
            continue

        vistas.add(matricula_normalizada)
        normalizadas.append(
            matricula_normalizada
        )

    if inexistentes:
        return {
            "sucesso": False,
            "erro": "COLABORADOR_NAO_ENCONTRADO",
            "matriculas_inexistentes": inexistentes,
        }

    perfil["schema_version"] = ambientes.SCHEMA_VERSION
    perfil.setdefault("descricao", "")
    perfil.setdefault("rois", {})
    perfil["colaboradores_vinculados"] = normalizadas

    try:
        ambientes.salvar_perfil(perfil)
    except ValueError as erro:
        return {
            "sucesso": False,
            "erro": "PERFIL_AMBIENTE_INVALIDO",
            "detalhe": str(erro),
        }
    except Exception:
        return {
            "sucesso": False,
            "erro": "ERRO_SALVAR_AMBIENTE",
        }

    return {
        "sucesso": True,
        "erro": None,
        "ambiente_id": ambiente_id,
        "matriculas": list(normalizadas),
        "quantidade": len(normalizadas),
    }


def vincular_colaborador(
    ambiente_id: str,
    matricula: str,
) -> Dict[str, Any]:
    """
    Adiciona um colaborador ao ambiente sem apagar os vínculos atuais.
    """
    perfil = _buscar_perfil_por_id(ambiente_id)

    if perfil is None:
        return {
            "sucesso": False,
            "erro": "AMBIENTE_NAO_ENCONTRADO",
        }

    matricula = str(matricula or "").strip()

    if not matricula:
        return {
            "sucesso": False,
            "erro": "MATRICULA_OBRIGATORIA",
        }

    colaborador = obter_colaborador(matricula)

    if not colaborador.get("sucesso"):
        return {
            "sucesso": False,
            "erro": "COLABORADOR_NAO_ENCONTRADO",
            "matricula": matricula,
        }

    atuais = perfil.get(
        "colaboradores_vinculados",
        [],
    )

    if not isinstance(atuais, list):
        atuais = []

    if matricula not in atuais:
        atuais.append(matricula)

    return definir_colaboradores_vinculados(
        ambiente_id,
        atuais,
    )


def desvincular_colaborador(
    ambiente_id: str,
    matricula: str,
) -> Dict[str, Any]:
    """
    Remove somente o vínculo colaborador ↔ ambiente.
    Não remove CSV nem biometria.
    """
    perfil = _buscar_perfil_por_id(ambiente_id)

    if perfil is None:
        return {
            "sucesso": False,
            "erro": "AMBIENTE_NAO_ENCONTRADO",
        }

    matricula = str(matricula or "").strip()

    if not matricula:
        return {
            "sucesso": False,
            "erro": "MATRICULA_OBRIGATORIA",
        }

    atuais = perfil.get(
        "colaboradores_vinculados",
        [],
    )

    if not isinstance(atuais, list):
        atuais = []

    if matricula not in atuais:
        return {
            "sucesso": False,
            "erro": "COLABORADOR_NAO_VINCULADO",
            "matricula": matricula,
        }

    novos = [
        item
        for item in atuais
        if item != matricula
    ]

    return definir_colaboradores_vinculados(
        ambiente_id,
        novos,
    )


# ============================================================
# REVISÃO / FINALIZAÇÃO DO AMBIENTE
# ============================================================

def obter_revisao_ambiente(
    ambiente_id: str,
) -> Dict[str, Any]:
    """
    Monta o resumo final do cadastro do ambiente sem alterar dados.

    Compatibilidade:
    - ambientes legados (schema 1/2) já calibrados continuam válidos;
    - ausência de ROI nesses ambientes vira aviso, não pendência;
    - ambientes novos ou ainda não calibrados exigem ROI por câmera.
    """
    perfil = _buscar_perfil_por_id(ambiente_id)

    if perfil is None:
        return {
            "sucesso": False,
            "erro": "AMBIENTE_NAO_ENCONTRADO",
        }

    try:
        schema_version = int(perfil.get("schema_version", 1))
    except (TypeError, ValueError):
        schema_version = 1

    calibrado = bool(perfil.get("calibrado", False))
    legado_calibrado = schema_version < 3 and calibrado

    cameras = perfil.get("cameras", [])
    if not isinstance(cameras, list):
        cameras = []

    rois = perfil.get("rois", {})
    if not isinstance(rois, dict):
        rois = {}

    cameras_sem_roi = []

    for camera in cameras:
        if not isinstance(camera, dict):
            continue

        camera_uid = str(
            camera.get("camera_uid") or ""
        ).strip()

        if camera_uid and camera_uid not in rois:
            cameras_sem_roi.append({
                "camera_uid": camera_uid,
                "nome": camera.get("nome"),
            })

    objetos = perfil.get("objetos_globais", {})
    if not isinstance(objetos, dict):
        objetos = {}

    maquinarios = [
        deepcopy(objeto)
        for objeto in objetos.values()
        if isinstance(objeto, dict)
        and objeto.get("maquinario") is True
    ]

    epis = perfil.get("epis_obrigatorios", [])
    if not isinstance(epis, list):
        epis = []

    colaboradores_resultado = obter_colaboradores_vinculados(
        ambiente_id
    )

    colaboradores = (
        colaboradores_resultado.get(
            "colaboradores",
            [],
        )
        if colaboradores_resultado.get("sucesso")
        else []
    )

    pendencias = []
    avisos = []

    if not str(perfil.get("nome") or "").strip():
        pendencias.append("NOME_AMBIENTE_OBRIGATORIO")

    if cameras_sem_roi:
        if legado_calibrado:
            avisos.append("AMBIENTE_LEGADO_SEM_ROI")
        else:
            pendencias.append("ROI_PENDENTE")

    return {
        "sucesso": True,
        "erro": None,
        "ambiente_id": ambiente_id,
        "nome": perfil.get("nome"),
        "descricao": str(perfil.get("descricao") or ""),
        "foto_ambiente": str(
            perfil.get("foto_ambiente") or ""
        ),
        "possui_foto": bool(
            str(
                perfil.get("foto_ambiente")
                or ""
            ).strip()
        ),
        "schema_version": schema_version,
        "calibrado": calibrado,
        "legado_calibrado": legado_calibrado,
        "pronto_para_finalizar": len(pendencias) == 0,
        "pendencias": pendencias,
        "avisos": avisos,
        "resumo": {
            "quantidade_cameras": len(cameras),
            "quantidade_rois": len(rois),
            "quantidade_objetos": len(objetos),
            "quantidade_maquinarios": len(maquinarios),
            "quantidade_epis": len(epis),
            "quantidade_colaboradores": len(colaboradores),
        },
        "cameras": deepcopy(cameras),
        "rois": deepcopy(rois),
        "cameras_sem_roi": cameras_sem_roi,
        "maquinarios": maquinarios,
        "epis_obrigatorios": deepcopy(epis),
        "colaboradores": deepcopy(colaboradores),
        "matriculas_ausentes": (
            colaboradores_resultado.get(
                "matriculas_ausentes",
                [],
            )
            if colaboradores_resultado.get("sucesso")
            else []
        ),
    }


def finalizar_ambiente(
    ambiente_id: str,
) -> Dict[str, Any]:
    """
    Finaliza o cadastro do ambiente.

    Ambientes legados já calibrados não são migrados automaticamente.
    Ambientes novos exigem ROI para cada câmera vinculada.
    """
    revisao = obter_revisao_ambiente(
        ambiente_id
    )

    if not revisao.get("sucesso"):
        return revisao

    if not revisao.get("pronto_para_finalizar"):
        return {
            "sucesso": False,
            "erro": "AMBIENTE_COM_PENDENCIAS",
            "ambiente_id": ambiente_id,
            "pendencias": deepcopy(
                revisao.get("pendencias", [])
            ),
            "cameras_sem_roi": deepcopy(
                revisao.get("cameras_sem_roi", [])
            ),
        }

    if revisao.get("legado_calibrado"):
        return {
            "sucesso": True,
            "erro": None,
            "ambiente_id": ambiente_id,
            "nome": revisao.get("nome"),
            "calibrado": True,
            "ja_finalizado": True,
            "migrado": False,
            "revisao": revisao,
        }

    perfil = _buscar_perfil_por_id(ambiente_id)

    if perfil is None:
        return {
            "sucesso": False,
            "erro": "AMBIENTE_NAO_ENCONTRADO",
        }

    perfil["schema_version"] = ambientes.SCHEMA_VERSION
    perfil.setdefault("descricao", "")
    perfil.setdefault("rois", {})
    perfil.setdefault("colaboradores_vinculados", [])
    perfil.setdefault("foto_ambiente", "")
    perfil["calibrado"] = True

    try:
        ambientes.salvar_perfil(perfil)
    except ValueError as erro:
        return {
            "sucesso": False,
            "erro": "PERFIL_AMBIENTE_INVALIDO",
            "detalhe": str(erro),
        }
    except Exception:
        return {
            "sucesso": False,
            "erro": "ERRO_SALVAR_AMBIENTE",
        }

    return {
        "sucesso": True,
        "erro": None,
        "ambiente_id": ambiente_id,
        "nome": perfil.get("nome"),
        "calibrado": True,
        "ja_finalizado": False,
        "migrado": True,
        "revisao": obter_revisao_ambiente(
            ambiente_id
        ),
    }


# ============================================================
# CONSULTA DE AMBIENTES — CONTRATO PARA FRONTEND
# ============================================================

def _mapa_status_cameras() -> Dict[str, Dict[str, Any]]:
    resultado = listar_cameras_com_status()

    if not resultado.get("sucesso"):
        return {}

    return {
        str(item.get("camera_uid")): item
        for item in resultado.get("cameras", [])
        if isinstance(item, dict)
        and item.get("camera_uid")
    }


def _status_ambiente_com_mapa(
    perfil: Dict[str, Any],
    status_cameras: Dict[str, Dict[str, Any]],
) -> Dict[str, Any]:
    cameras = perfil.get("cameras", [])

    if not isinstance(cameras, list):
        cameras = []

    calibrado = bool(perfil.get("calibrado", False))
    detalhes_cameras = []

    for camera in cameras:
        if not isinstance(camera, dict):
            continue

        camera_uid = str(
            camera.get("camera_uid") or ""
        ).strip()

        status = status_cameras.get(camera_uid)

        detalhes_cameras.append({
            "camera_uid": camera_uid or None,
            "nome": camera.get("nome"),
            "tipo": camera.get("tipo"),
            "online": (
                bool(status.get("online"))
                if isinstance(status, dict)
                else False
            ),
            "status": (
                status.get("status", "OFFLINE")
                if isinstance(status, dict)
                else "OFFLINE"
            ),
            "motivo": (
                status.get("motivo")
                if isinstance(status, dict)
                else "STATUS_CAMERA_INDISPONIVEL"
            ),
        })

    if not calibrado:
        status_ambiente = "INATIVO"
        motivo = "AMBIENTE_NAO_FINALIZADO"
    elif not cameras:
        status_ambiente = "INATIVO"
        motivo = "SEM_CAMERAS_VINCULADAS"
    elif detalhes_cameras and all(
        item.get("online") is True
        for item in detalhes_cameras
    ):
        status_ambiente = "ATIVO"
        motivo = None
    else:
        status_ambiente = "COM_PROBLEMA"
        motivo = "CAMERA_OFFLINE_OU_INDISPONIVEL"

    return {
        "status": status_ambiente,
        "monitoramento_ativo": status_ambiente == "ATIVO",
        "com_problema": status_ambiente == "COM_PROBLEMA",
        "inativo": status_ambiente == "INATIVO",
        "motivo": motivo,
        "cameras": detalhes_cameras,
    }


def obter_status_ambiente(
    ambiente_id: str,
) -> Dict[str, Any]:
    perfil = _buscar_perfil_por_id(ambiente_id)

    if perfil is None:
        return {
            "sucesso": False,
            "erro": "AMBIENTE_NAO_ENCONTRADO",
        }

    status = _status_ambiente_com_mapa(
        perfil,
        _mapa_status_cameras(),
    )

    return {
        "sucesso": True,
        "erro": None,
        "ambiente_id": ambiente_id,
        "nome": perfil.get("nome"),
        **status,
    }


def atualizar_status_ambientes() -> Dict[str, Any]:
    """
    Recalcula o status atual de todos os ambientes.
    Não persiste status: é uma fotografia operacional do momento.
    """
    perfis = ambientes.listar_perfis()
    mapa = _mapa_status_cameras()

    itens = []

    for perfil in perfis:
        status = _status_ambiente_com_mapa(
            perfil,
            mapa,
        )

        itens.append({
            "ambiente_id": perfil.get("ambiente_id"),
            "nome": perfil.get("nome"),
            **status,
        })

    ativos = sum(
        1 for item in itens
        if item.get("status") == "ATIVO"
    )
    problemas = sum(
        1 for item in itens
        if item.get("status") == "COM_PROBLEMA"
    )
    inativos = sum(
        1 for item in itens
        if item.get("status") == "INATIVO"
    )

    return {
        "sucesso": True,
        "erro": None,
        "quantidade": len(itens),
        "monitoramento_ativo": ativos,
        "com_problema": problemas,
        "inativos": inativos,
        "ambientes": itens,
    }


def _resumo_consulta_ambiente(
    perfil: Dict[str, Any],
    status: Dict[str, Any],
    infracoes_hoje: int,
) -> Dict[str, Any]:
    cameras = perfil.get("cameras", [])
    if not isinstance(cameras, list):
        cameras = []

    objetos = perfil.get("objetos_globais", {})
    if not isinstance(objetos, dict):
        objetos = {}

    epis = perfil.get("epis_obrigatorios", [])
    if not isinstance(epis, list):
        epis = []

    colaboradores = perfil.get(
        "colaboradores_vinculados",
        [],
    )
    if not isinstance(colaboradores, list):
        colaboradores = []

    maquinarios = [
        objeto
        for objeto in objetos.values()
        if isinstance(objeto, dict)
        and objeto.get("maquinario") is True
    ]

    camera_principal = (
        deepcopy(cameras[0])
        if cameras and isinstance(cameras[0], dict)
        else None
    )

    return {
        "ambiente_id": perfil.get("ambiente_id"),
        "nome": perfil.get("nome"),
        "descricao": str(perfil.get("descricao") or ""),
        "foto_ambiente": str(
            perfil.get("foto_ambiente") or ""
        ),
        "possui_foto": bool(
            str(
                perfil.get("foto_ambiente")
                or ""
            ).strip()
        ),
        "schema_version": perfil.get("schema_version"),
        "calibrado": bool(perfil.get("calibrado", False)),
        "status": status.get("status"),
        "monitoramento_ativo": status.get(
            "monitoramento_ativo",
            False,
        ),
        "com_problema": status.get(
            "com_problema",
            False,
        ),
        "status_motivo": status.get("motivo"),
        "camera_principal": camera_principal,
        "quantidade_cameras": len(cameras),
        "quantidade_maquinarios": len(maquinarios),
        "quantidade_epis": len(epis),
        "quantidade_colaboradores": len(colaboradores),
        "infracoes_hoje": int(infracoes_hoje),
        "metadata": deepcopy(
            perfil.get("metadata") or {}
        ),
    }


def listar_ambientes_consulta(
    busca: Optional[str] = None,
    status: Optional[str] = None,
    camera_uid: Optional[str] = None,
    epi: Optional[str] = None,
    pagina: int = 1,
    por_pagina: int = 20,
    atualizar_status: bool = True,
) -> Dict[str, Any]:
    """
    Contrato completo da tabela "Consulta de Ambientes".

    Filtros suportados:
    - busca por nome do ambiente ou nome da câmera;
    - status;
    - camera_uid;
    - EPI obrigatório;
    - paginação.
    """
    perfis = ambientes.listar_perfis()

    mapa_status = (
        _mapa_status_cameras()
        if atualizar_status
        else {}
    )

    infracoes = contar_infracoes_hoje_por_ambiente()
    por_ambiente = (
        infracoes.get("por_ambiente", {})
        if infracoes.get("sucesso")
        else {}
    )

    busca_normalizada = str(
        busca or ""
    ).strip().casefold()

    status_normalizado = str(
        status or ""
    ).strip().upper()

    camera_uid_normalizado = str(
        camera_uid or ""
    ).strip()

    epi_normalizado = str(
        epi or ""
    ).strip().casefold()

    itens = []

    for perfil in perfis:
        status_atual = (
            _status_ambiente_com_mapa(
                perfil,
                mapa_status,
            )
            if atualizar_status
            else {
                "status": (
                    "ATIVO"
                    if perfil.get("calibrado")
                    else "INATIVO"
                ),
                "monitoramento_ativo": bool(
                    perfil.get("calibrado")
                ),
                "com_problema": False,
                "motivo": None,
            }
        )

        cameras = perfil.get("cameras", [])
        if not isinstance(cameras, list):
            cameras = []

        epis = perfil.get("epis_obrigatorios", [])
        if not isinstance(epis, list):
            epis = []

        if busca_normalizada:
            nomes_busca = [
                str(perfil.get("nome") or "")
            ] + [
                str(camera.get("nome") or "")
                for camera in cameras
                if isinstance(camera, dict)
            ]

            if not any(
                busca_normalizada in nome.casefold()
                for nome in nomes_busca
            ):
                continue

        if (
            status_normalizado
            and status_normalizado != "TODOS"
            and status_atual.get("status") != status_normalizado
        ):
            continue

        if camera_uid_normalizado:
            if not any(
                isinstance(camera, dict)
                and str(
                    camera.get("camera_uid") or ""
                ).strip() == camera_uid_normalizado
                for camera in cameras
            ):
                continue

        if epi_normalizado:
            if not any(
                str(item or "").strip().casefold()
                == epi_normalizado
                for item in epis
            ):
                continue

        ambiente_id = str(
            perfil.get("ambiente_id") or ""
        )

        itens.append(
            _resumo_consulta_ambiente(
                perfil,
                status_atual,
                por_ambiente.get(
                    ambiente_id,
                    0,
                ),
            )
        )

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

    total = len(itens)
    total_paginas = max(
        1,
        (total + por_pagina - 1) // por_pagina,
    )

    if pagina > total_paginas:
        pagina = total_paginas

    inicio = (pagina - 1) * por_pagina
    fim = inicio + por_pagina
    pagina_itens = itens[inicio:fim]

    ativos = sum(
        1 for item in itens
        if item.get("status") == "ATIVO"
    )
    problemas = sum(
        1 for item in itens
        if item.get("status") == "COM_PROBLEMA"
    )
    inativos = sum(
        1 for item in itens
        if item.get("status") == "INATIVO"
    )

    return {
        "sucesso": True,
        "erro": None,
        "resumo": {
            "ambientes_cadastrados": total,
            "monitoramento_ativo": ativos,
            "com_problema": problemas,
            "inativos": inativos,
        },
        "paginacao": {
            "pagina": pagina,
            "por_pagina": por_pagina,
            "total_itens": total,
            "total_paginas": total_paginas,
        },
        "ambientes": pagina_itens,
        "infracoes_fonte_disponivel": bool(
            infracoes.get("sucesso")
        ),
    }


def obter_detalhes_ambiente_consulta(
    ambiente_id: str,
    atualizar_status: bool = True,
) -> Dict[str, Any]:
    """
    Contrato do painel lateral "Detalhes do Ambiente".
    """
    perfil = _buscar_perfil_por_id(ambiente_id)

    if perfil is None:
        return {
            "sucesso": False,
            "erro": "AMBIENTE_NAO_ENCONTRADO",
        }

    status = (
        _status_ambiente_com_mapa(
            perfil,
            _mapa_status_cameras(),
        )
        if atualizar_status
        else {
            "status": (
                "ATIVO"
                if perfil.get("calibrado")
                else "INATIVO"
            ),
            "monitoramento_ativo": bool(
                perfil.get("calibrado")
            ),
            "com_problema": False,
            "motivo": None,
            "cameras": [],
        }
    )

    infracoes = contar_infracoes_hoje_por_ambiente(
        ambiente_id
    )

    objetos = perfil.get("objetos_globais", {})
    if not isinstance(objetos, dict):
        objetos = {}

    maquinarios = [
        deepcopy(objeto)
        for objeto in objetos.values()
        if isinstance(objeto, dict)
        and objeto.get("maquinario") is True
    ]

    colaboradores_resultado = (
        obter_colaboradores_vinculados(
            ambiente_id
        )
    )

    colaboradores = (
        colaboradores_resultado.get(
            "colaboradores",
            [],
        )
        if colaboradores_resultado.get("sucesso")
        else []
    )

    rois = perfil.get("rois", {})
    if not isinstance(rois, dict):
        rois = {}

    return {
        "sucesso": True,
        "erro": None,
        "ambiente_id": ambiente_id,
        "nome": perfil.get("nome"),
        "descricao": str(
            perfil.get("descricao") or ""
        ),
        "foto_ambiente": str(
            perfil.get("foto_ambiente") or ""
        ),
        "possui_foto": bool(
            str(
                perfil.get("foto_ambiente")
                or ""
            ).strip()
        ),
        "schema_version": perfil.get(
            "schema_version"
        ),
        "calibrado": bool(
            perfil.get("calibrado", False)
        ),
        "status": status.get("status"),
        "monitoramento_ativo": status.get(
            "monitoramento_ativo",
            False,
        ),
        "com_problema": status.get(
            "com_problema",
            False,
        ),
        "status_motivo": status.get("motivo"),
        "status_cameras": status.get(
            "cameras",
            [],
        ),
        "cameras": deepcopy(
            perfil.get("cameras") or []
        ),
        "rois": deepcopy(rois),
        "maquinarios": maquinarios,
        "epis_obrigatorios": deepcopy(
            perfil.get("epis_obrigatorios") or []
        ),
        "colaboradores": colaboradores,
        "quantidade_colaboradores": len(
            colaboradores
        ),
        "infracoes_hoje": (
            int(infracoes.get("quantidade", 0))
            if infracoes.get("sucesso")
            else 0
        ),
        "infracoes_fonte_disponivel": bool(
            infracoes.get("sucesso")
        ),
        "metadata": deepcopy(
            perfil.get("metadata") or {}
        ),
    }


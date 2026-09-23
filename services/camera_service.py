import base64
import json
import os
import socket
import tempfile
import threading
import uuid

from concurrent.futures import ThreadPoolExecutor, as_completed
from copy import deepcopy
from datetime import datetime
from typing import Any, Dict, List, Optional
from urllib.parse import quote, urlparse, urlunparse

import cv2

from camera_registry import (
    atualizar_nome_camera,
    enumerar_dispositivos_usb,
    listar_cameras as registry_listar_cameras,
    obter_camera as registry_obter_camera,
    obter_dispositivo_por_indice,
    registrar_rede_selecionada,
    registrar_usb_selecionada,
    remover_camera as registry_remover_camera,
    resolver_usb,
)

from ambientes import listar_perfis

from descobrir_cameras_wifi import (
    consolidar_candidatos,
    descobrir_onvif,
    descobrir_por_portas,
    obter_rede_padrao,
    testar_stream,
    tentar_rtsp_comum,
)


# ============================================================
# COMPATIBILIDADE COM O FLUXO LEGADO WIFI
# ============================================================

_RAIZ_PROJETO = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__),
        "..",
    )
)

_PASTA_CAMERA_WIFI = os.path.join(
    _RAIZ_PROJETO,
    "camera_wifi",
)

_PATH_CAMERAS_WIFI = os.path.join(
    _PASTA_CAMERA_WIFI,
    "cameras_wifi.json",
)


def _wifi_legado_vazio() -> Dict[str, Any]:
    return {
        "versao": 1,
        "atualizado_em": datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"
        ),
        "modo": "wifi",
        "cameras": [],
    }


def _carregar_wifi_legado() -> Dict[str, Any]:
    if not os.path.exists(_PATH_CAMERAS_WIFI):
        return _wifi_legado_vazio()

    try:
        with open(
            _PATH_CAMERAS_WIFI,
            "r",
            encoding="utf-8",
        ) as arquivo:
            dados = json.load(arquivo)
    except Exception:
        return _wifi_legado_vazio()

    if not isinstance(dados, dict):
        return _wifi_legado_vazio()

    cameras = dados.get("cameras")

    if not isinstance(cameras, list):
        cameras = []

    dados["versao"] = int(
        dados.get("versao")
        or 1
    )
    dados["modo"] = "wifi"
    dados["cameras"] = cameras

    return dados


def _salvar_wifi_legado(
    dados: Dict[str, Any],
) -> str:
    os.makedirs(
        _PASTA_CAMERA_WIFI,
        exist_ok=True,
    )

    dados_salvar = deepcopy(dados)

    dados_salvar["versao"] = int(
        dados_salvar.get("versao")
        or 1
    )
    dados_salvar["modo"] = "wifi"
    dados_salvar["atualizado_em"] = (
        datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"
        )
    )

    cameras = dados_salvar.get("cameras")
    if not isinstance(cameras, list):
        dados_salvar["cameras"] = []

    fd, temporario = tempfile.mkstemp(
        prefix=".cameras_wifi.",
        suffix=".tmp",
        dir=_PASTA_CAMERA_WIFI,
        text=True,
    )

    try:
        with os.fdopen(
            fd,
            "w",
            encoding="utf-8",
        ) as arquivo:
            json.dump(
                dados_salvar,
                arquivo,
                indent=4,
                ensure_ascii=False,
            )
            arquivo.flush()
            os.fsync(
                arquivo.fileno()
            )

        with open(
            temporario,
            "r",
            encoding="utf-8",
        ) as arquivo:
            json.load(arquivo)

        os.replace(
            temporario,
            _PATH_CAMERAS_WIFI,
        )

    except Exception:
        try:
            if os.path.exists(
                temporario
            ):
                os.remove(
                    temporario
                )
        except Exception:
            pass
        raise

    return _PATH_CAMERAS_WIFI


def _sincronizar_camera_rede_wifi_legado(
    nome: str,
    fonte: str,
    onvif: bool = False,
    portas_detectadas: Optional[List[int]] = None,
) -> str:
    """
    Mantém camera_wifi/cameras_wifi.json sincronizado porque
    o fluxo atual do main/config ainda depende desse arquivo.

    O registry continua sendo a identidade principal.
    """
    fonte = str(
        fonte
        or ""
    ).strip()

    if not fonte:
        raise ValueError(
            "URL_STREAM_OBRIGATORIA"
        )

    parsed = urlparse(
        fonte
    )

    dados = _carregar_wifi_legado()

    cameras = [
        item
        for item in (
            dados.get("cameras")
            or []
        )
        if isinstance(item, dict)
    ]

    existente = None

    for item in cameras:
        if str(
            item.get("fonte")
            or ""
        ).strip() == fonte:
            existente = item
            break

    if existente is None:
        existente = {}
        cameras.append(
            existente
        )

    # Preserva resolução/FPS antigos, quando já existirem.
    resolucao_existente = deepcopy(
        existente.get("resolucao")
    )
    fps_existente = existente.get(
        "fps"
    )

    existente.clear()
    existente.update(
        {
            "nome": str(
                nome
                or "Camera"
            ).strip(),
            "tipo": (
                str(
                    parsed.scheme
                    or "wifi"
                ).lower()
            ),
            "fonte": fonte,
            "ip": parsed.hostname,
            "ativa": True,
            "onvif": bool(
                onvif
            ),
            "portas_detectadas": [
                int(porta)
                for porta in (
                    portas_detectadas
                    or []
                )
                if isinstance(
                    porta,
                    int,
                )
                or str(
                    porta
                ).isdigit()
            ],
            "resolucao": (
                resolucao_existente
                if isinstance(
                    resolucao_existente,
                    dict,
                )
                else None
            ),
            "fps": fps_existente,
        }
    )

    dados["cameras"] = cameras

    return _salvar_wifi_legado(
        dados
    )


def _remover_camera_rede_wifi_legado(
    fonte: str,
) -> str:
    fonte = str(
        fonte
        or ""
    ).strip()

    dados = _carregar_wifi_legado()

    cameras = (
        dados.get("cameras")
        or []
    )

    dados["cameras"] = [
        item
        for item in cameras
        if not (
            isinstance(item, dict)
            and str(
                item.get("fonte")
                or ""
            ).strip() == fonte
        )
    ]

    return _salvar_wifi_legado(
        dados
    )


# ============================================================
# CONFIGURAÇÕES INTERNAS
# ============================================================

_TIMEOUT_STATUS_MS = 3000
_TIMEOUT_SOCKET_SEGUNDOS = 0.8

_PREVIEWS: Dict[str, Dict[str, Any]] = {}
_PREVIEWS_LOCK = threading.RLock()


# ============================================================
# UTILITÁRIOS
# ============================================================

def _aplicar_credenciais_url(
    url: str,
    usuario: Optional[str] = None,
    senha: Optional[str] = None,
) -> str:
    if not usuario:
        return url

    parsed = urlparse(url)

    if not parsed.hostname:
        return url

    usuario_encoded = quote(str(usuario), safe="")
    senha_encoded = quote(str(senha or ""), safe="")

    host = parsed.hostname

    if parsed.port:
        host = f"{host}:{parsed.port}"

    netloc = f"{usuario_encoded}:{senha_encoded}@{host}"

    return urlunparse(
        (
            parsed.scheme,
            netloc,
            parsed.path,
            parsed.params,
            parsed.query,
            parsed.fragment,
        )
    )


def _normalizar_fps(valor) -> Optional[float]:
    try:
        fps = float(valor)
    except (TypeError, ValueError):
        return None

    if fps <= 0 or fps > 240:
        return None

    return round(fps, 2)


def _porta_padrao(parsed) -> Optional[int]:
    if parsed.port:
        return int(parsed.port)

    esquema = str(parsed.scheme or "").lower()

    if esquema == "rtsp":
        return 554
    if esquema == "http":
        return 80
    if esquema == "https":
        return 443

    return None


def _porta_acessivel(
    host: Optional[str],
    porta: Optional[int],
    timeout: float = _TIMEOUT_SOCKET_SEGUNDOS,
) -> bool:
    if not host or not porta:
        return True

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(timeout)

    try:
        return sock.connect_ex((str(host), int(porta))) == 0
    except Exception:
        return False
    finally:
        try:
            sock.close()
        except Exception:
            pass


def _abrir_video_capture_rede(
    fonte: str,
    timeout_ms: int = _TIMEOUT_STATUS_MS,
):
    cap = None

    try:
        timeout = max(250, int(timeout_ms))
    except (TypeError, ValueError):
        timeout = _TIMEOUT_STATUS_MS

    parametros = []

    if hasattr(cv2, "CAP_PROP_OPEN_TIMEOUT_MSEC"):
        parametros.extend(
            [cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, timeout]
        )

    if hasattr(cv2, "CAP_PROP_READ_TIMEOUT_MSEC"):
        parametros.extend(
            [cv2.CAP_PROP_READ_TIMEOUT_MSEC, timeout]
        )

    if parametros and hasattr(cv2, "CAP_FFMPEG"):
        try:
            cap = cv2.VideoCapture(
                fonte,
                cv2.CAP_FFMPEG,
                parametros,
            )
        except Exception:
            cap = None

    if cap is None or not cap.isOpened():
        if cap is not None:
            try:
                cap.release()
            except Exception:
                pass

        try:
            if hasattr(cv2, "CAP_FFMPEG"):
                cap = cv2.VideoCapture(
                    fonte,
                    cv2.CAP_FFMPEG,
                )
            else:
                cap = cv2.VideoCapture(fonte)
        except Exception:
            cap = None

    if cap is not None:
        try:
            if hasattr(cv2, "CAP_PROP_OPEN_TIMEOUT_MSEC"):
                cap.set(
                    cv2.CAP_PROP_OPEN_TIMEOUT_MSEC,
                    timeout,
                )
            if hasattr(cv2, "CAP_PROP_READ_TIMEOUT_MSEC"):
                cap.set(
                    cv2.CAP_PROP_READ_TIMEOUT_MSEC,
                    timeout,
                )
            if hasattr(cv2, "CAP_PROP_BUFFERSIZE"):
                # Nem todo backend OpenCV/FFmpeg respeita este valor,
                # mas quando suportado reduz o buffer interno do stream.
                cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        except Exception:
            pass

    return cap


def _resolver_fonte_preview(
    camera: Dict[str, Any],
) -> Dict[str, Any]:
    tipo = str(camera.get("tipo") or "").strip().lower()

    if tipo == "usb":
        dispositivos = enumerar_dispositivos_usb()
        resolucao = resolver_usb(
            camera,
            dispositivos=dispositivos,
        )

        if (
            resolucao.get("status_identidade") != "IDENTIFICADA"
            or resolucao.get("indice_runtime") is None
        ):
            return {
                "sucesso": False,
                "erro": "CAMERA_USB_NAO_RESOLVIDA",
                "resolucao": resolucao,
            }

        return {
            "sucesso": True,
            "erro": None,
            "tipo": "usb",
            "fonte": int(resolucao["indice_runtime"]),
            "resolucao_identidade": resolucao,
        }

    conexao = camera.get("conexao") or {}
    fonte = str(conexao.get("fonte") or "").strip()

    if not fonte:
        return {
            "sucesso": False,
            "erro": "FONTE_CAMERA_NAO_CONFIGURADA",
        }

    return {
        "sucesso": True,
        "erro": None,
        "tipo": tipo or "rede",
        "fonte": fonte,
    }


def _abrir_capture_preview(
    camera: Dict[str, Any],
    timeout_ms: int,
):
    fonte_resultado = _resolver_fonte_preview(camera)

    if not fonte_resultado.get("sucesso"):
        return fonte_resultado

    tipo = fonte_resultado["tipo"]
    fonte = fonte_resultado["fonte"]

    cap = None

    try:
        if tipo == "usb":
            cap = cv2.VideoCapture(
                int(fonte),
                cv2.CAP_DSHOW,
            )
        else:
            parsed = urlparse(str(fonte))
            porta = _porta_padrao(parsed)

            if not _porta_acessivel(
                parsed.hostname,
                porta,
            ):
                return {
                    "sucesso": False,
                    "erro": "STREAM_INDISPONIVEL",
                }

            cap = _abrir_video_capture_rede(
                str(fonte),
                timeout_ms=timeout_ms,
            )

        if cap is None or not cap.isOpened():
            if cap is not None:
                cap.release()

            return {
                "sucesso": False,
                "erro": "CAMERA_INDISPONIVEL",
            }

        ret, frame = cap.read()

        if not ret or frame is None or frame.size == 0:
            cap.release()
            return {
                "sucesso": False,
                "erro": "FRAME_NAO_RECEBIDO",
            }

        altura, largura = frame.shape[:2]

        return {
            "sucesso": True,
            "erro": None,
            "cap": cap,
            "tipo": tipo,
            "fonte": fonte,
            "frame_inicial": frame,
            "largura": int(largura),
            "altura": int(altura),
            "fps": _normalizar_fps(
                cap.get(cv2.CAP_PROP_FPS)
            ),
        }

    except Exception:
        if cap is not None:
            try:
                cap.release()
            except Exception:
                pass

        return {
            "sucesso": False,
            "erro": "ERRO_ABRIR_CAMERA",
        }


def _encodar_jpeg_base64(
    frame,
    qualidade_jpeg: int,
) -> Optional[str]:
    try:
        qualidade = int(qualidade_jpeg)
    except (TypeError, ValueError):
        qualidade = 80

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


# ============================================================
# CÂMERAS DE REDE / WIFI
# ============================================================

def buscar_cameras() -> Dict[str, Any]:
    rede = obter_rede_padrao()

    if rede is None:
        return {
            "sucesso": False,
            "erro": "REDE_LOCAL_NAO_IDENTIFICADA",
            "cameras": [],
        }

    encontrados_onvif = descobrir_onvif()
    encontrados_portas = descobrir_por_portas(rede)

    candidatos = consolidar_candidatos(
        encontrados_onvif,
        encontrados_portas,
    )

    return {
        "sucesso": True,
        "erro": None,
        "rede": str(rede),
        "quantidade": len(candidatos),
        "cameras": candidatos,
    }


def testar_camera_manual(
    url: str,
    usuario: Optional[str] = None,
    senha: Optional[str] = None,
) -> Dict[str, Any]:
    if not url or not url.strip():
        return {
            "sucesso": False,
            "erro": "URL_STREAM_OBRIGATORIA",
        }

    url_final = _aplicar_credenciais_url(
        url.strip(),
        usuario,
        senha,
    )

    dados = testar_stream(url_final)

    if dados is None:
        return {
            "sucesso": False,
            "erro": "STREAM_INDISPONIVEL",
        }

    parsed = urlparse(url_final)

    return {
        "sucesso": True,
        "erro": None,
        "fonte": url_final,
        "ip": parsed.hostname,
        "porta": parsed.port,
        "protocolo": parsed.scheme.lower(),
        "largura": dados.get("largura"),
        "altura": dados.get("altura"),
        "fps": dados.get("fps"),
    }


def testar_camera_descoberta(
    candidato: Dict[str, Any],
    usuario: Optional[str] = None,
    senha: Optional[str] = None,
) -> Dict[str, Any]:
    ip = candidato.get("ip")
    portas = candidato.get("portas", [])

    if not ip:
        return {
            "sucesso": False,
            "erro": "IP_CAMERA_INVALIDO",
        }

    stream = tentar_rtsp_comum(
        ip,
        portas,
        usuario=usuario or None,
        senha=senha or None,
    )

    if stream is None:
        return {
            "sucesso": False,
            "erro": "STREAM_NAO_DESCOBERTO",
        }

    return {
        "sucesso": True,
        "erro": None,
        "fonte": stream.get("url"),
        "largura": stream.get("largura"),
        "altura": stream.get("altura"),
        "fps": stream.get("fps"),
    }


def cadastrar_camera_rede(
    nome: str,
    fonte: str,
    onvif: bool = False,
    portas_detectadas: Optional[List[int]] = None,
    camera_uid: Optional[str] = None,
) -> Dict[str, Any]:
    if not nome or not nome.strip():
        return {
            "sucesso": False,
            "erro": "NOME_CAMERA_OBRIGATORIO",
        }

    if not fonte or not fonte.strip():
        return {
            "sucesso": False,
            "erro": "URL_STREAM_OBRIGATORIA",
        }

    parsed = urlparse(fonte)

    dados_config = {
        "tipo": parsed.scheme.lower() or "wifi",
        "fonte": fonte,
        "ip": parsed.hostname,
        "porta": parsed.port,
        "onvif": bool(onvif),
        "portas_detectadas": deepcopy(
            portas_detectadas or []
        ),
    }

    camera = registrar_rede_selecionada(
        dados_config=dados_config,
        nome=nome.strip(),
        camera_uid=camera_uid,
    )

    try:
        caminho_wifi = _sincronizar_camera_rede_wifi_legado(
            nome=nome.strip(),
            fonte=fonte,
            onvif=bool(onvif),
            portas_detectadas=portas_detectadas,
        )
    except Exception as erro:
        return {
            "sucesso": False,
            "erro": "ERRO_SINCRONIZAR_CAMERA_WIFI",
            "detalhe": str(erro),
            "camera": camera,
        }

    return {
        "sucesso": True,
        "erro": None,
        "camera": camera,
        "camera_wifi_path": caminho_wifi,
    }


def editar_camera_rede(
    camera_uid: str,
    nome: str,
    fonte: str,
    onvif: Optional[bool] = None,
) -> Dict[str, Any]:
    camera_atual = registry_obter_camera(camera_uid)

    fonte_antiga = ""
    if isinstance(camera_atual, dict):
        fonte_antiga = str(
            (camera_atual.get("conexao") or {}).get("fonte")
            or ""
        ).strip()

    if camera_atual is None:
        return {
            "sucesso": False,
            "erro": "CAMERA_NAO_ENCONTRADA",
            "camera": None,
        }

    if str(camera_atual.get("tipo", "")).lower() == "usb":
        return {
            "sucesso": False,
            "erro": "CAMERA_NAO_E_REDE",
            "camera": None,
        }

    nome = str(nome or "").strip()
    fonte = str(fonte or "").strip()

    if not nome:
        return {
            "sucesso": False,
            "erro": "NOME_CAMERA_OBRIGATORIO",
            "camera": None,
        }

    if not fonte:
        return {
            "sucesso": False,
            "erro": "URL_STREAM_OBRIGATORIA",
            "camera": None,
        }

    parsed = urlparse(fonte)
    conexao_atual = camera_atual.get("conexao") or {}
    compatibilidade = camera_atual.get(
        "compatibilidade"
    ) or {}

    dados_config = {
        "tipo": parsed.scheme.lower()
        or str(camera_atual.get("tipo", "wifi")).lower(),
        "fonte": fonte,
        "ip": parsed.hostname,
        "porta": parsed.port,
        "onvif": (
            bool(conexao_atual.get("onvif", False))
            if onvif is None
            else bool(onvif)
        ),
        "resolucao": deepcopy(
            conexao_atual.get("resolucao")
        ),
        "fps": conexao_atual.get("fps"),
    }

    camera = registrar_rede_selecionada(
        dados_config=dados_config,
        nome=nome,
        camera_uid=camera_uid,
        config_index_legado=compatibilidade.get(
            "config_index_legado"
        ),
    )

    try:
        if (
            fonte_antiga
            and fonte_antiga != fonte
        ):
            _remover_camera_rede_wifi_legado(
                fonte_antiga
            )

        caminho_wifi = _sincronizar_camera_rede_wifi_legado(
            nome=nome,
            fonte=fonte,
            onvif=bool(
                dados_config.get(
                    "onvif",
                    False,
                )
            ),
            portas_detectadas=(
                [parsed.port]
                if parsed.port is not None
                else []
            ),
        )
    except Exception as erro:
        return {
            "sucesso": False,
            "erro": "ERRO_SINCRONIZAR_CAMERA_WIFI",
            "detalhe": str(erro),
            "camera": camera,
        }

    return {
        "sucesso": True,
        "erro": None,
        "camera": camera,
        "camera_wifi_path": caminho_wifi,
    }


# ============================================================
# CÂMERAS USB / EMBUTIDA
# ============================================================

def buscar_cameras_usb() -> Dict[str, Any]:
    dispositivos = enumerar_dispositivos_usb()

    return {
        "sucesso": True,
        "erro": None,
        "quantidade": len(dispositivos),
        "cameras": dispositivos,
    }


def testar_camera_usb(
    indice: int,
) -> Dict[str, Any]:
    dispositivos = enumerar_dispositivos_usb()

    dispositivo = obter_dispositivo_por_indice(
        indice,
        dispositivos,
    )

    if dispositivo is None:
        return {
            "sucesso": False,
            "erro": "CAMERA_USB_NAO_ENCONTRADA",
            "indice": indice,
        }

    cap = None

    try:
        cap = cv2.VideoCapture(
            int(indice),
            cv2.CAP_DSHOW,
        )

        if not cap.isOpened():
            return {
                "sucesso": False,
                "erro": "CAMERA_USB_INDISPONIVEL",
                "indice": indice,
            }

        ret, frame = cap.read()

        if not ret or frame is None or frame.size == 0:
            return {
                "sucesso": False,
                "erro": "FRAME_USB_NAO_RECEBIDO",
                "indice": indice,
            }

        altura, largura = frame.shape[:2]

        return {
            "sucesso": True,
            "erro": None,
            "indice": int(indice),
            "nome_dispositivo": dispositivo.get(
                "nome_dispositivo"
            ),
            "largura": int(largura),
            "altura": int(altura),
            "fps": _normalizar_fps(
                cap.get(cv2.CAP_PROP_FPS)
            ),
        }

    except Exception:
        return {
            "sucesso": False,
            "erro": "ERRO_TESTE_CAMERA_USB",
            "indice": indice,
        }

    finally:
        if cap is not None:
            try:
                cap.release()
            except Exception:
                pass


def cadastrar_camera_usb(
    indice: int,
    nome: str,
    camera_uid: Optional[str] = None,
) -> Dict[str, Any]:
    if not nome or not nome.strip():
        return {
            "sucesso": False,
            "erro": "NOME_CAMERA_OBRIGATORIO",
        }

    dispositivos = enumerar_dispositivos_usb()

    dispositivo = obter_dispositivo_por_indice(
        indice,
        dispositivos,
    )

    if dispositivo is None:
        return {
            "sucesso": False,
            "erro": "CAMERA_USB_NAO_ENCONTRADA",
        }

    camera = registrar_usb_selecionada(
        indice=indice,
        nome=nome.strip(),
        dispositivos=dispositivos,
        camera_uid=camera_uid,
    )

    return {
        "sucesso": True,
        "erro": None,
        "camera": camera,
    }


def resolver_camera_usb(
    camera_uid: str,
) -> Dict[str, Any]:
    camera = registry_obter_camera(camera_uid)

    if camera is None:
        return {
            "sucesso": False,
            "erro": "CAMERA_NAO_ENCONTRADA",
        }

    if str(camera.get("tipo", "")).lower() != "usb":
        return {
            "sucesso": False,
            "erro": "CAMERA_NAO_E_USB",
        }

    dispositivos = enumerar_dispositivos_usb()

    resultado = resolver_usb(
        camera,
        dispositivos=dispositivos,
    )

    return {
        "sucesso": True,
        "erro": None,
        "resolucao": resultado,
    }


def editar_camera_usb(
    camera_uid: str,
    nome: str,
) -> Dict[str, Any]:
    camera_atual = registry_obter_camera(camera_uid)

    if camera_atual is None:
        return {
            "sucesso": False,
            "erro": "CAMERA_NAO_ENCONTRADA",
            "camera": None,
        }

    if str(camera_atual.get("tipo", "")).lower() != "usb":
        return {
            "sucesso": False,
            "erro": "CAMERA_NAO_E_USB",
            "camera": None,
        }

    nome = str(nome or "").strip()

    if not nome:
        return {
            "sucesso": False,
            "erro": "NOME_CAMERA_OBRIGATORIO",
            "camera": None,
        }

    camera = atualizar_nome_camera(
        camera_uid=camera_uid,
        nome=nome,
    )

    if camera is None:
        return {
            "sucesso": False,
            "erro": "CAMERA_NAO_ENCONTRADA",
            "camera": None,
        }

    return {
        "sucesso": True,
        "erro": None,
        "camera": camera,
    }


# ============================================================
# CONSULTA / REMOÇÃO
# ============================================================

def listar_cameras(
    tipo: Optional[str] = None,
) -> Dict[str, Any]:
    cameras = registry_listar_cameras(tipo)

    return {
        "sucesso": True,
        "erro": None,
        "quantidade": len(cameras),
        "cameras": cameras,
    }


def obter_camera(
    camera_uid: str,
) -> Dict[str, Any]:
    camera = registry_obter_camera(camera_uid)

    if camera is None:
        return {
            "sucesso": False,
            "erro": "CAMERA_NAO_ENCONTRADA",
            "camera": None,
        }

    return {
        "sucesso": True,
        "erro": None,
        "camera": deepcopy(camera),
    }


def verificar_vinculos_camera(
    camera_uid: str,
) -> Dict[str, Any]:
    camera = registry_obter_camera(camera_uid)

    if camera is None:
        return {
            "sucesso": False,
            "erro": "CAMERA_NAO_ENCONTRADA",
            "vinculada": False,
            "ambientes": [],
        }

    ambientes_vinculados: List[Dict[str, Any]] = []

    for perfil in listar_perfis():
        cameras = perfil.get("cameras", [])

        if not isinstance(cameras, list):
            continue

        vinculada = any(
            isinstance(item, dict)
            and item.get("camera_uid") == camera_uid
            for item in cameras
        )

        if vinculada:
            ambientes_vinculados.append({
                "ambiente_id": perfil.get("ambiente_id"),
                "nome": perfil.get("nome"),
            })

    return {
        "sucesso": True,
        "erro": None,
        "vinculada": bool(ambientes_vinculados),
        "quantidade_ambientes": len(
            ambientes_vinculados
        ),
        "ambientes": ambientes_vinculados,
    }


def remover_camera(
    camera_uid: str,
) -> Dict[str, Any]:
    camera = registry_obter_camera(camera_uid)

    fonte_rede = ""
    if isinstance(camera, dict):
        tipo_camera = str(
            camera.get("tipo")
            or ""
        ).strip().lower()

        if tipo_camera != "usb":
            fonte_rede = str(
                (camera.get("conexao") or {}).get("fonte")
                or ""
            ).strip()

    if camera is None:
        return {
            "sucesso": False,
            "erro": "CAMERA_NAO_ENCONTRADA",
        }

    vinculos = verificar_vinculos_camera(camera_uid)

    if not vinculos.get("sucesso"):
        return vinculos

    if vinculos.get("vinculada"):
        return {
            "sucesso": False,
            "erro": "CAMERA_VINCULADA_A_AMBIENTE",
            "ambientes": vinculos.get(
                "ambientes",
                [],
            ),
        }

    removida = registry_remover_camera(camera_uid)

    if not removida:
        return {
            "sucesso": False,
            "erro": "CAMERA_NAO_ENCONTRADA",
        }

    caminho_wifi = None

    if fonte_rede:
        try:
            caminho_wifi = _remover_camera_rede_wifi_legado(
                fonte_rede
            )
        except Exception as erro:
            return {
                "sucesso": False,
                "erro": "ERRO_SINCRONIZAR_CAMERA_WIFI",
                "detalhe": str(erro),
                "camera_uid": camera_uid,
            }

    return {
        "sucesso": True,
        "erro": None,
        "camera_uid": camera_uid,
        "camera_wifi_path": caminho_wifi,
    }


# ============================================================
# STATUS ONLINE / OFFLINE
# ============================================================

def obter_status_camera(
    camera_uid: str,
) -> Dict[str, Any]:
    camera = registry_obter_camera(camera_uid)

    if camera is None:
        return {
            "sucesso": False,
            "erro": "CAMERA_NAO_ENCONTRADA",
            "camera_uid": camera_uid,
            "online": False,
            "status": "OFFLINE",
        }

    tipo = str(camera.get("tipo", "")).strip().lower()

    if tipo == "usb":
        resolucao = resolver_camera_usb(camera_uid)

        if not resolucao.get("sucesso"):
            return {
                "sucesso": True,
                "erro": None,
                "camera_uid": camera_uid,
                "nome": camera.get("nome"),
                "tipo": tipo,
                "online": False,
                "status": "OFFLINE",
                "motivo": resolucao.get("erro"),
            }

        identidade = resolucao.get("resolucao") or {}
        status_identidade = identidade.get(
            "status_identidade"
        )
        indice_runtime = identidade.get(
            "indice_runtime"
        )

        if (
            status_identidade != "IDENTIFICADA"
            or indice_runtime is None
        ):
            return {
                "sucesso": True,
                "erro": None,
                "camera_uid": camera_uid,
                "nome": camera.get("nome"),
                "tipo": tipo,
                "online": False,
                "status": "OFFLINE",
                "status_identidade": status_identidade,
                "confianca": identidade.get("confianca"),
                "motivo": identidade.get("motivo"),
            }

        teste = testar_camera_usb(
            int(indice_runtime)
        )

        if not teste.get("sucesso"):
            return {
                "sucesso": True,
                "erro": None,
                "camera_uid": camera_uid,
                "nome": camera.get("nome"),
                "tipo": tipo,
                "online": False,
                "status": "OFFLINE",
                "indice_runtime": indice_runtime,
                "status_identidade": status_identidade,
                "confianca": identidade.get("confianca"),
                "motivo": teste.get("erro"),
            }

        return {
            "sucesso": True,
            "erro": None,
            "camera_uid": camera_uid,
            "nome": camera.get("nome"),
            "tipo": tipo,
            "online": True,
            "status": "ONLINE",
            "indice_runtime": indice_runtime,
            "status_identidade": status_identidade,
            "confianca": identidade.get("confianca"),
            "largura": teste.get("largura"),
            "altura": teste.get("altura"),
            "fps": teste.get("fps"),
        }

    conexao = camera.get("conexao") or {}
    fonte = str(conexao.get("fonte") or "").strip()

    if not fonte:
        return {
            "sucesso": True,
            "erro": None,
            "camera_uid": camera_uid,
            "nome": camera.get("nome"),
            "tipo": tipo,
            "online": False,
            "status": "OFFLINE",
            "motivo": "FONTE_CAMERA_NAO_CONFIGURADA",
        }

    parsed = urlparse(fonte)

    if not _porta_acessivel(
        parsed.hostname,
        _porta_padrao(parsed),
    ):
        return {
            "sucesso": True,
            "erro": None,
            "camera_uid": camera_uid,
            "nome": camera.get("nome"),
            "tipo": tipo,
            "online": False,
            "status": "OFFLINE",
            "motivo": "PORTA_STREAM_INDISPONIVEL",
        }

    cap = _abrir_video_capture_rede(
        fonte,
        timeout_ms=_TIMEOUT_STATUS_MS,
    )

    if cap is None or not cap.isOpened():
        if cap is not None:
            cap.release()

        return {
            "sucesso": True,
            "erro": None,
            "camera_uid": camera_uid,
            "nome": camera.get("nome"),
            "tipo": tipo,
            "online": False,
            "status": "OFFLINE",
            "motivo": "STREAM_INDISPONIVEL",
        }

    try:
        ret, frame = cap.read()

        if not ret or frame is None or frame.size == 0:
            return {
                "sucesso": True,
                "erro": None,
                "camera_uid": camera_uid,
                "nome": camera.get("nome"),
                "tipo": tipo,
                "online": False,
                "status": "OFFLINE",
                "motivo": "FRAME_NAO_RECEBIDO",
            }

        altura, largura = frame.shape[:2]

        return {
            "sucesso": True,
            "erro": None,
            "camera_uid": camera_uid,
            "nome": camera.get("nome"),
            "tipo": tipo,
            "online": True,
            "status": "ONLINE",
            "largura": int(largura),
            "altura": int(altura),
            "fps": _normalizar_fps(
                cap.get(cv2.CAP_PROP_FPS)
            ),
        }

    except Exception:
        return {
            "sucesso": True,
            "erro": None,
            "camera_uid": camera_uid,
            "nome": camera.get("nome"),
            "tipo": tipo,
            "online": False,
            "status": "OFFLINE",
            "motivo": "ERRO_TESTE_STREAM",
        }

    finally:
        try:
            cap.release()
        except Exception:
            pass


def listar_cameras_com_status(
    tipo: Optional[str] = None,
) -> Dict[str, Any]:
    cameras = registry_listar_cameras(tipo)

    if not cameras:
        return {
            "sucesso": True,
            "erro": None,
            "quantidade": 0,
            "cameras": [],
        }

    por_uid = {
        camera.get("camera_uid"): camera
        for camera in cameras
        if camera.get("camera_uid")
    }

    status_por_uid: Dict[str, Dict[str, Any]] = {}

    trabalhadores = max(
        1,
        min(8, len(por_uid)),
    )

    with ThreadPoolExecutor(
        max_workers=trabalhadores
    ) as executor:
        futuros = {
            executor.submit(
                obter_status_camera,
                camera_uid,
            ): camera_uid
            for camera_uid in por_uid
        }

        for futuro in as_completed(futuros):
            camera_uid = futuros[futuro]

            try:
                status_por_uid[camera_uid] = (
                    futuro.result()
                )
            except Exception:
                status_por_uid[camera_uid] = {
                    "sucesso": True,
                    "erro": None,
                    "camera_uid": camera_uid,
                    "online": False,
                    "status": "OFFLINE",
                    "motivo": "ERRO_VERIFICAR_STATUS",
                }

    resultados = []

    for camera in cameras:
        camera_uid = camera.get("camera_uid")
        status = status_por_uid.get(
            camera_uid,
            {},
        )

        resultados.append({
            "camera_uid": camera_uid,
            "nome": camera.get("nome"),
            "tipo": camera.get("tipo"),
            "online": status.get("online", False),
            "status": status.get(
                "status",
                "OFFLINE",
            ),
            "largura": status.get("largura"),
            "altura": status.get("altura"),
            "fps": status.get("fps"),
            "motivo": status.get("motivo"),
            "status_identidade": status.get(
                "status_identidade"
            ),
            "confianca": status.get("confianca"),
        })

    return {
        "sucesso": True,
        "erro": None,
        "quantidade": len(resultados),
        "cameras": resultados,
    }


# ============================================================
# PREVIEW
# ============================================================

def _normalizar_qualidade_jpeg_preview(qualidade_jpeg: int) -> int:
    try:
        qualidade = int(qualidade_jpeg)
    except (TypeError, ValueError):
        qualidade = 80

    return max(1, min(100, qualidade))


def _loop_captura_preview(sessao: Dict[str, Any]) -> None:
    """
    Drena o VideoCapture continuamente e mantém apenas o frame mais recente.

    O frontend pode consultar a sessão mais devagar do que a câmera produz
    frames sem criar uma fila de atraso. Frames antigos são descartados.
    """
    stop_event = sessao.get("stop_event")
    if stop_event is None:
        return

    while not stop_event.is_set():
        cap = sessao.get("cap")

        if cap is None or not cap.isOpened():
            with sessao["lock"]:
                sessao["capture_erro"] = "PREVIEW_INDISPONIVEL"
            stop_event.wait(0.05)
            continue

        try:
            with sessao["cap_lock"]:
                if stop_event.is_set():
                    break

                cap_atual = sessao.get("cap")
                if cap_atual is None or not cap_atual.isOpened():
                    ret = False
                    frame = None
                else:
                    ret, frame = cap_atual.read()
        except Exception:
            ret = False
            frame = None

        if stop_event.is_set():
            break

        if not ret or frame is None or frame.size == 0:
            with sessao["lock"]:
                sessao["capture_erro"] = "FRAME_PREVIEW_NAO_RECEBIDO"
            stop_event.wait(0.03)
            continue

        altura, largura = frame.shape[:2]

        with sessao["lock"]:
            # Sem fila: o frame anterior é substituído imediatamente.
            sessao["ultimo_frame"] = frame
            sessao["largura"] = int(largura)
            sessao["altura"] = int(altura)
            sessao["capture_erro"] = None
            sessao["frame_seq"] = int(sessao.get("frame_seq") or 0) + 1


def _iniciar_worker_preview(sessao: Dict[str, Any]) -> None:
    stop_event = threading.Event()
    sessao["stop_event"] = stop_event
    sessao["cap_lock"] = threading.RLock()
    sessao["ultimo_frame"] = sessao.get("frame_inicial")
    sessao["frame_inicial"] = None
    sessao["capture_erro"] = None
    sessao["frame_seq"] = 0

    thread = threading.Thread(
        target=_loop_captura_preview,
        args=(sessao,),
        name=f"preview-{sessao.get('session_id')}",
        daemon=True,
    )
    sessao["capture_thread"] = thread
    thread.start()


def _parar_worker_preview(
    sessao: Dict[str, Any],
    liberar_capture: bool = True,
) -> None:
    stop_event = sessao.get("stop_event")
    thread = sessao.get("capture_thread")

    if stop_event is not None:
        stop_event.set()

    if thread is not None and thread.is_alive():
        thread.join(timeout=1.0)

    if liberar_capture:
        cap_lock = sessao.get("cap_lock")
        cap = sessao.get("cap")
        try:
            if cap_lock is not None:
                with cap_lock:
                    if cap is not None:
                        cap.release()
            elif cap is not None:
                cap.release()
        except Exception:
            pass
        sessao["cap"] = None

    sessao["capture_thread"] = None


def _abrir_capture_preview_temporario_rede(
    fonte: str,
    timeout_ms: int = 3000,
) -> Dict[str, Any]:
    fonte = str(fonte or "").strip()

    if not fonte:
        return {
            "sucesso": False,
            "erro": "URL_STREAM_OBRIGATORIA",
        }

    parsed = urlparse(fonte)
    porta = _porta_padrao(parsed)

    if not _porta_acessivel(parsed.hostname, porta):
        return {
            "sucesso": False,
            "erro": "STREAM_INDISPONIVEL",
        }

    cap = _abrir_video_capture_rede(
        fonte,
        timeout_ms=timeout_ms,
    )

    if cap is None or not cap.isOpened():
        if cap is not None:
            try:
                cap.release()
            except Exception:
                pass

        return {
            "sucesso": False,
            "erro": "STREAM_INDISPONIVEL",
        }

    try:
        ret, frame = cap.read()
    except Exception:
        ret = False
        frame = None

    if not ret or frame is None or frame.size == 0:
        try:
            cap.release()
        except Exception:
            pass

        return {
            "sucesso": False,
            "erro": "FRAME_NAO_RECEBIDO",
        }

    altura, largura = frame.shape[:2]

    return {
        "sucesso": True,
        "erro": None,
        "cap": cap,
        "tipo": str(parsed.scheme or "rede").lower(),
        "fonte": fonte,
        "frame_inicial": frame,
        "largura": int(largura),
        "altura": int(altura),
        "fps": _normalizar_fps(cap.get(cv2.CAP_PROP_FPS)),
    }


def _abrir_capture_preview_temporario_usb(
    indice: int,
) -> Dict[str, Any]:
    dispositivos = enumerar_dispositivos_usb()
    dispositivo = obter_dispositivo_por_indice(
        int(indice),
        dispositivos,
    )

    if dispositivo is None:
        return {
            "sucesso": False,
            "erro": "CAMERA_USB_NAO_ENCONTRADA",
        }

    cap = None

    try:
        cap = cv2.VideoCapture(
            int(indice),
            cv2.CAP_DSHOW,
        )

        if cap is None or not cap.isOpened():
            if cap is not None:
                cap.release()
            return {
                "sucesso": False,
                "erro": "CAMERA_USB_INDISPONIVEL",
            }

        ret, frame = cap.read()

        if not ret or frame is None or frame.size == 0:
            cap.release()
            return {
                "sucesso": False,
                "erro": "FRAME_USB_NAO_RECEBIDO",
            }

        altura, largura = frame.shape[:2]

        return {
            "sucesso": True,
            "erro": None,
            "cap": cap,
            "tipo": "usb",
            "fonte": int(indice),
            "frame_inicial": frame,
            "largura": int(largura),
            "altura": int(altura),
            "fps": _normalizar_fps(cap.get(cv2.CAP_PROP_FPS)),
            "nome_dispositivo": dispositivo.get("nome_dispositivo"),
        }

    except Exception:
        if cap is not None:
            try:
                cap.release()
            except Exception:
                pass

        return {
            "sucesso": False,
            "erro": "ERRO_TESTE_CAMERA_USB",
        }


def iniciar_preview_temporario(
    fonte: Optional[str] = None,
    candidato: Optional[Dict[str, Any]] = None,
    usuario: Optional[str] = None,
    senha: Optional[str] = None,
    indice_usb: Optional[int] = None,
    nome: Optional[str] = None,
    qualidade_jpeg: int = 80,
    timeout_ms: int = 3000,
) -> Dict[str, Any]:
    """
    Abre uma sessão de preview sem cadastrar a câmera.

    A sessão temporária usa o mesmo repositório de previews do fluxo
    normal, portanto `obter_frame_preview()` e `parar_preview()`
    funcionam sem qualquer tratamento especial no frontend.
    """
    try:
        timeout = max(250, int(timeout_ms))
    except (TypeError, ValueError):
        timeout = 3000

    origem = None
    abertura = None
    indice_normalizado = None

    if indice_usb is not None:
        try:
            indice_normalizado = int(indice_usb)
        except (TypeError, ValueError):
            return {
                "sucesso": False,
                "erro": "INDICE_USB_INVALIDO",
            }

        origem = "usb"
        abertura = _abrir_capture_preview_temporario_usb(
            indice_normalizado
        )

    else:
        fonte_final = str(fonte or "").strip()

        if not fonte_final and isinstance(candidato, dict):
            ip = candidato.get("ip")
            portas = candidato.get("portas", [])

            if not ip:
                return {
                    "sucesso": False,
                    "erro": "IP_CAMERA_INVALIDO",
                }

            stream = tentar_rtsp_comum(
                ip,
                portas,
                usuario=usuario or None,
                senha=senha or None,
            )

            if stream is None or not stream.get("url"):
                return {
                    "sucesso": False,
                    "erro": "STREAM_NAO_DESCOBERTO",
                }

            fonte_final = str(stream.get("url")).strip()
        elif fonte_final:
            fonte_final = _aplicar_credenciais_url(
                fonte_final,
                usuario,
                senha,
            )

        if not fonte_final:
            return {
                "sucesso": False,
                "erro": "FONTE_OU_CANDIDATO_OBRIGATORIO",
            }

        origem = "rede"
        abertura = _abrir_capture_preview_temporario_rede(
            fonte_final,
            timeout_ms=timeout,
        )

    if not abertura or not abertura.get("sucesso"):
        return {
            "sucesso": False,
            "erro": (abertura or {}).get("erro") or "CAMERA_INDISPONIVEL",
        }

    session_id = str(uuid.uuid4())
    qualidade = _normalizar_qualidade_jpeg_preview(qualidade_jpeg)

    nome_sessao = str(
        nome
        or abertura.get("nome_dispositivo")
        or (candidato or {}).get("nome_onvif")
        or (candidato or {}).get("nome")
        or "Câmera temporária"
    ).strip()

    sessao = {
        "session_id": session_id,
        "camera_uid": None,
        "temporario": True,
        "origem": origem,
        "nome": nome_sessao,
        "tipo": abertura.get("tipo"),
        "fonte": abertura.get("fonte"),
        "indice_usb": indice_normalizado,
        "cap": abertura["cap"],
        "qualidade_jpeg": qualidade,
        "timeout_ms": timeout,
        "lock": threading.RLock(),
        "frame_inicial": abertura.get("frame_inicial"),
        "largura": abertura.get("largura"),
        "altura": abertura.get("altura"),
        "fps": abertura.get("fps"),
    }

    with _PREVIEWS_LOCK:
        _PREVIEWS[session_id] = sessao

    _iniciar_worker_preview(sessao)

    return {
        "sucesso": True,
        "erro": None,
        "session_id": session_id,
        "temporario": True,
        "origem": origem,
        "nome": nome_sessao,
        "tipo": abertura.get("tipo"),
        "largura": abertura.get("largura"),
        "altura": abertura.get("altura"),
        "fps": abertura.get("fps"),
    }


def iniciar_preview(

    camera_uid: str,
    qualidade_jpeg: int = 80,
    timeout_ms: int = 3000,
) -> Dict[str, Any]:
    camera = registry_obter_camera(camera_uid)

    if camera is None:
        return {
            "sucesso": False,
            "erro": "CAMERA_NAO_ENCONTRADA",
        }

    abertura = _abrir_capture_preview(
        camera,
        timeout_ms=timeout_ms,
    )

    if not abertura.get("sucesso"):
        return {
            "sucesso": False,
            "erro": abertura.get("erro"),
            "camera_uid": camera_uid,
        }

    session_id = str(uuid.uuid4())

    qualidade = _normalizar_qualidade_jpeg_preview(qualidade_jpeg)

    sessao = {
        "session_id": session_id,
        "camera_uid": camera_uid,
        "temporario": False,
        "origem": "cadastrada",
        "nome": camera.get("nome"),
        "tipo": abertura.get("tipo"),
        "fonte": abertura.get("fonte"),
        "cap": abertura["cap"],
        "qualidade_jpeg": qualidade,
        "timeout_ms": int(timeout_ms),
        "lock": threading.RLock(),
        "frame_inicial": abertura.get(
            "frame_inicial"
        ),
        "largura": abertura.get("largura"),
        "altura": abertura.get("altura"),
        "fps": abertura.get("fps"),
    }

    with _PREVIEWS_LOCK:
        _PREVIEWS[session_id] = sessao

    _iniciar_worker_preview(sessao)

    return {
        "sucesso": True,
        "erro": None,
        "session_id": session_id,
        "camera_uid": camera_uid,
        "nome": camera.get("nome"),
        "tipo": abertura.get("tipo"),
        "largura": abertura.get("largura"),
        "altura": abertura.get("altura"),
        "fps": abertura.get("fps"),
    }


def obter_frame_preview(
    session_id: str,
) -> Dict[str, Any]:
    with _PREVIEWS_LOCK:
        sessao = _PREVIEWS.get(session_id)

    if sessao is None:
        return {
            "sucesso": False,
            "erro": "PREVIEW_NAO_ENCONTRADO",
        }

    with sessao["lock"]:
        frame_atual = sessao.get("ultimo_frame")
        capture_erro = sessao.get("capture_erro")
        frame_seq = int(sessao.get("frame_seq") or 0)
        frame = frame_atual.copy() if frame_atual is not None else None

    if frame is None or frame.size == 0:
        return {
            "sucesso": False,
            "erro": capture_erro or "FRAME_PREVIEW_NAO_RECEBIDO",
            "session_id": session_id,
            "camera_uid": sessao.get("camera_uid"),
        }

    # A codificação acontece fora do lock da sessão, permitindo que a
    # captura continue avançando enquanto a resposta HTTP é preparada.
    frame_base64 = _encodar_jpeg_base64(
        frame,
        sessao.get("qualidade_jpeg", 80),
    )

    if frame_base64 is None:
        return {
            "sucesso": False,
            "erro": "ERRO_CODIFICAR_FRAME_PREVIEW",
            "session_id": session_id,
            "camera_uid": sessao.get("camera_uid"),
        }

    altura, largura = frame.shape[:2]

    return {
        "sucesso": True,
        "erro": None,
        "session_id": session_id,
        "camera_uid": sessao.get("camera_uid"),
        "temporario": bool(sessao.get("temporario")),
        "origem": sessao.get("origem"),
        "mime_type": "image/jpeg",
        "frame_base64": frame_base64,
        "largura": int(largura),
        "altura": int(altura),
        "fps": sessao.get("fps"),
        "frame_seq": frame_seq,
    }


def parar_preview(
    session_id: str,
) -> Dict[str, Any]:
    with _PREVIEWS_LOCK:
        sessao = _PREVIEWS.pop(
            session_id,
            None,
        )

    if sessao is None:
        return {
            "sucesso": False,
            "erro": "PREVIEW_NAO_ENCONTRADO",
        }

    _parar_worker_preview(sessao, liberar_capture=True)

    with sessao["lock"]:
        sessao["ultimo_frame"] = None
        sessao["frame_inicial"] = None

    return {
        "sucesso": True,
        "erro": None,
        "session_id": session_id,
        "camera_uid": sessao.get("camera_uid"),
        "temporario": bool(sessao.get("temporario")),
        "origem": sessao.get("origem"),
    }


def reconectar_preview(
    session_id: str,
) -> Dict[str, Any]:
    with _PREVIEWS_LOCK:
        sessao = _PREVIEWS.get(session_id)

    if sessao is None:
        return {
            "sucesso": False,
            "erro": "PREVIEW_NAO_ENCONTRADO",
        }

    camera_uid = sessao.get("camera_uid")

    _parar_worker_preview(sessao, liberar_capture=True)

    if sessao.get("temporario"):
        if sessao.get("origem") == "usb":
            abertura = _abrir_capture_preview_temporario_usb(
                sessao.get("indice_usb")
            )
        else:
            abertura = _abrir_capture_preview_temporario_rede(
                sessao.get("fonte"),
                timeout_ms=sessao.get("timeout_ms", 3000),
            )
    else:
        camera = registry_obter_camera(camera_uid)

        if camera is None:
            return {
                "sucesso": False,
                "erro": "CAMERA_NAO_ENCONTRADA",
                "session_id": session_id,
            }

        abertura = _abrir_capture_preview(
            camera,
            timeout_ms=sessao.get("timeout_ms", 3000),
        )

    if not abertura.get("sucesso"):
        return {
            "sucesso": False,
            "erro": abertura.get("erro"),
            "session_id": session_id,
            "camera_uid": camera_uid,
        }

    with sessao["lock"]:
        sessao["cap"] = abertura["cap"]
        sessao["fonte"] = abertura.get("fonte")
        sessao["tipo"] = abertura.get("tipo")
        sessao["frame_inicial"] = abertura.get("frame_inicial")
        sessao["largura"] = abertura.get("largura")
        sessao["altura"] = abertura.get("altura")
        sessao["fps"] = abertura.get("fps")
        sessao["capture_erro"] = None

    _iniciar_worker_preview(sessao)

    return {
        "sucesso": True,
        "erro": None,
        "session_id": session_id,
        "camera_uid": camera_uid,
        "largura": sessao.get("largura"),
        "altura": sessao.get("altura"),
        "fps": sessao.get("fps"),
    }


def listar_previews_ativos() -> Dict[str, Any]:
    with _PREVIEWS_LOCK:
        sessoes = [
            {
                "session_id": item.get("session_id"),
                "camera_uid": item.get("camera_uid"),
                "temporario": bool(item.get("temporario")),
                "origem": item.get("origem"),
                "nome": item.get("nome"),
                "tipo": item.get("tipo"),
                "largura": item.get("largura"),
                "altura": item.get("altura"),
                "fps": item.get("fps"),
            }
            for item in _PREVIEWS.values()
        ]

    return {
        "sucesso": True,
        "erro": None,
        "quantidade": len(sessoes),
        "previews": sessoes,
    }

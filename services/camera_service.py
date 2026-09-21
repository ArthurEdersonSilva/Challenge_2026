import base64
import socket
import threading
import uuid

from concurrent.futures import ThreadPoolExecutor, as_completed
from copy import deepcopy
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

    return {
        "sucesso": True,
        "erro": None,
        "camera": camera,
    }


def editar_camera_rede(
    camera_uid: str,
    nome: str,
    fonte: str,
    onvif: Optional[bool] = None,
) -> Dict[str, Any]:
    camera_atual = registry_obter_camera(camera_uid)

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

    return {
        "sucesso": True,
        "erro": None,
        "camera": camera,
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

    return {
        "sucesso": True,
        "erro": None,
        "camera_uid": camera_uid,
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

    try:
        qualidade = int(qualidade_jpeg)
    except (TypeError, ValueError):
        qualidade = 80

    qualidade = max(1, min(100, qualidade))

    sessao = {
        "session_id": session_id,
        "camera_uid": camera_uid,
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
        frame = sessao.get("frame_inicial")

        if frame is not None:
            sessao["frame_inicial"] = None
        else:
            cap = sessao.get("cap")

            if cap is None or not cap.isOpened():
                return {
                    "sucesso": False,
                    "erro": "PREVIEW_INDISPONIVEL",
                    "session_id": session_id,
                    "camera_uid": sessao.get(
                        "camera_uid"
                    ),
                }

            try:
                ret, frame = cap.read()
            except Exception:
                ret = False
                frame = None

            if (
                not ret
                or frame is None
                or frame.size == 0
            ):
                return {
                    "sucesso": False,
                    "erro": "FRAME_PREVIEW_NAO_RECEBIDO",
                    "session_id": session_id,
                    "camera_uid": sessao.get(
                        "camera_uid"
                    ),
                }

        frame_base64 = _encodar_jpeg_base64(
            frame,
            sessao.get("qualidade_jpeg", 80),
        )

        if frame_base64 is None:
            return {
                "sucesso": False,
                "erro": "ERRO_CODIFICAR_FRAME_PREVIEW",
                "session_id": session_id,
                "camera_uid": sessao.get(
                    "camera_uid"
                ),
            }

        altura, largura = frame.shape[:2]

        return {
            "sucesso": True,
            "erro": None,
            "session_id": session_id,
            "camera_uid": sessao.get("camera_uid"),
            "mime_type": "image/jpeg",
            "frame_base64": frame_base64,
            "largura": int(largura),
            "altura": int(altura),
            "fps": sessao.get("fps"),
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

    with sessao["lock"]:
        cap = sessao.get("cap")

        if cap is not None:
            try:
                cap.release()
            except Exception:
                pass

        sessao["cap"] = None
        sessao["frame_inicial"] = None

    return {
        "sucesso": True,
        "erro": None,
        "session_id": session_id,
        "camera_uid": sessao.get("camera_uid"),
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
    camera = registry_obter_camera(camera_uid)

    if camera is None:
        return {
            "sucesso": False,
            "erro": "CAMERA_NAO_ENCONTRADA",
            "session_id": session_id,
        }

    abertura = _abrir_capture_preview(
        camera,
        timeout_ms=sessao.get(
            "timeout_ms",
            3000,
        ),
    )

    if not abertura.get("sucesso"):
        return {
            "sucesso": False,
            "erro": abertura.get("erro"),
            "session_id": session_id,
            "camera_uid": camera_uid,
        }

    with sessao["lock"]:
        cap_antigo = sessao.get("cap")

        if cap_antigo is not None:
            try:
                cap_antigo.release()
            except Exception:
                pass

        sessao["cap"] = abertura["cap"]
        sessao["fonte"] = abertura.get("fonte")
        sessao["tipo"] = abertura.get("tipo")
        sessao["frame_inicial"] = abertura.get(
            "frame_inicial"
        )
        sessao["largura"] = abertura.get("largura")
        sessao["altura"] = abertura.get("altura")
        sessao["fps"] = abertura.get("fps")

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

import json
import os
import re
import subprocess
import tempfile
import uuid
from copy import deepcopy
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse


SCHEMA_VERSION = 1
PASTA_CONFIGURACOES = "configuracoes"
PATH_REGISTRY = os.path.join(
    PASTA_CONFIGURACOES,
    "cameras_registry.json",
)

TIPO_USB = "usb"
TIPOS_REDE = {"wifi", "ip", "rtsp", "http", "https"}

IDENTIFICADA = "IDENTIFICADA"
AMBIGUA = "AMBIGUA"
INDISPONIVEL = "INDISPONIVEL"

CONFIANCA_FORTE = "FORTE"
CONFIANCA_SUFICIENTE = "SUFICIENTE"
CONFIANCA_MANUAL = "MANUAL"


def _agora_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _normalizar_texto(valor: Any) -> str:
    return " ".join(str(valor or "").strip().casefold().split())


def gerar_camera_uid() -> str:
    return str(uuid.uuid4())


def _registry_vazio() -> Dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "cameras": [],
        "metadata": {
            "criado_em": _agora_iso(),
            "atualizado_em": _agora_iso(),
        },
    }


def carregar_registry() -> Dict[str, Any]:
    if not os.path.exists(PATH_REGISTRY):
        return _registry_vazio()

    try:
        with open(PATH_REGISTRY, "r", encoding="utf-8") as arquivo:
            dados = json.load(arquivo)
    except Exception as erro:
        print(f"⚠️ Erro ao carregar cadastro de cameras: {erro}")
        return _registry_vazio()

    if not isinstance(dados, dict):
        return _registry_vazio()

    cameras = dados.get("cameras")
    if not isinstance(cameras, list):
        return _registry_vazio()

    dados.setdefault("schema_version", SCHEMA_VERSION)
    dados.setdefault("metadata", {})
    return dados


def salvar_registry(registry: Dict[str, Any]) -> str:
    os.makedirs(PASTA_CONFIGURACOES, exist_ok=True)

    dados = deepcopy(registry)
    dados["schema_version"] = SCHEMA_VERSION
    dados.setdefault("cameras", [])
    metadata = dados.setdefault("metadata", {})
    metadata.setdefault("criado_em", _agora_iso())
    metadata["atualizado_em"] = _agora_iso()

    fd, temporario = tempfile.mkstemp(
        prefix=".cameras_registry.",
        suffix=".tmp",
        dir=PASTA_CONFIGURACOES,
        text=True,
    )

    try:
        with os.fdopen(fd, "w", encoding="utf-8") as arquivo:
            json.dump(dados, arquivo, indent=4, ensure_ascii=False)
            arquivo.flush()
            os.fsync(arquivo.fileno())

        with open(temporario, "r", encoding="utf-8") as arquivo:
            json.load(arquivo)

        os.replace(temporario, PATH_REGISTRY)
    except Exception:
        try:
            if os.path.exists(temporario):
                os.remove(temporario)
        except Exception:
            pass
        raise

    registry.clear()
    registry.update(dados)
    return PATH_REGISTRY


def obter_camera(camera_uid: str, registry: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
    dados = registry if registry is not None else carregar_registry()

    for camera in dados.get("cameras", []):
        if isinstance(camera, dict) and camera.get("camera_uid") == camera_uid:
            return camera

    return None


def _extrair_vid_pid(pnp_device_id: Optional[str]) -> Tuple[Optional[str], Optional[str]]:
    texto = str(pnp_device_id or "")
    vid = re.search(r"VID_([0-9A-Fa-f]{4})", texto)
    pid = re.search(r"PID_([0-9A-Fa-f]{4})", texto)
    return (
        vid.group(1).upper() if vid else None,
        pid.group(1).upper() if pid else None,
    )


def _extrair_serial_usb(pnp_device_id: Optional[str]) -> Optional[str]:
    texto = str(pnp_device_id or "").strip()
    if not texto or "\\" not in texto:
        return None

    parte = texto.rsplit("\\", 1)[-1].strip()
    if not parte or "&" in parte:
        return None
    return parte


def _enumerar_pnp_windows() -> List[Dict[str, Any]]:
    if os.name != "nt":
        return []

    script = r"""
$items = Get-PnpDevice -PresentOnly -ErrorAction SilentlyContinue |
    Where-Object { $_.Class -in @('Camera','Image') } |
    ForEach-Object {
        [PSCustomObject]@{
            FriendlyName = $_.FriendlyName
            InstanceId = $_.InstanceId
            Class = $_.Class
        }
    }
$items | ConvertTo-Json -Compress
""".strip()

    try:
        resultado = subprocess.run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", script],
            capture_output=True,
            text=True,
            timeout=8,
            check=False,
        )
    except Exception:
        return []

    if resultado.returncode != 0 or not resultado.stdout.strip():
        return []

    try:
        dados = json.loads(resultado.stdout)
    except Exception:
        return []

    if isinstance(dados, dict):
        dados = [dados]

    if not isinstance(dados, list):
        return []

    resultado_normalizado = []
    for item in dados:
        if not isinstance(item, dict):
            continue
        pnp_id = item.get("InstanceId")
        vid, pid = _extrair_vid_pid(pnp_id)
        resultado_normalizado.append({
            "nome_dispositivo": item.get("FriendlyName"),
            "pnp_device_id": pnp_id,
            "device_path": pnp_id,
            "vid": vid,
            "pid": pid,
            "serial": _extrair_serial_usb(pnp_id),
        })

    return resultado_normalizado


def _enumerar_nomes_directshow() -> List[str]:
    try:
        from pygrabber.dshow_graph import FilterGraph

        nomes = FilterGraph().get_input_devices()
        if isinstance(nomes, list):
            return [str(nome) for nome in nomes]
    except Exception:
        pass

    return []


def enumerar_dispositivos_usb() -> List[Dict[str, Any]]:
    """
    Enumera fontes USB sem abrir o pipeline de captura.

    O indice segue a ordem exposta pelo DirectShow/pygrabber quando
    disponivel. Metadados PnP sao enriquecimento; drivers podem omitir
    serial, VID/PID ou identificadores estaveis.
    """
    nomes = _enumerar_nomes_directshow()
    pnp = _enumerar_pnp_windows()
    dispositivos: List[Dict[str, Any]] = []

    grupos_pnp: Dict[str, List[Dict[str, Any]]] = {}
    for item in pnp:
        grupos_pnp.setdefault(
            _normalizar_texto(item.get("nome_dispositivo")),
            [],
        ).append(item)

    for indice, nome in enumerate(nomes):
        candidatos = grupos_pnp.get(_normalizar_texto(nome), [])

        # Somente anexa a identidade PnP ao indice DirectShow quando
        # o nome corresponde a exatamente um dispositivo. Com dois
        # dispositivos iguais, parear pela posicao seria inseguro.
        identidade_pnp = candidatos[0] if len(candidatos) == 1 else {}

        dispositivos.append({
            "indice": indice,
            "nome_dispositivo": nome,
            "vid": identidade_pnp.get("vid"),
            "pid": identidade_pnp.get("pid"),
            "serial": identidade_pnp.get("serial"),
            "device_path": identidade_pnp.get("device_path"),
            "pnp_device_id": identidade_pnp.get("pnp_device_id"),
        })

    return dispositivos


def obter_dispositivo_por_indice(
    indice: int,
    dispositivos: Optional[List[Dict[str, Any]]] = None,
) -> Optional[Dict[str, Any]]:
    lista = dispositivos if dispositivos is not None else enumerar_dispositivos_usb()
    for item in lista:
        if item.get("indice") == indice:
            return deepcopy(item)
    return None


def _identidade_usb_de_dispositivo(dispositivo: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "nome_dispositivo": dispositivo.get("nome_dispositivo"),
        "vid": dispositivo.get("vid"),
        "pid": dispositivo.get("pid"),
        "serial": dispositivo.get("serial"),
        "device_path": dispositivo.get("device_path"),
        "pnp_device_id": dispositivo.get("pnp_device_id"),
    }


def _pontuar_identidade_usb(
    identidade: Dict[str, Any],
    candidato: Dict[str, Any],
) -> Tuple[int, bool]:
    serial_salvo = _normalizar_texto(identidade.get("serial"))
    serial_atual = _normalizar_texto(candidato.get("serial"))
    if serial_salvo:
        # Se o cadastro possui serial confiável, não rebaixamos
        # silenciosamente para nome/VID/PID quando o runtime deixa de
        # expô-lo. Isso exigirá reassociação manual, evitando trocar
        # duas unidades fisicamente distintas do mesmo modelo.
        if not serial_atual or serial_salvo != serial_atual:
            return 0, False
        return 120, True

    pnp_salvo = _normalizar_texto(identidade.get("pnp_device_id"))
    pnp_atual = _normalizar_texto(candidato.get("pnp_device_id"))
    if pnp_salvo and pnp_atual and pnp_salvo == pnp_atual:
        return 110, True

    path_salvo = _normalizar_texto(identidade.get("device_path"))
    path_atual = _normalizar_texto(candidato.get("device_path"))
    if path_salvo and path_atual and path_salvo == path_atual:
        return 105, True

    score = 0
    vid_salvo = _normalizar_texto(identidade.get("vid"))
    vid_atual = _normalizar_texto(candidato.get("vid"))
    pid_salvo = _normalizar_texto(identidade.get("pid"))
    pid_atual = _normalizar_texto(candidato.get("pid"))

    if vid_salvo and vid_atual and vid_salvo != vid_atual:
        return 0, False
    if pid_salvo and pid_atual and pid_salvo != pid_atual:
        return 0, False

    if vid_salvo and vid_atual and vid_salvo == vid_atual:
        score += 25
    if pid_salvo and pid_atual and pid_salvo == pid_atual:
        score += 25

    nome_salvo = _normalizar_texto(identidade.get("nome_dispositivo"))
    nome_atual = _normalizar_texto(candidato.get("nome_dispositivo"))
    if nome_salvo and nome_atual and nome_salvo == nome_atual:
        score += 25

    return score, True


def resolver_usb(
    camera: Dict[str, Any],
    dispositivos: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    lista = dispositivos if dispositivos is not None else enumerar_dispositivos_usb()
    identidade = camera.get("identidade") or {}
    pontuados = []

    for candidato in lista:
        score, compativel = _pontuar_identidade_usb(identidade, candidato)
        if compativel and score > 0:
            pontuados.append((score, candidato))

    if not pontuados:
        return {
            "status_identidade": INDISPONIVEL,
            "confianca": None,
            "camera_uid": camera.get("camera_uid"),
            "candidatos": [],
            "indice_runtime": None,
            "motivo": "Nenhuma fonte USB compativel foi encontrada.",
        }

    pontuados.sort(key=lambda item: item[0], reverse=True)
    melhor_score = pontuados[0][0]
    melhores = [item for score, item in pontuados if score == melhor_score]

    if len(melhores) > 1:
        return {
            "status_identidade": AMBIGUA,
            "confianca": None,
            "camera_uid": camera.get("camera_uid"),
            "candidatos": deepcopy(melhores),
            "indice_runtime": None,
            "motivo": "Mais de uma fonte USB corresponde a identidade cadastrada.",
        }

    # Serial, PnP ID ou device path exatos sao fortes. Sem eles,
    # VID+PID+nome precisa resultar em candidato unico.
    if melhor_score >= 100:
        confianca = CONFIANCA_FORTE
    elif melhor_score >= 75:
        confianca = CONFIANCA_SUFICIENTE
    else:
        return {
            "status_identidade": AMBIGUA,
            "confianca": None,
            "camera_uid": camera.get("camera_uid"),
            "candidatos": deepcopy(melhores),
            "indice_runtime": None,
            "motivo": "Identidade USB insuficiente para associacao automatica.",
        }

    selecionado = melhores[0]
    return {
        "status_identidade": IDENTIFICADA,
        "confianca": confianca,
        "camera_uid": camera.get("camera_uid"),
        "candidatos": [deepcopy(selecionado)],
        "indice_runtime": selecionado.get("indice"),
        "motivo": "Fonte USB identificada de forma unica.",
    }


def _campos_conexao_rede(dados_config: Dict[str, Any]) -> Dict[str, Any]:
    fonte = dados_config.get("fonte")
    host = dados_config.get("host") or dados_config.get("ip")
    porta = dados_config.get("porta")
    caminho = dados_config.get("caminho_stream") or dados_config.get("path")

    if fonte:
        try:
            parsed = urlparse(str(fonte))
            if parsed.hostname:
                host = parsed.hostname
            if parsed.port is not None:
                porta = parsed.port
            if parsed.path:
                caminho = parsed.path
                if parsed.query:
                    caminho = f"{caminho}?{parsed.query}"
        except Exception:
            pass

    return {
        "fonte": fonte,
        "host": host,
        "porta": porta,
        "caminho_stream": caminho,
        "tipo_stream": dados_config.get("tipo", "wifi"),
        "onvif": bool(dados_config.get("onvif", False)),
        "resolucao": deepcopy(dados_config.get("resolucao")),
        "fps": dados_config.get("fps"),
    }


def registrar_usb_selecionada(
    indice: int,
    nome: str,
    dispositivos: Optional[List[Dict[str, Any]]] = None,
    camera_uid: Optional[str] = None,
) -> Dict[str, Any]:
    registry = carregar_registry()
    dispositivo = obter_dispositivo_por_indice(indice, dispositivos)

    if dispositivo is None:
        dispositivo = {
            "indice": indice,
            "nome_dispositivo": nome,
            "vid": None,
            "pid": None,
            "serial": None,
            "device_path": None,
            "pnp_device_id": None,
        }

    if camera_uid:
        camera = obter_camera(camera_uid, registry)
    else:
        camera = None

    if camera is None:
        camera = {
            "camera_uid": camera_uid or gerar_camera_uid(),
            "nome": nome,
            "tipo": TIPO_USB,
            "identidade": {},
            "ultimo_runtime": {},
            "metadata": {
                "criado_em": _agora_iso(),
                "atualizado_em": _agora_iso(),
            },
        }
        registry["cameras"].append(camera)

    camera["nome"] = nome
    camera["tipo"] = TIPO_USB
    camera["identidade"] = _identidade_usb_de_dispositivo(dispositivo)
    camera.setdefault("ultimo_runtime", {})["indice_usb"] = indice
    camera.setdefault("metadata", {})["atualizado_em"] = _agora_iso()
    salvar_registry(registry)
    return deepcopy(camera)


def registrar_rede_selecionada(
    dados_config: Dict[str, Any],
    nome: str,
    camera_uid: Optional[str] = None,
    config_index_legado: Optional[int] = None,
) -> Dict[str, Any]:
    registry = carregar_registry()
    camera = obter_camera(camera_uid, registry) if camera_uid else None

    if camera is None:
        camera = {
            "camera_uid": camera_uid or gerar_camera_uid(),
            "nome": nome,
            "tipo": str(dados_config.get("tipo", "wifi")).lower(),
            "identidade": {
                "tipo": "camera_rede_logica",
            },
            "conexao": {},
            "compatibilidade": {},
            "metadata": {
                "criado_em": _agora_iso(),
                "atualizado_em": _agora_iso(),
            },
        }
        registry["cameras"].append(camera)

    camera["nome"] = nome
    camera["tipo"] = str(dados_config.get("tipo", "wifi")).lower()
    camera["identidade"] = {"tipo": "camera_rede_logica"}
    camera["conexao"] = _campos_conexao_rede(dados_config)
    compatibilidade = camera.setdefault("compatibilidade", {})
    if config_index_legado is not None:
        compatibilidade["config_index_legado"] = int(config_index_legado)
    camera.setdefault("metadata", {})["atualizado_em"] = _agora_iso()
    salvar_registry(registry)
    return deepcopy(camera)


def atualizar_ultimo_indice_usb(camera_uid: str, indice: int) -> None:
    registry = carregar_registry()
    camera = obter_camera(camera_uid, registry)
    if camera is None:
        return
    camera.setdefault("ultimo_runtime", {})["indice_usb"] = int(indice)
    camera.setdefault("metadata", {})["atualizado_em"] = _agora_iso()
    salvar_registry(registry)


def conexao_rede(camera_uid: str) -> Optional[Dict[str, Any]]:
    camera = obter_camera(camera_uid)
    if not camera:
        return None
    conexao = camera.get("conexao")
    return deepcopy(conexao) if isinstance(conexao, dict) else None


def listar_cameras(tipo: Optional[str] = None) -> List[Dict[str, Any]]:
    registry = carregar_registry()
    cameras = [
        deepcopy(camera)
        for camera in registry.get("cameras", [])
        if isinstance(camera, dict)
    ]
    if tipo is None:
        return cameras
    normalizado = str(tipo).lower()
    return [camera for camera in cameras if str(camera.get("tipo", "")).lower() == normalizado]


def obter_ou_registrar_usb_selecionada(
    indice: int,
    nome: str,
    dispositivos: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    lista = dispositivos if dispositivos is not None else enumerar_dispositivos_usb()
    dispositivo = obter_dispositivo_por_indice(indice, lista)

    if dispositivo is not None:
        registry = carregar_registry()
        correspondencias = []
        for camera in registry.get("cameras", []):
            if not isinstance(camera, dict) or camera.get("tipo") != TIPO_USB:
                continue
            score, compativel = _pontuar_identidade_usb(
                camera.get("identidade") or {},
                dispositivo,
            )
            if compativel and score >= 75:
                correspondencias.append((score, camera))

        if correspondencias:
            correspondencias.sort(key=lambda item: item[0], reverse=True)
            maior = correspondencias[0][0]
            melhores = [camera for score, camera in correspondencias if score == maior]
            if len(melhores) == 1:
                camera = melhores[0]
                camera["nome"] = nome
                camera["identidade"] = _identidade_usb_de_dispositivo(dispositivo)
                camera.setdefault("ultimo_runtime", {})["indice_usb"] = indice
                camera.setdefault("metadata", {})["atualizado_em"] = _agora_iso()
                salvar_registry(registry)
                return deepcopy(camera)

    # A escolha da câmera no fluxo de novo ambiente é explícita. Se não
    # existe correspondência inequívoca com cadastro anterior, cria nova
    # entidade em vez de fundir duas câmeras possivelmente distintas.
    return registrar_usb_selecionada(
        indice=indice,
        nome=nome,
        dispositivos=lista,
    )


def obter_ou_registrar_rede_selecionada(
    dados_config: Dict[str, Any],
    nome: str,
    config_index_legado: Optional[int] = None,
) -> Dict[str, Any]:
    registry = carregar_registry()
    conexao = _campos_conexao_rede(dados_config)
    fonte = str(conexao.get("fonte") or "").strip()
    candidatos = []

    for camera in registry.get("cameras", []):
        if not isinstance(camera, dict):
            continue
        if str(camera.get("tipo", "")).lower() not in TIPOS_REDE:
            continue
        conexao_salva = camera.get("conexao") or {}
        if fonte and str(conexao_salva.get("fonte") or "").strip() == fonte:
            candidatos.append(camera)

    if len(candidatos) == 1:
        camera = candidatos[0]
        camera["nome"] = nome
        if config_index_legado is not None:
            camera.setdefault("compatibilidade", {})[
                "config_index_legado"
            ] = int(config_index_legado)
        camera.setdefault("metadata", {})["atualizado_em"] = _agora_iso()
        salvar_registry(registry)
        return deepcopy(camera)

    # Seleção no fluxo de novo ambiente é confirmação explícita daquela
    # entrada lógica atual. Conexões iguais não são fundidas se houver
    # ambiguidade no cadastro.
    return registrar_rede_selecionada(
        dados_config=dados_config,
        nome=nome,
        config_index_legado=config_index_legado,
    )

import json
import os
import tempfile
import uuid
from copy import deepcopy
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple


SCHEMA_VERSION = 2
SCHEMAS_SUPORTADOS = {1, 2}
PASTA_AMBIENTES = "ambientes"
ORIGEM_NOVO = "novo"
ORIGEM_LEGADO = "legado"


def _agora_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def garantir_pasta_ambientes() -> None:
    os.makedirs(PASTA_AMBIENTES, exist_ok=True)


def gerar_ambiente_id() -> str:
    return str(uuid.uuid4())


def caminho_perfil(ambiente_id: str) -> str:
    return os.path.join(PASTA_AMBIENTES, f"{ambiente_id}.json")


def validar_perfil(perfil: Any) -> Tuple[bool, List[str]]:
    erros: List[str] = []

    if not isinstance(perfil, dict):
        return False, ["perfil deve ser um objeto JSON"]

    schema_version = perfil.get("schema_version")
    if schema_version not in SCHEMAS_SUPORTADOS:
        erros.append(
            "schema_version inválido: "
            f"suportados {sorted(SCHEMAS_SUPORTADOS)}"
        )

    ambiente_id = perfil.get("ambiente_id")
    if not isinstance(ambiente_id, str) or not ambiente_id.strip():
        erros.append("ambiente_id ausente ou inválido")
    else:
        try:
            uuid.UUID(ambiente_id)
        except (ValueError, AttributeError, TypeError):
            erros.append("ambiente_id não é um UUID válido")

    nome = perfil.get("nome")
    if not isinstance(nome, str) or not nome.strip():
        erros.append("nome ausente ou inválido")

    if not isinstance(perfil.get("calibrado"), bool):
        erros.append("calibrado deve ser booleano")

    cameras = perfil.get("cameras")
    if not isinstance(cameras, list):
        erros.append("cameras deve ser uma lista")
    else:
        for indice, camera in enumerate(cameras):
            if not isinstance(camera, dict):
                erros.append(f"cameras[{indice}] inválida")
                continue

            tipo = camera.get("tipo")
            camera_uid = camera.get("camera_uid")
            referencia = camera.get("referencia")
            referencia_legada = camera.get("referencia_legada")

            if not isinstance(tipo, str) or not tipo:
                erros.append(f"cameras[{indice}].tipo inválido")

            tem_uid = isinstance(camera_uid, str) and bool(camera_uid.strip())
            if tem_uid:
                try:
                    uuid.UUID(camera_uid)
                except (ValueError, AttributeError, TypeError):
                    erros.append(f"cameras[{indice}].camera_uid inválido")

            # Perfis da ETAPA 3 continuam válidos. Referências legadas só
            # deixam de ser principais quando camera_uid for persistido.
            legado = referencia_legada if isinstance(referencia_legada, dict) else referencia
            tipo_normalizado = str(tipo).lower()

            if not tem_uid:
                if not isinstance(legado, dict):
                    erros.append(
                        f"cameras[{indice}] sem camera_uid e sem referência legada válida"
                    )
                    continue

                if tipo_normalizado == "usb":
                    if not isinstance(legado.get("indice"), int):
                        erros.append(
                            f"cameras[{indice}].referencia.indice inválido"
                        )
                else:
                    if not isinstance(legado.get("config_index"), int):
                        erros.append(
                            f"cameras[{indice}].referencia.config_index inválido"
                        )

    epis = perfil.get("epis_obrigatorios")
    if not isinstance(epis, list):
        erros.append("epis_obrigatorios deve ser uma lista")

    objetos = perfil.get("objetos_globais")
    if not isinstance(objetos, dict):
        erros.append("objetos_globais deve ser um objeto")

    metadata = perfil.get("metadata")
    if not isinstance(metadata, dict):
        erros.append("metadata deve ser um objeto")

    return not erros, erros


def criar_perfil(
    nome: str,
    cameras: List[Dict[str, Any]],
    epis_obrigatorios: Optional[List[str]] = None,
    objetos_globais: Optional[Dict[str, Dict[str, Any]]] = None,
    calibrado: bool = False,
    origem: str = ORIGEM_NOVO,
    ambiente_id: Optional[str] = None,
) -> Dict[str, Any]:
    agora = _agora_iso()

    return {
        "schema_version": SCHEMA_VERSION,
        "ambiente_id": ambiente_id or gerar_ambiente_id(),
        "nome": nome.strip(),
        "calibrado": bool(calibrado),
        "cameras": deepcopy(cameras or []),
        "epis_obrigatorios": list(epis_obrigatorios or []),
        "objetos_globais": deepcopy(objetos_globais or {}),
        "metadata": {
            "criado_em": agora,
            "atualizado_em": agora,
            "origem": origem,
        },
    }


def salvar_perfil(perfil: Dict[str, Any]) -> str:
    garantir_pasta_ambientes()

    perfil_salvar = deepcopy(perfil)
    metadata = perfil_salvar.setdefault("metadata", {})
    metadata.setdefault("criado_em", _agora_iso())
    metadata.setdefault("origem", ORIGEM_NOVO)
    metadata["atualizado_em"] = _agora_iso()

    valido, erros = validar_perfil(perfil_salvar)
    if not valido:
        raise ValueError(
            "Perfil de ambiente inválido: " + "; ".join(erros)
        )

    destino = caminho_perfil(perfil_salvar["ambiente_id"])
    pasta_destino = os.path.dirname(destino) or "."

    fd, temporario = tempfile.mkstemp(
        prefix=f".{perfil_salvar['ambiente_id']}.",
        suffix=".tmp",
        dir=pasta_destino,
        text=True,
    )

    try:
        with os.fdopen(fd, "w", encoding="utf-8") as arquivo:
            json.dump(
                perfil_salvar,
                arquivo,
                indent=4,
                ensure_ascii=False,
            )
            arquivo.flush()
            os.fsync(arquivo.fileno())

        with open(temporario, "r", encoding="utf-8") as arquivo:
            conferido = json.load(arquivo)

        valido, erros = validar_perfil(conferido)
        if not valido:
            raise ValueError(
                "Perfil temporário inválido: " + "; ".join(erros)
            )

        os.replace(temporario, destino)

    except Exception:
        try:
            if os.path.exists(temporario):
                os.remove(temporario)
        except Exception:
            pass
        raise

    perfil.clear()
    perfil.update(perfil_salvar)

    return destino


def persistir_camera_uid(
    perfil: Dict[str, Any],
    indice_camera: int,
    camera_uid: str,
    referencia_legada: Optional[Dict[str, Any]] = None,
) -> str:
    cameras = perfil.get("cameras", [])
    if not isinstance(cameras, list) or not (0 <= indice_camera < len(cameras)):
        raise IndexError("Índice de câmera inválido no perfil.")

    camera = cameras[indice_camera]
    if not isinstance(camera, dict):
        raise ValueError("Entrada de câmera inválida no perfil.")

    camera["camera_uid"] = camera_uid
    if referencia_legada is None:
        atual = camera.get("referencia_legada")
        if not isinstance(atual, dict):
            atual = camera.get("referencia")
        referencia_legada = atual if isinstance(atual, dict) else {}

    if referencia_legada:
        camera["referencia_legada"] = deepcopy(referencia_legada)

    # A referência legada pode continuar no JSON para diagnóstico, mas
    # camera_uid passa a ser a referência persistente principal.
    perfil["schema_version"] = SCHEMA_VERSION
    return salvar_perfil(perfil)



def carregar_perfil(caminho: str) -> Optional[Dict[str, Any]]:
    try:
        with open(caminho, "r", encoding="utf-8") as arquivo:
            perfil = json.load(arquivo)
    except Exception as erro:
        print(f"⚠️ Erro ao carregar perfil {caminho}: {erro}")
        return None

    valido, erros = validar_perfil(perfil)
    if not valido:
        print(
            f"⚠️ Perfil ignorado ({caminho}): "
            + "; ".join(erros)
        )
        return None

    return perfil


def listar_perfis() -> List[Dict[str, Any]]:
    garantir_pasta_ambientes()
    perfis: List[Dict[str, Any]] = []

    for nome_arquivo in sorted(os.listdir(PASTA_AMBIENTES)):
        if not nome_arquivo.lower().endswith(".json"):
            continue

        caminho = os.path.join(PASTA_AMBIENTES, nome_arquivo)
        perfil = carregar_perfil(caminho)

        if perfil is not None:
            perfis.append(perfil)

    perfis.sort(
        key=lambda item: str(item.get("nome", "")).casefold()
    )

    return perfis


def nome_ambiente_disponivel(nome: str, perfis=None) -> bool:
    nome_normalizado = nome.strip().casefold()

    if not nome_normalizado:
        return False

    if perfis is None:
        perfis = listar_perfis()

    return all(
        str(perfil.get("nome", "")).strip().casefold()
        != nome_normalizado
        for perfil in perfis
    )


def legado_disponivel(config) -> bool:
    caminho_ambiente = getattr(config, "PATH_CONFIG_AMBIENTE", "")
    caminho_epis = getattr(config, "PATH_CONFIG_EPIS", "")

    return bool(
        caminho_ambiente
        and caminho_epis
        and os.path.exists(caminho_ambiente)
        and os.path.exists(caminho_epis)
    )


def existe_perfil_migrado_legado(perfis=None) -> bool:
    if perfis is None:
        perfis = listar_perfis()

    for perfil in perfis:
        metadata = perfil.get("metadata", {})
        if metadata.get("origem") == ORIGEM_LEGADO:
            return True

    return False


def carregar_dados_legados(config) -> Optional[Dict[str, Any]]:
    ambiente = config.carregar_configuracao_ambiente()
    epis = config.carregar_configuracao_epis()

    if not isinstance(ambiente, dict) or not isinstance(epis, dict):
        return None

    return {
        "nome": ambiente.get(
            "ambiente",
            getattr(config, "NOME_AMBIENTE", "Ambiente Principal"),
        ),
        "calibrado": bool(ambiente.get("calibrado", False)),
        "objetos_globais": deepcopy(ambiente.get("objetos", {})),
        "epis_obrigatorios": list(epis.get("epis_obrigatorios", [])),
    }


def criar_perfil_legado(
    config,
    cameras: List[Dict[str, Any]],
) -> Optional[Dict[str, Any]]:
    dados = carregar_dados_legados(config)

    if dados is None:
        return None

    perfil = criar_perfil(
        nome=str(dados["nome"]),
        cameras=cameras,
        epis_obrigatorios=dados["epis_obrigatorios"],
        objetos_globais=dados["objetos_globais"],
        calibrado=dados["calibrado"],
        origem=ORIGEM_LEGADO,
    )

    perfil["metadata"]["migrado_em"] = _agora_iso()

    return perfil

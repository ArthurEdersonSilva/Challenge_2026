from __future__ import annotations

import os
import sys
from copy import deepcopy
from typing import Any, Dict

from flask import Flask, jsonify, request


# ============================================================
# AJUSTE DE IMPORT DO PROJETO
# ============================================================

RAIZ_PROJETO = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..")
)

if RAIZ_PROJETO not in sys.path:
    sys.path.insert(0, RAIZ_PROJETO)


from services.camera_service import (  # noqa: E402
    buscar_cameras,
    buscar_cameras_usb,
    cadastrar_camera_rede,
    cadastrar_camera_usb,
    editar_camera_rede,
    editar_camera_usb,
    listar_cameras,
    listar_cameras_com_status,
    obter_camera,
    obter_status_camera,
    remover_camera,
    resolver_camera_usb,
    testar_camera_descoberta,
    testar_camera_manual,
    testar_camera_usb,
    verificar_vinculos_camera,
)


# ============================================================
# CONFIGURACAO
# ============================================================

app = Flask(__name__)

HOST = "127.0.0.1"
PORTA = 5001


# ============================================================
# HELPERS GERAIS
# ============================================================

def _json_body() -> dict[str, Any]:
    dados = request.get_json(silent=True)
    return dados if isinstance(dados, dict) else {}


def _texto(valor: Any) -> str:
    return str(valor or "").strip()


def _credencial_opcional(valor: Any) -> str | None:
    texto = str(valor or "")
    return texto if texto else None


def _bool(valor: Any) -> bool:
    if isinstance(valor, bool):
        return valor

    if isinstance(valor, (int, float)):
        return bool(valor)

    if isinstance(valor, str):
        return valor.strip().lower() in {
            "1",
            "true",
            "sim",
            "s",
            "yes",
            "y",
        }

    return False


def _lista_portas(valor: Any) -> list[int]:
    if valor is None:
        return []

    if isinstance(valor, (list, tuple, set)):
        origem = valor
    else:
        origem = [valor]

    portas: list[int] = []

    for item in origem:
        try:
            porta = int(item)
        except (TypeError, ValueError):
            continue

        if porta > 0 and porta not in portas:
            portas.append(porta)

    return portas


def _status_erro(
    resultado: dict[str, Any],
    padrao: int = 400,
) -> int:
    if resultado.get("sucesso"):
        return 200

    erro = str(
        resultado.get("erro")
        or ""
    ).strip().upper()

    if erro in {
        "CAMERA_NAO_ENCONTRADA",
        "CAMERA_USB_NAO_ENCONTRADA",
    }:
        return 404

    if erro in {
        "CAMERA_VINCULADA_A_AMBIENTE",
        "CAMERA_POSSUI_VINCULOS",
    }:
        return 409

    if erro in {
        "STREAM_INDISPONIVEL",
        "STREAM_NAO_DESCOBERTO",
        "CAMERA_INDISPONIVEL",
        "CAMERA_USB_INDISPONIVEL",
        "FRAME_USB_NAO_RECEBIDO",
        "FRAME_NAO_RECEBIDO",
        "REDE_LOCAL_NAO_IDENTIFICADA",
    }:
        return 503

    return padrao


def _normalizar_busca_rede(
    resultado: dict[str, Any],
) -> dict[str, Any]:
    saida = deepcopy(resultado)

    candidatos = saida.get("candidatos")

    if candidatos is None:
        candidatos = saida.get("cameras")

    if candidatos is None:
        candidatos = []

    if not isinstance(candidatos, list):
        candidatos = (
            list(candidatos)
            if isinstance(candidatos, tuple)
            else []
        )

    saida["candidatos"] = candidatos
    saida["quantidade"] = int(
        saida.get("quantidade")
        or len(candidatos)
    )

    return saida


def _resumo_status(cameras):
    total = len(cameras)

    online = sum(
        1
        for camera in cameras
        if str(
            camera.get("status", "")
        ).upper() == "ONLINE"
        or bool(camera.get("online"))
    )

    return {
        "total": total,
        "online": online,
        "offline": total - online,
    }


# ============================================================
# CORS
# ============================================================

@app.after_request
def adicionar_cors(resposta):
    resposta.headers[
        "Access-Control-Allow-Origin"
    ] = "*"

    resposta.headers[
        "Access-Control-Allow-Headers"
    ] = (
        "Content-Type, X-Perfil, X-Matricula"
    )

    resposta.headers[
        "Access-Control-Allow-Methods"
    ] = (
        "GET, POST, PUT, DELETE, OPTIONS"
    )

    return resposta


# ============================================================
# HEALTH
# ============================================================

@app.route(
    "/api/front/cameras/health",
    methods=["GET"],
)
def health():
    return jsonify(
        {
            "sucesso": True,
            "erro": None,
            "servico": "cameras",
        }
    ), 200


# Mantida por compatibilidade com o antigo consultar-camera.py.
@app.route(
    "/api/front/cameras/consulta/health",
    methods=["GET"],
)
def health_consulta():
    return jsonify(
        {
            "sucesso": True,
            "erro": None,
            "servico": "cameras",
        }
    ), 200


# ============================================================
# BUSCA — REDE
# ============================================================

@app.route(
    "/api/front/cameras/rede/buscar",
    methods=["POST", "OPTIONS"],
)
@app.route(
    "/api/front/cameras/buscar",
    methods=["POST", "OPTIONS"],
)
def buscar_cameras_api():
    if request.method == "OPTIONS":
        return "", 204

    resultado = buscar_cameras()

    if not isinstance(resultado, dict):
        return jsonify(
            {
                "sucesso": False,
                "erro": "RESPOSTA_BUSCA_INVALIDA",
            }
        ), 500

    resultado = _normalizar_busca_rede(
        resultado
    )

    return jsonify(resultado), (
        200
        if resultado.get("sucesso")
        else _status_erro(
            resultado,
            500,
        )
    )


# ============================================================
# TESTE — REDE
# ============================================================

@app.route(
    "/api/front/cameras/rede/testar",
    methods=["POST", "OPTIONS"],
)
@app.route(
    "/api/front/cameras/testar",
    methods=["POST", "OPTIONS"],
)
def testar_camera_api():
    if request.method == "OPTIONS":
        return "", 204

    dados = _json_body()

    fonte = _texto(
        dados.get("fonte")
        or dados.get("url")
    )

    candidato = dados.get("candidato")

    usuario = _credencial_opcional(
        dados.get("usuario")
    )

    senha = _credencial_opcional(
        dados.get("senha")
    )

    if (
        isinstance(candidato, dict)
        and candidato
    ):
        resultado = testar_camera_descoberta(
            candidato,
            usuario=usuario,
            senha=senha,
        )

    elif fonte:
        resultado = testar_camera_manual(
            fonte,
            usuario=usuario,
            senha=senha,
        )

    else:
        return jsonify(
            {
                "sucesso": False,
                "erro": "FONTE_OU_CANDIDATO_OBRIGATORIO",
            }
        ), 400

    return jsonify(resultado), (
        200
        if resultado.get("sucesso")
        else _status_erro(resultado)
    )


# ============================================================
# CADASTRO — REDE
# ============================================================

@app.route(
    "/api/front/cameras/rede/cadastrar",
    methods=["POST", "OPTIONS"],
)
@app.route(
    "/api/front/cameras/cadastrar",
    methods=["POST", "OPTIONS"],
)
def cadastrar_camera_api():
    if request.method == "OPTIONS":
        return "", 204

    dados = _json_body()

    nome = _texto(
        dados.get("nome")
    )

    fonte = _texto(
        dados.get("fonte")
        or dados.get("url")
    )

    onvif = _bool(
        dados.get("onvif")
    )

    portas_detectadas = _lista_portas(
        dados.get("portas_detectadas")
        or dados.get("portas")
    )

    if not nome:
        return jsonify(
            {
                "sucesso": False,
                "erro": "NOME_CAMERA_OBRIGATORIO",
            }
        ), 400

    if not fonte:
        return jsonify(
            {
                "sucesso": False,
                "erro": "URL_STREAM_OBRIGATORIA",
            }
        ), 400

    resultado = cadastrar_camera_rede(
        nome=nome,
        fonte=fonte,
        onvif=onvif,
        portas_detectadas=portas_detectadas,
    )

    return jsonify(resultado), (
        201
        if resultado.get("sucesso")
        else _status_erro(resultado)
    )


# ============================================================
# USB
# ============================================================

@app.route(
    "/api/front/cameras/usb/buscar",
    methods=["POST", "OPTIONS"],
)
def buscar_cameras_usb_api():
    if request.method == "OPTIONS":
        return "", 204

    resultado = buscar_cameras_usb()

    return jsonify(resultado), (
        200
        if resultado.get("sucesso")
        else _status_erro(
            resultado,
            500,
        )
    )


@app.route(
    "/api/front/cameras/usb/testar",
    methods=["POST", "OPTIONS"],
)
def testar_camera_usb_api():
    if request.method == "OPTIONS":
        return "", 204

    dados = _json_body()

    indice = dados.get("indice")

    if (
        indice is None
        or str(indice).strip() == ""
    ):
        return jsonify(
            {
                "sucesso": False,
                "erro": "INDICE_USB_OBRIGATORIO",
            }
        ), 400

    try:
        indice = int(indice)
    except (TypeError, ValueError):
        return jsonify(
            {
                "sucesso": False,
                "erro": "INDICE_USB_INVALIDO",
            }
        ), 400

    resultado = testar_camera_usb(
        indice
    )

    return jsonify(resultado), (
        200
        if resultado.get("sucesso")
        else _status_erro(resultado)
    )


@app.route(
    "/api/front/cameras/usb/cadastrar",
    methods=["POST", "OPTIONS"],
)
def cadastrar_camera_usb_api():
    if request.method == "OPTIONS":
        return "", 204

    dados = _json_body()

    indice = dados.get("indice")
    nome = _texto(
        dados.get("nome")
    )

    if (
        indice is None
        or str(indice).strip() == ""
    ):
        return jsonify(
            {
                "sucesso": False,
                "erro": "INDICE_USB_OBRIGATORIO",
            }
        ), 400

    try:
        indice = int(indice)
    except (TypeError, ValueError):
        return jsonify(
            {
                "sucesso": False,
                "erro": "INDICE_USB_INVALIDO",
            }
        ), 400

    if not nome:
        return jsonify(
            {
                "sucesso": False,
                "erro": "NOME_CAMERA_OBRIGATORIO",
            }
        ), 400

    resultado = cadastrar_camera_usb(
        indice=indice,
        nome=nome,
    )

    return jsonify(resultado), (
        201
        if resultado.get("sucesso")
        else _status_erro(resultado)
    )


# ============================================================
# CONSULTA GERAL
# ============================================================

@app.route(
    "/api/front/cameras",
    methods=["GET", "OPTIONS"],
)
def listar_cameras_api():
    if request.method == "OPTIONS":
        return "", 204

    tipo = _texto(
        request.args.get("tipo")
    ) or None

    resultado = listar_cameras_com_status(
        tipo=tipo
    )

    if not resultado.get("sucesso"):
        return jsonify(resultado), _status_erro(
            resultado
        )

    cameras = resultado.get(
        "cameras"
    ) or []

    resposta = dict(resultado)
    resposta["resumo"] = _resumo_status(
        cameras
    )

    return jsonify(resposta), 200


@app.route(
    "/api/front/cameras/status",
    methods=["GET", "OPTIONS"],
)
def status_geral_api():
    if request.method == "OPTIONS":
        return "", 204

    resultado = listar_cameras_com_status()

    if not resultado.get("sucesso"):
        return jsonify(resultado), _status_erro(
            resultado
        )

    cameras = resultado.get(
        "cameras"
    ) or []

    resposta = dict(resultado)
    resposta["resumo"] = _resumo_status(
        cameras
    )

    return jsonify(resposta), 200


# ============================================================
# DETALHE / STATUS / VINCULOS
# ============================================================

@app.route(
    "/api/front/cameras/<camera_uid>",
    methods=["GET", "OPTIONS"],
)
def obter_camera_api(
    camera_uid: str,
):
    if request.method == "OPTIONS":
        return "", 204

    resultado = obter_camera(
        camera_uid
    )

    return jsonify(resultado), (
        200
        if resultado.get("sucesso")
        else _status_erro(resultado)
    )


@app.route(
    "/api/front/cameras/<camera_uid>/status",
    methods=["GET", "OPTIONS"],
)
def obter_status_camera_api(
    camera_uid: str,
):
    if request.method == "OPTIONS":
        return "", 204

    resultado = obter_status_camera(
        camera_uid
    )

    return jsonify(resultado), (
        200
        if resultado.get("sucesso")
        else _status_erro(resultado)
    )


@app.route(
    "/api/front/cameras/<camera_uid>/vinculos",
    methods=["GET", "OPTIONS"],
)
def vinculos_camera_api(
    camera_uid: str,
):
    if request.method == "OPTIONS":
        return "", 204

    resultado = verificar_vinculos_camera(
        camera_uid
    )

    return jsonify(resultado), (
        200
        if resultado.get("sucesso")
        else _status_erro(resultado)
    )


# ============================================================
# EDICAO
# ============================================================

@app.route(
    "/api/front/cameras/<camera_uid>",
    methods=["PUT", "OPTIONS"],
)
def editar_camera_api(
    camera_uid: str,
):
    if request.method == "OPTIONS":
        return "", 204

    atual = obter_camera(
        camera_uid
    )

    if not atual.get("sucesso"):
        return jsonify(atual), _status_erro(
            atual
        )

    camera = atual.get(
        "camera"
    ) or {}

    tipo = _texto(
        camera.get("tipo")
    ).lower()

    dados = _json_body()

    nome = _texto(
        dados.get("nome")
        or camera.get("nome")
    )

    if not nome:
        return jsonify(
            {
                "sucesso": False,
                "erro": "NOME_CAMERA_OBRIGATORIO",
            }
        ), 400

    if tipo == "usb":
        resultado = editar_camera_usb(
            camera_uid=camera_uid,
            nome=nome,
        )

        return jsonify(resultado), (
            200
            if resultado.get("sucesso")
            else _status_erro(resultado)
        )

    conexao = camera.get(
        "conexao"
    ) or {}

    fonte = _texto(
        dados.get("fonte")
        or conexao.get("fonte")
    )

    if not fonte:
        return jsonify(
            {
                "sucesso": False,
                "erro": "URL_STREAM_OBRIGATORIA",
            }
        ), 400

    onvif = dados.get("onvif")

    if onvif is None:
        onvif = conexao.get("onvif")

    resultado = editar_camera_rede(
        camera_uid=camera_uid,
        nome=nome,
        fonte=fonte,
        onvif=onvif,
    )

    return jsonify(resultado), (
        200
        if resultado.get("sucesso")
        else _status_erro(resultado)
    )


# ============================================================
# REMOCAO
# ============================================================

@app.route(
    "/api/front/cameras/<camera_uid>",
    methods=["DELETE", "OPTIONS"],
)
def remover_camera_api(
    camera_uid: str,
):
    if request.method == "OPTIONS":
        return "", 204

    vinculos = verificar_vinculos_camera(
        camera_uid
    )

    if not vinculos.get("sucesso"):
        return jsonify(vinculos), _status_erro(
            vinculos
        )

    if vinculos.get("vinculada"):
        return jsonify(
            {
                "sucesso": False,
                "erro": "CAMERA_POSSUI_VINCULOS",
                "vinculos": vinculos.get(
                    "ambientes",
                    [],
                ),
                "quantidade_vinculos": vinculos.get(
                    "quantidade_ambientes",
                    0,
                ),
            }
        ), 409

    resultado = remover_camera(
        camera_uid
    )

    if (
        not resultado.get("sucesso")
        and resultado.get("erro")
        == "CAMERA_VINCULADA_A_AMBIENTE"
    ):
        resultado = {
            "sucesso": False,
            "erro": "CAMERA_POSSUI_VINCULOS",
            "vinculos": resultado.get(
                "ambientes",
                [],
            ),
        }

    return jsonify(resultado), (
        200
        if resultado.get("sucesso")
        else _status_erro(resultado)
    )


# ============================================================
# TERMINAL — HELPERS
# ============================================================

def _descricao_camera_cadastrada(
    camera: Dict[str, Any],
) -> str:
    tipo = _texto(
        camera.get("tipo")
    ).lower()

    nome = _texto(
        camera.get("nome")
    ) or "Camera"

    if tipo == "usb":
        ultimo_runtime = camera.get(
            "ultimo_runtime"
        ) or {}

        indice = ultimo_runtime.get(
            "indice_usb"
        )

        identidade = camera.get(
            "identidade"
        ) or {}

        dispositivo = (
            identidade.get("nome_dispositivo")
            or nome
        )

        indice_texto = (
            str(indice)
            if isinstance(indice, int)
            else "-"
        )

        return (
            f"{nome} | USB | indice {indice_texto} "
            f"| {dispositivo}"
        )

    conexao = camera.get(
        "conexao"
    ) or {}

    host = (
        conexao.get("host")
        or conexao.get("ip")
        or "-"
    )

    porta = (
        conexao.get("porta")
        if conexao.get("porta") is not None
        else "-"
    )

    return (
        f"{nome} | {tipo.upper()} | "
        f"{host}:{porta}"
    )


def _listar_cadastradas_terminal():
    try:
        resultado = listar_cameras()
    except Exception as erro:
        print(
            f"Erro ao consultar cameras: {erro}"
        )
        return []

    if not isinstance(resultado, dict):
        return []

    if not resultado.get("sucesso"):
        return []

    return [
        camera
        for camera in (
            resultado.get("cameras")
            or []
        )
        if isinstance(camera, dict)
    ]


def _mostrar_cadastradas_terminal(
    titulo="CAMERAS CADASTRADAS",
):
    cameras = _listar_cadastradas_terminal()

    print(titulo)
    print("------------------------------------------")

    if not cameras:
        print("Nenhuma camera cadastrada.")
        return cameras

    for indice, camera in enumerate(
        cameras,
        start=1,
    ):
        print(
            f"[{indice}] "
            f"{_descricao_camera_cadastrada(camera)}"
        )

    return cameras


def _buscar_todas_cameras_terminal():
    encontradas = []

    print()
    print("Buscando cameras...")
    print()

    try:
        resultado_rede = buscar_cameras()

        if isinstance(
            resultado_rede,
            dict,
        ):
            resultado_rede = (
                _normalizar_busca_rede(
                    resultado_rede
                )
            )

            if resultado_rede.get(
                "sucesso"
            ):
                for candidato in (
                    resultado_rede.get(
                        "candidatos"
                    )
                    or []
                ):
                    if not isinstance(
                        candidato,
                        dict,
                    ):
                        continue

                    item = deepcopy(
                        candidato
                    )
                    item["_origem"] = "rede"
                    encontradas.append(
                        item
                    )

    except Exception as erro:
        print(
            f"⚠️ Busca de rede falhou: {erro}"
        )

    try:
        resultado_usb = buscar_cameras_usb()

        if (
            isinstance(
                resultado_usb,
                dict,
            )
            and resultado_usb.get(
                "sucesso"
            )
        ):
            for camera in (
                resultado_usb.get(
                    "cameras"
                )
                or []
            ):
                if not isinstance(
                    camera,
                    dict,
                ):
                    continue

                item = deepcopy(
                    camera
                )
                item["_origem"] = "usb"
                encontradas.append(
                    item
                )

    except Exception as erro:
        print(
            f"⚠️ Busca USB falhou: {erro}"
        )

    return encontradas


def _descricao_camera_encontrada(
    item: Dict[str, Any],
) -> str:
    origem = item.get("_origem")

    if origem == "usb":
        nome = (
            item.get("nome_dispositivo")
            or "Camera USB"
        )

        return (
            f"{nome} | USB | "
            f"indice {item.get('indice')}"
        )

    nome = (
        item.get("nome_onvif")
        or item.get("nome")
        or "Camera de rede"
    )

    ip = item.get("ip") or "-"

    portas = item.get("portas") or []

    portas_texto = (
        ",".join(
            str(porta)
            for porta in portas
        )
        if portas
        else "-"
    )

    protocolos = item.get(
        "protocolos"
    ) or []

    protocolo = (
        "/".join(
            str(valor).upper()
            for valor in protocolos
        )
        if protocolos
        else "REDE"
    )

    return (
        f"{nome} | {protocolo} | "
        f"{ip} | portas {portas_texto}"
    )


def _testar_camera_encontrada(
    item: Dict[str, Any],
):
    if item.get("_origem") == "usb":
        indice = item.get("indice")

        if not isinstance(indice, int):
            return {
                "sucesso": False,
                "erro": "INDICE_USB_INVALIDO",
            }

        return testar_camera_usb(
            indice
        )

    return testar_camera_descoberta(
        item
    )


# ============================================================
# TERMINAL — BUSCAR
# ============================================================

def buscar_cameras_terminal():
    print()
    print("=== BUSCAR CAMERAS ===")

    encontradas = (
        _buscar_todas_cameras_terminal()
    )

    print()
    print("CAMERAS ENCONTRADAS")
    print("------------------------------------------")

    if not encontradas:
        print("Nenhuma camera encontrada.")
    else:
        for indice, item in enumerate(
            encontradas,
            start=1,
        ):
            print(
                f"[{indice}] "
                f"{_descricao_camera_encontrada(item)}"
            )

    print()
    print("[M] Informar outra URL manualmente")
    print("[0] Voltar")
    print()

    escolha = input(
        "Selecione uma camera: "
    ).strip()

    if escolha == "0":
        return

    if escolha.lower() in {
        "m",
        "manual",
    }:
        fonte = input(
            "URL RTSP/HTTP: "
        ).strip()

        if not fonte:
            print(
                "Erro: URL_STREAM_OBRIGATORIA"
            )
            return

        usuario = input(
            "Usuario (ENTER se nao tiver): "
        ).strip() or None

        senha = input(
            "Senha (ENTER se nao tiver): "
        ).strip() or None

        resultado = testar_camera_manual(
            fonte,
            usuario=usuario,
            senha=senha,
        )

        print()
        print("Resultado:")
        print(resultado)
        return

    try:
        indice = int(escolha)
    except ValueError:
        print("Opcao invalida.")
        return

    if not (
        1 <= indice <= len(encontradas)
    ):
        print("Opcao invalida.")
        return

    selecionada = encontradas[
        indice - 1
    ]

    print()
    print(
        "Camera selecionada:"
    )
    print(
        _descricao_camera_encontrada(
            selecionada
        )
    )

    resultado = _testar_camera_encontrada(
        selecionada
    )

    print()
    print("Teste:")
    print(resultado)


# ============================================================
# TERMINAL — TESTAR
# ============================================================

def testar_camera_terminal():
    print()
    print("=== TESTAR CAMERA ===")
    print()

    cadastradas = (
        _mostrar_cadastradas_terminal(
            "CAMERAS CADASTRADAS"
        )
    )

    print()
    print("[M] Informar outra URL manualmente")
    print("[0] Voltar")
    print()

    escolha = input(
        "Selecione a camera para testar: "
    ).strip()

    if escolha == "0":
        return

    if escolha.lower() in {
        "m",
        "manual",
    }:
        fonte = input(
            "URL RTSP/HTTP: "
        ).strip()

        if not fonte:
            print(
                "Erro: URL_STREAM_OBRIGATORIA"
            )
            return

        usuario = input(
            "Usuario (ENTER se nao tiver): "
        ).strip() or None

        senha = input(
            "Senha (ENTER se nao tiver): "
        ).strip() or None

        resultado = testar_camera_manual(
            fonte,
            usuario=usuario,
            senha=senha,
        )

        print()
        print("Resultado:")
        print(resultado)
        return

    try:
        indice = int(escolha)
    except ValueError:
        print("Opcao invalida.")
        return

    if not (
        1 <= indice <= len(cadastradas)
    ):
        print("Opcao invalida.")
        return

    camera = cadastradas[
        indice - 1
    ]

    tipo = _texto(
        camera.get("tipo")
    ).lower()

    nome = _texto(
        camera.get("nome")
    ) or "Camera"

    print()
    print(
        f"Testando camera cadastrada: {nome}"
    )

    if tipo == "usb":
        camera_uid = _texto(
            camera.get("camera_uid")
        )

        resolucao = resolver_camera_usb(
            camera_uid
        )

        dados_resolucao = (
            resolucao.get("resolucao")
            if isinstance(
                resolucao,
                dict,
            )
            else {}
        ) or {}

        indice_usb = dados_resolucao.get(
            "indice_runtime"
        )

        if not (
            isinstance(
                resolucao,
                dict,
            )
            and resolucao.get(
                "sucesso"
            )
            and isinstance(
                indice_usb,
                int,
            )
        ):
            resultado = {
                "sucesso": False,
                "erro": (
                    dados_resolucao.get(
                        "motivo"
                    )
                    or (
                        resolucao.get("erro")
                        if isinstance(
                            resolucao,
                            dict,
                        )
                        else None
                    )
                    or "CAMERA_USB_NAO_RESOLVIDA"
                ),
            }
        else:
            resultado = testar_camera_usb(
                indice_usb
            )

    else:
        conexao = camera.get(
            "conexao"
        ) or {}

        fonte = _texto(
            conexao.get("fonte")
        )

        if not fonte:
            resultado = {
                "sucesso": False,
                "erro": "FONTE_CAMERA_NAO_CONFIGURADA",
            }
        else:
            resultado = testar_camera_manual(
                fonte
            )

    print()
    print("Resultado:")
    print(resultado)


# ============================================================
# TERMINAL — CADASTRAR
# ============================================================

def cadastrar_camera_terminal():
    print()
    print("=== CADASTRAR CAMERA ===")

    encontradas = (
        _buscar_todas_cameras_terminal()
    )

    print()
    print("CAMERAS ENCONTRADAS")
    print("------------------------------------------")

    if not encontradas:
        print("Nenhuma camera encontrada.")
    else:
        for indice, item in enumerate(
            encontradas,
            start=1,
        ):
            print(
                f"[{indice}] "
                f"{_descricao_camera_encontrada(item)}"
            )

    print()
    print("[M] Informar outra URL manualmente")
    print("[0] Voltar")
    print()

    escolha = input(
        "Selecione a camera para cadastrar: "
    ).strip()

    if escolha == "0":
        return

    if escolha.lower() in {
        "m",
        "manual",
    }:
        fonte = input(
            "URL RTSP/HTTP: "
        ).strip()

        if not fonte:
            print(
                "Erro: URL_STREAM_OBRIGATORIA"
            )
            return

        usuario = input(
            "Usuario (ENTER se nao tiver): "
        ).strip() or None

        senha = input(
            "Senha (ENTER se nao tiver): "
        ).strip() or None

        teste = testar_camera_manual(
            fonte,
            usuario=usuario,
            senha=senha,
        )

        print()
        print("Teste:")
        print(teste)

        if not teste.get("sucesso"):
            print("Camera nao cadastrada.")
            return

        nome = input(
            "Nome da camera: "
        ).strip()

        if not nome:
            print(
                "Erro: NOME_CAMERA_OBRIGATORIO"
            )
            return

        confirmar = input(
            "Confirmar cadastro? [s/N]: "
        ).strip().lower()

        if confirmar not in {
            "s",
            "sim",
            "y",
            "yes",
        }:
            print("Cadastro cancelado.")
            return

        resultado = cadastrar_camera_rede(
            nome=nome,
            fonte=(
                teste.get("fonte")
                or fonte
            ),
            onvif=False,
            portas_detectadas=(
                [teste["porta"]]
                if teste.get("porta")
                else []
            ),
        )

        print()
        print("Resultado:")
        print(resultado)
        return

    try:
        indice = int(escolha)
    except ValueError:
        print("Opcao invalida.")
        return

    if not (
        1 <= indice <= len(encontradas)
    ):
        print("Opcao invalida.")
        return

    selecionada = encontradas[
        indice - 1
    ]

    teste = _testar_camera_encontrada(
        selecionada
    )

    print()
    print("Teste:")
    print(teste)

    if not teste.get("sucesso"):
        print("Camera nao cadastrada.")
        return

    nome_padrao = (
        selecionada.get("nome_dispositivo")
        or selecionada.get("nome_onvif")
        or selecionada.get("nome")
        or "Camera"
    )

    nome = input(
        f"Nome da camera [{nome_padrao}]: "
    ).strip() or str(nome_padrao)

    confirmar = input(
        "Confirmar cadastro? [s/N]: "
    ).strip().lower()

    if confirmar not in {
        "s",
        "sim",
        "y",
        "yes",
    }:
        print("Cadastro cancelado.")
        return

    if selecionada.get("_origem") == "usb":
        indice_usb = selecionada.get(
            "indice"
        )

        resultado = cadastrar_camera_usb(
            indice=indice_usb,
            nome=nome,
        )

    else:
        resultado = cadastrar_camera_rede(
            nome=nome,
            fonte=teste.get("fonte"),
            onvif=bool(
                selecionada.get("onvif")
            ),
            portas_detectadas=_lista_portas(
                selecionada.get("portas")
            ),
        )

    print()
    print("Resultado:")
    print(resultado)


# ============================================================
# TERMINAL — CONSULTA
# ============================================================

def consultar_cameras_terminal():
    print()
    print("=== CONSULTAR CAMERAS ===")

    resultado = listar_cameras_com_status()

    if not resultado.get("sucesso"):
        print(resultado)
        return

    cameras = resultado.get(
        "cameras"
    ) or []

    print(
        f"Quantidade: {len(cameras)}"
    )

    if not cameras:
        print(
            "Nenhuma camera cadastrada."
        )
        return

    for indice, camera in enumerate(
        cameras,
        start=1,
    ):
        print()
        print("------------------------------------------")
        print(
            f"[{indice}] {camera.get('nome')} "
            f"| {str(camera.get('tipo') or '').upper()} "
            f"| {camera.get('status')}"
        )
        print(
            f"UID: {camera.get('camera_uid')}"
        )
        print(
            f"Resolucao: "
            f"{camera.get('largura')}x{camera.get('altura')}"
        )
        print(
            f"FPS: {camera.get('fps')}"
        )


# ============================================================
# API
# ============================================================

def iniciar_api():
    print()
    print("==========================================")
    print(" API UNIFICADA DE CAMERAS")
    print("==========================================")
    print(
        f"http://{HOST}:{PORTA}"
    )
    print("==========================================")
    print()

    app.run(
        host=HOST,
        port=PORTA,
        debug=False,
        use_reloader=False,
        threaded=True,
    )


# ============================================================
# MENU LOCAL
# ============================================================

def menu_terminal():
    while True:
        print()
        print("==========================================")
        print(" CAMERAS")
        print("==========================================")
        print("[1] Buscar cameras")
        print("[2] Testar camera")
        print("[3] Cadastrar camera")
        print("[4] Consultar cameras")
        print("[5] Iniciar API para o frontend")
        print("[6] Sair")
        print("==========================================")

        opcao = input(
            "Selecione uma opcao: "
        ).strip()

        if opcao == "1":
            buscar_cameras_terminal()

        elif opcao == "2":
            testar_camera_terminal()

        elif opcao == "3":
            cadastrar_camera_terminal()

        elif opcao == "4":
            consultar_cameras_terminal()

        elif opcao == "5":
            iniciar_api()

        elif opcao == "6":
            break

        else:
            print("Opcao invalida.")


if __name__ == "__main__":
    menu_terminal()

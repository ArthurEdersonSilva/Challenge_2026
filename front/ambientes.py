from __future__ import annotations

import base64
import os
import sys
from typing import Any

from flask import (
    Flask,
    jsonify,
    request,
    send_file,
)


# ============================================================
# AJUSTE DE IMPORT DO PROJETO
# ============================================================

RAIZ_PROJETO = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__),
        "..",
    )
)

if RAIZ_PROJETO not in sys.path:
    sys.path.insert(
        0,
        RAIZ_PROJETO,
    )


from services.ambiente_service import (  # noqa: E402
    capturar_foto_ambiente,
    criar_ambiente,
    definir_roi,
    editar_ambiente_basico,
    finalizar_ambiente,
    listar_ambientes_consulta,
    listar_cameras_para_ambiente,
    listar_rois,
    obter_detalhes_ambiente_consulta,
    obter_foto_ambiente,
    obter_revisao_ambiente,
    remover_ambiente,
    remover_foto_ambiente,
    remover_roi,
    salvar_foto_ambiente,
)


# ============================================================
# CONFIGURAÇÃO
# ============================================================

app = Flask(__name__)

HOST = "127.0.0.1"
PORTA = 5003


# ============================================================
# HELPERS
# ============================================================

def _json_body() -> dict[str, Any]:
    dados = request.get_json(
        silent=True
    )
    return (
        dados
        if isinstance(dados, dict)
        else {}
    )


def _status_http(
    resultado: dict[str, Any],
    sucesso: int = 200,
) -> int:
    if resultado.get("sucesso"):
        return sucesso

    erro = str(
        resultado.get("erro")
        or ""
    ).strip().upper()

    if erro in {
        "AMBIENTE_NAO_ENCONTRADO",
        "FOTO_AMBIENTE_NAO_DEFINIDA",
        "ARQUIVO_FOTO_AMBIENTE_NAO_ENCONTRADO",
        "ROI_NAO_DEFINIDA",
        "CAMERA_NAO_ENCONTRADA",
    }:
        return 404

    if erro in {
        "NOME_AMBIENTE_JA_EXISTE",
    }:
        return 409

    if erro in {
        "CAMERA_INDISPONIVEL",
        "STREAM_INDISPONIVEL",
    }:
        return 503

    return 400


def _enriquecer_foto(
    ambiente: dict[str, Any],
) -> dict[str, Any]:
    resposta = dict(
        ambiente
        or {}
    )

    ambiente_id = str(
        resposta.get("ambiente_id")
        or ""
    ).strip()

    foto = str(
        resposta.get("foto_ambiente")
        or ""
    ).strip()

    resposta["foto_url"] = (
        f"/api/front/ambientes/"
        f"{ambiente_id}/foto"
        if ambiente_id and foto
        else None
    )

    return resposta


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
    "/api/front/ambientes/health",
    methods=["GET"],
)
def health():
    return jsonify(
        {
            "sucesso": True,
            "erro": None,
            "servico": "ambientes",
        }
    ), 200


# ============================================================
# CÂMERAS DISPONÍVEIS
# ============================================================

@app.route(
    "/api/front/ambientes/cameras",
    methods=["GET", "OPTIONS"],
)
def cameras_disponiveis_api():
    if request.method == "OPTIONS":
        return "", 204

    resultado = (
        listar_cameras_para_ambiente()
    )

    return jsonify(resultado), _status_http(
        resultado
    )


# ============================================================
# CRIAR / LISTAR
# ============================================================

@app.route(
    "/api/front/ambientes",
    methods=["POST", "GET", "OPTIONS"],
)
def ambientes_api():
    if request.method == "OPTIONS":
        return "", 204

    if request.method == "GET":
        resultado = (
            listar_ambientes_consulta(
                busca=request.args.get(
                    "busca"
                ),
                status=request.args.get(
                    "status"
                ),
                camera_uid=request.args.get(
                    "camera_uid"
                ),
                epi=request.args.get(
                    "epi"
                ),
                pagina=request.args.get(
                    "pagina",
                    1,
                ),
                por_pagina=request.args.get(
                    "por_pagina",
                    20,
                ),
            )
        )

        if resultado.get("sucesso"):
            resultado = dict(
                resultado
            )

            resultado["ambientes"] = [
                _enriquecer_foto(
                    item
                )
                for item in (
                    resultado.get(
                        "ambientes"
                    )
                    or []
                )
            ]

        return jsonify(resultado), _status_http(
            resultado
        )

    dados = _json_body()

    camera_uids = dados.get(
        "camera_uids"
    )

    # Câmera é OPCIONAL.
    # [] = ambiente sem câmera.
    if camera_uids is None:
        camera_uids = []

    if not isinstance(
        camera_uids,
        list,
    ):
        return jsonify(
            {
                "sucesso": False,
                "erro": "CAMERA_UIDS_INVALIDOS",
            }
        ), 400

    resultado = criar_ambiente(
        nome=str(
            dados.get("nome")
            or ""
        ),
        descricao=str(
            dados.get("descricao")
            or ""
        ),
        camera_uids=camera_uids,
        epis_obrigatorios=(
            dados.get(
                "epis_obrigatorios"
            )
            if isinstance(
                dados.get(
                    "epis_obrigatorios"
                ),
                list,
            )
            else []
        ),
    )

    if not resultado.get("sucesso"):
        return jsonify(resultado), _status_http(
            resultado
        )

    ambiente = resultado.get(
        "ambiente"
    ) or {}

    ambiente_id = str(
        ambiente.get("ambiente_id")
        or ""
    )

    foto_base64 = (
        dados.get("foto_base64")
        or dados.get("imagem_base64")
    )

    if foto_base64:
        foto = salvar_foto_ambiente(
            ambiente_id=ambiente_id,
            imagem_base64=str(
                foto_base64
            ),
        )

        if not foto.get("sucesso"):
            # O ambiente continua salvo; o frontend pode
            # reenviar a foto sem precisar recriá-lo.
            resposta = dict(
                resultado
            )
            resposta["foto"] = foto
            resposta["ambiente"] = (
                _enriquecer_foto(
                    ambiente
                )
            )

            return jsonify(
                resposta
            ), 207

        ambiente["foto_ambiente"] = (
            foto.get("foto_ambiente")
        )

    resultado = dict(
        resultado
    )
    resultado["ambiente"] = (
        _enriquecer_foto(
            ambiente
        )
    )

    return jsonify(resultado), 201


# ============================================================
# DETALHE / EDIÇÃO / REMOÇÃO
# ============================================================

@app.route(
    "/api/front/ambientes/<ambiente_id>",
    methods=[
        "GET",
        "PUT",
        "DELETE",
        "OPTIONS",
    ],
)
def ambiente_detalhe_api(
    ambiente_id: str,
):
    if request.method == "OPTIONS":
        return "", 204

    if request.method == "GET":
        resultado = (
            obter_detalhes_ambiente_consulta(
                ambiente_id
            )
        )

        if resultado.get("sucesso"):
            resultado = (
                _enriquecer_foto(
                    resultado
                )
            )

        return jsonify(resultado), _status_http(
            resultado
        )

    if request.method == "DELETE":
        resultado = remover_ambiente(
            ambiente_id
        )

        return jsonify(resultado), _status_http(
            resultado
        )

    dados = _json_body()

    kwargs: dict[str, Any] = {}

    if "nome" in dados:
        kwargs["nome"] = dados.get(
            "nome"
        )

    if "descricao" in dados:
        kwargs["descricao"] = dados.get(
            "descricao"
        )

    if "camera_uids" in dados:
        camera_uids = dados.get(
            "camera_uids"
        )

        if not isinstance(
            camera_uids,
            list,
        ):
            return jsonify(
                {
                    "sucesso": False,
                    "erro": "CAMERA_UIDS_INVALIDOS",
                }
            ), 400

        # [] desvincula todas as câmeras.
        kwargs["camera_uids"] = (
            camera_uids
        )

    if "epis_obrigatorios" in dados:
        epis = dados.get(
            "epis_obrigatorios"
        )

        if not isinstance(
            epis,
            list,
        ):
            return jsonify(
                {
                    "sucesso": False,
                    "erro": "EPIS_OBRIGATORIOS_INVALIDOS",
                }
            ), 400

        kwargs["epis_obrigatorios"] = (
            epis
        )

    if "calibrado" in dados:
        kwargs["calibrado"] = bool(
            dados.get("calibrado")
        )

    resultado = editar_ambiente_basico(
        ambiente_id=ambiente_id,
        **kwargs,
    )

    if resultado.get("sucesso"):
        resultado = dict(
            resultado
        )
        resultado["ambiente"] = (
            _enriquecer_foto(
                resultado.get(
                    "ambiente"
                )
                or {}
            )
        )

    return jsonify(resultado), _status_http(
        resultado
    )


# ============================================================
# FOTO
# ============================================================

@app.route(
    "/api/front/ambientes/<ambiente_id>/foto",
    methods=[
        "GET",
        "POST",
        "DELETE",
        "OPTIONS",
    ],
)
def foto_ambiente_api(
    ambiente_id: str,
):
    if request.method == "OPTIONS":
        return "", 204

    if request.method == "GET":
        resultado = obter_foto_ambiente(
            ambiente_id
        )

        if not resultado.get("sucesso"):
            return jsonify(
                resultado
            ), _status_http(
                resultado
            )

        return send_file(
            resultado[
                "caminho_absoluto"
            ],
            mimetype="image/jpeg",
            conditional=True,
        )

    if request.method == "DELETE":
        resultado = remover_foto_ambiente(
            ambiente_id
        )

        return jsonify(resultado), _status_http(
            resultado
        )

    dados = _json_body()

    imagem_base64 = (
        dados.get("foto_base64")
        or dados.get("imagem_base64")
    )

    resultado = salvar_foto_ambiente(
        ambiente_id=ambiente_id,
        imagem_base64=str(
            imagem_base64
            or ""
        ),
    )

    return jsonify(resultado), _status_http(
        resultado,
        sucesso=201,
    )


@app.route(
    "/api/front/ambientes/<ambiente_id>/foto/capturar",
    methods=["POST", "OPTIONS"],
)
def capturar_foto_api(
    ambiente_id: str,
):
    if request.method == "OPTIONS":
        return "", 204

    dados = _json_body()

    resultado = capturar_foto_ambiente(
        ambiente_id=ambiente_id,
        session_id=str(
            dados.get("session_id")
            or ""
        ),
    )

    return jsonify(resultado), _status_http(
        resultado,
        sucesso=201,
    )


# ============================================================
# ROI
# ============================================================

@app.route(
    "/api/front/ambientes/<ambiente_id>/rois",
    methods=["GET", "OPTIONS"],
)
def listar_rois_api(
    ambiente_id: str,
):
    if request.method == "OPTIONS":
        return "", 204

    resultado = listar_rois(
        ambiente_id
    )

    return jsonify(resultado), _status_http(
        resultado
    )


@app.route(
    "/api/front/ambientes/<ambiente_id>/cameras/<camera_uid>/roi",
    methods=[
        "PUT",
        "DELETE",
        "OPTIONS",
    ],
)
def roi_camera_api(
    ambiente_id: str,
    camera_uid: str,
):
    if request.method == "OPTIONS":
        return "", 204

    if request.method == "DELETE":
        resultado = remover_roi(
            ambiente_id=ambiente_id,
            camera_uid=camera_uid,
        )

        return jsonify(resultado), _status_http(
            resultado
        )

    dados = _json_body()

    resultado = definir_roi(
        ambiente_id=ambiente_id,
        camera_uid=camera_uid,
        x1=dados.get("x1"),
        y1=dados.get("y1"),
        x2=dados.get("x2"),
        y2=dados.get("y2"),
    )

    return jsonify(resultado), _status_http(
        resultado
    )


# ============================================================
# REVISÃO / FINALIZAÇÃO
# ============================================================

@app.route(
    "/api/front/ambientes/<ambiente_id>/revisao",
    methods=["GET", "OPTIONS"],
)
def revisao_api(
    ambiente_id: str,
):
    if request.method == "OPTIONS":
        return "", 204

    resultado = obter_revisao_ambiente(
        ambiente_id
    )

    if resultado.get("sucesso"):
        resultado = _enriquecer_foto(
            resultado
        )

    return jsonify(resultado), _status_http(
        resultado
    )


@app.route(
    "/api/front/ambientes/<ambiente_id>/finalizar",
    methods=["POST", "OPTIONS"],
)
def finalizar_api(
    ambiente_id: str,
):
    if request.method == "OPTIONS":
        return "", 204

    resultado = finalizar_ambiente(
        ambiente_id
    )

    return jsonify(resultado), _status_http(
        resultado
    )


# ============================================================
# TERMINAL
# ============================================================

def _selecionar_cameras_terminal() -> list[str]:
    resultado = (
        listar_cameras_para_ambiente()
    )

    if not resultado.get("sucesso"):
        print(resultado)
        return []

    cameras = resultado.get(
        "cameras"
    ) or []

    print()
    print("CAMERAS CADASTRADAS")
    print("------------------------------------------")

    if not cameras:
        print("Nenhuma camera cadastrada.")
        print(
            "O ambiente pode ser criado sem camera."
        )
        return []

    for indice, camera in enumerate(
        cameras,
        start=1,
    ):
        print(
            f"[{indice}] "
            f"{camera.get('nome')} | "
            f"{str(camera.get('tipo') or '').upper()}"
        )

    print()
    print(
        "Digite os numeros separados por virgula."
    )
    print(
        "ENTER = criar ambiente sem camera."
    )

    escolha = input(
        "Cameras do ambiente: "
    ).strip()

    if not escolha:
        return []

    selecionadas: list[str] = []

    for parte in escolha.split(","):
        try:
            indice = int(
                parte.strip()
            )
        except ValueError:
            continue

        if 1 <= indice <= len(cameras):
            uid = str(
                cameras[
                    indice - 1
                ].get("camera_uid")
                or ""
            ).strip()

            if (
                uid
                and uid not in selecionadas
            ):
                selecionadas.append(
                    uid
                )

    return selecionadas


def cadastrar_terminal():
    print()
    print("=== CADASTRAR AMBIENTE ===")

    nome = input(
        "Nome: "
    ).strip()

    descricao = input(
        "Descricao: "
    ).strip()

    camera_uids = (
        _selecionar_cameras_terminal()
    )

    resultado = criar_ambiente(
        nome=nome,
        descricao=descricao,
        camera_uids=camera_uids,
    )

    print()
    print(resultado)

    if not resultado.get("sucesso"):
        return

    ambiente_id = str(
        (
            resultado.get("ambiente")
            or {}
        ).get("ambiente_id")
        or ""
    )

    caminho_foto = input(
        "Foto do ambiente "
        "(caminho local ou ENTER para salvar depois): "
    ).strip()

    if (
        caminho_foto
        and os.path.isfile(
            caminho_foto
        )
    ):
        try:
            with open(
                caminho_foto,
                "rb",
            ) as arquivo:
                imagem_base64 = (
                    base64.b64encode(
                        arquivo.read()
                    ).decode("ascii")
                )

            foto = salvar_foto_ambiente(
                ambiente_id,
                imagem_base64,
            )

            print()
            print("Foto:")
            print(foto)

        except Exception as erro:
            print(
                f"Erro ao ler foto: {erro}"
            )


def consultar_terminal():
    while True:
        print()
        print("=== CONSULTAR AMBIENTES ===")

        resultado = listar_ambientes_consulta(
            por_pagina=200
        )

        if not resultado.get("sucesso"):
            print(resultado)
            return

        ambientes = resultado.get(
            "ambientes"
        ) or []

        if not ambientes:
            print(
                "Nenhum ambiente cadastrado."
            )
            input(
                "ENTER para voltar..."
            )
            return

        print()

        for indice, ambiente in enumerate(
            ambientes,
            start=1,
        ):
            print(
                f"[{indice}] "
                f"{ambiente.get('nome')} | "
                f"{ambiente.get('status')} | "
                f"Cameras: "
                f"{ambiente.get('quantidade_cameras')} | "
                f"Foto: "
                f"{'SIM' if ambiente.get('possui_foto') else 'NAO'}"
            )

        print()
        print("[0] Voltar")
        print()

        escolha = input(
            "Selecione o ambiente: "
        ).strip()

        if escolha == "0":
            return

        try:
            indice_escolhido = int(
                escolha
            )
        except ValueError:
            print("Opcao invalida.")
            continue

        if not (
            1
            <= indice_escolhido
            <= len(ambientes)
        ):
            print("Opcao invalida.")
            continue

        ambiente_resumo = ambientes[
            indice_escolhido - 1
        ]

        ambiente_id = str(
            ambiente_resumo.get(
                "ambiente_id"
            )
            or ""
        ).strip()

        detalhes = (
            obter_detalhes_ambiente_consulta(
                ambiente_id
            )
        )

        print()
        print("==========================================")
        print(" DETALHES DO AMBIENTE")
        print("==========================================")

        if not detalhes.get("sucesso"):
            print(detalhes)
            input(
                "ENTER para voltar..."
            )
            continue

        print(
            f"Nome: {detalhes.get('nome')}"
        )
        print(
            f"Descricao: "
            f"{detalhes.get('descricao') or '-'}"
        )
        print(
            f"Status: {detalhes.get('status')}"
        )
        print(
            f"Calibrado: "
            f"{'SIM' if detalhes.get('calibrado') else 'NAO'}"
        )

        foto_relativa = str(
            detalhes.get("foto_ambiente")
            or ""
        ).strip()

        print(
            f"Foto: "
            f"{foto_relativa if foto_relativa else 'NAO CADASTRADA'}"
        )

        cameras = detalhes.get(
            "cameras"
        ) or []

        print()
        print("CAMERAS")
        print("------------------------------------------")

        if not cameras:
            print(
                "Nenhuma camera vinculada."
            )
        else:
            for indice_camera, camera in enumerate(
                cameras,
                start=1,
            ):
                print(
                    f"[{indice_camera}] "
                    f"{camera.get('nome')} | "
                    f"{str(camera.get('tipo') or '').upper()} | "
                    f"UID: {camera.get('camera_uid')}"
                )

        epis = detalhes.get(
            "epis_obrigatorios"
        ) or []

        print()
        print("EPIs OBRIGATORIOS")
        print("------------------------------------------")

        if epis:
            for epi in epis:
                print(
                    f"- {epi}"
                )
        else:
            print(
                "Nenhum EPI definido."
            )

        maquinarios = detalhes.get(
            "maquinarios"
        ) or []

        print()
        print("MAQUINARIOS")
        print("------------------------------------------")

        if maquinarios:
            for maquina in maquinarios:
                print(
                    f"- "
                    f"{maquina.get('nome') or maquina.get('id')}"
                )
        else:
            print(
                "Nenhum maquinario definido."
            )

        colaboradores = detalhes.get(
            "colaboradores"
        ) or []

        print()
        print("COLABORADORES")
        print("------------------------------------------")

        if colaboradores:
            for colaborador in colaboradores:
                nome_colaborador = (
                    colaborador.get("nome")
                    or colaborador.get("matricula")
                    or "Colaborador"
                )

                print(
                    f"- {nome_colaborador}"
                )
        else:
            print(
                "Nenhum colaborador vinculado."
            )

        print("==========================================")
        print()
        input(
            "ENTER para voltar a lista de ambientes..."
        )

def remover_terminal():
    consultar_terminal()

    ambiente_id = input(
        "ambiente_id para remover "
        "(ENTER para voltar): "
    ).strip()

    if not ambiente_id:
        return

    resultado = remover_ambiente(
        ambiente_id
    )

    print()
    print(resultado)


def iniciar_api():
    print()
    print("==========================================")
    print(" API DE AMBIENTES")
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


def menu_terminal():
    while True:
        print()
        print("==========================================")
        print(" AMBIENTES")
        print("==========================================")
        print("[1] Cadastrar ambiente")
        print("[2] Consultar ambientes")
        print("[3] Remover ambiente")
        print("[4] Iniciar API para o frontend")
        print("[5] Sair")
        print("==========================================")

        opcao = input(
            "Selecione uma opcao: "
        ).strip()

        if opcao == "1":
            cadastrar_terminal()

        elif opcao == "2":
            consultar_terminal()

        elif opcao == "3":
            remover_terminal()

        elif opcao == "4":
            iniciar_api()

        elif opcao == "5":
            break

        else:
            print("Opcao invalida.")


if __name__ == "__main__":
    menu_terminal()

from __future__ import annotations

import base64
import io
import os
import sys
import tempfile
from pathlib import Path
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


from services.evidencia_service import (  # noqa: E402
    exportar_evidencia,
    listar_evidencias,
    listar_opcoes_filtros_evidencias,
    obter_detalhes_evidencia,
    obter_imagem_evidencia,
)

from services.relatorio_service import (  # noqa: E402
    exportar_relatorio_pdf,
    gerar_relatorio_geral,
)


# ============================================================
# CONFIGURAÇÃO
# ============================================================

app = Flask(__name__)

HOST = "127.0.0.1"
PORTA = 5004


# ============================================================
# HELPERS
# ============================================================

def _texto(valor: Any) -> str | None:
    texto = str(valor or "").strip()
    return texto or None


def _inteiro(
    valor: Any,
    padrao: int,
) -> int:
    try:
        return int(valor)
    except (TypeError, ValueError):
        return padrao


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
        "EVIDENCIA_NAO_ENCONTRADA",
        "IMAGEM_EVIDENCIA_INDISPONIVEL",
    }:
        return 404

    if erro in {
        "PERIODO_INVALIDO",
        "DATA_INVALIDA",
        "TIPO_IMAGEM_INVALIDO",
    }:
        return 400

    return 500


def _filtros_request() -> dict[str, Any]:
    return {
        "data_inicio": _texto(
            request.args.get("data_inicio")
        ),
        "data_fim": _texto(
            request.args.get("data_fim")
        ),
        "ambiente": _texto(
            request.args.get("ambiente")
        ),
        "colaborador": _texto(
            request.args.get("colaborador")
        ),
        "epi": _texto(
            request.args.get("epi")
        ),
    }


def _evidencia_front(
    item: dict[str, Any],
) -> dict[str, Any]:
    saida = dict(item)

    evidencia_id = str(
        item.get("evidencia_id")
        or ""
    ).strip()

    if evidencia_id:
        saida["imagem_url"] = (
            f"/api/front/evidencias/"
            f"{evidencia_id}/imagem?tipo=frame"
        )

        saida["crop_url"] = (
            f"/api/front/evidencias/"
            f"{evidencia_id}/imagem?tipo=crop"
        )

        saida["detalhes_url"] = (
            f"/api/front/evidencias/"
            f"{evidencia_id}"
        )

        saida["exportar_url"] = (
            f"/api/front/evidencias/"
            f"{evidencia_id}/exportar"
        )

    return saida


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
        "GET, POST, OPTIONS"
    )

    return resposta


# ============================================================
# HEALTH
# ============================================================

@app.route(
    "/api/front/evidencias/health",
    methods=["GET"],
)
def health():
    return jsonify(
        {
            "sucesso": True,
            "erro": None,
            "servico": "evidencias-relatorios",
        }
    ), 200


# ============================================================
# FILTROS
# ============================================================

@app.route(
    "/api/front/evidencias/filtros",
    methods=["GET", "OPTIONS"],
)
def filtros_evidencias_api():
    if request.method == "OPTIONS":
        return "", 204

    resultado = (
        listar_opcoes_filtros_evidencias()
    )

    return jsonify(resultado), _status_http(
        resultado
    )


# ============================================================
# REGISTRO DE EVIDÊNCIAS
# ============================================================

@app.route(
    "/api/front/evidencias",
    methods=["GET", "OPTIONS"],
)
def listar_evidencias_api():
    if request.method == "OPTIONS":
        return "", 204

    filtros = _filtros_request()

    resultado = listar_evidencias(
        **filtros,
        busca=_texto(
            request.args.get("busca")
        ),
        pagina=_inteiro(
            request.args.get("pagina"),
            1,
        ),
        por_pagina=_inteiro(
            request.args.get("por_pagina"),
            20,
        ),
    )

    if resultado.get("sucesso"):
        resposta = dict(resultado)

        resposta["evidencias"] = [
            _evidencia_front(item)
            for item in (
                resultado.get("evidencias")
                or []
            )
            if isinstance(item, dict)
        ]

        resultado = resposta

    return jsonify(resultado), _status_http(
        resultado
    )


@app.route(
    "/api/front/evidencias/<evidencia_id>",
    methods=["GET", "OPTIONS"],
)
def detalhes_evidencia_api(
    evidencia_id: str,
):
    if request.method == "OPTIONS":
        return "", 204

    resultado = obter_detalhes_evidencia(
        evidencia_id
    )

    if resultado.get("sucesso"):
        resposta = dict(resultado)

        evidencia = resposta.get(
            "evidencia"
        ) or {}

        resposta["evidencia"] = (
            _evidencia_front(
                evidencia
            )
        )

        resultado = resposta

    return jsonify(resultado), _status_http(
        resultado
    )


@app.route(
    "/api/front/evidencias/<evidencia_id>/imagem",
    methods=["GET", "OPTIONS"],
)
def imagem_evidencia_api(
    evidencia_id: str,
):
    if request.method == "OPTIONS":
        return "", 204

    tipo = _texto(
        request.args.get("tipo")
    ) or "frame"

    resultado = obter_imagem_evidencia(
        evidencia_id,
        tipo=tipo,
    )

    if not resultado.get("sucesso"):
        return jsonify(
            resultado
        ), _status_http(
            resultado
        )

    try:
        conteudo = base64.b64decode(
            resultado.get(
                "imagem_base64"
            )
            or "",
            validate=True,
        )
    except Exception:
        return jsonify(
            {
                "sucesso": False,
                "erro": "IMAGEM_EVIDENCIA_INVALIDA",
            }
        ), 500

    nome = (
        f"{evidencia_id}_"
        f"{tipo}.jpg"
    )

    return send_file(
        io.BytesIO(conteudo),
        mimetype=(
            resultado.get("mime_type")
            or "image/jpeg"
        ),
        download_name=nome,
        as_attachment=False,
    )


@app.route(
    "/api/front/evidencias/<evidencia_id>/exportar",
    methods=["GET", "POST", "OPTIONS"],
)
def exportar_evidencia_api(
    evidencia_id: str,
):
    if request.method == "OPTIONS":
        return "", 204

    pasta_temp = Path(
        tempfile.gettempdir()
    ) / "challenge_epi_exports"

    pasta_temp.mkdir(
        parents=True,
        exist_ok=True,
    )

    caminho = (
        pasta_temp
        / f"evidencia_{evidencia_id}.zip"
    )

    resultado = exportar_evidencia(
        evidencia_id=evidencia_id,
        destino=str(caminho),
    )

    if not resultado.get("sucesso"):
        return jsonify(
            resultado
        ), _status_http(
            resultado
        )

    arquivo = Path(
        resultado["arquivo"]
    )

    return send_file(
        arquivo,
        mimetype="application/zip",
        as_attachment=True,
        download_name=arquivo.name,
    )


# ============================================================
# RELATÓRIO GERAL
# ============================================================

@app.route(
    "/api/front/relatorios/geral",
    methods=["GET", "OPTIONS"],
)
def relatorio_geral_api():
    if request.method == "OPTIONS":
        return "", 204

    filtros = _filtros_request()

    resultado = gerar_relatorio_geral(
        **filtros,
        granularidade=(
            _texto(
                request.args.get(
                    "granularidade"
                )
            )
            or "DIARIO"
        ),
    )

    return jsonify(resultado), _status_http(
        resultado
    )


@app.route(
    "/api/front/relatorios/geral/pdf",
    methods=["GET", "POST", "OPTIONS"],
)
def relatorio_pdf_api():
    if request.method == "OPTIONS":
        return "", 204

    filtros = _filtros_request()

    granularidade = (
        _texto(
            request.args.get(
                "granularidade"
            )
        )
        or "DIARIO"
    )

    pasta_temp = Path(
        tempfile.gettempdir()
    ) / "challenge_epi_exports"

    pasta_temp.mkdir(
        parents=True,
        exist_ok=True,
    )

    caminho = (
        pasta_temp
        / "relatorio_geral.pdf"
    )

    resultado = exportar_relatorio_pdf(
        destino=str(caminho),
        **filtros,
        granularidade=granularidade,
    )

    if not resultado.get("sucesso"):
        return jsonify(
            resultado
        ), _status_http(
            resultado
        )

    arquivo = Path(
        resultado["arquivo"]
    )

    return send_file(
        arquivo,
        mimetype="application/pdf",
        as_attachment=True,
        download_name="relatorio_geral.pdf",
    )


# ============================================================
# TERMINAL — CONSULTA DE EVIDÊNCIAS
# ============================================================

def consultar_evidencias_terminal():
    while True:
        print()
        print("=== REGISTRO DE EVIDENCIAS ===")

        resultado = listar_evidencias(
            pagina=1,
            por_pagina=200,
        )

        if not resultado.get("sucesso"):
            print(resultado)
            return

        evidencias = resultado.get(
            "evidencias"
        ) or []

        if not evidencias:
            print(
                "Nenhuma evidencia registrada."
            )
            input(
                "ENTER para voltar..."
            )
            return

        print()

        for indice, item in enumerate(
            evidencias,
            start=1,
        ):
            print(
                f"[{indice}] "
                f"{item.get('data') or '-'} "
                f"{item.get('horario') or '-'} | "
                f"{item.get('nome') or 'DESCONHECIDO'} | "
                f"{item.get('ambiente_nome') or '-'} | "
                f"{item.get('infracao') or '-'} | "
                f"{item.get('camera_nome') or '-'}"
            )

        print()
        print("[0] Voltar")
        print()

        escolha = input(
            "Selecione a evidencia: "
        ).strip()

        if escolha == "0":
            return

        try:
            indice = int(escolha)
        except ValueError:
            print("Opcao invalida.")
            continue

        if not (
            1 <= indice <= len(evidencias)
        ):
            print("Opcao invalida.")
            continue

        evidencia = evidencias[
            indice - 1
        ]

        evidencia_id = str(
            evidencia.get(
                "evidencia_id"
            )
            or ""
        ).strip()

        detalhes = obter_detalhes_evidencia(
            evidencia_id
        )

        print()
        print("==========================================")
        print(" DETALHES DA EVIDENCIA")
        print("==========================================")

        if not detalhes.get("sucesso"):
            print(detalhes)
        else:
            item = detalhes.get(
                "evidencia"
            ) or {}

            print(
                f"ID: {item.get('evidencia_id')}"
            )
            print(
                f"Data: {item.get('data')}"
            )
            print(
                f"Horario: {item.get('horario')}"
            )
            print(
                f"Colaborador: "
                f"{item.get('nome')} "
                f"({item.get('matricula')})"
            )
            print(
                f"Ambiente: "
                f"{item.get('ambiente_nome')}"
            )
            print(
                f"Camera: "
                f"{item.get('camera_nome')}"
            )
            print(
                f"Infracao: "
                f"{item.get('infracao')}"
            )
            print(
                f"Imagem disponivel: "
                f"{'SIM' if item.get('imagem_disponivel') else 'NAO'}"
            )
            print(
                f"Confianca: "
                f"{item.get('confianca_deteccao')}"
            )
            print(
                f"Maquinario: "
                f"{item.get('maquinario_relacionado')}"
            )

            epis = item.get(
                "epis_analisados"
            ) or []

            print()
            print("EPIs ANALISADOS")
            print("------------------------------------------")

            if epis:
                for epi in epis:
                    print(
                        f"- {epi}"
                    )
            else:
                print(
                    "Metadata enriquecido nao disponivel."
                )

        print("==========================================")
        print()
        input(
            "ENTER para voltar a lista..."
        )


# ============================================================
# TERMINAL — RELATÓRIO
# ============================================================

def relatorio_terminal():
    print()
    print("=== RELATORIO GERAL ===")

    data_inicio = input(
        "Data inicial YYYY-MM-DD "
        "(ENTER = padrao): "
    ).strip() or None

    data_fim = input(
        "Data final YYYY-MM-DD "
        "(ENTER = hoje): "
    ).strip() or None

    resultado = gerar_relatorio_geral(
        data_inicio=data_inicio,
        data_fim=data_fim,
    )

    print()

    if not resultado.get("sucesso"):
        print(resultado)
        return

    indicadores = resultado.get(
        "indicadores"
    ) or {}

    def atual(chave):
        item = indicadores.get(
            chave
        ) or {}
        return item.get("atual", 0)

    print(
        f"Total de infracoes: "
        f"{atual('total_infracoes')}"
    )
    print(
        f"Colaboradores envolvidos: "
        f"{atual('colaboradores_envolvidos')}"
    )
    print(
        f"Ambientes com ocorrencias: "
        f"{atual('ambientes_com_ocorrencias')}"
    )
    print(
        f"Total de evidencias: "
        f"{atual('total_evidencias')}"
    )

    print()
    print("INFRACOES POR AMBIENTE")
    print("------------------------------------------")

    for item in (
        resultado.get(
            "infracoes_por_ambiente"
        )
        or []
    ):
        print(
            f"- {item.get('ambiente')}: "
            f"{item.get('infracoes')}"
        )

    print()
    print("INFRACOES POR EPI")
    print("------------------------------------------")

    for item in (
        resultado.get(
            "infracoes_por_epi"
        )
        or []
    ):
        print(
            f"- {item.get('epi')}: "
            f"{item.get('infracoes')}"
        )

    print()
    input(
        "ENTER para voltar..."
    )


def exportar_pdf_terminal():
    print()
    print("=== EXPORTAR RELATORIO PDF ===")

    data_inicio = input(
        "Data inicial YYYY-MM-DD "
        "(ENTER = padrao): "
    ).strip() or None

    data_fim = input(
        "Data final YYYY-MM-DD "
        "(ENTER = hoje): "
    ).strip() or None

    destino = input(
        "Destino do PDF "
        "(ENTER = relatorios/relatorio_geral.pdf): "
    ).strip()

    if not destino:
        destino = os.path.join(
            RAIZ_PROJETO,
            "relatorios",
            "relatorio_geral.pdf",
        )

    resultado = exportar_relatorio_pdf(
        destino=destino,
        data_inicio=data_inicio,
        data_fim=data_fim,
    )

    print()
    print(resultado)
    print()


# ============================================================
# API
# ============================================================

def iniciar_api():
    print()
    print("==========================================")
    print(" API DE EVIDENCIAS E RELATORIOS")
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
        print(" EVIDENCIAS")
        print("==========================================")
        print("[1] Consultar evidencias")
        print("[2] Relatorio geral")
        print("[3] Exportar relatorio PDF")
        print("[4] Iniciar API para o frontend")
        print("[5] Sair")
        print("==========================================")

        opcao = input(
            "Selecione uma opcao: "
        ).strip()

        if opcao == "1":
            consultar_evidencias_terminal()

        elif opcao == "2":
            relatorio_terminal()

        elif opcao == "3":
            exportar_pdf_terminal()

        elif opcao == "4":
            iniciar_api()

        elif opcao == "5":
            break

        else:
            print("Opcao invalida.")


if __name__ == "__main__":
    menu_terminal()

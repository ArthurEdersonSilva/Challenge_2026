from __future__ import annotations

import os
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from flask import Flask, after_this_request, jsonify, request, send_file
from flask_cors import CORS

from services.dashboard_infracoes_service import (
    listar_opcoes_filtros_dashboard,
    obter_dashboard_infracoes,
)
from services.evidencia_service import (
    listar_evidencias,
    listar_opcoes_filtros_evidencias,
    obter_detalhes_evidencia,
    obter_imagem_evidencia,
    exportar_evidencia,
)
from services.relatorio_service import (
    exportar_relatorio_pdf,
    gerar_relatorio_geral,
)


ERROS_404 = {
    "EVIDENCIA_NAO_ENCONTRADA",
    "IMAGEM_EVIDENCIA_INDISPONIVEL",
}

ERROS_500 = {
    "ERRO_EXPORTAR_EVIDENCIA",
}

ERROS_400 = {
    "DATA_INVALIDA",
    "PERIODO_INVALIDO",
    "TIPO_IMAGEM_INVALIDO",
}


def _valor_query(nome: str) -> Optional[str]:
    valor = request.args.get(nome)

    if valor is None:
        return None

    valor = valor.strip()
    return valor or None


def _status_http(resultado: Dict[str, Any]) -> int:
    if resultado.get("sucesso"):
        return 200

    erro = str(resultado.get("erro") or "")

    if erro in ERROS_404:
        return 404

    if erro in ERROS_400:
        return 400

    if erro in ERROS_500:
        return 500

    return 500


def _responder(resultado: Dict[str, Any]):
    return jsonify(resultado), _status_http(resultado)


def _filtros_comuns() -> Dict[str, Optional[str]]:
    return {
        "data_inicio": _valor_query("data_inicio"),
        "data_fim": _valor_query("data_fim"),
        "ambiente": _valor_query("ambiente"),
        "colaborador": _valor_query("colaborador"),
        "epi": _valor_query("epi"),
    }



def _contexto_autenticacao_local() -> Dict[str, Any]:
    """
    Adaptador local compatível com api_sistema.py.

    Headers atuais:
        X-Perfil: GERENCIAL | GESTOR | OPERADOR | COLABORADOR
        X-Matricula: opcional neste módulo gerencial

    Não representa autenticação definitiva de produção.
    """
    perfil = str(
        request.headers.get("X-Perfil") or ""
    ).strip().upper()

    matricula = str(
        request.headers.get("X-Matricula") or ""
    ).strip() or None

    if perfil not in {
        "GERENCIAL",
        "GESTOR",
        "OPERADOR",
        "COLABORADOR",
    }:
        return {
            "autenticado": False,
            "perfil": None,
            "matricula": None,
        }

    if perfil == "GESTOR":
        perfil = "GERENCIAL"

    if perfil == "COLABORADOR":
        perfil = "OPERADOR"

    return {
        "autenticado": True,
        "perfil": perfil,
        "matricula": matricula,
    }


def _proteger_rota_gerencial():
    contexto = _contexto_autenticacao_local()

    if not contexto.get("autenticado"):
        return jsonify(
            {
                "sucesso": False,
                "erro": "NAO_AUTENTICADO",
            }
        ), 401

    if contexto.get("perfil") != "GERENCIAL":
        return jsonify(
            {
                "sucesso": False,
                "erro": "ACESSO_NEGADO",
            }
        ), 403

    return None

def criar_app() -> Flask:
    app = Flask(__name__)

    origins_env = os.getenv(
        "CHALLENGE_FRONTEND_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173",
    )

    origins = [
        origem.strip()
        for origem in origins_env.split(",")
        if origem.strip()
    ]

    CORS(
        app,
        resources={
            r"/api/*": {
                "origins": origins,
            }
        },
    )

    @app.before_request
    def proteger_rotas_gerenciais():
        caminho = request.path

        protegido = (
            caminho.startswith("/api/dashboard-infracoes")
            or caminho.startswith("/api/evidencias")
            or caminho.startswith("/api/relatorios/geral")
        )

        if not protegido:
            return None

        return _proteger_rota_gerencial()

    @app.get("/api/health")
    def health():
        return jsonify(
            {
                "sucesso": True,
                "servico": "api_evidencias",
                "timestamp": datetime.now().astimezone().isoformat(),
            }
        )

    @app.get("/api/dashboard-infracoes")
    def dashboard_infracoes():
        filtros = _filtros_comuns()

        resultado = obter_dashboard_infracoes(
            **filtros,
            limite_recentes=(
                _valor_query("limite_recentes") or 20
            ),
        )

        return _responder(resultado)

    @app.get("/api/dashboard-infracoes/filtros")
    def dashboard_infracoes_filtros():
        return _responder(
            listar_opcoes_filtros_dashboard()
        )

    @app.get("/api/evidencias")
    def registro_evidencias():
        filtros = _filtros_comuns()

        resultado = listar_evidencias(
            **filtros,
            busca=_valor_query("busca"),
            pagina=_valor_query("pagina") or 1,
            por_pagina=_valor_query("por_pagina") or 20,
        )

        return _responder(resultado)

    @app.get("/api/evidencias/filtros")
    def evidencias_filtros():
        return _responder(
            listar_opcoes_filtros_evidencias()
        )

    @app.get("/api/evidencias/<evidencia_id>")
    def detalhes_evidencia(evidencia_id: str):
        return _responder(
            obter_detalhes_evidencia(
                evidencia_id
            )
        )

    @app.get("/api/evidencias/<evidencia_id>/imagem")
    def imagem_evidencia(evidencia_id: str):
        resultado = obter_imagem_evidencia(
            evidencia_id=evidencia_id,
            tipo=_valor_query("tipo") or "frame",
        )

        return _responder(resultado)

    @app.get("/api/evidencias/<evidencia_id>/exportar")
    def exportar_evidencia_http(evidencia_id: str):
        temporario = tempfile.NamedTemporaryFile(
            prefix=f"evidencia_{evidencia_id}_",
            suffix=".zip",
            delete=False,
        )
        caminho_temporario = Path(
            temporario.name
        )
        temporario.close()

        resultado = exportar_evidencia(
            evidencia_id=evidencia_id,
            destino=str(caminho_temporario),
        )

        if not resultado.get("sucesso"):
            try:
                caminho_temporario.unlink(
                    missing_ok=True
                )
            except Exception:
                pass

            return _responder(resultado)

        arquivo = Path(
            resultado["arquivo"]
        )

        @after_this_request
        def remover_zip_temporario(response):
            try:
                arquivo.unlink(
                    missing_ok=True
                )
            except Exception:
                pass
            return response

        return send_file(
            arquivo,
            mimetype="application/zip",
            as_attachment=True,
            download_name=(
                f"evidencia_{evidencia_id}.zip"
            ),
        )

    @app.get("/api/relatorios/geral")
    def relatorio_geral():
        filtros = _filtros_comuns()

        resultado = gerar_relatorio_geral(
            **filtros,
            granularidade=(
                _valor_query("granularidade")
                or "DIARIO"
            ),
        )

        return _responder(resultado)

    @app.post("/api/relatorios/geral/pdf")
    def relatorio_geral_pdf():
        payload = request.get_json(
            silent=True
        ) or {}

        filtros = {
            "data_inicio": payload.get(
                "data_inicio"
            ),
            "data_fim": payload.get(
                "data_fim"
            ),
            "ambiente": payload.get(
                "ambiente"
            ),
            "colaborador": payload.get(
                "colaborador"
            ),
            "epi": payload.get("epi"),
            "granularidade": (
                payload.get("granularidade")
                or "DIARIO"
            ),
        }

        temporario = tempfile.NamedTemporaryFile(
            prefix="relatorio_geral_",
            suffix=".pdf",
            delete=False,
        )
        caminho_temporario = Path(
            temporario.name
        )
        temporario.close()

        resultado = exportar_relatorio_pdf(
            destino=str(caminho_temporario),
            **filtros,
        )

        if not resultado.get("sucesso"):
            try:
                caminho_temporario.unlink(
                    missing_ok=True
                )
            except Exception:
                pass

            return _responder(resultado)

        arquivo = Path(
            resultado["arquivo"]
        )

        @after_this_request
        def remover_temporario(response):
            try:
                arquivo.unlink(
                    missing_ok=True
                )
            except Exception:
                pass
            return response

        return send_file(
            arquivo,
            mimetype="application/pdf",
            as_attachment=True,
            download_name="relatorio_geral.pdf",
        )

    return app


app = criar_app()


if __name__ == "__main__":
    porta = int(
        os.getenv(
            "CHALLENGE_API_PORT",
            "5000",
        )
    )

    app.run(
        host="127.0.0.1",
        port=porta,
        debug=False,
    )

from __future__ import annotations

import importlib
import io
import unittest
from unittest.mock import patch

import cv2
import numpy as np


class TestHTTPAPISistema(unittest.TestCase):
    """
    Testes HTTP esperados para api_sistema.py.

    Cobertura:
    - Câmeras
    - Ambientes
    - Colaboradores
    - Monitoramento do Colaborador
    - Dashboard Gerencial

    Códigos HTTP exigidos:
    - 200 / 201 sucesso
    - 400 validação
    - 401 não autenticado
    - 403 permissão
    - 404 recurso inexistente
    - 409 conflito/vínculo/duplicidade
    - 500 erro interno inesperado
    - 503 recurso/runtime indisponível

    Contrato de autenticação esperado no módulo:
        obter_contexto_autenticacao() -> {
            "autenticado": bool,
            "perfil": "GERENCIAL" | "OPERADOR" | None,
            "matricula": str | None,
        }

    Os testes usam patch desse resolvedor. Isso permite testar as permissões
    HTTP sem definir ainda como será a autenticação definitiva do frontend.

    IMPORTANTE:
    - nenhum service real é executado;
    - nenhum CSV/JSON/imagem real é alterado;
    - nenhuma câmera é aberta;
    - nenhuma IA é executada.
    """

    @classmethod
    def setUpClass(cls):
        try:
            cls.api = importlib.import_module("api_sistema")
        except ModuleNotFoundError as erro:
            raise AssertionError(
                "Módulo api_sistema ainda não foi implementado. "
                f"Detalhe: {erro}"
            ) from erro

        if not hasattr(cls.api, "app"):
            raise AssertionError(
                "api_sistema.py deve expor a aplicação Flask como `app`."
            )

        cls.api.app.config.update(
            TESTING=True,
            PROPAGATE_EXCEPTIONS=False,
        )

    def setUp(self):
        self.client = self.api.app.test_client()

    # ============================================================
    # HELPERS
    # ============================================================

    def _auth(self, perfil="GERENCIAL", matricula="557079"):
        return patch.object(
            self.api,
            "obter_contexto_autenticacao",
            return_value={
                "autenticado": True,
                "perfil": perfil,
                "matricula": matricula,
            },
        )

    def _sem_auth(self):
        return patch.object(
            self.api,
            "obter_contexto_autenticacao",
            return_value={
                "autenticado": False,
                "perfil": None,
                "matricula": None,
            },
        )

    @staticmethod
    def _jpeg_bytes():
        imagem = np.zeros((32, 32, 3), dtype=np.uint8)
        imagem[:, :] = (120, 120, 120)
        sucesso, buffer = cv2.imencode(".jpg", imagem)
        if not sucesso:
            raise AssertionError("Falha ao gerar JPEG temporário do teste.")
        return buffer.tobytes()

    def _assert_json_erro(self, resposta, status, erro):
        self.assertEqual(resposta.status_code, status)
        dados = resposta.get_json()
        self.assertIsInstance(dados, dict)
        self.assertFalse(dados.get("sucesso"))
        self.assertEqual(dados.get("erro"), erro)

    # ============================================================
    # AUTENTICAÇÃO / CORS
    # ============================================================

    def test_01_sem_autenticacao_retorna_401(self):
        with self._sem_auth():
            resposta = self.client.get("/api/cameras")

        self._assert_json_erro(
            resposta,
            401,
            "NAO_AUTENTICADO",
        )

    def test_02_cors_localhost_5173(self):
        with (
            self._auth(),
            patch.object(
                self.api,
                "listar_cameras_com_status",
                return_value={
                    "sucesso": True,
                    "erro": None,
                    "quantidade": 0,
                    "cameras": [],
                },
            ),
        ):
            resposta = self.client.get(
                "/api/cameras",
                headers={
                    "Origin": "http://localhost:5173",
                },
            )

        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(
            resposta.headers.get("Access-Control-Allow-Origin"),
            "http://localhost:5173",
        )

    # ============================================================
    # CÂMERAS
    # ============================================================

    def test_03_cameras_listagem_sucesso_200(self):
        retorno = {
            "sucesso": True,
            "erro": None,
            "quantidade": 1,
            "cameras": [
                {
                    "camera_uid": "cam-001",
                    "nome": "Camera 1",
                    "tipo": "rtsp",
                    "online": True,
                    "status": "ONLINE",
                }
            ],
        }

        with (
            self._auth(),
            patch.object(
                self.api,
                "listar_cameras_com_status",
                return_value=retorno,
            ) as mock_service,
        ):
            resposta = self.client.get("/api/cameras")

        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(resposta.get_json(), retorno)
        mock_service.assert_called_once_with()

    def test_04_camera_inexistente_404(self):
        with (
            self._auth(),
            patch.object(
                self.api,
                "obter_camera",
                return_value={
                    "sucesso": False,
                    "erro": "CAMERA_NAO_ENCONTRADA",
                    "camera": None,
                },
            ),
        ):
            resposta = self.client.get(
                "/api/cameras/cam-inexistente"
            )

        self._assert_json_erro(
            resposta,
            404,
            "CAMERA_NAO_ENCONTRADA",
        )

    def test_05_operador_nao_pode_buscar_cameras_403(self):
        with self._auth(perfil="OPERADOR"):
            resposta = self.client.post(
                "/api/cameras/rede/buscar",
                json={},
            )

        self._assert_json_erro(
            resposta,
            403,
            "ACESSO_NEGADO",
        )

    def test_06_cadastro_camera_sem_nome_retorna_400(self):
        with self._auth():
            resposta = self.client.post(
                "/api/cameras/rede",
                json={
                    "fonte": "rtsp://10.0.0.10/stream",
                    "onvif": False,
                },
            )

        self._assert_json_erro(
            resposta,
            400,
            "NOME_OBRIGATORIO",
        )

    def test_07_camera_com_vinculos_retorna_409(self):
        with (
            self._auth(),
            patch.object(
                self.api,
                "verificar_vinculos_camera",
                return_value={
                    "sucesso": True,
                    "erro": None,
                    "possui_vinculos": True,
                    "vinculos": [
                        {
                            "ambiente_id": "amb-001",
                            "nome": "Linha 1",
                        }
                    ],
                },
            ),
        ):
            resposta = self.client.delete(
                "/api/cameras/cam-001"
            )

        self._assert_json_erro(
            resposta,
            409,
            "CAMERA_POSSUI_VINCULOS",
        )
        self.assertTrue(
            resposta.get_json().get("vinculos")
        )

    def test_08_preview_camera_indisponivel_retorna_503(self):
        with (
            self._auth(),
            patch.object(
                self.api,
                "iniciar_preview",
                return_value={
                    "sucesso": False,
                    "erro": "CAMERA_INDISPONIVEL",
                    "session_id": None,
                },
            ),
        ):
            resposta = self.client.post(
                "/api/cameras/cam-001/preview",
                json={},
            )

        self._assert_json_erro(
            resposta,
            503,
            "CAMERA_INDISPONIVEL",
        )

    def test_09_excecao_inesperada_em_camera_retorna_500(self):
        with (
            self._auth(),
            patch.object(
                self.api,
                "listar_cameras_com_status",
                side_effect=RuntimeError("falha simulada"),
            ),
        ):
            resposta = self.client.get("/api/cameras")

        self._assert_json_erro(
            resposta,
            500,
            "ERRO_INTERNO",
        )

    # ============================================================
    # AMBIENTES
    # ============================================================

    def test_10_ambientes_consulta_sucesso_200(self):
        retorno = {
            "sucesso": True,
            "erro": None,
            "total": 1,
            "pagina": 1,
            "por_pagina": 20,
            "total_paginas": 1,
            "ambientes": [
                {
                    "ambiente_id": "amb-001",
                    "nome": "Linha 1",
                    "status": "ATIVO",
                }
            ],
        }

        with (
            self._auth(),
            patch.object(
                self.api,
                "consultar_ambientes",
                return_value=retorno,
            ) as mock_service,
        ):
            resposta = self.client.get(
                "/api/ambientes?busca=Linha&status=ATIVO"
                "&pagina=1&por_pagina=20"
            )

        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(resposta.get_json(), retorno)
        mock_service.assert_called_once()
        kwargs = mock_service.call_args.kwargs
        self.assertEqual(kwargs.get("busca"), "Linha")
        self.assertEqual(kwargs.get("status"), "ATIVO")
        self.assertEqual(kwargs.get("pagina"), 1)
        self.assertEqual(kwargs.get("por_pagina"), 20)

    def test_11_ambiente_cadastro_sem_nome_retorna_400(self):
        with self._auth():
            resposta = self.client.post(
                "/api/ambientes",
                json={
                    "cameras": ["cam-001"],
                    "epis_obrigatorios": ["Capacete"],
                },
            )

        self._assert_json_erro(
            resposta,
            400,
            "NOME_AMBIENTE_OBRIGATORIO",
        )

    def test_12_ambiente_inexistente_retorna_404(self):
        with (
            self._auth(),
            patch.object(
                self.api,
                "obter_ambiente",
                return_value={
                    "sucesso": False,
                    "erro": "AMBIENTE_NAO_ENCONTRADO",
                    "ambiente": None,
                },
            ),
        ):
            resposta = self.client.get(
                "/api/ambientes/amb-inexistente"
            )

        self._assert_json_erro(
            resposta,
            404,
            "AMBIENTE_NAO_ENCONTRADO",
        )

    def test_13_nome_ambiente_duplicado_retorna_409(self):
        with (
            self._auth(),
            patch.object(
                self.api,
                "criar_ambiente",
                return_value={
                    "sucesso": False,
                    "erro": "NOME_AMBIENTE_JA_EXISTE",
                },
            ),
        ):
            resposta = self.client.post(
                "/api/ambientes",
                json={
                    "nome": "Linha 1",
                    "cameras": ["cam-001"],
                    "epis_obrigatorios": ["Capacete"],
                },
            )

        self._assert_json_erro(
            resposta,
            409,
            "NOME_AMBIENTE_JA_EXISTE",
        )

    def test_14_operador_nao_pode_administrar_ambientes_403(self):
        with self._auth(perfil="OPERADOR"):
            resposta = self.client.get("/api/ambientes")

        self._assert_json_erro(
            resposta,
            403,
            "ACESSO_NEGADO",
        )

    def test_15_excecao_inesperada_ambientes_retorna_500(self):
        with (
            self._auth(),
            patch.object(
                self.api,
                "consultar_ambientes",
                side_effect=RuntimeError("falha simulada"),
            ),
        ):
            resposta = self.client.get("/api/ambientes")

        self._assert_json_erro(
            resposta,
            500,
            "ERRO_INTERNO",
        )

    # ============================================================
    # COLABORADORES
    # ============================================================

    def test_16_colaboradores_listagem_sucesso_200(self):
        retorno = {
            "sucesso": True,
            "erro": None,
            "total": 1,
            "pagina": 1,
            "por_pagina": 20,
            "total_paginas": 1,
            "colaboradores": [
                {
                    "matricula": "557079",
                    "nome": "Arthur",
                    "cargo": "Operador",
                    "biometria_cadastrada": True,
                }
            ],
        }

        with (
            self._auth(),
            patch.object(
                self.api,
                "consultar_colaboradores",
                return_value=retorno,
            ),
        ):
            resposta = self.client.get(
                "/api/colaboradores?busca=Arthur"
            )

        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(resposta.get_json(), retorno)

    def test_17_cadastro_colaborador_sucesso_201(self):
        retorno = {
            "sucesso": True,
            "erro": None,
            "colaborador": {
                "matricula": "999001",
                "nome": "Teste",
                "cargo": "Operador",
                "biometria_cadastrada": True,
            },
        }

        with (
            self._auth(),
            patch.object(
                self.api,
                "cadastrar_colaborador",
                return_value=retorno,
            ) as mock_service,
        ):
            resposta = self.client.post(
                "/api/colaboradores",
                data={
                    "matricula": "999001",
                    "nome": "Teste",
                    "cargo": "Operador",
                    "imagem_biometrica": (
                        io.BytesIO(self._jpeg_bytes()),
                        "biometria.jpg",
                    ),
                },
                content_type="multipart/form-data",
            )

        self.assertEqual(resposta.status_code, 201)
        self.assertEqual(resposta.get_json(), retorno)
        mock_service.assert_called_once()

    def test_18_cadastro_sem_imagem_biometrica_retorna_400(self):
        with self._auth():
            resposta = self.client.post(
                "/api/colaboradores",
                data={
                    "matricula": "999001",
                    "nome": "Teste",
                    "cargo": "Operador",
                },
                content_type="multipart/form-data",
            )

        self._assert_json_erro(
            resposta,
            400,
            "IMAGEM_BIOMETRICA_OBRIGATORIA",
        )

    def test_19_colaborador_inexistente_retorna_404(self):
        with (
            self._auth(),
            patch.object(
                self.api,
                "obter_detalhes_colaborador",
                return_value={
                    "sucesso": False,
                    "erro": "COLABORADOR_NAO_ENCONTRADO",
                    "colaborador": None,
                },
            ),
        ):
            resposta = self.client.get(
                "/api/colaboradores/999999"
            )

        self._assert_json_erro(
            resposta,
            404,
            "COLABORADOR_NAO_ENCONTRADO",
        )

    def test_20_matricula_duplicada_retorna_409(self):
        with (
            self._auth(),
            patch.object(
                self.api,
                "cadastrar_colaborador",
                return_value={
                    "sucesso": False,
                    "erro": "MATRICULA_JA_CADASTRADA",
                    "colaborador": None,
                },
            ),
        ):
            resposta = self.client.post(
                "/api/colaboradores",
                data={
                    "matricula": "557079",
                    "nome": "Arthur",
                    "cargo": "Operador",
                    "imagem_biometrica": (
                        io.BytesIO(self._jpeg_bytes()),
                        "biometria.jpg",
                    ),
                },
                content_type="multipart/form-data",
            )

        self._assert_json_erro(
            resposta,
            409,
            "MATRICULA_JA_CADASTRADA",
        )

    def test_21_operador_nao_pode_listar_colaboradores_403(self):
        with self._auth(perfil="OPERADOR"):
            resposta = self.client.get("/api/colaboradores")

        self._assert_json_erro(
            resposta,
            403,
            "ACESSO_NEGADO",
        )

    def test_22_excecao_colaboradores_retorna_500(self):
        with (
            self._auth(),
            patch.object(
                self.api,
                "consultar_colaboradores",
                side_effect=RuntimeError("falha simulada"),
            ),
        ):
            resposta = self.client.get("/api/colaboradores")

        self._assert_json_erro(
            resposta,
            500,
            "ERRO_INTERNO",
        )

    # ============================================================
    # MONITORAMENTO DO COLABORADOR
    # ============================================================

    def test_23_operador_acessa_proprio_monitoramento_200(self):
        retorno = {
            "sucesso": True,
            "erro": None,
            "colaborador": {
                "matricula": "557079",
                "nome": "Arthur",
                "cargo": "Operador",
                "identificado": True,
            },
            "monitoramento": {
                "presente": True,
                "camera": {"camera_uid": "cam-001"},
                "ambiente": {"ambiente_id": "amb-001"},
                "status_geral": "CONFORME",
                "epis_obrigatorios": [],
                "ergonomia": {
                    "disponivel": False,
                    "estado": None,
                    "postura": None,
                    "problemas": [],
                },
                "atualizado_em": None,
            },
        }

        with (
            self._auth(
                perfil="OPERADOR",
                matricula="557079",
            ),
            patch.object(
                self.api,
                "obter_estado_sistema",
                return_value=object(),
            ),
            patch.object(
                self.api,
                "obter_monitoramento_colaborador",
                return_value=retorno,
            ) as mock_service,
        ):
            resposta = self.client.get(
                "/api/monitoramento/me"
            )

        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(resposta.get_json(), retorno)
        args = mock_service.call_args.args
        self.assertEqual(args[0], "557079")

    def test_24_operador_nao_acessa_outro_colaborador_403(self):
        with self._auth(
            perfil="OPERADOR",
            matricula="557079",
        ):
            resposta = self.client.get(
                "/api/monitoramento/colaboradores/100002"
            )

        self._assert_json_erro(
            resposta,
            403,
            "ACESSO_NEGADO",
        )

    def test_25_gerencial_acessa_monitoramento_colaborador_200(self):
        retorno = {
            "sucesso": True,
            "erro": None,
            "colaborador": {
                "matricula": "100002",
                "nome": "Beatriz",
                "cargo": "Supervisora",
                "identificado": False,
            },
            "monitoramento": {
                "presente": False,
                "camera": None,
                "ambiente": None,
                "status_geral": "INDETERMINADO",
                "epis_obrigatorios": [],
                "ergonomia": {
                    "disponivel": False,
                    "estado": None,
                    "postura": None,
                    "problemas": [],
                },
                "atualizado_em": None,
            },
        }

        with (
            self._auth(),
            patch.object(
                self.api,
                "obter_estado_sistema",
                return_value=object(),
            ),
            patch.object(
                self.api,
                "obter_monitoramento_colaborador",
                return_value=retorno,
            ),
        ):
            resposta = self.client.get(
                "/api/monitoramento/colaboradores/100002"
            )

        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(resposta.get_json(), retorno)

    def test_26_monitoramento_colaborador_inexistente_404(self):
        with (
            self._auth(),
            patch.object(
                self.api,
                "obter_estado_sistema",
                return_value=object(),
            ),
            patch.object(
                self.api,
                "obter_monitoramento_colaborador",
                return_value={
                    "sucesso": False,
                    "erro": "COLABORADOR_NAO_ENCONTRADO",
                    "colaborador": None,
                    "monitoramento": None,
                },
            ),
        ):
            resposta = self.client.get(
                "/api/monitoramento/colaboradores/999999"
            )

        self._assert_json_erro(
            resposta,
            404,
            "COLABORADOR_NAO_ENCONTRADO",
        )

    def test_27_estado_sistema_indisponivel_retorna_503(self):
        with (
            self._auth(),
            patch.object(
                self.api,
                "obter_estado_sistema",
                return_value=None,
            ),
        ):
            resposta = self.client.get(
                "/api/monitoramento/colaboradores/557079"
            )

        self._assert_json_erro(
            resposta,
            503,
            "ESTADO_SISTEMA_INDISPONIVEL",
        )

    def test_28_excecao_monitoramento_retorna_500(self):
        with (
            self._auth(),
            patch.object(
                self.api,
                "obter_estado_sistema",
                return_value=object(),
            ),
            patch.object(
                self.api,
                "obter_monitoramento_colaborador",
                side_effect=RuntimeError("falha simulada"),
            ),
        ):
            resposta = self.client.get(
                "/api/monitoramento/colaboradores/557079"
            )

        self._assert_json_erro(
            resposta,
            500,
            "ERRO_INTERNO",
        )

    # ============================================================
    # DASHBOARD GERENCIAL
    # ============================================================

    def test_29_dashboard_gerencial_sucesso_200(self):
        retorno = {
            "sucesso": True,
            "erro": None,
            "resumo": {
                "cameras_total": 5,
                "cameras_online": 4,
                "cameras_offline": 1,
                "ambientes_total": 3,
                "ambientes_ativos": 2,
                "ambientes_com_problema": 1,
                "ambientes_inativos": 0,
                "colaboradores_total": 2,
                "infracoes_periodo": 12,
            },
            "alertas": [],
            "ambientes_com_mais_infracoes": [],
            "serie_temporal": [],
            "status_cameras": [],
            "periodo": {
                "data_inicio": "2026-09-01",
                "data_fim": "2026-09-19",
            },
        }

        with (
            self._auth(),
            patch.object(
                self.api,
                "obter_dashboard_gerencial",
                return_value=retorno,
            ) as mock_service,
        ):
            resposta = self.client.get(
                "/api/dashboard-gerencial"
                "?data_inicio=2026-09-01"
                "&data_fim=2026-09-19"
            )

        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(resposta.get_json(), retorno)
        mock_service.assert_called_once_with(
            data_inicio="2026-09-01",
            data_fim="2026-09-19",
        )

    def test_30_operador_nao_acessa_dashboard_gerencial_403(self):
        with self._auth(perfil="OPERADOR"):
            resposta = self.client.get(
                "/api/dashboard-gerencial"
            )

        self._assert_json_erro(
            resposta,
            403,
            "ACESSO_NEGADO",
        )

    def test_31_data_dashboard_invalida_retorna_400(self):
        with self._auth():
            resposta = self.client.get(
                "/api/dashboard-gerencial"
                "?data_inicio=19-09-2026"
                "&data_fim=2026-09-20"
            )

        self._assert_json_erro(
            resposta,
            400,
            "DATA_INVALIDA",
        )

    def test_32_excecao_dashboard_retorna_500(self):
        with (
            self._auth(),
            patch.object(
                self.api,
                "obter_dashboard_gerencial",
                side_effect=RuntimeError("falha simulada"),
            ),
        ):
            resposta = self.client.get(
                "/api/dashboard-gerencial"
            )

        self._assert_json_erro(
            resposta,
            500,
            "ERRO_INTERNO",
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)

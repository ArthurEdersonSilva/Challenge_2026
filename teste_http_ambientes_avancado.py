from __future__ import annotations

import importlib
import unittest
from unittest.mock import patch


class TestHTTPAmbientesAvancado(unittest.TestCase):
    """
    Testes HTTP do transporte avançado de Ambientes.

    IMPORTANTE:
    - nenhum service real é executado;
    - nenhuma câmera é aberta;
    - FastSAM não é executado;
    - nenhum JSON/CSV real é alterado;
    - os testes validam somente rota, autorização, payload e status HTTP.
    """

    @classmethod
    def setUpClass(cls):
        cls.api = importlib.import_module("api_sistema")
        cls.api.app.config.update(
            TESTING=True,
            PROPAGATE_EXCEPTIONS=False,
        )

    def setUp(self):
        self.client = self.api.app.test_client()

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

    def _assert_erro(self, resposta, status, erro):
        self.assertEqual(resposta.status_code, status)
        dados = resposta.get_json()
        self.assertFalse(dados.get("sucesso"))
        self.assertEqual(dados.get("erro"), erro)

    def test_01_operador_bloqueado_roi_403(self):
        with self._auth(perfil="OPERADOR"):
            resposta = self.client.get("/api/ambientes/amb-1/rois")
        self._assert_erro(resposta, 403, "ACESSO_NEGADO")

    def test_02_listar_rois_200(self):
        retorno = {
            "sucesso": True,
            "erro": None,
            "ambiente_id": "amb-1",
            "rois": {"cam-1": {"x1": 0.1, "y1": 0.1, "x2": 0.9, "y2": 0.9}},
            "quantidade": 1,
        }
        with self._auth(), patch.object(
            self.api, "listar_rois", return_value=retorno
        ) as mock_service:
            resposta = self.client.get("/api/ambientes/amb-1/rois")
        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(resposta.get_json(), retorno)
        mock_service.assert_called_once_with("amb-1")

    def test_03_obter_roi_inexistente_404(self):
        with self._auth(), patch.object(
            self.api,
            "obter_roi",
            return_value={"sucesso": False, "erro": "ROI_NAO_DEFINIDA"},
        ):
            resposta = self.client.get("/api/ambientes/amb-1/rois/cam-1")
        self._assert_erro(resposta, 404, "ROI_NAO_DEFINIDA")

    def test_04_definir_roi_encaminha_payload(self):
        retorno = {
            "sucesso": True,
            "erro": None,
            "ambiente_id": "amb-1",
            "camera_uid": "cam-1",
            "roi": {"x1": 0.1, "y1": 0.2, "x2": 0.8, "y2": 0.9},
        }
        with self._auth(), patch.object(
            self.api, "definir_roi", return_value=retorno
        ) as mock_service:
            resposta = self.client.put(
                "/api/ambientes/amb-1/rois/cam-1",
                json={"x1": 0.1, "y1": 0.2, "x2": 0.8, "y2": 0.9},
            )
        self.assertEqual(resposta.status_code, 200)
        mock_service.assert_called_once_with(
            ambiente_id="amb-1",
            camera_uid="cam-1",
            x1=0.1,
            y1=0.2,
            x2=0.8,
            y2=0.9,
        )

    def test_05_remover_roi_200(self):
        with self._auth(), patch.object(
            self.api,
            "remover_roi",
            return_value={"sucesso": True, "erro": None},
        ) as mock_service:
            resposta = self.client.delete("/api/ambientes/amb-1/rois/cam-1")
        self.assertEqual(resposta.status_code, 200)
        mock_service.assert_called_once_with("amb-1", "cam-1")

    def test_06_previsualizar_area_encaminha_payload(self):
        retorno = {"sucesso": True, "erro": None, "camera_uid": "cam-1"}
        with self._auth(), patch.object(
            self.api, "previsualizar_area_monitoramento", return_value=retorno
        ) as mock_service:
            resposta = self.client.post(
                "/api/ambientes/area-monitoramento/previsualizar",
                json={
                    "session_id": "sess-1",
                    "camera_uid": "cam-1",
                    "x1": 0.1,
                    "y1": 0.1,
                    "x2": 0.9,
                    "y2": 0.9,
                    "qualidade_jpeg": 85,
                },
            )
        self.assertEqual(resposta.status_code, 200)
        mock_service.assert_called_once_with(
            session_id="sess-1",
            camera_uid="cam-1",
            x1=0.1,
            y1=0.1,
            x2=0.9,
            y2=0.9,
            qualidade_jpeg=85,
        )

    def test_07_preview_roi_salva_200(self):
        with self._auth(), patch.object(
            self.api,
            "obter_area_monitoramento",
            return_value={"sucesso": True, "erro": None},
        ) as mock_service:
            resposta = self.client.post(
                "/api/ambientes/amb-1/rois/cam-1/preview",
                json={"session_id": "sess-1", "qualidade_jpeg": 90},
            )
        self.assertEqual(resposta.status_code, 200)
        mock_service.assert_called_once_with(
            ambiente_id="amb-1",
            camera_uid="cam-1",
            session_id="sess-1",
            qualidade_jpeg=90,
        )

    def test_08_analisar_area_encaminha_quantidade_frames(self):
        with self._auth(), patch.object(
            self.api,
            "analisar_area_selecionada",
            return_value={"sucesso": True, "erro": None, "objetos": []},
        ) as mock_service:
            resposta = self.client.post(
                "/api/ambientes/area-monitoramento/analisar",
                json={
                    "session_id": "sess-1",
                    "camera_uid": "cam-1",
                    "x1": 0.1,
                    "y1": 0.1,
                    "x2": 0.9,
                    "y2": 0.9,
                    "quantidade_frames": 10,
                },
            )
        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(mock_service.call_args.kwargs["quantidade_frames"], 10)

    def test_09_analisar_roi_salva_sem_frame_valido_503(self):
        with self._auth(), patch.object(
            self.api,
            "analisar_roi_salva",
            return_value={
                "sucesso": False,
                "erro": "NENHUM_FRAME_VALIDO_PARA_ANALISE",
            },
        ):
            resposta = self.client.post(
                "/api/ambientes/amb-1/rois/cam-1/analisar",
                json={"session_id": "sess-1"},
            )
        self._assert_erro(resposta, 503, "NENHUM_FRAME_VALIDO_PARA_ANALISE")

    def test_10_preparar_maquinario_200(self):
        with self._auth(), patch.object(
            self.api,
            "preparar_selecao_maquinario",
            return_value={"sucesso": True, "erro": None, "analise_id": "an-1"},
        ) as mock_service:
            resposta = self.client.post(
                "/api/ambientes/amb-1/maquinario/preparar",
                json={"sessoes_por_camera": {"cam-1": "sess-1"}},
            )
        self.assertEqual(resposta.status_code, 200)
        mock_service.assert_called_once_with(
            ambiente_id="amb-1",
            sessoes_por_camera={"cam-1": "sess-1"},
            qualidade_jpeg=90,
        )

    def test_11_salvar_maquinario_analise_inexistente_404(self):
        with self._auth(), patch.object(
            self.api,
            "salvar_selecao_maquinario",
            return_value={
                "sucesso": False,
                "erro": "ANALISE_MAQUINARIO_NAO_ENCONTRADA",
            },
        ):
            resposta = self.client.put(
                "/api/ambientes/amb-1/maquinario",
                json={"analise_id": "an-1", "ids_maquinario": ["obj-1"]},
            )
        self._assert_erro(resposta, 404, "ANALISE_MAQUINARIO_NAO_ENCONTRADA")

    def test_12_analise_de_outro_ambiente_409(self):
        with self._auth(), patch.object(
            self.api,
            "salvar_selecao_maquinario",
            return_value={"sucesso": False, "erro": "ANALISE_DE_OUTRO_AMBIENTE"},
        ):
            resposta = self.client.put(
                "/api/ambientes/amb-1/maquinario",
                json={"analise_id": "an-2", "ids_maquinario": []},
            )
        self._assert_erro(resposta, 409, "ANALISE_DE_OUTRO_AMBIENTE")

    def test_13_listar_objetos_200(self):
        with self._auth(), patch.object(
            self.api,
            "listar_objetos_ambiente",
            return_value={"sucesso": True, "erro": None, "objetos": []},
        ):
            resposta = self.client.get("/api/ambientes/amb-1/objetos")
        self.assertEqual(resposta.status_code, 200)

    def test_14_listar_maquinarios_200(self):
        with self._auth(), patch.object(
            self.api,
            "listar_maquinarios_ambiente",
            return_value={"sucesso": True, "erro": None, "maquinarios": []},
        ):
            resposta = self.client.get("/api/ambientes/amb-1/maquinarios")
        self.assertEqual(resposta.status_code, 200)

    def test_15_descartar_analise_inexistente_404(self):
        with self._auth(), patch.object(
            self.api,
            "descartar_analise_maquinario",
            return_value={
                "sucesso": False,
                "erro": "ANALISE_MAQUINARIO_NAO_ENCONTRADA",
            },
        ):
            resposta = self.client.delete(
                "/api/ambientes/analises-maquinario/an-404"
            )
        self._assert_erro(resposta, 404, "ANALISE_MAQUINARIO_NAO_ENCONTRADA")

    def test_16_catalogo_epis_200(self):
        retorno = {"sucesso": True, "erro": None, "epis": ["Capacete"]}
        with self._auth(), patch.object(
            self.api, "listar_epis_disponiveis", return_value=retorno
        ) as mock_service:
            resposta = self.client.get("/api/ambientes/epis/disponiveis")
        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(resposta.get_json(), retorno)
        mock_service.assert_called_once_with()

    def test_17_obter_epis_200(self):
        with self._auth(), patch.object(
            self.api,
            "obter_epis_obrigatorios",
            return_value={
                "sucesso": True,
                "erro": None,
                "epis_obrigatorios": ["Capacete"],
            },
        ) as mock_service:
            resposta = self.client.get("/api/ambientes/amb-1/epis")
        self.assertEqual(resposta.status_code, 200)
        mock_service.assert_called_once_with("amb-1")

    def test_18_definir_epis_invalido_400(self):
        with self._auth(), patch.object(
            self.api,
            "definir_epis_obrigatorios",
            return_value={"sucesso": False, "erro": "EPI_NAO_DISPONIVEL"},
        ):
            resposta = self.client.put(
                "/api/ambientes/amb-1/epis",
                json={"epis_obrigatorios": ["EPI Fake"]},
            )
        self._assert_erro(resposta, 400, "EPI_NAO_DISPONIVEL")

    def test_19_colaboradores_disponiveis_200(self):
        retorno = {"sucesso": True, "erro": None, "colaboradores": []}
        with self._auth(), patch.object(
            self.api, "listar_colaboradores_para_ambiente", return_value=retorno
        ) as mock_service:
            resposta = self.client.get("/api/ambientes/colaboradores/disponiveis")
        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(resposta.get_json(), retorno)
        mock_service.assert_called_once_with()

    def test_20_obter_colaboradores_vinculados_200(self):
        with self._auth(), patch.object(
            self.api,
            "obter_colaboradores_vinculados",
            return_value={"sucesso": True, "erro": None, "colaboradores": []},
        ) as mock_service:
            resposta = self.client.get("/api/ambientes/amb-1/colaboradores")
        self.assertEqual(resposta.status_code, 200)
        mock_service.assert_called_once_with("amb-1")

    def test_21_definir_colaboradores_encaminha_matriculas(self):
        with self._auth(), patch.object(
            self.api,
            "definir_colaboradores_vinculados",
            return_value={"sucesso": True, "erro": None, "quantidade": 2},
        ) as mock_service:
            resposta = self.client.put(
                "/api/ambientes/amb-1/colaboradores",
                json={"matriculas": ["1", "2"]},
            )
        self.assertEqual(resposta.status_code, 200)
        mock_service.assert_called_once_with(
            ambiente_id="amb-1", matriculas=["1", "2"]
        )

    def test_22_vincular_colaborador_200(self):
        with self._auth(), patch.object(
            self.api,
            "vincular_colaborador",
            return_value={"sucesso": True, "erro": None},
        ) as mock_service:
            resposta = self.client.post(
                "/api/ambientes/amb-1/colaboradores/557079"
            )
        self.assertEqual(resposta.status_code, 200)
        mock_service.assert_called_once_with("amb-1", "557079")

    def test_23_desvincular_nao_vinculado_404(self):
        with self._auth(), patch.object(
            self.api,
            "desvincular_colaborador",
            return_value={"sucesso": False, "erro": "COLABORADOR_NAO_VINCULADO"},
        ):
            resposta = self.client.delete(
                "/api/ambientes/amb-1/colaboradores/557079"
            )
        self._assert_erro(resposta, 404, "COLABORADOR_NAO_VINCULADO")

    def test_24_revisao_200(self):
        retorno = {
            "sucesso": True,
            "erro": None,
            "pronto_para_finalizar": True,
            "pendencias": [],
        }
        with self._auth(), patch.object(
            self.api, "obter_revisao_ambiente", return_value=retorno
        ) as mock_service:
            resposta = self.client.get("/api/ambientes/amb-1/revisao")
        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(resposta.get_json(), retorno)
        mock_service.assert_called_once_with("amb-1")

    def test_25_detalhes_enriquecidos_200(self):
        retorno = {
            "sucesso": True,
            "erro": None,
            "ambiente_id": "amb-1",
            "status": "ATIVO",
            "rois": {},
            "maquinarios": [],
            "colaboradores": [],
        }
        with self._auth(), patch.object(
            self.api, "obter_detalhes_ambiente_consulta", return_value=retorno
        ) as mock_service:
            resposta = self.client.get("/api/ambientes/amb-1/detalhes")
        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(resposta.get_json(), retorno)
        mock_service.assert_called_once_with("amb-1")

    def test_26_status_individual_200(self):
        retorno = {"sucesso": True, "erro": None, "status": "ATIVO"}
        with self._auth(), patch.object(
            self.api, "obter_status_ambiente", return_value=retorno
        ) as mock_service:
            resposta = self.client.get("/api/ambientes/amb-1/status")
        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(resposta.get_json(), retorno)
        mock_service.assert_called_once_with("amb-1")

    def test_27_excecao_inesperada_retorna_500(self):
        with self._auth(), patch.object(
            self.api,
            "obter_revisao_ambiente",
            side_effect=RuntimeError("falha simulada"),
        ):
            resposta = self.client.get("/api/ambientes/amb-1/revisao")
        self._assert_erro(resposta, 500, "ERRO_INTERNO")


if __name__ == "__main__":
    unittest.main(verbosity=2)

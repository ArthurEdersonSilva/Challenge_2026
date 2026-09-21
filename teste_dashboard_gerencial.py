from __future__ import annotations

import copy
import importlib
import unittest
from unittest.mock import patch


class TestDashboardGerencial(unittest.TestCase):
    """
    Testes da etapa Dashboard Gerencial.

    Contrato esperado:

    services/dashboard_gerencial_service.py

    obter_dashboard_gerencial(
        data_inicio=None,
        data_fim=None,
    ) -> {
        "sucesso": bool,
        "erro": str | None,
        "resumo": {
            "cameras_total": int,
            "cameras_online": int,
            "cameras_offline": int,
            "ambientes_total": int,
            "ambientes_ativos": int,
            "ambientes_com_problema": int,
            "ambientes_inativos": int,
            "colaboradores_total": int,
            "infracoes_periodo": int,
        },
        "alertas": list,
        "ambientes_com_mais_infracoes": list,
        "serie_temporal": list,
        "status_cameras": list,
        "periodo": {
            "data_inicio": str | None,
            "data_fim": str | None,
        },
    }

    Dependências públicas esperadas no serviço:
    - listar_cameras_com_status()
    - atualizar_status_ambientes()
    - listar_colaboradores()
    - obter_dashboard_infracoes(...)

    Regras:
    - o dashboard apenas agrega/projeta dados já produzidos pelos serviços;
    - não acessa JSON/CSV/imagens diretamente;
    - não executa OpenCV/YOLO/biometria;
    - câmera offline gera alerta;
    - ambiente COM_PROBLEMA gera alerta;
    - dados dos serviços-fonte não podem ser alterados;
    - falha de dependência deve ser propagada de forma controlada.
    """

    def _modulo(self):
        try:
            return importlib.import_module(
                "services.dashboard_gerencial_service"
            )
        except ModuleNotFoundError as erro:
            self.fail(
                "Módulo services.dashboard_gerencial_service "
                "ainda não foi implementado. "
                f"Detalhe: {erro}"
            )

    def _funcao(self):
        modulo = self._modulo()
        funcao = getattr(
            modulo,
            "obter_dashboard_gerencial",
            None,
        )
        self.assertIsNotNone(
            funcao,
            "Função obter_dashboard_gerencial "
            "ainda não foi implementada.",
        )
        return modulo, funcao

    @staticmethod
    def _cameras():
        return {
            "sucesso": True,
            "erro": None,
            "quantidade": 3,
            "cameras": [
                {
                    "camera_uid": "cam-001",
                    "nome": "Camera 1",
                    "tipo": "rtsp",
                    "online": True,
                    "status": "ONLINE",
                    "largura": 1920,
                    "altura": 1080,
                    "fps": 25.0,
                    "motivo": None,
                },
                {
                    "camera_uid": "cam-002",
                    "nome": "Camera 2",
                    "tipo": "rtsp",
                    "online": False,
                    "status": "OFFLINE",
                    "largura": None,
                    "altura": None,
                    "fps": None,
                    "motivo": "STREAM_INDISPONIVEL",
                },
                {
                    "camera_uid": "cam-003",
                    "nome": "Camera 3",
                    "tipo": "usb",
                    "online": True,
                    "status": "ONLINE",
                    "largura": 1280,
                    "altura": 720,
                    "fps": 30.0,
                    "motivo": None,
                },
            ],
        }

    @staticmethod
    def _ambientes():
        return {
            "sucesso": True,
            "erro": None,
            "quantidade": 3,
            "monitoramento_ativo": 1,
            "com_problema": 1,
            "inativos": 1,
            "ambientes": [
                {
                    "ambiente_id": "amb-001",
                    "nome": "Linha 1",
                    "status": "ATIVO",
                    "monitoramento_ativo": True,
                    "com_problema": False,
                    "inativo": False,
                    "motivo": None,
                    "cameras": [],
                },
                {
                    "ambiente_id": "amb-002",
                    "nome": "Linha 2",
                    "status": "COM_PROBLEMA",
                    "monitoramento_ativo": False,
                    "com_problema": True,
                    "inativo": False,
                    "motivo": "CAMERA_OFFLINE_OU_INDISPONIVEL",
                    "cameras": [],
                },
                {
                    "ambiente_id": "amb-003",
                    "nome": "Linha 3",
                    "status": "INATIVO",
                    "monitoramento_ativo": False,
                    "com_problema": False,
                    "inativo": True,
                    "motivo": "AMBIENTE_NAO_FINALIZADO",
                    "cameras": [],
                },
            ],
        }

    @staticmethod
    def _colaboradores():
        return {
            "sucesso": True,
            "erro": None,
            "quantidade": 2,
            "colaboradores": [
                {
                    "matricula": "100001",
                    "nome": "Arthur",
                    "cargo": "Operador",
                    "biometria_cadastrada": True,
                },
                {
                    "matricula": "100002",
                    "nome": "Beatriz",
                    "cargo": "Supervisora",
                    "biometria_cadastrada": True,
                },
            ],
        }

    @staticmethod
    def _infracoes():
        return {
            "sucesso": True,
            "erro": None,
            "indicadores": {
                "total_infracoes": {
                    "anterior": 8,
                    "atual": 12,
                    "sem_base_comparacao": False,
                    "variacao_percentual": 50.0,
                },
                "total_evidencias": {
                    "anterior": 8,
                    "atual": 12,
                    "sem_base_comparacao": False,
                    "variacao_percentual": 50.0,
                },
                "ambientes_com_ocorrencias": {
                    "anterior": 1,
                    "atual": 2,
                    "sem_base_comparacao": False,
                    "variacao_percentual": 100.0,
                },
                "colaboradores_envolvidos": {
                    "anterior": 1,
                    "atual": 2,
                    "sem_base_comparacao": False,
                    "variacao_percentual": 100.0,
                },
            },
            "serie_temporal": [
                {"periodo": "2026-09-17", "infracoes": 3},
                {"periodo": "2026-09-18", "infracoes": 4},
                {"periodo": "2026-09-19", "infracoes": 5},
            ],
            "infracoes_por_ambiente": [
                {"ambiente": "Linha 2", "infracoes": 7},
                {"ambiente": "Linha 1", "infracoes": 5},
            ],
            "infracoes_por_epi": [
                {"epi": "Capacete", "infracoes": 12},
            ],
            "infracoes_por_colaborador": [],
            "estado_incidentes_historico": {
                "ativos": 2,
                "observacao_suspensa": 1,
                "encerrados": 9,
            },
            "ocorrencias_recentes": [],
            "filtros": {
                "data_inicio": "2026-09-17",
                "data_fim": "2026-09-19",
                "ambiente": None,
                "colaborador": None,
                "epi": None,
                "granularidade": "DIARIO",
            },
        }

    def _executar(
        self,
        cameras=None,
        ambientes=None,
        colaboradores=None,
        infracoes=None,
        **kwargs,
    ):
        modulo, funcao = self._funcao()

        cameras = (
            self._cameras()
            if cameras is None
            else cameras
        )
        ambientes = (
            self._ambientes()
            if ambientes is None
            else ambientes
        )
        colaboradores = (
            self._colaboradores()
            if colaboradores is None
            else colaboradores
        )
        infracoes = (
            self._infracoes()
            if infracoes is None
            else infracoes
        )

        with (
            patch.object(
                modulo,
                "listar_cameras_com_status",
                return_value=copy.deepcopy(cameras),
            ) as mock_cameras,
            patch.object(
                modulo,
                "atualizar_status_ambientes",
                return_value=copy.deepcopy(ambientes),
            ) as mock_ambientes,
            patch.object(
                modulo,
                "listar_colaboradores",
                return_value=copy.deepcopy(colaboradores),
            ) as mock_colaboradores,
            patch.object(
                modulo,
                "obter_dashboard_infracoes",
                return_value=copy.deepcopy(infracoes),
            ) as mock_infracoes,
        ):
            resultado = funcao(**kwargs)

        return {
            "resultado": resultado,
            "mock_cameras": mock_cameras,
            "mock_ambientes": mock_ambientes,
            "mock_colaboradores": mock_colaboradores,
            "mock_infracoes": mock_infracoes,
        }

    def test_01_resumo_geral_agrega_todos_os_modulos(self):
        execucao = self._executar()
        resultado = execucao["resultado"]

        self.assertTrue(resultado["sucesso"])
        self.assertIsNone(resultado["erro"])

        self.assertEqual(
            resultado["resumo"],
            {
                "cameras_total": 3,
                "cameras_online": 2,
                "cameras_offline": 1,
                "ambientes_total": 3,
                "ambientes_ativos": 1,
                "ambientes_com_problema": 1,
                "ambientes_inativos": 1,
                "colaboradores_total": 2,
                "infracoes_periodo": 12,
            },
        )

    def test_02_status_das_cameras_e_exposto(self):
        resultado = self._executar()["resultado"]

        cameras = resultado["status_cameras"]

        self.assertEqual(len(cameras), 3)

        por_uid = {
            item["camera_uid"]: item
            for item in cameras
        }

        self.assertTrue(por_uid["cam-001"]["online"])
        self.assertEqual(
            por_uid["cam-001"]["status"],
            "ONLINE",
        )
        self.assertFalse(por_uid["cam-002"]["online"])
        self.assertEqual(
            por_uid["cam-002"]["status"],
            "OFFLINE",
        )

    def test_03_camera_offline_gera_alerta(self):
        resultado = self._executar()["resultado"]

        alertas_camera = [
            alerta
            for alerta in resultado["alertas"]
            if alerta.get("tipo") == "CAMERA_OFFLINE"
        ]

        self.assertEqual(len(alertas_camera), 1)
        self.assertEqual(
            alertas_camera[0]["camera_uid"],
            "cam-002",
        )
        self.assertEqual(
            alertas_camera[0]["camera_nome"],
            "Camera 2",
        )
        self.assertEqual(
            alertas_camera[0]["motivo"],
            "STREAM_INDISPONIVEL",
        )

    def test_04_ambiente_com_problema_gera_alerta(self):
        resultado = self._executar()["resultado"]

        alertas_ambiente = [
            alerta
            for alerta in resultado["alertas"]
            if alerta.get("tipo")
            == "AMBIENTE_COM_PROBLEMA"
        ]

        self.assertEqual(len(alertas_ambiente), 1)
        self.assertEqual(
            alertas_ambiente[0]["ambiente_id"],
            "amb-002",
        )
        self.assertEqual(
            alertas_ambiente[0]["ambiente_nome"],
            "Linha 2",
        )

    def test_05_ambientes_com_mais_infracoes_sao_expostos(self):
        resultado = self._executar()["resultado"]

        ranking = resultado[
            "ambientes_com_mais_infracoes"
        ]

        self.assertEqual(
            ranking,
            [
                {
                    "ambiente": "Linha 2",
                    "infracoes": 7,
                },
                {
                    "ambiente": "Linha 1",
                    "infracoes": 5,
                },
            ],
        )

    def test_06_serie_temporal_e_exposta_sem_recalcular(self):
        infracoes = self._infracoes()
        esperado = copy.deepcopy(
            infracoes["serie_temporal"]
        )

        resultado = self._executar(
            infracoes=infracoes
        )["resultado"]

        self.assertEqual(
            resultado["serie_temporal"],
            esperado,
        )

    def test_07_periodo_e_repassado_ao_dashboard_de_infracoes(self):
        execucao = self._executar(
            data_inicio="2026-09-01",
            data_fim="2026-09-19",
        )

        execucao["mock_infracoes"].assert_called_once_with(
            data_inicio="2026-09-01",
            data_fim="2026-09-19",
        )

    def test_08_sem_alertas_quando_operacao_esta_saudavel(self):
        cameras = self._cameras()
        for camera in cameras["cameras"]:
            camera["online"] = True
            camera["status"] = "ONLINE"
            camera["motivo"] = None

        ambientes = self._ambientes()
        ambientes["monitoramento_ativo"] = 3
        ambientes["com_problema"] = 0
        ambientes["inativos"] = 0

        for ambiente in ambientes["ambientes"]:
            ambiente["status"] = "ATIVO"
            ambiente["monitoramento_ativo"] = True
            ambiente["com_problema"] = False
            ambiente["inativo"] = False
            ambiente["motivo"] = None

        resultado = self._executar(
            cameras=cameras,
            ambientes=ambientes,
        )["resultado"]

        self.assertEqual(resultado["alertas"], [])
        self.assertEqual(
            resultado["resumo"]["cameras_offline"],
            0,
        )
        self.assertEqual(
            resultado["resumo"][
                "ambientes_com_problema"
            ],
            0,
        )

    def test_09_dashboard_vazio_retorna_zeros(self):
        resultado = self._executar(
            cameras={
                "sucesso": True,
                "erro": None,
                "quantidade": 0,
                "cameras": [],
            },
            ambientes={
                "sucesso": True,
                "erro": None,
                "quantidade": 0,
                "monitoramento_ativo": 0,
                "com_problema": 0,
                "inativos": 0,
                "ambientes": [],
            },
            colaboradores={
                "sucesso": True,
                "erro": None,
                "quantidade": 0,
                "colaboradores": [],
            },
            infracoes={
                "sucesso": True,
                "erro": None,
                "indicadores": {
                    "total_infracoes": {
                        "anterior": 0,
                        "atual": 0,
                        "sem_base_comparacao": True,
                        "variacao_percentual": None,
                    },
                },
                "serie_temporal": [],
                "infracoes_por_ambiente": [],
                "infracoes_por_epi": [],
                "infracoes_por_colaborador": [],
                "estado_incidentes_historico": {
                    "ativos": 0,
                    "observacao_suspensa": 0,
                    "encerrados": 0,
                },
                "ocorrencias_recentes": [],
                "filtros": {
                    "data_inicio": None,
                    "data_fim": None,
                    "ambiente": None,
                    "colaborador": None,
                    "epi": None,
                    "granularidade": "DIARIO",
                },
            },
        )["resultado"]

        self.assertTrue(resultado["sucesso"])
        self.assertEqual(
            resultado["resumo"],
            {
                "cameras_total": 0,
                "cameras_online": 0,
                "cameras_offline": 0,
                "ambientes_total": 0,
                "ambientes_ativos": 0,
                "ambientes_com_problema": 0,
                "ambientes_inativos": 0,
                "colaboradores_total": 0,
                "infracoes_periodo": 0,
            },
        )
        self.assertEqual(resultado["alertas"], [])
        self.assertEqual(
            resultado["ambientes_com_mais_infracoes"],
            [],
        )
        self.assertEqual(resultado["serie_temporal"], [])
        self.assertEqual(resultado["status_cameras"], [])

    def test_10_falha_de_cameras_e_propagada(self):
        resultado = self._executar(
            cameras={
                "sucesso": False,
                "erro": "ERRO_LISTAR_CAMERAS",
                "cameras": [],
            },
        )["resultado"]

        self.assertFalse(resultado["sucesso"])
        self.assertEqual(
            resultado["erro"],
            "ERRO_LISTAR_CAMERAS",
        )

    def test_11_falha_do_dashboard_de_infracoes_e_propagada(self):
        resultado = self._executar(
            infracoes={
                "sucesso": False,
                "erro": "ERRO_CARREGAR_INCIDENTES",
            },
        )["resultado"]

        self.assertFalse(resultado["sucesso"])
        self.assertEqual(
            resultado["erro"],
            "ERRO_CARREGAR_INCIDENTES",
        )

    def test_12_dashboard_nao_altera_dados_das_dependencias(self):
        cameras = self._cameras()
        ambientes = self._ambientes()
        colaboradores = self._colaboradores()
        infracoes = self._infracoes()

        cameras_antes = copy.deepcopy(cameras)
        ambientes_antes = copy.deepcopy(ambientes)
        colaboradores_antes = copy.deepcopy(colaboradores)
        infracoes_antes = copy.deepcopy(infracoes)

        resultado = self._executar(
            cameras=cameras,
            ambientes=ambientes,
            colaboradores=colaboradores,
            infracoes=infracoes,
        )["resultado"]

        self.assertTrue(resultado["sucesso"])
        self.assertEqual(cameras, cameras_antes)
        self.assertEqual(ambientes, ambientes_antes)
        self.assertEqual(
            colaboradores,
            colaboradores_antes,
        )
        self.assertEqual(infracoes, infracoes_antes)


if __name__ == "__main__":
    unittest.main(verbosity=2)

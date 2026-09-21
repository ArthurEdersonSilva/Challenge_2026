from __future__ import annotations

import copy
import glob
import hashlib
import os
import unittest

import config

from estado_sistema import criar_estado_sistema_legado
from services.camera_service import listar_cameras_com_status
from services.ambiente_service import atualizar_status_ambientes
from services.colaborador_service import listar_colaboradores
from services.dashboard_infracoes_service import obter_dashboard_infracoes
from services.dashboard_gerencial_service import obter_dashboard_gerencial


class TestIntegracaoDashboardGerencialReal(unittest.TestCase):
    """
    Integração REAL do Dashboard Gerencial.

    Usa:
    - services.camera_service real;
    - services.ambiente_service real;
    - services.colaborador_service real;
    - services.dashboard_infracoes_service real;
    - services.dashboard_gerencial_service real;
    - EstadoSistema real criado por criar_estado_sistema_legado(config).

    Não usa mocks.
    Não altera arquivos existentes.
    Não cadastra/remove câmeras, ambientes ou colaboradores.
    Não grava incidentes.
    """

    @classmethod
    def setUpClass(cls):
        # EstadoSistema real, sem importar main.py e sem iniciar pipeline de IA.
        cls.estado_sistema = criar_estado_sistema_legado(config)
        cls.estado_antes = copy.deepcopy(
            cls.estado_sistema.snapshot()
        )

        cls.arquivos_monitorados = cls._arquivos_persistencia()
        cls.hashes_antes = cls._hashes(cls.arquivos_monitorados)

        # Serviços-fonte reais.
        cls.cameras = listar_cameras_com_status()
        cls.ambientes = atualizar_status_ambientes()
        cls.colaboradores = listar_colaboradores()
        cls.infracoes = obter_dashboard_infracoes()

        # Serviço final real, sem patch/mock.
        cls.dashboard = obter_dashboard_gerencial()

        cls.estado_depois = copy.deepcopy(
            cls.estado_sistema.snapshot()
        )
        cls.hashes_depois = cls._hashes(cls.arquivos_monitorados)

    @staticmethod
    def _arquivos_persistencia():
        candidatos = set()

        caminhos_fixos = [
            os.path.join(
                "configuracoes",
                "cameras_registry.json",
            ),
            getattr(
                config,
                "PATH_DADOS_OPERADORES",
                os.path.join(
                    "banco_biometria",
                    "dados_operadores.csv",
                ),
            ),
            getattr(
                config,
                "PATH_INCIDENTES_EPI_CSV",
                "incidentes_epi.csv",
            ),
        ]

        for caminho in caminhos_fixos:
            if caminho and os.path.isfile(caminho):
                candidatos.add(os.path.abspath(caminho))

        for caminho in glob.glob(
            os.path.join("ambientes", "*.json")
        ):
            if os.path.isfile(caminho):
                candidatos.add(os.path.abspath(caminho))

        return tuple(sorted(candidatos))

    @staticmethod
    def _hash_arquivo(caminho):
        sha = hashlib.sha256()
        with open(caminho, "rb") as arquivo:
            for bloco in iter(
                lambda: arquivo.read(1024 * 1024),
                b"",
            ):
                sha.update(bloco)
        return sha.hexdigest()

    @classmethod
    def _hashes(cls, caminhos):
        return {
            caminho: cls._hash_arquivo(caminho)
            for caminho in caminhos
            if os.path.isfile(caminho)
        }

    @staticmethod
    def _total_infracoes(resultado):
        indicadores = resultado.get("indicadores") or {}
        total = indicadores.get("total_infracoes")

        if isinstance(total, dict):
            return int(total.get("atual") or 0)

        return int(total or 0)

    def test_01_servicos_reais_responderam_com_sucesso(self):
        self.assertTrue(
            self.cameras.get("sucesso"),
            self.cameras,
        )
        self.assertTrue(
            self.ambientes.get("sucesso"),
            self.ambientes,
        )
        self.assertTrue(
            self.colaboradores.get("sucesso"),
            self.colaboradores,
        )
        self.assertTrue(
            self.infracoes.get("sucesso"),
            self.infracoes,
        )

    def test_02_dashboard_real_responde_com_sucesso(self):
        self.assertTrue(
            self.dashboard.get("sucesso"),
            self.dashboard,
        )
        self.assertIsNone(self.dashboard.get("erro"))

        for campo in (
            "resumo",
            "alertas",
            "ambientes_com_mais_infracoes",
            "serie_temporal",
            "status_cameras",
            "periodo",
        ):
            self.assertIn(campo, self.dashboard)

    def test_03_resumo_real_e_coerente_com_fontes(self):
        resumo = self.dashboard["resumo"]

        self.assertEqual(
            resumo["cameras_total"],
            int(self.cameras.get("quantidade") or 0),
        )
        self.assertEqual(
            resumo["ambientes_total"],
            int(self.ambientes.get("quantidade") or 0),
        )
        self.assertEqual(
            resumo["colaboradores_total"],
            int(self.colaboradores.get("quantidade") or 0),
        )
        self.assertEqual(
            resumo["infracoes_periodo"],
            self._total_infracoes(self.infracoes),
        )

        self.assertEqual(
            resumo["cameras_online"]
            + resumo["cameras_offline"],
            resumo["cameras_total"],
        )

        self.assertEqual(
            resumo["ambientes_ativos"]
            + resumo["ambientes_com_problema"]
            + resumo["ambientes_inativos"],
            resumo["ambientes_total"],
        )

    def test_04_status_cameras_real_e_internamente_consistente(self):
        status_cameras = self.dashboard["status_cameras"]
        resumo = self.dashboard["resumo"]

        self.assertEqual(
            len(status_cameras),
            resumo["cameras_total"],
        )

        online = sum(
            1
            for camera in status_cameras
            if bool(camera.get("online"))
        )

        self.assertEqual(
            online,
            resumo["cameras_online"],
        )
        self.assertEqual(
            len(status_cameras) - online,
            resumo["cameras_offline"],
        )

        for camera in status_cameras:
            self.assertIn("camera_uid", camera)
            self.assertIn("nome", camera)
            self.assertIn("tipo", camera)
            self.assertIn("online", camera)
            self.assertIn("status", camera)

    def test_05_alertas_de_camera_correspondem_ao_status_real(self):
        offline_por_uid = {
            camera.get("camera_uid"): camera
            for camera in self.dashboard["status_cameras"]
            if not bool(camera.get("online"))
        }

        alertas_camera = [
            alerta
            for alerta in self.dashboard["alertas"]
            if alerta.get("tipo") == "CAMERA_OFFLINE"
        ]

        self.assertEqual(
            len(alertas_camera),
            len(offline_por_uid),
        )

        for alerta in alertas_camera:
            uid = alerta.get("camera_uid")
            self.assertIn(uid, offline_por_uid)
            self.assertEqual(
                alerta.get("camera_nome"),
                offline_por_uid[uid].get("nome"),
            )

    def test_06_alertas_de_ambiente_correspondem_ao_servico_real(self):
        problemas = {
            item.get("ambiente_id"): item
            for item in self.ambientes.get("ambientes", [])
            if str(item.get("status") or "").upper()
            == "COM_PROBLEMA"
        }

        alertas = [
            alerta
            for alerta in self.dashboard["alertas"]
            if alerta.get("tipo")
            == "AMBIENTE_COM_PROBLEMA"
        ]

        # A quantidade pode variar somente se o estado das câmeras mudar
        # exatamente entre as duas leituras reais. Todo alerta retornado,
        # porém, precisa apontar para um ambiente existente.
        ids_reais = {
            item.get("ambiente_id")
            for item in self.ambientes.get("ambientes", [])
        }

        for alerta in alertas:
            self.assertIn(
                alerta.get("ambiente_id"),
                ids_reais,
            )

        if len(alertas) == len(problemas):
            self.assertEqual(
                {a.get("ambiente_id") for a in alertas},
                set(problemas),
            )

    def test_07_infracoes_reais_sao_repassadas_sem_recalculo(self):
        self.assertEqual(
            self.dashboard["serie_temporal"],
            self.infracoes.get("serie_temporal") or [],
        )
        self.assertEqual(
            self.dashboard["ambientes_com_mais_infracoes"],
            self.infracoes.get("infracoes_por_ambiente") or [],
        )

    def test_08_estado_sistema_real_permanece_inalterado(self):
        self.assertEqual(
            self.estado_antes,
            self.estado_depois,
            "O Dashboard Gerencial alterou o EstadoSistema real.",
        )

    def test_09_persistencia_real_permanece_inalterada(self):
        self.assertEqual(
            self.hashes_antes,
            self.hashes_depois,
            "O teste/dashboard alterou arquivo persistente do projeto.",
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)

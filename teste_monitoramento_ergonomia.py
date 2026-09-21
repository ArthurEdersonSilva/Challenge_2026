from __future__ import annotations

import copy
import unittest
from unittest.mock import patch

import services.monitoramento_colaborador_service as monitoramento_service


class TestMonitoramentoErgonomia(unittest.TestCase):
    def _snapshot(self, keypoints=True):
        return {
            "ambiente": {
                "ambiente_id": "amb-1",
                "nome": "Area 1",
                "calibrado": True,
                "epis_obrigatorios": ("Capacete",),
            },
            "cameras": {
                1: {
                    "camera_id": 1,
                    "camera_uid": "cam-1",
                    "nome": "CAM-01",
                    "tipo": "rtsp",
                    "status": "ONLINE",
                    "ativa": True,
                }
            },
            "pessoas": {
                (1, "track-abc"): {
                    "camera_id": 1,
                    "track_id": 10,
                    "track_instance_id": "track-abc",
                    "ativo": True,
                    "detectado_no_frame": True,
                    "keypoints": ({"nariz": {"x": 10, "y": 20, "confiavel": True}} if keypoints else {}),
                    "identidade": {
                        "matricula": "100001",
                        "conhecida": True,
                        "status_identidade": "IDENTIFICADO",
                    },
                }
            },
            "estados_epi_temporais": {
                (1, "track-abc", "Capacete"): {
                    "estado_confirmado": "CORRETO",
                }
            },
            "atualizado_em": "2026-09-19T23:30:00+00:00",
        }

    def _detalhes_ok(self):
        return {
            "sucesso": True,
            "erro": None,
            "colaborador": {
                "matricula": "100001",
                "nome": "Arthur Silva",
                "cargo": "Operador",
                "setor": "Producao",
            },
        }

    def _executar(self, snapshot, ergonomia_resultado=None, ergonomia_side_effect=None):
        with patch.object(
            monitoramento_service,
            "obter_detalhes_colaborador",
            return_value=self._detalhes_ok(),
        ):
            with patch.object(
                monitoramento_service,
                "obter_estado_ergonomia",
                return_value=ergonomia_resultado,
                side_effect=ergonomia_side_effect,
            ):
                return monitoramento_service.obter_monitoramento_colaborador(
                    "100001",
                    snapshot,
                )

    def test_01_sem_keypoints_ergonomia_permanece_indisponivel(self):
        resultado = self._executar(
            self._snapshot(keypoints=False),
            ergonomia_resultado={
                "estado": "ADEQUADA",
                "problemas": [],
                "modo": "EM_PE",
            },
        )
        self.assertEqual(
            resultado["monitoramento"]["ergonomia"],
            {
                "disponivel": False,
                "estado": None,
                "postura": None,
                "problemas": [],
            },
        )

    def test_02_ergonomia_adequada_em_pe(self):
        resultado = self._executar(
            self._snapshot(),
            ergonomia_resultado={
                "estado": "ADEQUADA",
                "problemas": [],
                "modo": "EM_PE",
                "metricas": {"x": 1},
            },
        )
        self.assertEqual(
            resultado["monitoramento"]["ergonomia"],
            {
                "disponivel": True,
                "estado": "ADEQUADA",
                "postura": "EM_PE",
                "problemas": [],
            },
        )

    def test_03_ergonomia_inadequada_preserva_problemas(self):
        problemas = [
            {"regiao": "Tronco", "descricao": "INCLINACAO EXCESSIVA"},
            {"regiao": "Bracos", "descricao": "ELEVACAO EXCESSIVA"},
        ]
        resultado = self._executar(
            self._snapshot(),
            ergonomia_resultado={
                "estado": "INADEQUADA",
                "problemas": problemas,
                "modo": "SENTADA",
            },
        )
        ergonomia = resultado["monitoramento"]["ergonomia"]
        self.assertTrue(ergonomia["disponivel"])
        self.assertEqual(ergonomia["estado"], "INADEQUADA")
        self.assertEqual(ergonomia["postura"], "SENTADA")
        self.assertEqual(ergonomia["problemas"], problemas)

    def test_04_estado_indeterminado_continua_fonte_disponivel(self):
        resultado = self._executar(
            self._snapshot(),
            ergonomia_resultado={
                "estado": "INDETERMINADA",
                "problemas": [],
                "modo": "INDETERMINADA",
            },
        )
        ergonomia = resultado["monitoramento"]["ergonomia"]
        self.assertTrue(ergonomia["disponivel"])
        self.assertEqual(ergonomia["estado"], "INDETERMINADA")
        self.assertEqual(ergonomia["postura"], "INDETERMINADA")

    def test_05_falha_ao_ler_runtime_nao_quebra_monitoramento(self):
        resultado = self._executar(
            self._snapshot(),
            ergonomia_side_effect=RuntimeError("falha runtime"),
        )
        self.assertTrue(resultado["sucesso"])
        self.assertEqual(
            resultado["monitoramento"]["ergonomia"],
            {
                "disponivel": False,
                "estado": None,
                "postura": None,
                "problemas": [],
            },
        )

    def test_06_consulta_nao_altera_snapshot(self):
        snapshot = self._snapshot()
        antes = copy.deepcopy(snapshot)
        resultado = self._executar(
            snapshot,
            ergonomia_resultado={
                "estado": "ADEQUADA",
                "problemas": [],
                "modo": "EM_PE",
            },
        )
        self.assertTrue(resultado["sucesso"])
        self.assertEqual(snapshot, antes)


if __name__ == "__main__":
    unittest.main(verbosity=2)

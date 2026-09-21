from __future__ import annotations

import copy
import unittest

from estado_sistema import (
    CAMERA_ONLINE,
    EPI_AUSENTE,
    EPI_CORRETO,
    EstadoAmbiente,
    EstadoCamera,
    EstadoEPITemporal,
    EstadoSistema,
    IdentidadePessoa,
    PessoaTrack,
    IDENTIDADE_IDENTIFICADO,
)
from services.colaborador_service import listar_colaboradores
from services.monitoramento_colaborador_service import (
    obter_monitoramento_colaborador,
)


class TestIntegracaoMonitoramentoEstadoSistemaReal(unittest.TestCase):
    """
    Integração do monitoramento com as classes REAIS de estado_sistema.py.

    Não usa EstadoSistemaFake.
    Não altera CSV.
    Não altera biometria.
    Não abre câmera.
    Não executa IA.
    """

    @classmethod
    def setUpClass(cls):
        cadastro = listar_colaboradores()
        if not cadastro.get("sucesso"):
            raise AssertionError(
                f"Falha ao ler colaboradores reais: {cadastro}"
            )

        colaboradores = cadastro.get("colaboradores") or []
        if not colaboradores:
            raise AssertionError(
                "Nenhum colaborador real cadastrado para o teste."
            )

        cls.colaborador = colaboradores[0]
        cls.matricula = str(cls.colaborador["matricula"])

    def _criar_estado(self):
        ambiente = EstadoAmbiente(
            ambiente_id="TESTE-INTEGRACAO-MONITORAMENTO",
            nome="Ambiente Teste Integração",
            carregado=True,
            calibrado=True,
            camera_ids=[1],
            epis_obrigatorios=["Capacete"],
        )

        estado = EstadoSistema(
            fase_execucao="MONITORAMENTO",
            ambiente=ambiente,
        )

        estado.cameras[1] = EstadoCamera(
            camera_id=1,
            nome="Camera Teste Integração",
            tipo="rtsp",
            camera_uid="camera-teste-integracao",
            status=CAMERA_ONLINE,
            ativa=True,
            tracks_ativos=[10],
        )

        identidade = IdentidadePessoa(
            conhecida=True,
            status_identidade=IDENTIDADE_IDENTIFICADO,
            matricula=self.matricula,
            nome=str(self.colaborador.get("nome") or ""),
            cargo=str(self.colaborador.get("cargo") or ""),
            motivo="TESTE_INTEGRACAO",
        )

        pessoa = PessoaTrack(
            camera_id=1,
            track_id=10,
            track_instance_id="track-integracao-001",
            ativo=True,
            detectado_no_frame=True,
            bbox=(10.0, 20.0, 100.0, 200.0),
            confianca=0.95,
            identidade=identidade,
        )

        estado.pessoas[
            (1, "track-integracao-001")
        ] = pessoa

        estado.estados_epi_temporais[
            (1, "track-integracao-001", "Capacete")
        ] = EstadoEPITemporal(
            camera_id=1,
            track_id=10,
            track_instance_id="track-integracao-001",
            epi="Capacete",
            estado_instantaneo=EPI_CORRETO,
            estado_confirmado=EPI_CORRETO,
            confirmado_desde=1.0,
            ultima_observacao=2.0,
            status_temporal="CONFIRMADO",
        )

        return estado

    def test_01_estado_sistema_real_conforme(self):
        estado = self._criar_estado()
        snapshot_antes = copy.deepcopy(estado.snapshot())

        resultado = obter_monitoramento_colaborador(
            self.matricula,
            estado,
        )

        self.assertTrue(resultado["sucesso"])
        self.assertEqual(
            resultado["colaborador"]["matricula"],
            self.matricula,
        )
        self.assertTrue(
            resultado["colaborador"]["identificado"]
        )
        self.assertTrue(
            resultado["monitoramento"]["presente"]
        )
        self.assertEqual(
            resultado["monitoramento"]["status_geral"],
            "CONFORME",
        )
        self.assertEqual(
            resultado["monitoramento"]["camera"]["camera_uid"],
            "camera-teste-integracao",
        )
        self.assertEqual(
            resultado["monitoramento"]["ambiente"]["ambiente_id"],
            "TESTE-INTEGRACAO-MONITORAMENTO",
        )

        self.assertEqual(
            estado.snapshot(),
            snapshot_antes,
            "O serviço alterou o EstadoSistema real.",
        )

    def test_02_estado_sistema_real_nao_conforme(self):
        estado = self._criar_estado()

        estado.estados_epi_temporais[
            (1, "track-integracao-001", "Capacete")
        ] = EstadoEPITemporal(
            camera_id=1,
            track_id=10,
            track_instance_id="track-integracao-001",
            epi="Capacete",
            estado_instantaneo=EPI_AUSENTE,
            estado_confirmado=EPI_AUSENTE,
            confirmado_desde=1.0,
            ultima_observacao=2.0,
            status_temporal="CONFIRMADO",
        )

        resultado = obter_monitoramento_colaborador(
            self.matricula,
            estado,
        )

        self.assertTrue(resultado["sucesso"])
        self.assertEqual(
            resultado["monitoramento"]["status_geral"],
            "NAO_CONFORME",
        )
        self.assertEqual(
            resultado["monitoramento"]["epis_obrigatorios"],
            [
                {
                    "epi": "Capacete",
                    "estado": "AUSENTE",
                }
            ],
        )

    def test_03_estado_sistema_real_colaborador_ausente(self):
        estado = self._criar_estado()
        estado.pessoas.clear()
        estado.estados_epi_temporais.clear()

        resultado = obter_monitoramento_colaborador(
            self.matricula,
            estado,
        )

        self.assertTrue(resultado["sucesso"])
        self.assertFalse(
            resultado["colaborador"]["identificado"]
        )
        self.assertFalse(
            resultado["monitoramento"]["presente"]
        )
        self.assertEqual(
            resultado["monitoramento"]["status_geral"],
            "INDETERMINADO",
        )
        self.assertIsNone(
            resultado["monitoramento"]["camera"]
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)

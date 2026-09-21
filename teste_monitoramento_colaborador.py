from __future__ import annotations

import copy
import csv
import hashlib
import importlib
import os
import tempfile
import unittest
from unittest.mock import patch

import cv2
import numpy as np

import services.colaborador_service as colaborador_service


class EstadoSistemaFake:
    def __init__(self, snapshot):
        self._snapshot = snapshot

    def snapshot(self):
        return copy.deepcopy(self._snapshot)


class TestMonitoramentoColaborador(unittest.TestCase):
    """
    Testes da etapa Monitoramento do Colaborador.

    Contrato esperado:

    services/monitoramento_colaborador_service.py

    obter_monitoramento_colaborador(
        matricula,
        estado_sistema,
    ) -> {
        "sucesso": bool,
        "erro": str | None,
        "colaborador": {
            "matricula": str,
            "nome": str,
            "cargo": str,
            "identificado": bool,
        } | None,
        "monitoramento": {
            "presente": bool,
            "camera": dict | None,
            "ambiente": dict | None,
            "status_geral": "CONFORME" | "NAO_CONFORME" | "INDETERMINADO",
            "epis_obrigatorios": [
                {"epi": str, "estado": str},
            ],
            "ergonomia": {
                "disponivel": bool,
                "estado": str | None,
                "postura": str | None,
                "problemas": list,
            },
            "atualizado_em": str | None,
        } | None,
    }

    Regras:
    - somente EPIs obrigatórios entram na resposta;
    - todos CORRETO -> CONFORME;
    - AUSENTE ou INCORRETO -> NAO_CONFORME;
    - sem confirmação suficiente -> INDETERMINADO;
    - consulta é somente-leitura;
    - biometria e EstadoSistema não podem ser alterados;
    - ergonomia deve ser marcada como indisponível quando o runtime
      atual não fornecer uma fonte explícita.
    """

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.pasta_biometria = os.path.join(
            self.temp_dir.name,
            "banco_biometria",
        )
        self.arquivo_csv = os.path.join(
            self.pasta_biometria,
            "dados_operadores.csv",
        )
        os.makedirs(self.pasta_biometria, exist_ok=True)

        with open(
            self.arquivo_csv,
            "w",
            encoding="utf-8",
            newline="",
        ) as arquivo:
            writer = csv.DictWriter(
                arquivo,
                fieldnames=["Matricula", "Nome", "Cargo"],
            )
            writer.writeheader()
            writer.writerow({
                "Matricula": "100001",
                "Nome": "Arthur Silva",
                "Cargo": "Operador",
            })
            writer.writerow({
                "Matricula": "100002",
                "Nome": "Beatriz Souza",
                "Cargo": "Supervisora",
            })

        self._criar_biometria("100001")
        self._criar_biometria("100002")

        self.patch_csv = patch.object(
            colaborador_service,
            "ARQUIVO_CSV",
            self.arquivo_csv,
        )
        self.patch_biometria = patch.object(
            colaborador_service,
            "PASTA_BIOMETRIA",
            self.pasta_biometria,
        )
        self.patch_csv.start()
        self.patch_biometria.start()

    def tearDown(self):
        self.patch_biometria.stop()
        self.patch_csv.stop()
        self.temp_dir.cleanup()

    def _criar_biometria(self, matricula):
        caminho = os.path.join(
            self.pasta_biometria,
            f"{matricula}.jpg",
        )
        imagem = np.zeros((64, 64, 3), dtype=np.uint8)
        imagem[:, :] = (120, 120, 120)
        self.assertTrue(cv2.imwrite(caminho, imagem))
        return caminho

    @staticmethod
    def _hash_arquivo(caminho):
        sha = hashlib.sha256()
        with open(caminho, "rb") as arquivo:
            for bloco in iter(lambda: arquivo.read(8192), b""):
                sha.update(bloco)
        return sha.hexdigest()

    def _funcao_monitoramento(self):
        try:
            modulo = importlib.import_module(
                "services.monitoramento_colaborador_service"
            )
        except ModuleNotFoundError as erro:
            self.fail(
                "Módulo services.monitoramento_colaborador_service "
                "ainda não foi implementado. "
                f"Detalhe: {erro}"
            )

        funcao = getattr(
            modulo,
            "obter_monitoramento_colaborador",
            None,
        )
        self.assertIsNotNone(
            funcao,
            "Função obter_monitoramento_colaborador "
            "ainda não foi implementada.",
        )
        return funcao

    def _snapshot_base(self):
        return {
            "fase_execucao": "MONITORAMENTO",
            "ambiente": {
                "ambiente_id": "amb-001",
                "nome": "Linha de Produção 1",
                "carregado": True,
                "calibrado": True,
                "camera_ids": (1,),
                "cameras_associadas": (),
                "epis_obrigatorios": (
                    "Capacete",
                    "Óculos",
                ),
                "total_objetos_globais": 0,
                "maquinarios": (),
            },
            "cameras": {
                1: {
                    "camera_id": 1,
                    "nome": "Camera Linha 1",
                    "tipo": "rtsp",
                    "camera_uid": "cam-uid-001",
                    "status_identidade": None,
                    "indice_runtime": 0,
                    "status": "ONLINE",
                    "ativa": True,
                    "ultimo_frame_em": 100.0,
                    "ultima_leitura_ok_em": 100.0,
                    "falhas_consecutivas": 0,
                    "tracks_ativos": (10,),
                },
            },
            "pessoas": {
                (1, "track-inst-001"): {
                    "camera_id": 1,
                    "track_id": 10,
                    "track_instance_id": "track-inst-001",
                    "ativo": True,
                    "detectado_no_frame": True,
                    "frames_sem_deteccao": 0,
                    "bbox": (10.0, 20.0, 100.0, 200.0),
                    "confianca": 0.95,
                    "primeira_deteccao_em": "2026-09-19T20:00:00+00:00",
                    "ultima_deteccao_em": "2026-09-19T20:00:05+00:00",
                    "keypoints": {},
                    "identidade": {
                        "conhecida": True,
                        "status_identidade": "IDENTIFICADO",
                        "status_processamento": "OCIOSO",
                        "matricula": "100001",
                        "nome": "Arthur Silva",
                        "cargo": "Operador",
                        "confianca": 0.92,
                        "distancia_match": 0.08,
                        "metodo": "DeepFace/cosine",
                        "modelo": "Facenet",
                        "tentativas": 1,
                        "tentativas_validas": 1,
                        "ultima_tentativa_monotonica": 99.0,
                        "candidato_matricula": None,
                        "confirmacoes_candidato": 0,
                        "confirmacoes_desconhecido": 0,
                        "candidato_conflito": None,
                        "confirmacoes_conflito": 0,
                        "job_pendente_id": None,
                        "observacao_pendente_id": None,
                        "motivo": "IDENTIDADE_CONFIRMADA",
                    },
                    "epis": {
                        "Capacete": "CORRETO",
                        "Óculos": "CORRETO",
                        "Luvas": "AUSENTE",
                    },
                },
            },
            "associacoes_epi": {},
            "evidencias_epi_sem_associacao": {},
            "estados_epi_individuais": {},
            "estados_epi_temporais": {
                (1, "track-inst-001", "Capacete"): {
                    "camera_id": 1,
                    "track_id": 10,
                    "track_instance_id": "track-inst-001",
                    "epi": "Capacete",
                    "estado_instantaneo": "CORRETO",
                    "estado_candidato": None,
                    "estado_confirmado": "CORRETO",
                    "candidato_desde": None,
                    "confirmado_desde": 90.0,
                    "ultima_observacao": 100.0,
                    "quantidade_observacoes_candidato": 0,
                    "status_temporal": "CONFIRMADO",
                    "atualizado_em": "2026-09-19T20:00:05+00:00",
                },
                (1, "track-inst-001", "Óculos"): {
                    "camera_id": 1,
                    "track_id": 10,
                    "track_instance_id": "track-inst-001",
                    "epi": "Óculos",
                    "estado_instantaneo": "CORRETO",
                    "estado_candidato": None,
                    "estado_confirmado": "CORRETO",
                    "candidato_desde": None,
                    "confirmado_desde": 90.0,
                    "ultima_observacao": 100.0,
                    "quantidade_observacoes_candidato": 0,
                    "status_temporal": "CONFIRMADO",
                    "atualizado_em": "2026-09-19T20:00:05+00:00",
                },
            },
            "incidentes": {},
            "notificacoes_incidentes": {},
            "metricas_runtime": {},
            "iniciado_em": "2026-09-19T19:00:00+00:00",
            "atualizado_em": "2026-09-19T20:00:05+00:00",
        }

    def _executar(self, matricula="100001", snapshot=None):
        funcao = self._funcao_monitoramento()
        estado = EstadoSistemaFake(
            snapshot if snapshot is not None else self._snapshot_base()
        )
        return funcao(matricula, estado)

    def test_01_identificado_e_todos_epis_corretos_conforme(self):
        resultado = self._executar()

        self.assertTrue(resultado["sucesso"])
        self.assertIsNone(resultado["erro"])

        colaborador = resultado["colaborador"]
        monitoramento = resultado["monitoramento"]

        self.assertEqual(colaborador["matricula"], "100001")
        self.assertEqual(colaborador["nome"], "Arthur Silva")
        self.assertEqual(colaborador["cargo"], "Operador")
        self.assertTrue(colaborador["identificado"])

        self.assertTrue(monitoramento["presente"])
        self.assertEqual(
            monitoramento["status_geral"],
            "CONFORME",
        )

    def test_02_epi_ausente_gera_nao_conforme(self):
        snapshot = self._snapshot_base()
        snapshot["estados_epi_temporais"][
            (1, "track-inst-001", "Capacete")
        ]["estado_confirmado"] = "AUSENTE"

        resultado = self._executar(snapshot=snapshot)

        self.assertTrue(resultado["sucesso"])
        self.assertEqual(
            resultado["monitoramento"]["status_geral"],
            "NAO_CONFORME",
        )

        estados = {
            item["epi"]: item["estado"]
            for item in resultado["monitoramento"]["epis_obrigatorios"]
        }
        self.assertEqual(estados["Capacete"], "AUSENTE")

    def test_03_epi_incorreto_gera_nao_conforme(self):
        snapshot = self._snapshot_base()
        snapshot["estados_epi_temporais"][
            (1, "track-inst-001", "Óculos")
        ]["estado_confirmado"] = "INCORRETO"

        resultado = self._executar(snapshot=snapshot)

        self.assertTrue(resultado["sucesso"])
        self.assertEqual(
            resultado["monitoramento"]["status_geral"],
            "NAO_CONFORME",
        )

    def test_04_epi_sem_estado_confirmado_gera_indeterminado(self):
        snapshot = self._snapshot_base()
        snapshot["estados_epi_temporais"][
            (1, "track-inst-001", "Óculos")
        ]["estado_confirmado"] = None
        snapshot["estados_epi_temporais"][
            (1, "track-inst-001", "Óculos")
        ]["estado_instantaneo"] = "CORRETO"

        resultado = self._executar(snapshot=snapshot)

        self.assertTrue(resultado["sucesso"])
        self.assertEqual(
            resultado["monitoramento"]["status_geral"],
            "INDETERMINADO",
        )

        estados = {
            item["epi"]: item["estado"]
            for item in resultado["monitoramento"]["epis_obrigatorios"]
        }
        self.assertEqual(estados["Óculos"], "INDETERMINADO")

    def test_05_colaborador_cadastrado_mas_nao_presente(self):
        snapshot = self._snapshot_base()
        snapshot["pessoas"] = {}
        snapshot["estados_epi_temporais"] = {}

        resultado = self._executar(snapshot=snapshot)

        self.assertTrue(resultado["sucesso"])
        self.assertFalse(resultado["colaborador"]["identificado"])
        self.assertFalse(resultado["monitoramento"]["presente"])
        self.assertEqual(
            resultado["monitoramento"]["status_geral"],
            "INDETERMINADO",
        )
        self.assertIsNone(resultado["monitoramento"]["camera"])

    def test_06_colaborador_nao_cadastrado(self):
        resultado = self._executar(matricula="999999")

        self.assertFalse(resultado["sucesso"])
        self.assertEqual(
            resultado["erro"],
            "COLABORADOR_NAO_ENCONTRADO",
        )
        self.assertIsNone(resultado["colaborador"])
        self.assertIsNone(resultado["monitoramento"])

    def test_07_expoe_camera_e_ambiente_corretos(self):
        resultado = self._executar()

        monitoramento = resultado["monitoramento"]

        self.assertEqual(
            monitoramento["ambiente"]["ambiente_id"],
            "amb-001",
        )
        self.assertEqual(
            monitoramento["ambiente"]["nome"],
            "Linha de Produção 1",
        )
        self.assertEqual(
            monitoramento["camera"]["camera_id"],
            1,
        )
        self.assertEqual(
            monitoramento["camera"]["camera_uid"],
            "cam-uid-001",
        )
        self.assertEqual(
            monitoramento["camera"]["nome"],
            "Camera Linha 1",
        )
        self.assertEqual(
            monitoramento["camera"]["status"],
            "ONLINE",
        )

    def test_08_apenas_epis_obrigatorios_sao_expostos(self):
        resultado = self._executar()

        epis = [
            item["epi"]
            for item in resultado["monitoramento"]["epis_obrigatorios"]
        ]

        self.assertEqual(
            epis,
            ["Capacete", "Óculos"],
        )
        self.assertNotIn("Luvas", epis)

    def test_09_estado_temporal_confirmado_tem_prioridade(self):
        snapshot = self._snapshot_base()

        snapshot["pessoas"][
            (1, "track-inst-001")
        ]["epis"]["Capacete"] = "CORRETO"

        snapshot["estados_epi_temporais"][
            (1, "track-inst-001", "Capacete")
        ]["estado_confirmado"] = "AUSENTE"

        resultado = self._executar(snapshot=snapshot)

        estados = {
            item["epi"]: item["estado"]
            for item in resultado["monitoramento"]["epis_obrigatorios"]
        }

        self.assertEqual(estados["Capacete"], "AUSENTE")
        self.assertEqual(
            resultado["monitoramento"]["status_geral"],
            "NAO_CONFORME",
        )

    def test_10_nao_associa_outro_colaborador_ao_monitoramento(self):
        snapshot = self._snapshot_base()

        identidade = snapshot["pessoas"][
            (1, "track-inst-001")
        ]["identidade"]
        identidade["matricula"] = "100002"
        identidade["nome"] = "Beatriz Souza"
        identidade["cargo"] = "Supervisora"

        resultado = self._executar(
            matricula="100001",
            snapshot=snapshot,
        )

        self.assertTrue(resultado["sucesso"])
        self.assertFalse(resultado["colaborador"]["identificado"])
        self.assertFalse(resultado["monitoramento"]["presente"])
        self.assertEqual(
            resultado["monitoramento"]["status_geral"],
            "INDETERMINADO",
        )

    def test_11_ergonomia_indisponivel_sem_fonte_runtime(self):
        resultado = self._executar()

        ergonomia = resultado["monitoramento"]["ergonomia"]

        self.assertEqual(
            ergonomia,
            {
                "disponivel": False,
                "estado": None,
                "postura": None,
                "problemas": [],
            },
        )

    def test_12_monitoramento_nao_altera_biometria_nem_estado(self):
        caminho_biometria = os.path.join(
            self.pasta_biometria,
            "100001.jpg",
        )
        hash_antes = self._hash_arquivo(caminho_biometria)

        snapshot = self._snapshot_base()
        snapshot_antes = copy.deepcopy(snapshot)

        resultado = self._executar(snapshot=snapshot)

        self.assertTrue(resultado["sucesso"])
        self.assertEqual(
            hash_antes,
            self._hash_arquivo(caminho_biometria),
        )
        self.assertEqual(snapshot, snapshot_antes)


if __name__ == "__main__":
    unittest.main(verbosity=2)

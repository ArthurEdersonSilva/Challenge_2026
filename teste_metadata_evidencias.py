from __future__ import annotations

import csv
import json
import os
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

import cv2
import numpy as np

import config
from estado_sistema import (
    EstadoSistema,
    EstadoEPIIndividual,
    EstadoEvidenciaSemanticaEPI,
)
from gestao_incidentes_epi import GestorIncidentesEPI
from services.evidencia_service import obter_detalhes_evidencia


CAMPOS_CSV = GestorIncidentesEPI.CAMPOS_CSV


def criar_evidencia_semantica(detection_id, epi, confianca, tipo="POSITIVO"):
    return EstadoEvidenciaSemanticaEPI(
        detection_id=detection_id,
        classe_modelo=epi,
        tipo_deteccao=tipo,
        bbox_epi=(10.0, 10.0, 40.0, 40.0),
        confianca_deteccao=confianca,
        status_associacao="ASSOCIADA",
        utilizavel=True,
        posicao="CORRETA",
    )


def criar_estado_runtime():
    estado = EstadoSistema(fase_execucao="TESTE")

    capacete_ev1 = criar_evidencia_semantica("DET_CAP_1", "Capacete", 0.91)
    capacete_ev2 = criar_evidencia_semantica("DET_CAP_2", "Capacete", 0.83)
    oculos_ev = criar_evidencia_semantica("DET_OC_1", "Óculos", 0.77, "NEGATIVO")

    estado.estados_epi_individuais[(0, "TRACK-1", "Capacete")] = EstadoEPIIndividual(
        camera_id=0,
        track_id=1,
        track_instance_id="TRACK-1",
        epi="Capacete",
        estado="CORRETO",
        evidencias_positivas=(capacete_ev1, capacete_ev2),
        metodo="TESTE",
    )
    estado.estados_epi_individuais[(0, "TRACK-1", "Óculos")] = EstadoEPIIndividual(
        camera_id=0,
        track_id=1,
        track_instance_id="TRACK-1",
        epi="Óculos",
        estado="AUSENTE",
        evidencias_negativas=(oculos_ev,),
        metodo="TESTE",
    )

    resultado = estado.garantir_incidente_epi_atomico(
        ambiente_id="AMB-1",
        ambiente_nome="Ambiente Teste",
        camera_id=0,
        camera_nome="Camera Teste",
        track_id=1,
        track_instance_id="TRACK-1",
        epi="Capacete",
        tipo_irregularidade="USO_INCORRETO_EPI",
        identidade={
            "status_identidade": "IDENTIFICADO",
            "matricula": "557079",
            "nome": "Arthur",
            "cargo": "Operador",
        },
        agora_monotonico=100.0,
        agora_datetime=datetime(2026, 9, 19, 18, 0, tzinfo=timezone.utc),
    )
    return estado, resultado["incidente"]


class TestMetadataEvidencias(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.raiz = Path(self.tmp.name)
        self.csv_path = self.raiz / "incidentes_epi.csv"
        self.pasta_provas = self.raiz / "provas_incidentes"
        config.PATH_INCIDENTES_EPI_CSV = str(self.csv_path)
        config.PASTA_PROVAS_INCIDENTES = str(self.pasta_provas)

    def tearDown(self):
        self.tmp.cleanup()

    def _capturar_nova_evidencia(self, contexto_override=None):
        estado, incidente = criar_estado_runtime()
        if contexto_override is not None:
            estado.obter_contexto_metadata_evidencia = lambda **kwargs: contexto_override

        gestor = GestorIncidentesEPI(
            estado_sistema=estado,
            caminho_csv=str(self.csv_path),
            pasta_evidencias=str(self.pasta_provas),
            intervalo_evidencia_segundos=0,
            qualidade_jpeg=90,
            salvar_frame_completo=True,
            salvar_crop_pessoa=True,
            now_fn=lambda: datetime(2026, 9, 19, 18, 0, tzinfo=timezone.utc),
        )
        frame = np.zeros((120, 160, 3), dtype=np.uint8)
        gestor._capturar_evidencia(
            incidente=incidente,
            frame=frame,
            bbox=(20, 20, 100, 110),
            agora_mono=101.0,
            agora_dt=datetime(2026, 9, 19, 18, 0, tzinfo=timezone.utc),
        )

        with self.csv_path.open("r", encoding="utf-8", newline="") as arq:
            linhas = list(csv.DictReader(arq))
        evid = next(l for l in linhas if l["tipo_registro"] == "EVIDENCIA")
        evidencia_id = evid["evidencia_id"]
        metadata_path = self.pasta_provas / incidente.incidente_id / f"{evidencia_id}_metadata.json"
        return estado, incidente, evid, metadata_path

    def test_01_contexto_runtime_confiança_e_epis(self):
        estado, _ = criar_estado_runtime()
        contexto = estado.obter_contexto_metadata_evidencia(
            camera_id=0,
            track_instance_id="TRACK-1",
            epi_incidente="Capacete",
        )
        self.assertEqual(contexto["confianca_deteccao"], 0.91)
        self.assertEqual([i["epi"] for i in contexto["epis_analisados"]], ["Capacete", "Óculos"])
        self.assertEqual(contexto["epis_analisados"][0]["estado"], "CORRETO")
        self.assertEqual(contexto["epis_analisados"][0]["confianca_deteccao"], 0.91)
        self.assertEqual(contexto["epis_analisados"][1]["estado"], "AUSENTE")
        self.assertEqual(contexto["epis_analisados"][1]["confianca_deteccao"], 0.77)
        self.assertIsNone(contexto["maquinario_relacionado"])

    def test_02_nova_evidencia_persiste_metadata_sem_alterar_csv(self):
        _, incidente, evid, metadata_path = self._capturar_nova_evidencia()
        self.assertTrue(metadata_path.exists())
        dados = json.loads(metadata_path.read_text(encoding="utf-8"))
        self.assertEqual(dados["schema_version"], 1)
        self.assertEqual(dados["evidencia_id"], evid["evidencia_id"])
        self.assertEqual(dados["incidente_id"], incidente.incidente_id)
        self.assertEqual(dados["confianca_deteccao"], 0.91)
        self.assertEqual(len(dados["epis_analisados"]), 2)
        self.assertIsNone(dados["maquinario_relacionado"])

        with self.csv_path.open("r", encoding="utf-8", newline="") as arq:
            leitor = csv.DictReader(arq)
            self.assertEqual(tuple(leitor.fieldnames), CAMPOS_CSV)
            self.assertNotIn("confianca_deteccao", leitor.fieldnames)
            self.assertNotIn("epis_analisados", leitor.fieldnames)
            self.assertNotIn("maquinario_relacionado", leitor.fieldnames)

    def test_03_service_le_metadata_novo(self):
        _, _, evid, _ = self._capturar_nova_evidencia()
        resultado = obter_detalhes_evidencia(evid["evidencia_id"])
        self.assertTrue(resultado["sucesso"])
        dados = resultado["evidencia"]
        self.assertTrue(dados["metadata_enriquecido_disponivel"])
        self.assertEqual(dados["confianca_deteccao"], 0.91)
        self.assertEqual(len(dados["epis_analisados"]), 2)
        self.assertIsNone(dados["maquinario_relacionado"])
        self.assertFalse(dados["maquinario_relacionado_disponivel"])

    def test_04_maquinario_so_e_persistido_quando_contexto_real_fornece(self):
        contexto = {
            "confianca_deteccao": 0.88,
            "epis_analisados": [
                {"epi": "Capacete", "estado": "INCORRETO", "confianca_deteccao": 0.88}
            ],
            "maquinario_relacionado": {
                "objeto_id": "OBJETO_007",
                "nome": "Máquina 02",
            },
        }
        _, _, evid, metadata_path = self._capturar_nova_evidencia(contexto_override=contexto)
        dados = json.loads(metadata_path.read_text(encoding="utf-8"))
        self.assertEqual(dados["maquinario_relacionado"], contexto["maquinario_relacionado"])

        resultado = obter_detalhes_evidencia(evid["evidencia_id"])
        self.assertTrue(resultado["sucesso"])
        detalhe = resultado["evidencia"]
        self.assertEqual(detalhe["maquinario_relacionado"], contexto["maquinario_relacionado"])
        self.assertTrue(detalhe["maquinario_relacionado_disponivel"])

    def test_05_historico_sem_metadata_continua_compativel_sem_inventar(self):
        incidente_id = "INC-HIST-001"
        evidencia_id = "EVID-HIST-001"
        pasta = self.pasta_provas / incidente_id
        pasta.mkdir(parents=True, exist_ok=True)
        imagem = pasta / f"{evidencia_id}_frame.jpg"
        cv2.imwrite(str(imagem), np.zeros((60, 80, 3), dtype=np.uint8))

        linhas = [
            {
                "schema_version": "1",
                "registro_id": "REG-HIST-AB",
                "incidente_id": incidente_id,
                "tipo_registro": "ABERTURA",
                "timestamp": "2026-08-30T03:06:40+00:00",
                "ambiente_id": "AMB-HIST",
                "ambiente_nome": "Histórico",
                "camera_id": "0",
                "camera_nome": "Camera Histórica",
                "track_id": "1",
                "track_instance_id": "TRACK-HIST",
                "epi": "Capacete",
                "tipo_irregularidade": "AUSENCIA_EPI",
                "estado_incidente": "ATIVO",
                "motivo_encerramento": "",
                "matricula": "--",
                "nome": "DESCONHECIDO",
                "cargo": "--",
                "status_identidade": "INDETERMINADO",
                "evidencia_id": "",
                "caminho_frame": "",
                "caminho_crop": "",
                "detalhe": "",
            },
            {
                "schema_version": "1",
                "registro_id": "REG-HIST-EV",
                "incidente_id": incidente_id,
                "tipo_registro": "EVIDENCIA",
                "timestamp": "2026-08-30T03:06:41+00:00",
                "ambiente_id": "AMB-HIST",
                "ambiente_nome": "Histórico",
                "camera_id": "0",
                "camera_nome": "Camera Histórica",
                "track_id": "1",
                "track_instance_id": "TRACK-HIST",
                "epi": "Capacete",
                "tipo_irregularidade": "AUSENCIA_EPI",
                "estado_incidente": "ATIVO",
                "motivo_encerramento": "",
                "matricula": "--",
                "nome": "DESCONHECIDO",
                "cargo": "--",
                "status_identidade": "INDETERMINADO",
                "evidencia_id": evidencia_id,
                "caminho_frame": str(imagem),
                "caminho_crop": "",
                "detalhe": "",
            },
        ]
        with self.csv_path.open("w", encoding="utf-8", newline="") as arq:
            w = csv.DictWriter(arq, fieldnames=CAMPOS_CSV)
            w.writeheader()
            w.writerows(linhas)

        metadata = pasta / f"{evidencia_id}_metadata.json"
        self.assertFalse(metadata.exists())

        resultado = obter_detalhes_evidencia(evidencia_id)
        self.assertTrue(resultado["sucesso"])
        dados = resultado["evidencia"]
        self.assertFalse(dados["metadata_enriquecido_disponivel"])
        self.assertIsNone(dados["confianca_deteccao"])
        self.assertEqual(dados["epis_analisados"], [])
        self.assertIsNone(dados["maquinario_relacionado"])
        self.assertFalse(dados["maquinario_relacionado_disponivel"])
        self.assertTrue(any("não foram reconstruídos" in x for x in resultado["limitacoes"]))


if __name__ == "__main__":
    unittest.main(verbosity=2)

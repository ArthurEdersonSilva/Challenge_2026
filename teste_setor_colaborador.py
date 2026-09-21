from __future__ import annotations

import csv
import hashlib
import io
import os
import tempfile
import unittest
from unittest.mock import patch

import cv2
import numpy as np

import api_sistema
import services.colaborador_service as service


class TestSetorColaboradorService(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.base = self.tmp.name
        self.bio_dir = os.path.join(self.base, "banco_biometria")
        self.csv_path = os.path.join(self.bio_dir, "dados_operadores.csv")
        os.makedirs(self.bio_dir, exist_ok=True)

        self.patch_csv = patch.object(service, "ARQUIVO_CSV", self.csv_path)
        self.patch_bio = patch.object(service, "PASTA_BIOMETRIA", self.bio_dir)
        self.patch_csv.start()
        self.patch_bio.start()

        # Arquivo LEGADO propositalmente sem a coluna Setor.
        with open(self.csv_path, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=["Matricula", "Nome", "Cargo"])
            writer.writeheader()
            writer.writerow({
                "Matricula": "557079",
                "Nome": "Arthur",
                "Cargo": "Operador",
            })

        self._criar_biometria("557079", 90)
        self.imagem = np.full((120, 120, 3), 127, dtype=np.uint8)

    def tearDown(self):
        self.patch_bio.stop()
        self.patch_csv.stop()
        self.tmp.cleanup()

    def _criar_biometria(self, matricula: str, valor: int = 100) -> str:
        caminho = os.path.join(self.bio_dir, f"{matricula}.jpg")
        imagem = np.full((64, 64, 3), valor, dtype=np.uint8)
        self.assertTrue(cv2.imwrite(caminho, imagem))
        return caminho

    @staticmethod
    def _hash(caminho: str) -> str:
        sha = hashlib.sha256()
        with open(caminho, "rb") as f:
            for bloco in iter(lambda: f.read(8192), b""):
                sha.update(bloco)
        return sha.hexdigest()

    @staticmethod
    def _validacao_ok(_imagem):
        return {
            "sucesso": True,
            "erro": None,
            "captura_valida": True,
            "quantidade_rostos": 1,
            "motivo": "UM_ROSTO_UTILIZAVEL",
            "confiancas": [0.99],
        }

    def test_01_csv_legado_sem_setor_continua_compativel(self):
        r = service.obter_colaborador("557079")
        self.assertTrue(r["sucesso"], r)
        self.assertEqual(r["colaborador"]["nome"], "Arthur")
        self.assertEqual(r["colaborador"]["cargo"], "Operador")
        self.assertIsNone(r["colaborador"]["setor"])

    def test_02_cadastro_novo_com_setor(self):
        with patch.object(service, "validar_captura_facial", side_effect=self._validacao_ok):
            r = service.cadastrar_colaborador(
                "900001",
                "Colaborador Setor",
                "Operador",
                self.imagem,
                setor="Produção",
            )

        self.assertTrue(r["sucesso"], r)
        self.assertEqual(r["colaborador"]["setor"], "Produção")
        self.assertTrue(os.path.isfile(os.path.join(self.bio_dir, "900001.jpg")))

    def test_03_cadastro_sem_setor_continua_valido(self):
        with patch.object(service, "validar_captura_facial", side_effect=self._validacao_ok):
            r = service.cadastrar_colaborador(
                "900002",
                "Sem Setor",
                "Operador",
                self.imagem,
            )

        self.assertTrue(r["sucesso"], r)
        self.assertIsNone(r["colaborador"]["setor"])

    def test_04_editar_setor_preserva_biometria(self):
        caminho = os.path.join(self.bio_dir, "557079.jpg")
        hash_antes = self._hash(caminho)

        r = service.editar_colaborador(
            "557079",
            setor="Logística",
        )

        self.assertTrue(r["sucesso"], r)
        self.assertEqual(r["colaborador"]["setor"], "Logística")
        self.assertEqual(hash_antes, self._hash(caminho))

    def test_05_setor_vazio_remove_setor_e_retorna_null(self):
        r1 = service.editar_colaborador("557079", setor="Operações")
        self.assertTrue(r1["sucesso"], r1)
        self.assertEqual(r1["colaborador"]["setor"], "Operações")

        r2 = service.editar_colaborador("557079", setor="")
        self.assertTrue(r2["sucesso"], r2)
        self.assertIsNone(r2["colaborador"]["setor"])

    def test_06_filtro_por_setor_case_insensitive(self):
        with patch.object(service, "validar_captura_facial", side_effect=self._validacao_ok):
            service.cadastrar_colaborador(
                "900003",
                "A",
                "Operador",
                self.imagem,
                setor="Produção",
            )
            service.cadastrar_colaborador(
                "900004",
                "B",
                "Operador",
                self.imagem,
                setor="Logística",
            )

        r = service.consultar_colaboradores(setor="produção")
        self.assertTrue(r["sucesso"], r)
        self.assertEqual(r["total"], 1)
        self.assertEqual(r["colaboradores"][0]["matricula"], "900003")
        self.assertEqual(r["colaboradores"][0]["setor"], "Produção")

    def test_07_busca_textual_tambem_considera_setor(self):
        with patch.object(service, "validar_captura_facial", side_effect=self._validacao_ok):
            service.cadastrar_colaborador(
                "900005",
                "C",
                "Operador",
                self.imagem,
                setor="Qualidade",
            )

        r = service.consultar_colaboradores(busca="qualidade")
        self.assertTrue(r["sucesso"], r)
        self.assertEqual(r["total"], 1)
        self.assertEqual(r["colaboradores"][0]["matricula"], "900005")

    def test_08_primeira_escrita_migra_csv_sem_perder_legado(self):
        r = service.editar_colaborador("557079", setor="Manutenção")
        self.assertTrue(r["sucesso"], r)

        with open(self.csv_path, "r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            self.assertEqual(
                reader.fieldnames,
                ["Matricula", "Nome", "Cargo", "Setor"],
            )
            linhas = list(reader)

        self.assertEqual(len(linhas), 1)
        self.assertEqual(linhas[0]["Matricula"], "557079")
        self.assertEqual(linhas[0]["Nome"], "Arthur")
        self.assertEqual(linhas[0]["Cargo"], "Operador")
        self.assertEqual(linhas[0]["Setor"], "Manutenção")


class TestSetorColaboradorHTTP(unittest.TestCase):
    def setUp(self):
        api_sistema.app.config.update(TESTING=True, PROPAGATE_EXCEPTIONS=False)
        self.client = api_sistema.app.test_client()
        self.headers = {"X-Perfil": "GERENCIAL"}

    @staticmethod
    def _jpeg_bytes() -> bytes:
        imagem = np.full((32, 32, 3), 120, dtype=np.uint8)
        ok, buffer = cv2.imencode(".jpg", imagem)
        if not ok:
            raise AssertionError("Falha ao criar JPEG de teste.")
        return buffer.tobytes()

    def test_09_get_encaminha_filtro_setor(self):
        retorno = {
            "sucesso": True,
            "erro": None,
            "total": 0,
            "pagina": 1,
            "por_pagina": 20,
            "total_paginas": 0,
            "colaboradores": [],
        }
        with patch.object(api_sistema, "consultar_colaboradores", return_value=retorno) as mock_service:
            resposta = self.client.get(
                "/api/colaboradores?setor=Produ%C3%A7%C3%A3o",
                headers=self.headers,
            )

        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(mock_service.call_args.kwargs["setor"], "Produção")

    def test_10_post_encaminha_setor(self):
        retorno = {
            "sucesso": True,
            "erro": None,
            "colaborador": {
                "matricula": "900010",
                "nome": "Teste",
                "cargo": "Operador",
                "setor": "Produção",
                "biometria_cadastrada": True,
            },
        }
        with patch.object(api_sistema, "cadastrar_colaborador", return_value=retorno) as mock_service:
            resposta = self.client.post(
                "/api/colaboradores",
                headers=self.headers,
                data={
                    "matricula": "900010",
                    "nome": "Teste",
                    "cargo": "Operador",
                    "setor": "Produção",
                    "imagem_biometrica": (io.BytesIO(self._jpeg_bytes()), "bio.jpg"),
                },
                content_type="multipart/form-data",
            )

        self.assertEqual(resposta.status_code, 201)
        self.assertEqual(mock_service.call_args.kwargs["setor"], "Produção")

    def test_11_put_encaminha_setor(self):
        retorno = {
            "sucesso": True,
            "erro": None,
            "colaborador": {
                "matricula": "557079",
                "nome": "Arthur",
                "cargo": "Operador",
                "setor": "Logística",
                "biometria_cadastrada": True,
            },
        }
        with patch.object(api_sistema, "editar_colaborador", return_value=retorno) as mock_service:
            resposta = self.client.put(
                "/api/colaboradores/557079",
                headers=self.headers,
                json={"setor": "Logística"},
            )

        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(mock_service.call_args.kwargs["setor"], "Logística")

    def test_12_operador_continua_bloqueado(self):
        resposta = self.client.get(
            "/api/colaboradores?setor=Produção",
            headers={"X-Perfil": "OPERADOR", "X-Matricula": "557079"},
        )
        self.assertEqual(resposta.status_code, 403)
        self.assertEqual(resposta.get_json()["erro"], "ACESSO_NEGADO")


if __name__ == "__main__":
    unittest.main(verbosity=2)

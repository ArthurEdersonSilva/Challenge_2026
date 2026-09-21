from __future__ import annotations

import base64
import csv
import os
import tempfile
import unittest
from unittest.mock import patch

import cv2
import numpy as np

import api_sistema
import services.colaborador_service as colaborador_service


HEADERS_GERENCIAL = {"X-Perfil": "GERENCIAL"}
HEADERS_OPERADOR = {"X-Perfil": "OPERADOR", "X-Matricula": "COL-001"}


class TestHTTPColaboradorImagem(unittest.TestCase):
    def setUp(self):
        self.client = api_sistema.app.test_client()

    def test_01_operador_bloqueado_403(self):
        resposta = self.client.get(
            "/api/colaboradores/COL-001/imagem",
            headers=HEADERS_OPERADOR,
        )
        self.assertEqual(resposta.status_code, 403)
        self.assertEqual(resposta.get_json()["erro"], "ACESSO_NEGADO")

    @patch("api_sistema.obter_imagem_colaborador")
    def test_02_imagem_200(self, mock_imagem):
        mock_imagem.return_value = {
            "sucesso": True,
            "erro": None,
            "matricula": "COL-001",
            "mime_type": "image/jpeg",
            "largura": 120,
            "altura": 80,
            "imagem_disponivel": True,
            "imagem_base64": base64.b64encode(b"jpeg").decode("ascii"),
        }
        resposta = self.client.get(
            "/api/colaboradores/COL-001/imagem",
            headers=HEADERS_GERENCIAL,
        )
        self.assertEqual(resposta.status_code, 200)
        dados = resposta.get_json()
        self.assertTrue(dados["sucesso"])
        self.assertTrue(dados["imagem_disponivel"])
        self.assertEqual(dados["mime_type"], "image/jpeg")
        mock_imagem.assert_called_once_with("COL-001")

    @patch("api_sistema.obter_imagem_colaborador")
    def test_03_imagem_inexistente_404(self, mock_imagem):
        mock_imagem.return_value = {
            "sucesso": False,
            "erro": "IMAGEM_COLABORADOR_NAO_ENCONTRADA",
            "matricula": "COL-001",
            "imagem_disponivel": False,
        }
        resposta = self.client.get(
            "/api/colaboradores/COL-001/imagem",
            headers=HEADERS_GERENCIAL,
        )
        self.assertEqual(resposta.status_code, 404)
        self.assertEqual(
            resposta.get_json()["erro"],
            "IMAGEM_COLABORADOR_NAO_ENCONTRADA",
        )

    @patch("api_sistema.obter_imagem_colaborador")
    def test_04_erro_leitura_500(self, mock_imagem):
        mock_imagem.return_value = {
            "sucesso": False,
            "erro": "ERRO_LER_IMAGEM_COLABORADOR",
            "matricula": "COL-001",
            "imagem_disponivel": False,
        }
        resposta = self.client.get(
            "/api/colaboradores/COL-001/imagem",
            headers=HEADERS_GERENCIAL,
        )
        self.assertEqual(resposta.status_code, 500)
        self.assertEqual(
            resposta.get_json()["erro"],
            "ERRO_LER_IMAGEM_COLABORADOR",
        )


class TestServiceColaboradorImagem(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.pasta = self.tempdir.name
        self.csv_path = os.path.join(self.pasta, "dados_operadores.csv")
        self.bio_path = os.path.join(self.pasta, "biometria")
        os.makedirs(self.bio_path, exist_ok=True)

        with open(self.csv_path, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=["Matricula", "Nome", "Cargo"])
            writer.writeheader()
            writer.writerow({
                "Matricula": "COL-001",
                "Nome": "Teste",
                "Cargo": "Operador",
            })

        self.old_csv = colaborador_service.ARQUIVO_CSV
        self.old_pasta = colaborador_service.PASTA_BIOMETRIA
        colaborador_service.ARQUIVO_CSV = self.csv_path
        colaborador_service.PASTA_BIOMETRIA = self.bio_path

    def tearDown(self):
        colaborador_service.ARQUIVO_CSV = self.old_csv
        colaborador_service.PASTA_BIOMETRIA = self.old_pasta
        self.tempdir.cleanup()

    def test_05_service_retorna_base64_real(self):
        imagem = np.zeros((40, 60, 3), dtype=np.uint8)
        caminho = os.path.join(self.bio_path, "COL-001.jpg")
        self.assertTrue(cv2.imwrite(caminho, imagem))

        resultado = colaborador_service.obter_imagem_colaborador("COL-001")

        self.assertTrue(resultado["sucesso"])
        self.assertTrue(resultado["imagem_disponivel"])
        self.assertEqual(resultado["mime_type"], "image/jpeg")
        self.assertEqual(resultado["largura"], 60)
        self.assertEqual(resultado["altura"], 40)
        self.assertTrue(base64.b64decode(resultado["imagem_base64"]))

    def test_06_service_sem_arquivo_retorna_404_logico(self):
        resultado = colaborador_service.obter_imagem_colaborador("COL-001")
        self.assertFalse(resultado["sucesso"])
        self.assertEqual(resultado["erro"], "IMAGEM_COLABORADOR_NAO_ENCONTRADA")
        self.assertFalse(resultado["imagem_disponivel"])


if __name__ == "__main__":
    unittest.main(verbosity=2)

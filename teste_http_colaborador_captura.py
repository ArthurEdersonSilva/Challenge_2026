from __future__ import annotations

import io
import unittest
from unittest.mock import patch

import cv2
import numpy as np

import api_sistema


class TestHTTPColaboradorCaptura(unittest.TestCase):
    def setUp(self):
        self.client = api_sistema.app.test_client()
        self.headers_gerencial = {"X-Perfil": "GERENCIAL"}
        self.headers_operador = {
            "X-Perfil": "OPERADOR",
            "X-Matricula": "999001",
        }

    @staticmethod
    def _imagem_upload():
        imagem = np.full((80, 80, 3), 127, dtype=np.uint8)
        ok, buffer = cv2.imencode(".jpg", imagem)
        assert ok
        return io.BytesIO(buffer.tobytes())

    def test_01_operador_bloqueado_403(self):
        resposta = self.client.post(
            "/api/colaboradores/biometria/validar",
            headers=self.headers_operador,
            data={
                "imagem_biometrica": (self._imagem_upload(), "captura.jpg")
            },
            content_type="multipart/form-data",
        )
        self.assertEqual(resposta.status_code, 403)
        self.assertEqual(resposta.get_json()["erro"], "ACESSO_NEGADO")

    def test_02_imagem_obrigatoria_400(self):
        resposta = self.client.post(
            "/api/colaboradores/biometria/validar",
            headers=self.headers_gerencial,
            data={},
            content_type="multipart/form-data",
        )
        self.assertEqual(resposta.status_code, 400)
        self.assertEqual(
            resposta.get_json()["erro"],
            "IMAGEM_BIOMETRICA_OBRIGATORIA",
        )

    @patch("api_sistema.validar_captura_facial")
    def test_03_captura_valida_200(self, mock_validar):
        mock_validar.return_value = {
            "sucesso": True,
            "erro": None,
            "captura_valida": True,
            "quantidade_rostos": 1,
            "motivo": "OK",
            "confiancas": [0.95],
        }

        resposta = self.client.post(
            "/api/colaboradores/biometria/validar",
            headers=self.headers_gerencial,
            data={
                "imagem_biometrica": (self._imagem_upload(), "captura.jpg")
            },
            content_type="multipart/form-data",
        )

        self.assertEqual(resposta.status_code, 200)
        dados = resposta.get_json()
        self.assertTrue(dados["sucesso"])
        self.assertTrue(dados["captura_valida"])
        self.assertEqual(dados["quantidade_rostos"], 1)
        self.assertTrue(mock_validar.called)

    @patch("api_sistema.validar_captura_facial")
    def test_04_rosto_nao_detectado_400(self, mock_validar):
        mock_validar.return_value = {
            "sucesso": False,
            "erro": "ROSTO_NAO_DETECTADO",
            "captura_valida": False,
            "quantidade_rostos": 0,
            "motivo": "ROSTO_NAO_DETECTADO",
            "confiancas": [],
        }

        resposta = self.client.post(
            "/api/colaboradores/biometria/validar",
            headers=self.headers_gerencial,
            data={
                "imagem_biometrica": (self._imagem_upload(), "captura.jpg")
            },
            content_type="multipart/form-data",
        )

        self.assertEqual(resposta.status_code, 400)
        self.assertEqual(resposta.get_json()["erro"], "ROSTO_NAO_DETECTADO")

    @patch("api_sistema.validar_captura_facial")
    def test_05_multiplos_rostos_400(self, mock_validar):
        mock_validar.return_value = {
            "sucesso": False,
            "erro": "MULTIPLOS_ROSTOS_UTILIZAVEIS",
            "captura_valida": False,
            "quantidade_rostos": 2,
            "motivo": "MULTIPLOS_ROSTOS_UTILIZAVEIS",
            "confiancas": [0.95, 0.91],
        }

        resposta = self.client.post(
            "/api/colaboradores/biometria/validar",
            headers=self.headers_gerencial,
            data={
                "imagem_biometrica": (self._imagem_upload(), "captura.jpg")
            },
            content_type="multipart/form-data",
        )

        self.assertEqual(resposta.status_code, 400)
        dados = resposta.get_json()
        self.assertEqual(dados["erro"], "MULTIPLOS_ROSTOS_UTILIZAVEIS")
        self.assertEqual(dados["quantidade_rostos"], 2)


if __name__ == "__main__":
    unittest.main(verbosity=2)

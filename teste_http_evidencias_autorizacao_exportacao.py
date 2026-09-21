from __future__ import annotations

import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

import api_evidencias


GERENCIAL = {"X-Perfil": "GERENCIAL"}
GESTOR = {"X-Perfil": "GESTOR"}
OPERADOR = {
    "X-Perfil": "OPERADOR",
    "X-Matricula": "COL-001",
}


class TestEvidenciasAutorizacaoExportacao(unittest.TestCase):

    def setUp(self):
        self.client = api_evidencias.app.test_client()

    def test_01_health_continua_publico(self):
        resposta = self.client.get("/api/health")
        self.assertEqual(resposta.status_code, 200)
        self.assertTrue(resposta.get_json()["sucesso"])

    def test_02_dashboard_sem_autenticacao_401(self):
        resposta = self.client.get("/api/dashboard-infracoes")
        self.assertEqual(resposta.status_code, 401)
        self.assertEqual(
            resposta.get_json()["erro"],
            "NAO_AUTENTICADO",
        )

    def test_03_dashboard_operador_403(self):
        resposta = self.client.get(
            "/api/dashboard-infracoes",
            headers=OPERADOR,
        )
        self.assertEqual(resposta.status_code, 403)
        self.assertEqual(
            resposta.get_json()["erro"],
            "ACESSO_NEGADO",
        )

    def test_04_alias_gestor_e_aceito(self):
        with patch.object(
            api_evidencias,
            "obter_dashboard_infracoes",
            return_value={
                "sucesso": True,
                "erro": None,
                "indicadores": {},
            },
        ):
            resposta = self.client.get(
                "/api/dashboard-infracoes",
                headers=GESTOR,
            )
        self.assertEqual(resposta.status_code, 200)

    def test_05_evidencias_operador_403(self):
        resposta = self.client.get(
            "/api/evidencias",
            headers=OPERADOR,
        )
        self.assertEqual(resposta.status_code, 403)

    def test_06_relatorio_operador_403(self):
        resposta = self.client.get(
            "/api/relatorios/geral",
            headers=OPERADOR,
        )
        self.assertEqual(resposta.status_code, 403)

    def test_07_exportacao_sem_autenticacao_401(self):
        resposta = self.client.get(
            "/api/evidencias/EV-001/exportar"
        )
        self.assertEqual(resposta.status_code, 401)

    def test_08_exportacao_inexistente_404(self):
        with patch.object(
            api_evidencias,
            "exportar_evidencia",
            return_value={
                "sucesso": False,
                "erro": "EVIDENCIA_NAO_ENCONTRADA",
            },
        ):
            resposta = self.client.get(
                "/api/evidencias/EV-404/exportar",
                headers=GERENCIAL,
            )
        self.assertEqual(resposta.status_code, 404)

    def test_09_exportacao_erro_500(self):
        with patch.object(
            api_evidencias,
            "exportar_evidencia",
            return_value={
                "sucesso": False,
                "erro": "ERRO_EXPORTAR_EVIDENCIA",
            },
        ):
            resposta = self.client.get(
                "/api/evidencias/EV-500/exportar",
                headers=GERENCIAL,
            )
        self.assertEqual(resposta.status_code, 500)

    def test_10_exportacao_zip_200(self):
        def exportar_fake(evidencia_id, destino):
            arquivo = Path(destino)
            with zipfile.ZipFile(
                arquivo,
                "w",
                compression=zipfile.ZIP_DEFLATED,
            ) as zip_file:
                zip_file.writestr(
                    "metadata.json",
                    '{"evidencia_id":"EV-001"}',
                )

            return {
                "sucesso": True,
                "erro": None,
                "evidencia_id": evidencia_id,
                "arquivo": str(arquivo),
            }

        with patch.object(
            api_evidencias,
            "exportar_evidencia",
            side_effect=exportar_fake,
        ):
            resposta = self.client.get(
                "/api/evidencias/EV-001/exportar",
                headers=GERENCIAL,
            )

        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(
            resposta.mimetype,
            "application/zip",
        )
        self.assertIn(
            "evidencia_EV-001.zip",
            resposta.headers.get(
                "Content-Disposition",
                "",
            ),
        )
        self.assertGreater(len(resposta.data), 0)

    def test_11_evidencias_gerencial_200(self):
        with patch.object(
            api_evidencias,
            "listar_evidencias",
            return_value={
                "sucesso": True,
                "erro": None,
                "total": 0,
                "paginacao": {
                    "pagina": 1,
                    "por_pagina": 20,
                    "total_itens": 0,
                    "total_paginas": 0,
                },
                "evidencias": [],
            },
        ):
            resposta = self.client.get(
                "/api/evidencias",
                headers=GERENCIAL,
            )

        self.assertEqual(resposta.status_code, 200)
        self.assertTrue(resposta.get_json()["sucesso"])


if __name__ == "__main__":
    unittest.main(verbosity=2)

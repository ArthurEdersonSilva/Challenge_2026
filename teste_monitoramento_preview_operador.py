from __future__ import annotations

import unittest
from unittest.mock import patch

import api_sistema


HEADERS_OPERADOR = {
    "X-Perfil": "OPERADOR",
    "X-Matricula": "COL-001",
}


class TestMonitoramentoPreviewOperador(unittest.TestCase):
    def setUp(self):
        self.client = api_sistema.app.test_client()
        api_sistema.definir_estado_sistema(object())
        api_sistema._monitoramento_previews.clear()

    def tearDown(self):
        api_sistema._monitoramento_previews.clear()
        api_sistema.definir_estado_sistema(None)

    @staticmethod
    def _monitoramento_com_camera():
        return {
            "sucesso": True,
            "erro": None,
            "colaborador": {
                "matricula": "COL-001",
                "nome": "João",
                "cargo": "Operador",
                "identificado": True,
            },
            "monitoramento": {
                "presente": True,
                "camera": {
                    "camera_uid": "cam-uid-1",
                    "nome": "CAM-01",
                    "tipo": "rtsp",
                    "status": "ONLINE",
                    "fonte": "rtsp://segredo",
                    "senha": "nao-pode-vazar",
                },
                "ambiente": {
                    "ambiente_id": "amb-1",
                    "nome": "Área 01",
                    "calibrado": True,
                },
                "status_geral": "CONFORME",
                "epis_obrigatorios": [],
                "ergonomia": {
                    "disponivel": False,
                    "estado": None,
                    "postura": None,
                    "problemas": [],
                },
                "atualizado_em": None,
            },
        }

    def test_01_sem_autenticacao_retorna_401(self):
        resposta = self.client.post(
            "/api/monitoramento/me/preview"
        )
        self.assertEqual(resposta.status_code, 401)
        self.assertEqual(resposta.get_json()["erro"], "NAO_AUTENTICADO")

    def test_02_operador_sem_matricula_retorna_403(self):
        resposta = self.client.post(
            "/api/monitoramento/me/preview",
            headers={"X-Perfil": "OPERADOR"},
        )
        self.assertEqual(resposta.status_code, 403)
        self.assertEqual(resposta.get_json()["erro"], "ACESSO_NEGADO")

    def test_03_sem_estado_sistema_retorna_503(self):
        api_sistema.definir_estado_sistema(None)
        resposta = self.client.post(
            "/api/monitoramento/me/preview",
            headers=HEADERS_OPERADOR,
        )
        self.assertEqual(resposta.status_code, 503)
        self.assertEqual(
            resposta.get_json()["erro"],
            "ESTADO_SISTEMA_INDISPONIVEL",
        )

    def test_04_sem_camera_atual_retorna_503(self):
        monitoramento = self._monitoramento_com_camera()
        monitoramento["monitoramento"]["presente"] = False
        monitoramento["monitoramento"]["camera"] = None

        with patch.object(
            api_sistema,
            "obter_monitoramento_colaborador",
            return_value=monitoramento,
        ):
            resposta = self.client.post(
                "/api/monitoramento/me/preview",
                headers=HEADERS_OPERADOR,
            )

        self.assertEqual(resposta.status_code, 503)
        self.assertEqual(
            resposta.get_json()["erro"],
            "MONITORAMENTO_CAMERA_INDISPONIVEL",
        )

    def test_05_iniciar_preview_usa_camera_do_monitoramento_e_sanitiza(self):
        with (
            patch.object(
                api_sistema,
                "obter_monitoramento_colaborador",
                return_value=self._monitoramento_com_camera(),
            ),
            patch.object(
                api_sistema,
                "iniciar_preview",
                return_value={
                    "sucesso": True,
                    "erro": None,
                    "session_id": "preview-interno",
                    "camera_uid": "cam-uid-1",
                    "nome": "CAM-01",
                    "tipo": "rtsp",
                    "status": "PREVIEW_ATIVO",
                    "reutilizada": False,
                    "fonte": "rtsp://segredo",
                    "senha": "segredo",
                },
            ) as iniciar,
        ):
            resposta = self.client.post(
                "/api/monitoramento/me/preview",
                headers=HEADERS_OPERADOR,
            )

        self.assertEqual(resposta.status_code, 200)
        iniciar.assert_called_once_with("cam-uid-1")
        dados = resposta.get_json()
        self.assertTrue(dados["sucesso"])
        self.assertNotEqual(dados["session_id"], "preview-interno")
        texto = str(dados).lower()
        for chave in (
            "senha",
            "password",
            "usuario",
            "username",
            "fonte",
            "rtsp://",
            "stream_url",
        ):
            self.assertNotIn(chave, texto)

    def test_06_frame_usa_sessao_interna_sem_expor_id_interno(self):
        api_sistema._monitoramento_previews["token-publico"] = {
            "matricula": "COL-001",
            "camera_uid": "cam-uid-1",
            "preview_session_id": "preview-interno",
            "preview_reutilizado": False,
        }

        with patch.object(
            api_sistema,
            "obter_frame_preview",
            return_value={
                "sucesso": True,
                "erro": None,
                "session_id": "preview-interno",
                "camera_uid": "cam-uid-1",
                "mime_type": "image/jpeg",
                "frame_base64": "QUJD",
                "largura": 640,
                "altura": 480,
            },
        ) as frame:
            resposta = self.client.get(
                "/api/monitoramento/me/preview/token-publico/frame",
                headers=HEADERS_OPERADOR,
            )

        self.assertEqual(resposta.status_code, 200)
        frame.assert_called_once_with("preview-interno")
        dados = resposta.get_json()
        self.assertEqual(dados["session_id"], "token-publico")
        self.assertEqual(dados["frame_base64"], "QUJD")
        self.assertNotIn("preview-interno", str(dados))

    def test_07_outro_operador_nao_pode_usar_sessao(self):
        api_sistema._monitoramento_previews["token-publico"] = {
            "matricula": "COL-001",
            "camera_uid": "cam-uid-1",
            "preview_session_id": "preview-interno",
            "preview_reutilizado": False,
        }

        resposta = self.client.get(
            "/api/monitoramento/me/preview/token-publico/frame",
            headers={
                "X-Perfil": "OPERADOR",
                "X-Matricula": "COL-999",
            },
        )
        self.assertEqual(resposta.status_code, 403)
        self.assertEqual(resposta.get_json()["erro"], "ACESSO_NEGADO")

    def test_08_sessao_inexistente_retorna_404(self):
        resposta = self.client.get(
            "/api/monitoramento/me/preview/inexistente/frame",
            headers=HEADERS_OPERADOR,
        )
        self.assertEqual(resposta.status_code, 404)
        self.assertEqual(
            resposta.get_json()["erro"],
            "MONITORAMENTO_PREVIEW_NAO_ENCONTRADO",
        )

    def test_09_encerrar_sessao_propria_fecha_preview_criado_por_ela(self):
        api_sistema._monitoramento_previews["token-publico"] = {
            "matricula": "COL-001",
            "camera_uid": "cam-uid-1",
            "preview_session_id": "preview-interno",
            "preview_reutilizado": False,
        }

        with patch.object(
            api_sistema,
            "parar_preview",
            return_value={
                "sucesso": True,
                "erro": None,
                "session_id": "preview-interno",
                "status": "PREVIEW_ENCERRADO",
            },
        ) as parar:
            resposta = self.client.delete(
                "/api/monitoramento/me/preview/token-publico",
                headers=HEADERS_OPERADOR,
            )

        self.assertEqual(resposta.status_code, 200)
        parar.assert_called_once_with("preview-interno")
        self.assertNotIn("token-publico", api_sistema._monitoramento_previews)

    def test_10_encerrar_preview_reutilizado_nao_fecha_sessao_compartilhada(self):
        api_sistema._monitoramento_previews["token-publico"] = {
            "matricula": "COL-001",
            "camera_uid": "cam-uid-1",
            "preview_session_id": "preview-compartilhado",
            "preview_reutilizado": True,
        }

        with patch.object(api_sistema, "parar_preview") as parar:
            resposta = self.client.delete(
                "/api/monitoramento/me/preview/token-publico",
                headers=HEADERS_OPERADOR,
            )

        self.assertEqual(resposta.status_code, 200)
        parar.assert_not_called()
        self.assertNotIn("token-publico", api_sistema._monitoramento_previews)


if __name__ == "__main__":
    unittest.main(verbosity=2)

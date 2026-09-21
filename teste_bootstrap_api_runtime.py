import unittest
from unittest.mock import patch, MagicMock

import api_sistema
import main as pipeline_main
import executar_sistema_integrado as bootstrap


class _ThreadFake:
    def __init__(self, target=None, name=None, daemon=None):
        self.target = target
        self.name = name
        self.daemon = daemon
        self.started = False

    def start(self):
        self.started = True

    def is_alive(self):
        return self.started


class TestBootstrapRuntimeAPI(unittest.TestCase):

    def setUp(self):
        bootstrap._thread_api = None
        api_sistema.definir_estado_sistema(None)

    def tearDown(self):
        bootstrap._thread_api = None
        api_sistema.definir_estado_sistema(None)

    def test_01_injeta_mesma_instancia_estado_sistema(self):
        estado = bootstrap.preparar_estado_runtime()

        self.assertIs(
            estado,
            pipeline_main.estado_sistema,
        )
        self.assertIs(
            api_sistema.obter_estado_sistema(),
            pipeline_main.estado_sistema,
        )

    def test_02_nao_cria_segundo_estado_sistema(self):
        original = pipeline_main.estado_sistema

        bootstrap.preparar_estado_runtime()
        primeira = api_sistema.obter_estado_sistema()

        bootstrap.preparar_estado_runtime()
        segunda = api_sistema.obter_estado_sistema()

        self.assertIs(primeira, original)
        self.assertIs(segunda, original)
        self.assertIs(primeira, segunda)

    @patch.object(bootstrap.threading, "Thread", _ThreadFake)
    def test_03_api_inicia_em_thread_daemon(self):
        thread = bootstrap.iniciar_api_background()

        self.assertTrue(thread.started)
        self.assertTrue(thread.daemon)
        self.assertEqual(
            thread.name,
            "challenge-api-http",
        )
        self.assertIs(
            thread.target,
            bootstrap._executar_api,
        )

    @patch.object(bootstrap.threading, "Thread", _ThreadFake)
    def test_04_nao_duplica_thread_api_ativa(self):
        primeira = bootstrap.iniciar_api_background()
        segunda = bootstrap.iniciar_api_background()

        self.assertIs(primeira, segunda)

    def test_05_executar_api_usa_configuracao_local_sem_reloader(self):
        with patch.object(
            api_sistema.app,
            "run",
        ) as run_mock:
            bootstrap._executar_api()

        run_mock.assert_called_once_with(
            host="127.0.0.1",
            port=5000,
            debug=False,
            use_reloader=False,
            threaded=True,
        )

    def test_06_executar_injeta_antes_de_chamar_main(self):
        ordem = []

        def preparar_fake():
            ordem.append("estado")
            api_sistema.definir_estado_sistema(
                pipeline_main.estado_sistema
            )

        def api_fake():
            ordem.append("api")
            return MagicMock()

        def main_fake():
            self.assertIs(
                api_sistema.obter_estado_sistema(),
                pipeline_main.estado_sistema,
            )
            ordem.append("main")

        with patch.object(
            bootstrap,
            "preparar_estado_runtime",
            side_effect=preparar_fake,
        ), patch.object(
            bootstrap,
            "iniciar_api_background",
            side_effect=api_fake,
        ), patch.object(
            pipeline_main,
            "main",
            side_effect=main_fake,
        ):
            bootstrap.executar()

        self.assertEqual(
            ordem,
            ["estado", "api", "main"],
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)

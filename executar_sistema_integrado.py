from __future__ import annotations

import threading
from typing import Optional

import api_sistema
import main as pipeline_main


_HOST_API = "127.0.0.1"
_PORTA_API = 5000
_thread_api: Optional[threading.Thread] = None


def preparar_estado_runtime():
    """
    Injeta no transporte HTTP a MESMA instância de EstadoSistema
    utilizada pelo pipeline principal.

    Não cria um segundo EstadoSistema.
    """
    api_sistema.definir_estado_sistema(
        pipeline_main.estado_sistema
    )
    return pipeline_main.estado_sistema


def _executar_api():
    api_sistema.app.run(
        host=_HOST_API,
        port=_PORTA_API,
        debug=False,
        use_reloader=False,
        threaded=True,
    )


def iniciar_api_background():
    """
    Inicia a API Flask no mesmo processo do pipeline, em thread daemon.

    Isso permite que /api/monitoramento/... leia o EstadoSistema real
    atualizado pelo main.py.
    """
    global _thread_api

    if (
        _thread_api is not None
        and _thread_api.is_alive()
    ):
        return _thread_api

    _thread_api = threading.Thread(
        target=_executar_api,
        name="challenge-api-http",
        daemon=True,
    )
    _thread_api.start()

    return _thread_api


def executar():
    preparar_estado_runtime()
    iniciar_api_background()
    pipeline_main.main()


if __name__ == "__main__":
    executar()

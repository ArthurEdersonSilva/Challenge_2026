import socket
import time
from urllib.parse import urlparse, urlunparse

from services.camera_service import obter_camera, obter_status_camera


CAMERAS = [
    ("6cdd37e1-0fff-40cd-aabd-f3b92d690f9b", "Teste 1"),
    ("f8beea31-ea87-4ec6-8e7d-c41a4a277d0f", "Teste 2"),
    ("312ca746-58d5-440e-ac1c-e179ce68113e", "SICK"),
]

TIMEOUT_TCP = 3.0


def porta_padrao(esquema):
    esquema = str(esquema or "").lower()
    if esquema == "rtsp":
        return 554
    if esquema == "http":
        return 80
    if esquema == "https":
        return 443
    return None


def mascarar_url(url):
    parsed = urlparse(url)
    if not parsed.hostname:
        return url

    host = parsed.hostname
    if parsed.port:
        host = f"{host}:{parsed.port}"

    if parsed.username:
        host = f"***:***@{host}"

    return urlunparse(
        (
            parsed.scheme,
            host,
            parsed.path,
            parsed.params,
            parsed.query,
            parsed.fragment,
        )
    )


def diagnosticar(camera_uid, nome_esperado):
    print()
    print("=" * 72)
    print(f"CÂMERA: {nome_esperado}")
    print(f"UID: {camera_uid}")
    print("=" * 72)

    consulta = obter_camera(camera_uid)

    if not consulta.get("sucesso"):
        print("RESULTADO: FALHA")
        print(f"MOTIVO: {consulta.get('erro')}")
        return

    camera = consulta.get("camera") or {}
    nome = camera.get("nome")
    tipo = camera.get("tipo")
    conexao = camera.get("conexao") or {}
    fonte = str(conexao.get("fonte") or "").strip()

    print(f"Nome cadastrado: {nome}")
    print(f"Tipo: {tipo}")

    if not fonte:
        print("RESULTADO: FALHA")
        print("MOTIVO EXATO: FONTE_CAMERA_NAO_CONFIGURADA")
        return

    parsed = urlparse(fonte)
    endereco = parsed.hostname
    porta = parsed.port or porta_padrao(parsed.scheme)

    print(f"Fonte: {mascarar_url(fonte)}")
    print(f"Protocolo: {parsed.scheme or 'NÃO_IDENTIFICADO'}")
    print(f"Endereço: {endereco or 'NÃO_IDENTIFICADO'}")
    print(f"Porta: {porta if porta is not None else 'NÃO_IDENTIFICADA'}")

    # --------------------------------------------------------
    # DNS / resolução de endereço
    # --------------------------------------------------------
    ip_resolvido = None
    inicio = time.perf_counter()

    try:
        ip_resolvido = socket.gethostbyname(endereco)
        tempo_dns_ms = (time.perf_counter() - inicio) * 1000
        print(f"IP resolvido: {ip_resolvido}")
        print(f"Tempo resolução endereço: {tempo_dns_ms:.1f} ms")
    except Exception as erro:
        tempo_dns_ms = (time.perf_counter() - inicio) * 1000
        print(f"Tempo resolução endereço: {tempo_dns_ms:.1f} ms")
        print("TCP: FALHA")
        print(f"MOTIVO EXATO: {type(erro).__name__}: {erro}")
        return

    # --------------------------------------------------------
    # TCP / porta
    # --------------------------------------------------------
    if porta is None:
        print("TCP: NÃO TESTADO")
        print("MOTIVO EXATO: PORTA_NAO_IDENTIFICADA")
        return

    inicio = time.perf_counter()

    try:
        with socket.create_connection(
            (endereco, int(porta)),
            timeout=TIMEOUT_TCP,
        ):
            tempo_tcp_ms = (time.perf_counter() - inicio) * 1000

        print("TCP: OK")
        print(f"Tempo resposta TCP: {tempo_tcp_ms:.1f} ms")

    except Exception as erro:
        tempo_tcp_ms = (time.perf_counter() - inicio) * 1000
        print("TCP: FALHA")
        print(f"Tempo até falha TCP: {tempo_tcp_ms:.1f} ms")
        print(f"MOTIVO EXATO TCP: {type(erro).__name__}: {erro}")

        # Também mostra a interpretação oficial do camera_service.
        inicio_status = time.perf_counter()
        status = obter_status_camera(camera_uid)
        tempo_status_ms = (time.perf_counter() - inicio_status) * 1000

        print(f"Status camera_service: {status.get('status')}")
        print(f"Motivo camera_service: {status.get('motivo')}")
        print(f"Tempo camera_service: {tempo_status_ms:.1f} ms")
        return

    # --------------------------------------------------------
    # Teste completo do stream pelo camera_service
    # --------------------------------------------------------
    inicio_status = time.perf_counter()
    status = obter_status_camera(camera_uid)
    tempo_status_ms = (time.perf_counter() - inicio_status) * 1000

    print(f"Status camera_service: {status.get('status')}")
    print(f"Online: {status.get('online')}")
    print(f"Tempo teste completo: {tempo_status_ms:.1f} ms")

    if status.get("online"):
        print(
            "Stream: OK | "
            f"{status.get('largura')}x{status.get('altura')} | "
            f"FPS={status.get('fps')}"
        )
    else:
        print(
            "MOTIVO EXATO STREAM: "
            f"{status.get('motivo') or status.get('erro')}"
        )


def main():
    print()
    print("DIAGNÓSTICO DETALHADO DAS CÂMERAS")
    print(f"Timeout TCP: {TIMEOUT_TCP:.1f}s")

    for camera_uid, nome in CAMERAS:
        diagnosticar(camera_uid, nome)


if __name__ == "__main__":
    main()

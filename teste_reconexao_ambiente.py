import json
import time
import uuid

from services.camera_service import obter_status_camera
from services.ambiente_service import (
    criar_ambiente,
    definir_roi,
    finalizar_ambiente,
    obter_status_ambiente,
    remover_ambiente,
)


CAMERA_UID = "94172bf6-4532-448f-87ab-26b6ba11993d"
INTERVALO_SEGUNDOS = 2
TIMEOUT_SEGUNDOS = 60


def esperar_camera(online_esperado: bool):
    inicio = time.time()

    while time.time() - inicio < TIMEOUT_SEGUNDOS:
        status = obter_status_camera(CAMERA_UID)

        online = bool(status.get("online"))

        print(
            f"CÂMERA -> {status.get('status')} | "
            f"motivo={status.get('motivo')}"
        )

        if online == online_esperado:
            return status

        time.sleep(INTERVALO_SEGUNDOS)

    return None


def main():
    nome = f"TESTE_RECONEXAO_{uuid.uuid4().hex[:6]}"
    ambiente_id = None

    try:
        criado = criar_ambiente(
            nome,
            [CAMERA_UID],
        )

        if not criado.get("sucesso"):
            print("FALHA AO CRIAR AMBIENTE:")
            print(json.dumps(criado, ensure_ascii=False, indent=2))
            return

        ambiente_id = criado["ambiente"]["ambiente_id"]

        roi = definir_roi(
            ambiente_id,
            CAMERA_UID,
            0.10,
            0.10,
            0.90,
            0.90,
        )

        if not roi.get("sucesso"):
            print("FALHA AO DEFINIR ROI:")
            print(json.dumps(roi, ensure_ascii=False, indent=2))
            return

        finalizado = finalizar_ambiente(ambiente_id)

        if not finalizado.get("sucesso"):
            print("FALHA AO FINALIZAR AMBIENTE:")
            print(json.dumps(finalizado, ensure_ascii=False, indent=2))
            return

        print()
        print("=" * 60)
        print("ETAPA 1 — OFFLINE")
        print("=" * 60)
        input(
            "Desligue a câmera/servidor RTSP do celular e pressione ENTER..."
        )

        offline = esperar_camera(False)

        if offline is None:
            print("FALHA: câmera não ficou OFFLINE dentro do timeout.")
            return

        status_offline = obter_status_ambiente(ambiente_id)

        print()
        print("STATUS DO AMBIENTE COM CÂMERA OFFLINE:")
        print(
            json.dumps(
                status_offline,
                ensure_ascii=False,
                indent=2,
            )
        )

        passou_offline = (
            status_offline.get("status") == "COM_PROBLEMA"
            and status_offline.get("com_problema") is True
            and status_offline.get("monitoramento_ativo") is False
        )

        print()
        print("=" * 60)
        print("ETAPA 2 — RECONEXÃO")
        print("=" * 60)
        input(
            "Ligue novamente a câmera/servidor RTSP do celular e pressione ENTER..."
        )

        online = esperar_camera(True)

        if online is None:
            print("FALHA: câmera não voltou ONLINE dentro do timeout.")
            return

        status_online = obter_status_ambiente(ambiente_id)

        print()
        print("STATUS DO AMBIENTE APÓS RECONEXÃO:")
        print(
            json.dumps(
                status_online,
                ensure_ascii=False,
                indent=2,
            )
        )

        passou_online = (
            status_online.get("status") == "ATIVO"
            and status_online.get("monitoramento_ativo") is True
            and status_online.get("com_problema") is False
        )

        print()
        print("=" * 60)
        print("RESULTADO FINAL")
        print("=" * 60)

        if passou_offline and passou_online:
            print("PASSOU")
            print("COM_PROBLEMA -> ATIVO confirmado.")
        else:
            print("FALHOU")
            print(f"Offline correto: {passou_offline}")
            print(f"Online correto: {passou_online}")

    finally:
        if ambiente_id:
            limpeza = remover_ambiente(ambiente_id)
            print()
            print("LIMPEZA:")
            print(
                json.dumps(
                    limpeza,
                    ensure_ascii=False,
                    indent=2,
                )
            )


if __name__ == "__main__":
    main()

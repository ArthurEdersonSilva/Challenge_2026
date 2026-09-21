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

CAMERA_FIXA_UID = "8c086203-d10f-4782-b2b1-545996043e56"      # Integrated Webcam
CAMERA_TESTE_UID = "94172bf6-4532-448f-87ab-26b6ba11993d"     # TESTE_CELULAR_FINAL

INTERVALO_SEGUNDOS = 2
TIMEOUT_SEGUNDOS = 60


def esperar_camera(camera_uid, online_esperado):
    inicio = time.time()

    while time.time() - inicio < TIMEOUT_SEGUNDOS:
        status = obter_status_camera(camera_uid)

        print(
            f"{status.get('nome')} -> {status.get('status')} | "
            f"motivo={status.get('motivo')}"
        )

        if bool(status.get("online")) == bool(online_esperado):
            return status

        time.sleep(INTERVALO_SEGUNDOS)

    return None


def status_resumido(ambiente_id):
    resultado = obter_status_ambiente(ambiente_id)

    print(
        json.dumps(
            resultado,
            ensure_ascii=False,
            indent=2,
        )
    )

    return resultado


def main():
    nome = f"TESTE_MULTI_CAMERA_{uuid.uuid4().hex[:6]}"
    ambiente_id = None

    try:
        print()
        print("=" * 64)
        print("ETAPA 0 — CONFIRMAR AS DUAS CÂMERAS ONLINE")
        print("=" * 64)

        fixa = esperar_camera(CAMERA_FIXA_UID, True)
        teste = esperar_camera(CAMERA_TESTE_UID, True)

        if fixa is None:
            print("FALHA: câmera fixa não ficou ONLINE.")
            return

        if teste is None:
            print("FALHA: câmera do celular não ficou ONLINE.")
            return

        criado = criar_ambiente(
            nome,
            [
                CAMERA_FIXA_UID,
                CAMERA_TESTE_UID,
            ],
        )

        if not criado.get("sucesso"):
            print("FALHA AO CRIAR AMBIENTE:")
            print(json.dumps(criado, ensure_ascii=False, indent=2))
            return

        ambiente_id = criado["ambiente"]["ambiente_id"]

        for camera_uid in (
            CAMERA_FIXA_UID,
            CAMERA_TESTE_UID,
        ):
            roi = definir_roi(
                ambiente_id,
                camera_uid,
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
        print("=" * 64)
        print("ETAPA 1 — DUAS CÂMERAS ONLINE")
        print("=" * 64)

        status_inicial = status_resumido(ambiente_id)

        passou_inicial = (
            status_inicial.get("status") == "ATIVO"
            and status_inicial.get("monitoramento_ativo") is True
        )

        print()
        print("=" * 64)
        print("ETAPA 2 — DEIXAR APENAS A CÂMERA DO CELULAR OFFLINE")
        print("=" * 64)

        input(
            "Desligue SOMENTE a câmera/servidor RTSP do celular e pressione ENTER..."
        )

        offline = esperar_camera(CAMERA_TESTE_UID, False)

        if offline is None:
            print("FALHA: câmera do celular não ficou OFFLINE.")
            return

        status_offline = status_resumido(ambiente_id)

        cameras_offline = [
            camera
            for camera in status_offline.get("cameras", [])
            if camera.get("online") is False
        ]

        passou_offline = (
            status_offline.get("status") == "COM_PROBLEMA"
            and status_offline.get("com_problema") is True
            and status_offline.get("monitoramento_ativo") is False
            and len(cameras_offline) == 1
            and cameras_offline[0].get("camera_uid") == CAMERA_TESTE_UID
        )

        print()
        print("=" * 64)
        print("ETAPA 3 — RECONECTAR A CÂMERA DO CELULAR")
        print("=" * 64)

        input(
            "Ligue novamente a câmera/servidor RTSP do celular e pressione ENTER..."
        )

        online = esperar_camera(CAMERA_TESTE_UID, True)

        if online is None:
            print("FALHA: câmera do celular não voltou ONLINE.")
            return

        status_final = status_resumido(ambiente_id)

        passou_final = (
            status_final.get("status") == "ATIVO"
            and status_final.get("monitoramento_ativo") is True
            and status_final.get("com_problema") is False
            and all(
                camera.get("online") is True
                for camera in status_final.get("cameras", [])
            )
        )

        print()
        print("=" * 64)
        print("RESULTADO FINAL")
        print("=" * 64)

        if passou_inicial and passou_offline and passou_final:
            print("PASSOU")
            print("ATIVO -> COM_PROBLEMA -> ATIVO confirmado.")
        else:
            print("FALHOU")
            print(f"Inicial ATIVO: {passou_inicial}")
            print(f"Uma câmera OFFLINE -> COM_PROBLEMA: {passou_offline}")
            print(f"Reconexão -> ATIVO: {passou_final}")

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

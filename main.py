import cv2
import os
import csv
import torch
from ultralytics import YOLO
from deepface import DeepFace

import config
from decision_engine import processar_regras_situacionais


def carregar_dados_biometricos():
    arquivo_csv = os.path.join("banco_biometria", "dados_operadores.csv")
    operadores = {}
    if os.path.exists(arquivo_csv):
        with open(arquivo_csv, mode='r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for linha in reader:
                primeiro_nome = linha["Nome"].split()[0]
                operadores[linha["Matricula"]] = f"{primeiro_nome} ({linha['Cargo']})"
    return operadores


DADOS_OPERADORES = carregar_dados_biometricos()

# Classes usadas pelo modelo e nomes exibidos no painel.
# O modelo atual detecta principalmente as classes de ausencia de EPI.
EPIS_OBRIGATORIOS = {
    "Without Helmet": "Capacete",
    "Without Glass": "Oculos",
    "Without Ear Protectors": "Protetor auricular",
    "Without Safety Vest": "Colete",
    "Without Glove": "Luvas",
    "Without Mask": "Mascara",
}

# Se a classe de ausencia aparecer, o painel mostra NAO.
# Caso contrario, o painel mostra OK. Isso mantem a interface simples
# sem desenhar textos e caixas sobre o trabalhador.

if os.path.exists(config.PATH_MODELO):
    model_epi = YOLO(config.PATH_MODELO)
    print(f"Modelo de EPIs carregado: {config.PATH_MODELO}")
else:
    model_epi = YOLO("yolov8n.pt")

model_pose = YOLO("yolov8n-pose.pt")

device = "0" if torch.cuda.is_available() else ("mps" if torch.backends.mps.is_available() else "cpu")
model_epi.to(device)
model_pose.to(device)

# =====================================================================
# FUNCOES DE INTERFACE
# =====================================================================
def detectar_status_epis(results_epi):
    """Converte as deteccoes do modelo em status simples por EPI."""
    status = {nome: True for nome in EPIS_OBRIGATORIOS.values()}

    for r in results_epi:
        for box in r.boxes:
            cls_id = int(box.cls[0])
            label = r.names[cls_id]
            if label in EPIS_OBRIGATORIOS:
                nome_epi = EPIS_OBRIGATORIOS[label]
                status[nome_epi] = False

    return status


def desenhar_painel_epi(frame, status):
    """Desenha um painel lateral limpo com nome do EPI e OK/NAO."""
    altura, largura = frame.shape[:2]
    painel_largura = 250
    x_inicio = max(0, largura - painel_largura)

    painel = frame.copy()
    cv2.rectangle(painel, (x_inicio, 0), (largura, altura), (25, 25, 25), -1)
    cv2.addWeighted(painel, 0.88, frame, 0.12, 0, frame)

    cv2.putText(
        frame, "STATUS DE EPI", (x_inicio + 18, 38),
        cv2.FONT_HERSHEY_SIMPLEX, 0.72, (255, 255, 255), 2, cv2.LINE_AA
    )

    y = 78
    for nome, correto in status.items():
        texto_status = "OK" if correto else "NAO"
        cor = (0, 200, 0) if correto else (0, 0, 255)

        cv2.putText(
            frame, nome, (x_inicio + 18, y),
            cv2.FONT_HERSHEY_SIMPLEX, 0.52, (235, 235, 235), 1, cv2.LINE_AA
        )
        cv2.putText(
            frame, texto_status, (x_inicio + 178, y),
            cv2.FONT_HERSHEY_SIMPLEX, 0.58, cor, 2, cv2.LINE_AA
        )

        cv2.line(
            frame, (x_inicio + 18, y + 12), (largura - 18, y + 12),
            (75, 75, 75), 1
        )
        y += 48

    return frame


# =====================================================================
# SELETOR DE CAMERA
# =====================================================================
cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
# cap = cv2.VideoCapture(1)

cap.set(cv2.CAP_PROP_FRAME_WIDTH, config.LARGURA_CAM)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, config.ALTURA_CAM)

ultimo_operador_identificado = "Buscando Biometria..."
matricula_atual = "0000"
contador_frames = 0

while cap.isOpened():
    success, frame = cap.read()
    if not success:
        break

    results_epi = list(
        model_epi(
            frame,
            conf=config.CONFIDENCIA_MINIMA,
            imgsz=config.TAMANHO_IMAGEM,
            stream=True,
            device=device,
        )
    )
    results_pose = list(
        model_pose(frame, conf=0.5, stream=True, device=device)
    )

    # Comecamos sempre com o frame original.
    # Nao usamos r.plot() nem desenhamos bounding boxes dos EPIs.
    annotated_frame = frame.copy()
    ombro_esquerdo = [0, 0]
    quadril_esquerdo = [0, 0]

    contador_frames += 1

    for r_pose in results_pose:
        # Mantem apenas os keypoints da pose; as caixas do pose model ficam ocultas.
        annotated_frame = r_pose.plot(img=annotated_frame, boxes=False)

        if r_pose.keypoints is not None and len(r_pose.keypoints.xy) > 0:
            kp = r_pose.keypoints.xy[0].cpu().numpy()
            if len(kp) > 11:
                ombro_esquerdo = kp[5]
                quadril_esquerdo = kp[11]

        for box in r_pose.boxes:
            if int(box.cls[0]) == 0:
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                conf_pessoa = float(box.conf[0])

                if contador_frames % 15 == 0:
                    h_box = y2 - y1
                    y_peito = y1 + int(h_box * 0.55)
                    recorte_rosto = frame[
                        max(0, y1):max(0, y_peito),
                        max(0, x1):max(0, x2)
                    ]

                    if recorte_rosto.size > 0:
                        try:
                            match = DeepFace.find(
                                img_path=recorte_rosto,
                                db_path="banco_biometria",
                                model_name="Facenet",
                                enforce_detection=False,
                                silent=True,
                            )
                            if len(match) > 0 and not match[0].empty:
                                arquivo_id = os.path.basename(
                                    match[0].iloc[0]["identity"]
                                )
                                matricula_atual = os.path.splitext(arquivo_id)[0].split('_')[0]
                                ultimo_operador_identificado = DADOS_OPERADORES.get(
                                    matricula_atual, "Rosto Desconhecido"
                                )
                        except Exception:
                            pass

    severidade, lista_pes, epis_detectados = processar_regras_situacionais(
        results_epi,
        config.PONTOS_ZONA_RISCO,
        matricula=matricula_atual,
        operador=ultimo_operador_identificado,
        frame=frame,
        ombro=ombro_esquerdo,
        quadril=quadril_esquerdo,
    )

    # Status simples: nome do EPI na lateral + OK/NAO.
    status_epis = detectar_status_epis(results_epi)

    # Zona de risco continua visivel, mas sem textos/caixas de EPI sobre o operador.
    overlay = annotated_frame.copy()
    cv2.fillPoly(overlay, [config.PONTOS_ZONA_RISCO], (0, 0, 255))
    cv2.addWeighted(overlay, 0.18, annotated_frame, 0.82, 0, annotated_frame)

    for pe in lista_pes:
        cv2.circle(annotated_frame, pe, 6, (0, 255, 255), -1)

    if severidade == "CRITICA":
        cv2.putText(
            annotated_frame,
            "CRITICO: OPERADOR NA ZONA SEM CAPACETE!",
            (15, 40),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (0, 0, 255),
            2,
            cv2.LINE_AA,
        )
    elif severidade == "ALTA":
        cv2.putText(
            annotated_frame,
            "ALTO: INFRACAO OU FADIGA ERGONOMICA",
            (15, 40),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (0, 165, 255),
            2,
            cv2.LINE_AA,
        )

    annotated_frame = desenhar_painel_epi(annotated_frame, status_epis)

    cv2.imshow("FIAP x SPI Challenge 2026", annotated_frame)
    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

cap.release()
cv2.destroyAllWindows()

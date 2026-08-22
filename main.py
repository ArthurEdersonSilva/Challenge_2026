import cv2
import os
import csv
import torch
import numpy as np

from ultralytics import YOLO
from deepface import DeepFace

import config
from decision_engine import processar_regras_situacionais


# ============================================================
# CONFIGURAÇÕES
# ============================================================

LARGURA_SIDEBAR = 330

CAMERA_ID = 0


# ============================================================
# CLASSES DE EPI
# ============================================================

EQUIPAMENTOS_AUSENCIA = {
    "Without Helmet": "Capacete",
    "Without Glass": "Óculos",
    "Without Mask": "Máscara",
    "Without Glove": "Luvas",
    "Without Ear Protectors": "Protetor auricular",
    "Without Safety Vest": "Colete"
}


EQUIPAMENTOS_PRESENCA = {
    "Helmet": "Capacete",
    "Glass": "Óculos",
    "Mask": "Máscara",
    "Glove": "Luvas",
    "Ear Protectors": "Protetor auricular",
    "Safety Vest": "Colete"
}


# ============================================================
# CONFIGURAÇÃO DA CÂMERA
# ============================================================

def obter_configuracao_camera(camera_id):

    cameras = getattr(
        config,
        "CAMERAS",
        None
    )

    # --------------------------------------------------------
    # NOVA CONFIGURAÇÃO
    # --------------------------------------------------------

    if isinstance(cameras, dict):

        camera = cameras.get(
            camera_id
        )

        if camera is not None:

            return {
                "id": camera_id,
                "nome": camera.get(
                    "nome",
                    f"Câmera {camera_id + 1}"
                ),
                "ambiente": camera.get(
                    "ambiente",
                    "Ambiente não definido"
                ),
                "fonte": camera.get(
                    "fonte",
                    camera_id
                ),
                "ativa": camera.get(
                    "ativa",
                    True
                ),
                "epis_obrigatorios": camera.get(
                    "epis_obrigatorios",
                    getattr(
                        config,
                        "EPIS_PADRAO",
                        list(
                            EQUIPAMENTOS_AUSENCIA.values()
                        )
                    )
                ),
                "zona_risco": camera.get(
                    "zona_risco",
                    getattr(
                        config,
                        "PONTOS_ZONA_RISCO",
                        None
                    )
                )
            }

    # --------------------------------------------------------
    # COMPATIBILIDADE COM CONFIG ANTIGO
    # --------------------------------------------------------

    return {
        "id": camera_id,
        "nome": f"Câmera {camera_id + 1}",
        "ambiente": "Ambiente principal",
        "fonte": camera_id,
        "ativa": True,
        "epis_obrigatorios": getattr(
            config,
            "EPIS_PADRAO",
            list(
                EQUIPAMENTOS_AUSENCIA.values()
            )
        ),
        "zona_risco": getattr(
            config,
            "PONTOS_ZONA_RISCO",
            None
        )
    }


CONFIG_CAMERA = obter_configuracao_camera(
    CAMERA_ID
)


# ============================================================
# DADOS BIOMÉTRICOS
# ============================================================

def carregar_dados_biometricos():

    arquivo_csv = os.path.join(
        "banco_biometria",
        "dados_operadores.csv"
    )

    operadores = {}

    if not os.path.exists(
        arquivo_csv
    ):
        return operadores

    try:

        with open(
            arquivo_csv,
            mode="r",
            encoding="utf-8"
        ) as arquivo:

            reader = csv.DictReader(
                arquivo
            )

            for linha in reader:

                matricula = str(
                    linha.get(
                        "Matricula",
                        ""
                    )
                ).strip()

                nome = str(
                    linha.get(
                        "Nome",
                        ""
                    )
                ).strip()

                cargo = str(
                    linha.get(
                        "Cargo",
                        ""
                    )
                ).strip()

                if not matricula:
                    continue

                operadores[matricula] = {
                    "matricula": matricula,
                    "nome": nome,
                    "cargo": cargo
                }

    except Exception as erro:

        print(
            f"⚠️ Erro ao carregar biometria: {erro}"
        )

    return operadores


DADOS_OPERADORES = carregar_dados_biometricos()


# ============================================================
# FORMATA OPERADOR PARA SIDEBAR
# ============================================================

def formatar_operador(
    dados_operador
):

    if not dados_operador:
        return "Rosto Desconhecido"

    nome = dados_operador.get(
        "nome",
        "Desconhecido"
    )

    cargo = dados_operador.get(
        "cargo",
        ""
    )

    if cargo:

        return f"{nome} ({cargo})"

    return nome


# ============================================================
# CARREGAMENTO DOS MODELOS
# ============================================================

if os.path.exists(
    config.PATH_MODELO
):

    model_epi = YOLO(
        config.PATH_MODELO
    )

    print(
        f"✅ Modelo de EPIs carregado: "
        f"{config.PATH_MODELO}"
    )

else:

    model_epi = YOLO(
        "yolov8n.pt"
    )

    print(
        "⚠️ best.pt não encontrado. "
        "Usando yolov8n.pt."
    )


# ------------------------------------------------------------
# POSE
# ------------------------------------------------------------

model_pose = YOLO(
    "yolov8n-pose.pt"
)


# ============================================================
# DEVICE
# ============================================================

device = (
    "0"
    if torch.cuda.is_available()
    else (
        "mps"
        if torch.backends.mps.is_available()
        else "cpu"
    )
)


model_epi.to(device)
model_pose.to(device)


print(
    f"🖥️ Device utilizado: {device}"
)


# ============================================================
# CLASSES DO MODELO
# ============================================================

print()
print(
    "=============================="
)
print(
    "CLASSES DO MODELO DE EPI"
)
print(
    "=============================="
)

try:

    print(
        model_epi.names
    )

except Exception:

    print(
        "Não foi possível listar as classes."
    )

print(
    "=============================="
)
print()


# ============================================================
# CÂMERA
# ============================================================

if not CONFIG_CAMERA["ativa"]:

    print(
        f"❌ A câmera {CAMERA_ID} "
        "está desativada no config."
    )

    raise SystemExit


fonte_camera = CONFIG_CAMERA[
    "fonte"
]


cap = cv2.VideoCapture(
    fonte_camera,
    cv2.CAP_DSHOW
)


if not cap.isOpened():

    print(
        f"❌ Não foi possível abrir "
        f"a câmera {fonte_camera}."
    )

    raise SystemExit


cap.set(
    cv2.CAP_PROP_FRAME_WIDTH,
    config.LARGURA_CAM
)

cap.set(
    cv2.CAP_PROP_FRAME_HEIGHT,
    config.ALTURA_CAM
)


print(
    f"📷 Câmera ativa: "
    f"{CONFIG_CAMERA['nome']}"
)

print(
    f"🏭 Ambiente: "
    f"{CONFIG_CAMERA['ambiente']}"
)


# ============================================================
# VARIÁVEIS
# ============================================================

ultimo_operador_identificado = (
    "Buscando Biometria..."
)

dados_operador_atual = None

matricula_atual = "0000"

contador_frames = 0


# ============================================================
# ANALISAR STATUS DOS EPIs
# ============================================================

def analisar_status_epis(
    results_epi,
    epis_obrigatorios
):

    status = {}

    # --------------------------------------------------------
    # SOMENTE EPIs OBRIGATÓRIOS
    # --------------------------------------------------------

    for nome in epis_obrigatorios:

        status[nome] = {
            "status": "NÃO DETECTADO",
            "cor": (0, 200, 255)
        }

    classes_detectadas = set()

    # --------------------------------------------------------
    # CLASSES DETECTADAS
    # --------------------------------------------------------

    for resultado in results_epi:

        if resultado.boxes is None:
            continue

        for box in resultado.boxes:

            cls_id = int(
                box.cls[0]
            )

            label = resultado.names[
                cls_id
            ]

            classes_detectadas.add(
                label
            )

    # --------------------------------------------------------
    # ANALISA CADA EPI
    # --------------------------------------------------------

    for classe_ausencia, nome in (
        EQUIPAMENTOS_AUSENCIA.items()
    ):

        if nome not in epis_obrigatorios:
            continue

        classe_presenca = None

        for classe, nome_presenca in (
            EQUIPAMENTOS_PRESENCA.items()
        ):

            if nome_presenca == nome:

                classe_presenca = classe

                break

        # ----------------------------------------------------
        # AUSÊNCIA
        # ----------------------------------------------------

        if classe_ausencia in classes_detectadas:

            status[nome] = {
                "status": "FALTANTE",
                "cor": (0, 0, 255)
            }

        # ----------------------------------------------------
        # PRESENÇA
        # ----------------------------------------------------

        elif (
            classe_presenca is not None
            and classe_presenca
            in classes_detectadas
        ):

            status[nome] = {
                "status": "OK",
                "cor": (0, 200, 0)
            }

        # ----------------------------------------------------
        # SEM INFORMAÇÃO
        # ----------------------------------------------------

        else:

            status[nome] = {
                "status": "NÃO DETECTADO",
                "cor": (0, 200, 255)
            }

    return status


# ============================================================
# DESENHAR SIDEBAR
# ============================================================

def desenhar_sidebar(
    frame,
    status_epis,
    operador,
    severidade
):

    altura = frame.shape[0]

    sidebar = np.zeros(
        (
            altura,
            LARGURA_SIDEBAR,
            3
        ),
        dtype=np.uint8
    )

    sidebar[:] = (
        30,
        30,
        30
    )

    # ========================================================
    # TÍTULO
    # ========================================================

    cv2.putText(
        sidebar,
        "STATUS DOS EPIs",
        (20, 40),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.72,
        (255, 255, 255),
        2,
        cv2.LINE_AA
    )

    cv2.line(
        sidebar,
        (20, 55),
        (
            LARGURA_SIDEBAR - 20,
            55
        ),
        (90, 90, 90),
        1
    )

    # ========================================================
    # CÂMERA
    # ========================================================

    cv2.putText(
        sidebar,
        CONFIG_CAMERA["nome"],
        (20, 82),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.48,
        (170, 170, 170),
        1,
        cv2.LINE_AA
    )

    cv2.putText(
        sidebar,
        CONFIG_CAMERA["ambiente"],
        (20, 104),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.43,
        (150, 150, 150),
        1,
        cv2.LINE_AA
    )

    # ========================================================
    # OPERADOR
    # ========================================================

    cv2.putText(
        sidebar,
        "OPERADOR",
        (20, 135),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.42,
        (170, 170, 170),
        1,
        cv2.LINE_AA
    )

    nome_operador = operador

    if len(nome_operador) > 28:

        nome_operador = (
            nome_operador[:28]
            + "..."
        )

    cv2.putText(
        sidebar,
        nome_operador,
        (20, 160),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.52,
        (255, 255, 255),
        1,
        cv2.LINE_AA
    )

    # ========================================================
    # STATUS GERAL
    # ========================================================

    if severidade == "CRITICA":

        cor_severidade = (
            0,
            0,
            255
        )

    elif severidade == "ALTA":

        cor_severidade = (
            0,
            165,
            255
        )

    elif severidade == "INFORMATIVA":

        cor_severidade = (
            255,
            200,
            0
        )

    else:

        cor_severidade = (
            0,
            200,
            0
        )

    cv2.putText(
        sidebar,
        f"Status: {severidade}",
        (20, 190),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.5,
        cor_severidade,
        2,
        cv2.LINE_AA
    )

    # ========================================================
    # EPIs
    # ========================================================

    y = 230

    for nome_equipamento in (
        CONFIG_CAMERA[
            "epis_obrigatorios"
        ]
    ):

        if nome_equipamento not in status_epis:
            continue

        dados = status_epis[
            nome_equipamento
        ]

        status = dados[
            "status"
        ]

        cor = dados[
            "cor"
        ]

        cv2.putText(
            sidebar,
            nome_equipamento,
            (20, y),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.50,
            (255, 255, 255),
            1,
            cv2.LINE_AA
        )

        cv2.putText(
            sidebar,
            status,
            (185, y),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.45,
            cor,
            2,
            cv2.LINE_AA
        )

        cv2.line(
            sidebar,
            (20, y + 15),
            (
                LARGURA_SIDEBAR - 20,
                y + 15
            ),
            (65, 65, 65),
            1
        )

        y += 48

    # ========================================================
    # JUNTA CÂMERA + SIDEBAR
    # ========================================================

    return np.hstack(
        (
            frame,
            sidebar
        )
    )


# ============================================================
# LOOP PRINCIPAL
# ============================================================

while cap.isOpened():

    success, frame = cap.read()

    if not success:

        print(
            "❌ Não foi possível "
            "capturar imagem da câmera."
        )

        break

    contador_frames += 1

    # ========================================================
    # DETECÇÃO DE EPI
    # ========================================================

    results_epi = list(
        model_epi(
            frame,
            conf=config.CONFIDENCIA_MINIMA,
            imgsz=config.TAMANHO_IMAGEM,
            stream=True,
            device=device
        )
    )

    # ========================================================
    # DETECÇÃO DE POSE
    # ========================================================

    results_pose = list(
        model_pose(
            frame,
            conf=0.5,
            stream=True,
            device=device
        )
    )

    # ========================================================
    # FRAME VISUAL
    # ========================================================

    annotated_frame = frame.copy()

    ombro_principal = [0, 0]
    quadril_principal = [0, 0]

    # ========================================================
    # PROCESSAMENTO DA POSE
    # ========================================================

    for resultado_pose in results_pose:

        if (
            resultado_pose.keypoints
            is not None
            and len(
                resultado_pose.keypoints.xy
            ) > 0
        ):

            # -----------------------------------------------
            # POR ENQUANTO USAMOS A PRIMEIRA PESSOA
            # -----------------------------------------------

            kp = (
                resultado_pose
                .keypoints
                .xy[0]
                .cpu()
                .numpy()
            )

            if len(kp) > 11:

                ombro_principal = (
                    kp[5]
                )

                quadril_principal = (
                    kp[11]
                )

        # ====================================================
        # BIOMETRIA
        # ====================================================

        for box in resultado_pose.boxes:

            if int(box.cls[0]) != 0:
                continue

            x1, y1, x2, y2 = map(
                int,
                box.xyxy[0]
            )

            conf_pessoa = float(
                box.conf[0]
            )

            # -----------------------------------------------
            # BIOMETRIA A CADA 15 FRAMES
            # -----------------------------------------------

            if contador_frames % 15 == 0:

                h_box = y2 - y1

                y_peito = (
                    y1
                    + int(
                        h_box * 0.55
                    )
                )

                recorte_rosto = frame[
                    max(0, y1):
                    max(0, y_peito),
                    max(0, x1):
                    max(0, x2)
                ]

                if recorte_rosto.size > 0:

                    try:

                        match = DeepFace.find(
                            img_path=recorte_rosto,
                            db_path="banco_biometria",
                            model_name="Facenet",
                            enforce_detection=False,
                            silent=True
                        )

                        if (
                            len(match) > 0
                            and not match[
                                0
                            ].empty
                        ):

                            caminho_identidade = (
                                match[0]
                                .iloc[0]
                                ["identity"]
                            )

                            arquivo_id = (
                                os.path.basename(
                                    caminho_identidade
                                )
                            )

                            matricula = (
                                os.path.splitext(
                                    arquivo_id
                                )[0]
                            )

                            matricula_atual = (
                                matricula
                            )

                            dados_operador_atual = (
                                DADOS_OPERADORES.get(
                                    matricula
                                )
                            )

                            if dados_operador_atual:

                                ultimo_operador_identificado = (
                                    formatar_operador(
                                        dados_operador_atual
                                    )
                                )

                            else:

                                ultimo_operador_identificado = (
                                    "Rosto Desconhecido"
                                )

                    except Exception:
                        pass

    # ========================================================
    # REGRAS SITUACIONAIS
    # ========================================================

    severidade, lista_pes, epis_detectados = (
        processar_regras_situacionais(

            results_epi,

            CONFIG_CAMERA[
                "zona_risco"
            ],

            matricula=matricula_atual,

            operador=ultimo_operador_identificado,

            frame=frame,

            ombro=ombro_principal,

            quadril=quadril_principal,

            # NOVOS PARÂMETROS
            camera_id=CONFIG_CAMERA[
                "id"
            ],

            camera_nome=CONFIG_CAMERA[
                "nome"
            ],

            ambiente=CONFIG_CAMERA[
                "ambiente"
            ],

            epis_obrigatorios=CONFIG_CAMERA[
                "epis_obrigatorios"
            ]
        )
    )

    # ========================================================
    # STATUS DOS EPIs
    # ========================================================

    status_epis = analisar_status_epis(
        results_epi,
        CONFIG_CAMERA[
            "epis_obrigatorios"
        ]
    )

    # ========================================================
    # ALERTA VISUAL
    # ========================================================

    if severidade == "CRITICA":

        cv2.putText(
            annotated_frame,
            "CRITICO: RISCO DE SEGURANCA",
            (15, 40),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (0, 0, 255),
            2,
            cv2.LINE_AA
        )

    elif severidade == "ALTA":

        cv2.putText(
            annotated_frame,
            "ALTO: INFRACAO OU RISCO ERGONOMICO",
            (15, 40),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (0, 165, 255),
            2,
            cv2.LINE_AA
        )

    # ========================================================
    # SIDEBAR
    # ========================================================

    tela_final = desenhar_sidebar(
        annotated_frame,
        status_epis,
        ultimo_operador_identificado,
        severidade
    )

    # ========================================================
    # EXIBIÇÃO
    # ========================================================

    cv2.imshow(
        "FIAP x SPI Challenge 2026",
        tela_final
    )

    # ========================================================
    # SAÍDA
    # ========================================================

    if (
        cv2.waitKey(1) & 0xFF
        == ord("q")
    ):

        break


# ============================================================
# FINALIZAÇÃO
# ============================================================

cap.release()

cv2.destroyAllWindows()
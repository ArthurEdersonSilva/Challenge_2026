import cv2
import csv
import os
import time
from datetime import datetime

import config


# ============================================================
# ESTADOS
# ============================================================

contadores_fadiga = {}

incidentes_ativos = {}


# ============================================================
# FUNÇÕES BÁSICAS
# ============================================================

def verificar_ponto_em_poligono(
    ponto,
    poligono
):

    if poligono is None:
        return -1

    return cv2.pointPolygonTest(
        poligono,
        ponto,
        False
    )


# ============================================================
# ERGONOMIA
# ============================================================

def avaliar_fadiga_ergonomica(
    ombro,
    quadril,
    identificador="global"
):

    if ombro is None or quadril is None:
        return False

    if (
        ombro[0] == 0
        and ombro[1] == 0
    ):
        return False

    if (
        quadril[0] == 0
        and quadril[1] == 0
    ):
        return False

    distancia_vertical = abs(
        quadril[1] - ombro[1]
    )

    limiar = getattr(
        config,
        "LIMIAR_POSTURA_INADEQUADA",
        85
    )

    limite_frames = getattr(
        config,
        "LIMITE_FRAMES_FADIGA",
        90
    )

    contador = contadores_fadiga.get(
        identificador,
        0
    )

    if distancia_vertical < limiar:

        contador += 1

    else:

        contador = max(
            0,
            contador - 1
        )

    contadores_fadiga[
        identificador
    ] = contador

    return contador >= limite_frames


# ============================================================
# REGISTRO DE INCIDENTE
# ============================================================

def registrar_incidente_csv(
    severidade,
    tipo_infracao,
    matricula,
    operador,
    frame,
    camera_id=None,
    camera_nome=None,
    ambiente=None
):

    caminho_csv = getattr(
        config,
        "PATH_LOGS_CSV",
        "historico_incidentes.csv"
    )

    pasta_provas = getattr(
        config,
        "PASTA_PROVAS_INCIDENTES",
        "provas_incidentes"
    )

    os.makedirs(
        pasta_provas,
        exist_ok=True
    )

    agora = datetime.now()

    timestamp_log = agora.strftime(
        "%Y-%m-%d %H:%M:%S"
    )

    timestamp_arquivo = agora.strftime(
        "%Y%m%d_%H%M%S_%f"
    )

    matricula_segura = (
        str(matricula)
        .replace("/", "_")
        .replace("\\", "_")
    )

    camera_segura = (
        str(camera_id)
        if camera_id is not None
        else "global"
    )

    tipo_seguro = (
        str(tipo_infracao)
        .replace(" ", "_")
        .replace("/", "_")
    )

    nome_foto = (
        f"cam_{camera_segura}_"
        f"{matricula_segura}_"
        f"{tipo_seguro}_"
        f"{timestamp_arquivo}.jpg"
    )

    caminho_foto = os.path.join(
        pasta_provas,
        nome_foto
    )

    if frame is not None:

        try:

            sucesso = cv2.imwrite(
                caminho_foto,
                frame
            )

            if not sucesso:

                caminho_foto = (
                    "FALHA_NA_CAPTURA_DO_FRAME"
                )

        except Exception:

            caminho_foto = (
                "FALHA_NA_CAPTURA_DO_FRAME"
            )

    else:

        caminho_foto = (
            "FALHA_NA_CAPTURA_DO_FRAME"
        )

    arquivo_novo = not os.path.exists(
        caminho_csv
    )

    try:

        with open(
            caminho_csv,
            mode="a",
            newline="",
            encoding="utf-8"
        ) as arquivo:

            writer = csv.writer(
                arquivo
            )

            if arquivo_novo:

                writer.writerow([
                    "Timestamp",
                    "Camera_ID",
                    "Camera",
                    "Ambiente",
                    "Matricula",
                    "Operador",
                    "Severidade",
                    "Tipo_Infracao",
                    "Foto_Prova",
                ])

            writer.writerow([
                timestamp_log,
                camera_id,
                camera_nome,
                ambiente,
                matricula,
                operador,
                severidade,
                tipo_infracao,
                caminho_foto,
            ])

        print(
            f"📸 Incidente registrado: "
            f"{tipo_infracao} | "
            f"{camera_nome} | "
            f"{matricula}"
        )

    except Exception as erro:

        print(
            f"❌ Erro ao registrar incidente: "
            f"{erro}"
        )


# ============================================================
# CHAVE DO INCIDENTE
# ============================================================

def criar_chave_incidente(
    camera_id,
    matricula,
    tipo_infracao
):

    camera = (
        str(camera_id)
        if camera_id is not None
        else "global"
    )

    matricula = (
        str(matricula)
        if matricula
        else "desconhecido"
    )

    return (
        f"{camera}|"
        f"{matricula}|"
        f"{tipo_infracao}"
    )


# ============================================================
# ESTADO DO INCIDENTE
# ============================================================

def obter_estado_incidente(
    chave
):

    if chave not in incidentes_ativos:

        incidentes_ativos[chave] = {

            "frames_confirmados": 0,

            "ativo": False,

            "ultima_foto": None,

            "ultimo_frame_detectado": None,
        }

    return incidentes_ativos[
        chave
    ]


# ============================================================
# PROCESSAR INCIDENTE
# ============================================================

def processar_incidente(
    camera_id,
    camera_nome,
    ambiente,
    matricula,
    operador,
    tipo_infracao,
    severidade,
    frame
):

    chave = criar_chave_incidente(
        camera_id,
        matricula,
        tipo_infracao
    )

    estado = obter_estado_incidente(
        chave
    )

    agora = time.time()

    frames_confirmacao = getattr(
        config,
        "FRAMES_CONFIRMACAO_INFRACAO",
        5
    )

    cooldown = getattr(
        config,
        "INTERVALO_REPETICAO_INCIDENTE_SEGUNDOS",
        300
    )

    estado[
        "frames_confirmados"
    ] += 1

    estado[
        "ultimo_frame_detectado"
    ] = agora

    # --------------------------------------------------------
    # AINDA NÃO CONFIRMOU
    # --------------------------------------------------------

    if (
        estado["frames_confirmados"]
        < frames_confirmacao
    ):

        return False

    # --------------------------------------------------------
    # PRIMEIRA CONFIRMAÇÃO
    # --------------------------------------------------------

    if not estado["ativo"]:

        estado[
            "ativo"
        ] = True

        estado[
            "ultima_foto"
        ] = agora

        registrar_incidente_csv(
            severidade,
            tipo_infracao,
            matricula,
            operador,
            frame,
            camera_id=camera_id,
            camera_nome=camera_nome,
            ambiente=ambiente,
        )

        return True

    # --------------------------------------------------------
    # INCIDENTE CONTINUA
    # --------------------------------------------------------

    ultima_foto = estado.get(
        "ultima_foto"
    )

    if ultima_foto is None:

        estado[
            "ultima_foto"
        ] = agora

        return False

    tempo_decorrido = (
        agora - ultima_foto
    )

    # --------------------------------------------------------
    # 5 MINUTOS
    # --------------------------------------------------------

    if tempo_decorrido >= cooldown:

        registrar_incidente_csv(
            severidade,
            tipo_infracao,
            matricula,
            operador,
            frame,
            camera_id=camera_id,
            camera_nome=camera_nome,
            ambiente=ambiente,
        )

        estado[
            "ultima_foto"
        ] = agora

        return True

    return False


# ============================================================
# RESETAR INCIDENTES QUE SUMIRAM
# ============================================================

def atualizar_incidentes_ausentes(
    chaves_detectadas
):

    agora = time.time()

    tempo_reset = getattr(
        config,
        "TEMPO_RESET_INCIDENTE_SEGUNDOS",
        1.0
    )

    chaves_para_remover = []

    for chave, estado in (
        incidentes_ativos.items()
    ):

        if chave in chaves_detectadas:
            continue

        ultimo_frame = estado.get(
            "ultimo_frame_detectado"
        )

        if ultimo_frame is None:

            chaves_para_remover.append(
                chave
            )

            continue

        if (
            agora - ultimo_frame
            >= tempo_reset
        ):

            chaves_para_remover.append(
                chave
            )

    for chave in chaves_para_remover:

        incidentes_ativos.pop(
            chave,
            None
        )


# ============================================================
# SEVERIDADE
# ============================================================

def definir_severidade(
    tipo_infracao,
    tem_pessoa_na_zona=False
):

    if (
        tipo_infracao == "Capacete"
        and tem_pessoa_na_zona
    ):

        return "CRITICA"

    if tipo_infracao:

        return "ALTA"

    return "NORMAL"


# ============================================================
# REGRAS SITUACIONAIS
# ============================================================

def processar_regras_situacionais(
    results,
    poligono_risco,
    matricula,
    operador,
    frame,
    ombro=None,
    quadril=None,
    camera_id=None,
    camera_nome=None,
    ambiente=None,
    epis_obrigatorios=None
):

    # ========================================================
    # IMPORTANTE
    #
    # Se os EPIs ainda não foram configurados,
    # nenhum EPI deve ser considerado obrigatório.
    # ========================================================

    if epis_obrigatorios is None:

        epis_obrigatorios = []

    tem_pessoa_na_zona = False

    pontos_pes = []

    infracoes_detectadas = []

    mapa_ausencias = getattr(
        config,
        "EPIS_AUSENCIA",
        {}
    )

    # ========================================================
    # DETECÇÕES
    # ========================================================

    for resultado in results:

        if resultado.boxes is None:
            continue

        for box in resultado.boxes:

            cls_id = int(
                box.cls[0]
            )

            label = resultado.names[
                cls_id
            ]

            # =================================================
            # PESSOA
            # =================================================

            if label == "person":

                x1, y1, x2, y2 = map(
                    int,
                    box.xyxy[0]
                )

                ponto_base = (
                    int(
                        (x1 + x2) / 2
                    ),
                    y2
                )

                pontos_pes.append(
                    ponto_base
                )

                if (
                    poligono_risco is not None
                    and verificar_ponto_em_poligono(
                        ponto_base,
                        poligono_risco
                    ) >= 0
                ):

                    tem_pessoa_na_zona = True

            # =================================================
            # AUSÊNCIA DE EPI
            # =================================================

            if label in mapa_ausencias:

                epi = mapa_ausencias[
                    label
                ]

                if epi in epis_obrigatorios:

                    infracoes_detectadas.append(
                        epi
                    )

    # ========================================================
    # REMOVE DUPLICADOS
    # ========================================================

    infracoes_detectadas = list(
        dict.fromkeys(
            infracoes_detectadas
        )
    )

    # ========================================================
    # ERGONOMIA
    # ========================================================

    identificador_fadiga = (
        f"{camera_id}|{matricula}"
    )

    fadiga_detectada = False

    if (
        ombro is not None
        and quadril is not None
    ):

        fadiga_detectada = (
            avaliar_fadiga_ergonomica(
                ombro,
                quadril,
                identificador_fadiga
            )
        )

    if fadiga_detectada:

        infracoes_detectadas.append(
            "FADIGA_ERGONOMICA"
        )

    # ========================================================
    # PROCESSAMENTO INDIVIDUAL
    #
    # Cada infração possui seu próprio incidente.
    # ========================================================

    chaves_detectadas = set()

    severidade_geral = "NORMAL"

    for tipo_infracao in (
        infracoes_detectadas
    ):

        severidade = definir_severidade(
            tipo_infracao,
            tem_pessoa_na_zona
        )

        if severidade == "CRITICA":

            severidade_geral = "CRITICA"

        elif (
            severidade == "ALTA"
            and severidade_geral
            != "CRITICA"
        ):

            severidade_geral = "ALTA"

        chave = criar_chave_incidente(
            camera_id,
            matricula,
            tipo_infracao
        )

        chaves_detectadas.add(
            chave
        )

        processar_incidente(
            camera_id,
            camera_nome,
            ambiente,
            matricula,
            operador,
            tipo_infracao,
            severidade,
            frame
        )

    # ========================================================
    # INCIDENTES QUE DESAPARECERAM
    # ========================================================

    atualizar_incidentes_ausentes(
        chaves_detectadas
    )

    return (
        severidade_geral,
        pontos_pes,
        infracoes_detectadas
    )
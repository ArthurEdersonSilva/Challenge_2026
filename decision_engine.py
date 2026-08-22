import cv2
import csv
import os
import time
from datetime import datetime

import winsound

import config


# ============================================================
# ESTADO POR CÂMERA / PESSOA
# ============================================================

# Evita que o contador de ergonomia seja compartilhado
# entre pessoas ou câmeras.
contadores_fadiga = {}

# Guarda o último estado de cada câmera.
estados_severidade = {}

# Guarda quando cada incidente foi registrado pela última vez.
ultimos_incidentes = {}


# ============================================================
# FUNÇÕES BÁSICAS
# ============================================================

def verificar_ponto_em_poligono(ponto, poligono):

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

    return contador > limite_frames


# ============================================================
# REGISTRO DE INCIDENTE
# ============================================================

def registrar_incidente_csv(
    severidade,
    infracoes,
    matricula,
    operador,
    frame,
    camera_id=None,
    camera_nome=None,
    ambiente=None,
    epis_faltantes=None
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

    if infracoes:

        lista_infracoes = "; ".join(
            infracoes
        )

    elif epis_faltantes:

        lista_infracoes = (
            "EPI faltante: "
            + "; ".join(epis_faltantes)
        )

    else:

        lista_infracoes = (
            "Fadiga Ergonomica"
        )

    matricula_segura = str(
        matricula
    ).replace("/", "_")

    nome_foto = (
        f"infra_"
        f"{matricula_segura}_"
        f"{timestamp_arquivo}.jpg"
    )

    caminho_foto = os.path.join(
        pasta_provas,
        nome_foto
    )

    if frame is not None:

        try:

            cv2.imwrite(
                caminho_foto,
                frame
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
        ) as file:

            writer = csv.writer(file)

            if arquivo_novo:

                writer.writerow([
                    "Timestamp",
                    "Camera_ID",
                    "Camera",
                    "Ambiente",
                    "Matricula",
                    "Operador",
                    "Severidade",
                    "Infracoes",
                    "EPIs_Faltantes",
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
                lista_infracoes,
                "; ".join(
                    epis_faltantes or []
                ),
                caminho_foto,
            ])

    except Exception as erro:

        print(
            f"⚠️ Erro ao registrar incidente: "
            f"{erro}"
        )


# ============================================================
# ALERTA SONORO
# ============================================================

def disparar_alerta_proativo(
    severidade
):

    if severidade != "CRITICA":
        return

    frequencia = getattr(
        config,
        "FREQ_BEEP_CRITICO",
        1500
    )

    duracao = getattr(
        config,
        "DURACAO_BEEP_CRITICO",
        400
    )

    try:

        winsound.Beep(
            frequencia,
            duracao
        )

    except Exception:

        pass


# ============================================================
# CONTROLE DE REPETIÇÃO
# ============================================================

def pode_registrar_incidente(
    chave_incidente
):

    agora = time.time()

    intervalo = getattr(
        config,
        "INTERVALO_REPETICAO_INCIDENTE_SEGUNDOS",
        300
    )

    ultimo = ultimos_incidentes.get(
        chave_incidente
    )

    if ultimo is None:

        ultimos_incidentes[
            chave_incidente
        ] = agora

        return True

    if agora - ultimo >= intervalo:

        ultimos_incidentes[
            chave_incidente
        ] = agora

        return True

    return False


# ============================================================
# SEVERIDADE
# ============================================================

def calcular_nivel_severidade(
    tem_pessoa_na_zona,
    infracoes_detectadas,
    fadiga_detectada,
    matricula,
    operador,
    frame,
    camera_id=None,
    camera_nome=None,
    ambiente=None,
    epis_faltantes=None
):

    if (
        len(infracoes_detectadas) == 0
        and not fadiga_detectada
        and not epis_faltantes
    ):

        severidade_atual = "NORMAL"

    elif (
        tem_pessoa_na_zona
        and (
            "Without Helmet"
            in infracoes_detectadas
        )
    ):

        severidade_atual = "CRITICA"

    elif (
        len(infracoes_detectadas) > 0
        or len(epis_faltantes or []) > 0
        or fadiga_detectada
    ):

        severidade_atual = "ALTA"

    else:

        severidade_atual = "INFORMATIVA"

    chave_camera = (
        str(camera_id)
        if camera_id is not None
        else "global"
    )

    estado_anterior = estados_severidade.get(
        chave_camera,
        "NORMAL"
    )

    estados_severidade[
        chave_camera
    ] = severidade_atual

    # --------------------------------------------------------
    # NÃO HÁ INCIDENTE
    # --------------------------------------------------------

    if severidade_atual == "NORMAL":

        return severidade_atual

    # --------------------------------------------------------
    # IDENTIFICA O TIPO DO INCIDENTE
    # --------------------------------------------------------

    partes_chave = []

    if infracoes_detectadas:

        partes_chave.extend(
            sorted(infracoes_detectadas)
        )

    if epis_faltantes:

        partes_chave.extend(
            sorted(epis_faltantes)
        )

    if fadiga_detectada:

        partes_chave.append(
            "FADIGA_ERGONOMICA"
        )

    chave_incidente = (
        f"{camera_id}|"
        f"{matricula}|"
        f"{'|'.join(partes_chave)}"
    )

    # --------------------------------------------------------
    # REGISTRO
    # --------------------------------------------------------

    houve_mudanca = (
        severidade_atual
        != estado_anterior
    )

    deve_registrar = False

    if houve_mudanca:

        deve_registrar = True

    elif pode_registrar_incidente(
        chave_incidente
    ):

        deve_registrar = True

    if deve_registrar:

        registrar_incidente_csv(
            severidade_atual,
            infracoes_detectadas,
            matricula,
            operador,
            frame,
            camera_id=camera_id,
            camera_nome=camera_nome,
            ambiente=ambiente,
            epis_faltantes=epis_faltantes,
        )

    # --------------------------------------------------------
    # ALERTA
    # --------------------------------------------------------

    if (
        houve_mudanca
        and severidade_atual
        in ["CRITICA", "ALTA"]
    ):

        disparar_alerta_proativo(
            severidade_atual
        )

    return severidade_atual


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

    tem_pessoa_na_zona = False

    pontos_pes = []

    infracoes_detectadas = []

    # --------------------------------------------------------
    # EPIs OBRIGATÓRIOS
    # --------------------------------------------------------

    if epis_obrigatorios is None:

        epis_obrigatorios = getattr(
            config,
            "EPIS_PADRAO",
            [
                "Capacete",
                "Óculos",
                "Máscara",
                "Luvas",
                "Protetor auricular",
                "Colete",
            ]
        )

    mapa_ausencias = {
        "Without Helmet": "Capacete",
        "Without Glass": "Óculos",
        "Without Mask": "Máscara",
        "Without Glove": "Luvas",
        "Without Ear Protectors":
            "Protetor auricular",
        "Without Safety Vest": "Colete",
    }

    # --------------------------------------------------------
    # DETECÇÃO
    # --------------------------------------------------------

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

            # ----------------------------------------------
            # PESSOA
            # ----------------------------------------------

            if label == "person":

                x1, y1, x2, y2 = map(
                    int,
                    box.xyxy[0]
                )

                ponto_base = (
                    int((x1 + x2) / 2),
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

            # ----------------------------------------------
            # AUSÊNCIA DE EPI
            # ----------------------------------------------

            if label in mapa_ausencias:

                nome_epi = mapa_ausencias[
                    label
                ]

                # Só considera infração se
                # o EPI for obrigatório naquela câmera.
                if nome_epi in epis_obrigatorios:

                    infracoes_detectadas.append(
                        label
                    )

    # --------------------------------------------------------
    # REMOVE DUPLICADOS
    # --------------------------------------------------------

    infracoes_detectadas = list(
        dict.fromkeys(
            infracoes_detectadas
        )
    )

    # --------------------------------------------------------
    # EPI FALTANTE EM FORMATO HUMANO
    # --------------------------------------------------------

    epis_faltantes = []

    for infracao in infracoes_detectadas:

        nome_epi = mapa_ausencias.get(
            infracao
        )

        if nome_epi:
            epis_faltantes.append(
                nome_epi
            )

    # --------------------------------------------------------
    # ERGONOMIA
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # SEVERIDADE
    # --------------------------------------------------------

    severidade = calcular_nivel_severidade(
        tem_pessoa_na_zona,
        infracoes_detectadas,
        fadiga_detectada,
        matricula,
        operador,
        frame,
        camera_id=camera_id,
        camera_nome=camera_nome,
        ambiente=ambiente,
        epis_faltantes=epis_faltantes,
    )

    return (
        severidade,
        pontos_pes,
        infracoes_detectadas
    )
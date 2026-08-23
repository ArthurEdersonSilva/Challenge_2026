import cv2
import numpy as np

import config


# ============================================================
# CONFIGURAÇÕES DA ANÁLISE
# ============================================================

AREA_MINIMA_PERCENTUAL = 0.015

AREA_MAXIMA_PERCENTUAL = 0.85

LARGURA_MINIMA = 45

ALTURA_MINIMA = 45

DISTANCIA_SOBREPOSICAO = 0.35


# ============================================================
# IOU
# ============================================================

def calcular_iou(
    caixa_a,
    caixa_b
):

    ax1, ay1, ax2, ay2 = caixa_a
    bx1, by1, bx2, by2 = caixa_b

    x1 = max(
        ax1,
        bx1
    )

    y1 = max(
        ay1,
        by1
    )

    x2 = min(
        ax2,
        bx2
    )

    y2 = min(
        ay2,
        by2
    )

    largura = max(
        0,
        x2 - x1
    )

    altura = max(
        0,
        y2 - y1
    )

    intersecao = (
        largura * altura
    )

    area_a = (
        (ax2 - ax1)
        * (ay2 - ay1)
    )

    area_b = (
        (bx2 - bx1)
        * (by2 - by1)
    )

    uniao = (
        area_a
        + area_b
        - intersecao
    )

    if uniao <= 0:

        return 0.0

    return (
        intersecao / uniao
    )


# ============================================================
# REMOVER CAIXAS REPETIDAS
# ============================================================

def remover_sobreposicoes(
    caixas
):

    if not caixas:

        return []

    caixas = sorted(
        caixas,
        key=lambda caixa: caixa["area"],
        reverse=True
    )

    resultado = []

    for candidata in caixas:

        repetida = False

        for existente in resultado:

            iou = calcular_iou(
                candidata["bbox"],
                existente["bbox"]
            )

            if (
                iou
                >= DISTANCIA_SOBREPOSICAO
            ):

                repetida = True

                break

        if not repetida:

            resultado.append(
                candidata
            )

    return resultado


# ============================================================
# PREPARAR IMAGEM
# ============================================================

def preparar_imagem(
    frame
):

    cinza = cv2.cvtColor(
        frame,
        cv2.COLOR_BGR2GRAY
    )

    cinza = cv2.GaussianBlur(
        cinza,
        (7, 7),
        0
    )

    return cinza


# ============================================================
# CRIAR REGIÕES
# ============================================================

def detectar_regioes(
    frame
):

    altura_frame, largura_frame = (
        frame.shape[:2]
    )

    area_frame = (
        altura_frame
        * largura_frame
    )

    area_minima = int(
        area_frame
        * AREA_MINIMA_PERCENTUAL
    )

    area_maxima = int(
        area_frame
        * AREA_MAXIMA_PERCENTUAL
    )

    cinza = preparar_imagem(
        frame
    )

    # ========================================================
    # BORDAS
    # ========================================================

    bordas = cv2.Canny(
        cinza,
        40,
        120
    )

    # ========================================================
    # FECHA PEQUENAS ABERTURAS
    # ========================================================

    kernel = cv2.getStructuringElement(
        cv2.MORPH_RECT,
        (9, 9)
    )

    mascara = cv2.morphologyEx(
        bordas,
        cv2.MORPH_CLOSE,
        kernel,
        iterations=2
    )

    mascara = cv2.dilate(
        mascara,
        kernel,
        iterations=1
    )

    # ========================================================
    # CONTORNOS
    # ========================================================

    contornos, _ = cv2.findContours(
        mascara,
        cv2.RETR_EXTERNAL,
        cv2.CHAIN_APPROX_SIMPLE
    )

    caixas = []

    for contorno in contornos:

        area_contorno = cv2.contourArea(
            contorno
        )

        if (
            area_contorno
            < area_minima
        ):

            continue

        x, y, largura, altura = (
            cv2.boundingRect(
                contorno
            )
        )

        if (
            largura
            < LARGURA_MINIMA
        ):

            continue

        if (
            altura
            < ALTURA_MINIMA
        ):

            continue

        area_caixa = (
            largura * altura
        )

        if (
            area_caixa
            > area_maxima
        ):

            continue

        # ----------------------------------------------------
        # Evita considerar praticamente a tela inteira
        # como um objeto.
        # ----------------------------------------------------

        if (
            largura
            >= largura_frame * 0.95
            and
            altura
            >= altura_frame * 0.95
        ):

            continue

        caixas.append({

            "bbox": [
                int(x),
                int(y),
                int(x + largura),
                int(y + altura)
            ],

            "area":
                int(area_caixa),
        })

    caixas = remover_sobreposicoes(
        caixas
    )

    return caixas


# ============================================================
# ANALISAR UM FRAME
# ============================================================

def analisar_frame(
    frame,
    camera_id
):

    if frame is None:

        return []

    if frame.size == 0:

        return []

    regioes = detectar_regioes(
        frame
    )

    objetos = []

    # ========================================================
    # ORDENA PARA A NUMERAÇÃO NÃO FICAR COMPLETAMENTE ALEATÓRIA
    # ========================================================

    regioes = sorted(
        regioes,
        key=lambda objeto: (
            objeto["bbox"][1],
            objeto["bbox"][0]
        )
    )

    for indice, regiao in enumerate(
        regioes,
        start=1
    ):

        x1, y1, x2, y2 = (
            regiao["bbox"]
        )

        objetos.append({

            "id_local":
                indice,

            "camera_id":
                camera_id,

            "nome":
                f"Objeto {indice}",

            "bbox": [
                x1,
                y1,
                x2,
                y2
            ],

            "centro": [
                int(
                    (x1 + x2) / 2
                ),
                int(
                    (y1 + y2) / 2
                )
            ],

            "area":
                regiao["area"],

            "maquinario":
                None,
        })

    return objetos


# ============================================================
# DESENHAR OBJETOS
# ============================================================

def desenhar_objetos(
    frame,
    objetos
):

    if frame is None:

        return frame

    frame_visual = (
        frame.copy()
    )

    for objeto in objetos:

        x1, y1, x2, y2 = (
            objeto["bbox"]
        )

        nome = objeto.get(
            "nome",
            "Objeto"
        )

        # ====================================================
        # CAIXA
        # ====================================================

        cv2.rectangle(
            frame_visual,
            (x1, y1),
            (x2, y2),
            (0, 255, 255),
            2
        )

        # ====================================================
        # FUNDO DO TEXTO
        # ====================================================

        (
            largura_texto,
            altura_texto
        ), _ = cv2.getTextSize(
            nome,
            cv2.FONT_HERSHEY_SIMPLEX,
            0.55,
            2
        )

        topo = max(
            0,
            y1 - altura_texto - 12
        )

        cv2.rectangle(
            frame_visual,
            (
                x1,
                topo
            ),
            (
                x1
                + largura_texto
                + 12,

                y1
            ),
            (0, 0, 0),
            -1
        )

        # ====================================================
        # NOME
        # ====================================================

        cv2.putText(
            frame_visual,
            nome,
            (
                x1 + 6,
                max(
                    altura_texto + 2,
                    y1 - 6
                )
            ),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.55,
            (0, 255, 255),
            2,
            cv2.LINE_AA
        )

    return frame_visual


# ============================================================
# CRIAR RESUMO DA CÂMERA
# ============================================================

def criar_resumo_objetos(
    objetos
):

    resumo = []

    for objeto in objetos:

        resumo.append(
            objeto["nome"]
        )

    return resumo
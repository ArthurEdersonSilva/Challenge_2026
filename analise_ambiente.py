import cv2
import numpy as np

from ultralytics import FastSAM


# ============================================================
# CONFIGURAÇÕES
# ============================================================

MODELO_AMBIENTE = "FastSAM-s.pt"

CONFIANCA_MINIMA = 0.35
IOU_MODELO = 0.80
TAMANHO_ANALISE = 1024

# Ignora fragmentos muito pequenos
AREA_MINIMA_PERCENTUAL = 0.012

# Ignora máscaras que praticamente representam a cena inteira
AREA_MAXIMA_PERCENTUAL = 0.70

LARGURA_MINIMA = 45
ALTURA_MINIMA = 45

# Sobreposição para considerar duas caixas redundantes
IOU_REPETICAO = 0.55

# Se uma caixa estiver quase toda dentro de outra,
# pode representar fragmentação do mesmo objeto.
PERCENTUAL_CONTENCAO = 0.82


# ============================================================
# MODELO
# ============================================================

modelo_ambiente = None


# ============================================================
# CARREGAR MODELO
# ============================================================

def carregar_modelo_ambiente():

    global modelo_ambiente

    if modelo_ambiente is not None:
        return modelo_ambiente

    print()
    print("==========================================")
    print(" MODELO DE ANALISE DO AMBIENTE")
    print("==========================================")

    try:

        modelo_ambiente = FastSAM(
            MODELO_AMBIENTE
        )

        print(
            f"Modelo carregado: {MODELO_AMBIENTE}"
        )

    except Exception as erro:

        print(
            f"Erro carregando FastSAM: {erro}"
        )

        modelo_ambiente = None

    print("==========================================")
    print()

    return modelo_ambiente


# ============================================================
# ÁREA DA CAIXA
# ============================================================

def calcular_area_caixa(
    caixa
):

    x1, y1, x2, y2 = caixa

    largura = max(
        0,
        x2 - x1
    )

    altura = max(
        0,
        y2 - y1
    )

    return (
        largura * altura
    )


# ============================================================
# INTERSEÇÃO
# ============================================================

def calcular_intersecao(
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

    return (
        largura * altura
    )


# ============================================================
# IOU
# ============================================================

def calcular_iou(
    caixa_a,
    caixa_b
):

    intersecao = calcular_intersecao(
        caixa_a,
        caixa_b
    )

    if intersecao <= 0:
        return 0.0

    area_a = calcular_area_caixa(
        caixa_a
    )

    area_b = calcular_area_caixa(
        caixa_b
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
# PERCENTUAL DE CONTENÇÃO
# ============================================================

def calcular_contencao(
    caixa_a,
    caixa_b
):

    intersecao = calcular_intersecao(
        caixa_a,
        caixa_b
    )

    if intersecao <= 0:
        return 0.0

    area_a = calcular_area_caixa(
        caixa_a
    )

    area_b = calcular_area_caixa(
        caixa_b
    )

    menor_area = min(
        area_a,
        area_b
    )

    if menor_area <= 0:
        return 0.0

    return (
        intersecao / menor_area
    )


# ============================================================
# VALIDAR CAIXA
# ============================================================

def caixa_valida(
    bbox,
    largura_frame,
    altura_frame
):

    x1, y1, x2, y2 = bbox

    largura = (
        x2 - x1
    )

    altura = (
        y2 - y1
    )

    if largura < LARGURA_MINIMA:
        return False

    if altura < ALTURA_MINIMA:
        return False

    area_frame = (
        largura_frame
        * altura_frame
    )

    area_caixa = (
        largura
        * altura
    )

    percentual = (
        area_caixa
        / max(
            area_frame,
            1
        )
    )

    if percentual < AREA_MINIMA_PERCENTUAL:
        return False

    if percentual > AREA_MAXIMA_PERCENTUAL:
        return False

    # Evita regiões que praticamente representam
    # toda a largura da câmera.

    if (
        largura
        >= largura_frame * 0.96
    ):
        return False

    # Evita regiões que praticamente representam
    # toda a altura da câmera.

    if (
        altura
        >= altura_frame * 0.96
    ):
        return False

    return True


# ============================================================
# CONVERTER MÁSCARA EM OBJETO
# ============================================================

def mascara_para_objeto(
    mascara,
    largura_frame,
    altura_frame
):

    mascara = np.asarray(
        mascara
    )

    mascara = np.squeeze(
        mascara
    )

    if mascara.ndim != 2:
        return None

    mascara = (
        mascara > 0.5
    ).astype(
        np.uint8
    ) * 255

    if (
        mascara.shape[1]
        != largura_frame
        or
        mascara.shape[0]
        != altura_frame
    ):

        mascara = cv2.resize(
            mascara,
            (
                largura_frame,
                altura_frame
            ),
            interpolation=cv2.INTER_NEAREST
        )

    contornos, _ = cv2.findContours(
        mascara,
        cv2.RETR_EXTERNAL,
        cv2.CHAIN_APPROX_SIMPLE
    )

    if not contornos:
        return None

    # Uma máscara pode possuir pequenos fragmentos.
    # Pegamos somente a região principal.

    contorno = max(
        contornos,
        key=cv2.contourArea
    )

    area_mascara = cv2.contourArea(
        contorno
    )

    if area_mascara <= 0:
        return None

    x, y, largura, altura = cv2.boundingRect(
        contorno
    )

    bbox = [
        int(x),
        int(y),
        int(x + largura),
        int(y + altura)
    ]

    if not caixa_valida(
        bbox,
        largura_frame,
        altura_frame
    ):
        return None

    return {

        "bbox":
            bbox,

        "area":
            int(
                area_mascara
            ),

        "area_caixa":
            int(
                largura
                * altura
            ),
    }


# ============================================================
# REMOVER FRAGMENTAÇÃO
# ============================================================

def remover_fragmentacao(
    candidatos
):

    if not candidatos:
        return []

    # Começa pelas regiões maiores.

    candidatos = sorted(
        candidatos,
        key=lambda item: item["area"],
        reverse=True
    )

    resultado = []

    for candidato in candidatos:

        caixa_candidata = (
            candidato["bbox"]
        )

        repetido = False

        for existente in resultado:

            caixa_existente = (
                existente["bbox"]
            )

            # ------------------------------------------------
            # IOU
            # ------------------------------------------------

            iou = calcular_iou(
                caixa_candidata,
                caixa_existente
            )

            if iou >= IOU_REPETICAO:

                repetido = True
                break

            # ------------------------------------------------
            # CONTENÇÃO
            #
            # FastSAM frequentemente cria:
            #
            # cadeira inteira
            # assento
            # encosto
            # pernas
            #
            # Se uma região está praticamente contida
            # em outra, eliminamos o fragmento.
            # ------------------------------------------------

            contencao = calcular_contencao(
                caixa_candidata,
                caixa_existente
            )

            if (
                contencao
                >= PERCENTUAL_CONTENCAO
            ):

                area_candidata = (
                    calcular_area_caixa(
                        caixa_candidata
                    )
                )

                area_existente = (
                    calcular_area_caixa(
                        caixa_existente
                    )
                )

                menor = min(
                    area_candidata,
                    area_existente
                )

                maior = max(
                    area_candidata,
                    area_existente
                )

                proporcao = (
                    menor
                    / max(
                        maior,
                        1
                    )
                )

                # Não removemos automaticamente
                # objetos muito pequenos dentro de
                # objetos muito grandes.
                #
                # Exemplo:
                # pessoa sentada em cadeira.
                #
                # Mas removemos máscaras redundantes
                # de tamanho semelhante.

                if proporcao >= 0.25:

                    repetido = True
                    break

        if not repetido:

            resultado.append(
                candidato
            )

    return resultado


# ============================================================
# DETECTAR REGIÕES
# ============================================================

def detectar_regioes(
    frame
):

    if frame is None:
        return []

    if frame.size == 0:
        return []

    modelo = carregar_modelo_ambiente()

    if modelo is None:
        return []

    altura_frame, largura_frame = (
        frame.shape[:2]
    )

    # ========================================================
    # FASTSAM
    # ========================================================

    try:

        resultados = modelo(
            frame,
            device="cpu",
            retina_masks=True,
            imgsz=TAMANHO_ANALISE,
            conf=CONFIANCA_MINIMA,
            iou=IOU_MODELO,
            verbose=False
        )

    except Exception as erro:

        print(
            "Erro na analise do ambiente: "
            f"{erro}"
        )

        return []

    candidatos = []

    # ========================================================
    # MÁSCARAS
    # ========================================================

    for resultado in resultados:

        if resultado.masks is None:
            continue

        try:

            mascaras = (
                resultado
                .masks
                .data
                .cpu()
                .numpy()
            )

        except Exception:
            continue

        for mascara in mascaras:

            objeto = mascara_para_objeto(
                mascara,
                largura_frame,
                altura_frame
            )

            if objeto is None:
                continue

            candidatos.append(
                objeto
            )

    # ========================================================
    # REMOVER FRAGMENTOS
    # ========================================================

    candidatos = remover_fragmentacao(
        candidatos
    )

    return candidatos


# ============================================================
# ANALISAR FRAME
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

    # Ordenação visual estável:
    # cima → baixo
    # esquerda → direita

    regioes = sorted(
        regioes,
        key=lambda objeto: (
            objeto["bbox"][1],
            objeto["bbox"][0]
        )
    )

    objetos = []

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
                int(x1),
                int(y1),
                int(x2),
                int(y2)
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
                int(
                    regiao["area"]
                ),

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

    frame_visual = frame.copy()

    for objeto in objetos:

        x1, y1, x2, y2 = (
            objeto["bbox"]
        )

        # ----------------------------------------------------
        # Usa o nome global quando ele já existir.
        # Isso será importante na próxima etapa.
        # ----------------------------------------------------

        nome = objeto.get(
            "nome_global"
        )

        if not nome:

            nome = objeto.get(
                "nome",
                "Objeto"
            )

        cv2.rectangle(
            frame_visual,
            (x1, y1),
            (x2, y2),
            (0, 255, 255),
            2
        )

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
            y1
            - altura_texto
            - 12
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
# CRIAR RESUMO
# ============================================================

def criar_resumo_objetos(
    objetos
):

    resumo = []

    for objeto in objetos:

        nome = objeto.get(
            "nome_global"
        )

        if not nome:

            nome = objeto.get(
                "nome",
                "Objeto"
            )

        resumo.append(
            nome
        )

    return resumo
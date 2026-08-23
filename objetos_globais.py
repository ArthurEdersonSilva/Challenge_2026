import cv2
import numpy as np


# ============================================================
# CONFIGURAÇÕES
# ============================================================

LIMIAR_SIMILARIDADE = 0.72


# ============================================================
# HISTOGRAMA VISUAL
# ============================================================

def gerar_assinatura_visual(
    frame,
    bbox
):

    x1, y1, x2, y2 = bbox

    altura, largura = frame.shape[:2]

    x1 = max(
        0,
        min(
            largura - 1,
            x1
        )
    )

    y1 = max(
        0,
        min(
            altura - 1,
            y1
        )
    )

    x2 = max(
        x1 + 1,
        min(
            largura,
            x2
        )
    )

    y2 = max(
        y1 + 1,
        min(
            altura,
            y2
        )
    )

    recorte = frame[
        y1:y2,
        x1:x2
    ]

    if recorte.size == 0:

        return None

    recorte = cv2.resize(
        recorte,
        (128, 128)
    )

    hsv = cv2.cvtColor(
        recorte,
        cv2.COLOR_BGR2HSV
    )

    histograma = cv2.calcHist(
        [hsv],
        [0, 1],
        None,
        [32, 32],
        [0, 180, 0, 256]
    )

    cv2.normalize(
        histograma,
        histograma
    )

    return histograma


# ============================================================
# SIMILARIDADE
# ============================================================

def comparar_assinaturas(
    assinatura_a,
    assinatura_b
):

    if (
        assinatura_a is None
        or assinatura_b is None
    ):

        return 0.0

    similaridade = cv2.compareHist(
        assinatura_a,
        assinatura_b,
        cv2.HISTCMP_CORREL
    )

    return float(
        similaridade
    )


# ============================================================
# CRIAR OBJETOS GLOBAIS
# ============================================================

def criar_objetos_globais(
    frames_originais
):

    objetos_globais = {}

    proximo_id = 1

    # ========================================================
    # ANALISA AS CÂMERAS
    # ========================================================

    for (
        camera,
        frame
    ) in frames_originais:

        for objeto in camera.objetos:

            bbox = objeto[
                "bbox"
            ]

            assinatura = (
                gerar_assinatura_visual(
                    frame,
                    bbox
                )
            )

            melhor_global = None

            melhor_similaridade = 0.0

            # =================================================
            # PROCURA OBJETO PARECIDO JÁ EXISTENTE
            # =================================================

            for (
                global_id,
                global_objeto
            ) in objetos_globais.items():

                # Não associa duas detecções
                # da mesma câmera.
                if (
                    camera.camera_id
                    in global_objeto[
                        "cameras"
                    ]
                ):

                    continue

                assinatura_referencia = (
                    global_objeto.get(
                        "assinatura"
                    )
                )

                similaridade = (
                    comparar_assinaturas(
                        assinatura,
                        assinatura_referencia
                    )
                )

                if (
                    similaridade
                    > melhor_similaridade
                ):

                    melhor_similaridade = (
                        similaridade
                    )

                    melhor_global = (
                        global_id
                    )

            # =================================================
            # MESMO OBJETO
            # =================================================

            if (
                melhor_global is not None
                and melhor_similaridade
                >= LIMIAR_SIMILARIDADE
            ):

                objeto_global = (
                    objetos_globais[
                        melhor_global
                    ]
                )

                objeto_global[
                    "cameras"
                ].append(
                    camera.camera_id
                )

                objeto_global[
                    "deteccoes"
                ][
                    str(
                        camera.camera_id
                    )
                ] = bbox

                objeto[
                    "id_global"
                ] = melhor_global

            # =================================================
            # NOVO OBJETO
            # =================================================

            else:

                global_id = (
                    f"OBJETO_{proximo_id:03d}"
                )

                objetos_globais[
                    global_id
                ] = {

                    "id":
                        global_id,

                    "numero":
                        proximo_id,

                    "nome":
                        f"Objeto {proximo_id}",

                    "cameras": [
                        camera.camera_id
                    ],

                    "deteccoes": {
                        str(
                            camera.camera_id
                        ):
                            bbox
                    },

                    "assinatura":
                        assinatura,

                    "maquinario":
                        None,
                }

                objeto[
                    "id_global"
                ] = global_id

                proximo_id += 1

    return objetos_globais


# ============================================================
# PREPARAR PARA SALVAR EM JSON
# ============================================================

def preparar_objetos_para_salvar(
    objetos_globais
):

    resultado = {}

    for (
        global_id,
        objeto
    ) in objetos_globais.items():

        resultado[
            global_id
        ] = {

            "id":
                objeto["id"],

            "numero":
                objeto["numero"],

            "nome":
                objeto["nome"],

            "cameras":
                objeto["cameras"],

            "deteccoes":
                objeto["deteccoes"],

            "maquinario":
                objeto["maquinario"],
        }

    return resultado
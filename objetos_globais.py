import cv2
import numpy as np


# ============================================================
# CONFIGURAÇÕES
# ============================================================

# Associação entre câmeras deve ser conservadora.
# É melhor manter dois objetos separados do que unir
# dois objetos físicos diferentes por engano.

LIMIAR_SIMILARIDADE_GLOBAL = 0.76

PESO_COR = 0.35
PESO_TEXTURA = 0.40
PESO_FORMA = 0.25

LIMIAR_COR_MINIMO = 0.20
LIMIAR_TEXTURA_MINIMO = 0.20
LIMIAR_FORMA_MINIMO = 0.30


# ============================================================
# RECORTAR OBJETO
# ============================================================

def recortar_objeto(
    frame,
    bbox
):

    if frame is None:
        return None

    if frame.size == 0:
        return None

    x1, y1, x2, y2 = bbox

    altura, largura = frame.shape[:2]

    x1 = max(
        0,
        min(
            largura - 1,
            int(x1)
        )
    )

    y1 = max(
        0,
        min(
            altura - 1,
            int(y1)
        )
    )

    x2 = max(
        x1 + 1,
        min(
            largura,
            int(x2)
        )
    )

    y2 = max(
        y1 + 1,
        min(
            altura,
            int(y2)
        )
    )

    recorte = frame[
        y1:y2,
        x1:x2
    ]

    if recorte.size == 0:
        return None

    return recorte


# ============================================================
# ASSINATURA DE COR
# ============================================================

def gerar_assinatura_cor(
    recorte
):

    if recorte is None:
        return None

    if recorte.size == 0:
        return None

    try:

        imagem = cv2.resize(
            recorte,
            (128, 128)
        )

        hsv = cv2.cvtColor(
            imagem,
            cv2.COLOR_BGR2HSV
        )

        histograma = cv2.calcHist(
            [hsv],
            [0, 1],
            None,
            [32, 32],
            [
                0, 180,
                0, 256
            ]
        )

        cv2.normalize(
            histograma,
            histograma
        )

        return histograma

    except Exception:

        return None


# ============================================================
# ASSINATURA DE TEXTURA
# ============================================================

def gerar_assinatura_textura(
    recorte
):

    if recorte is None:
        return None

    if recorte.size == 0:
        return None

    try:

        imagem = cv2.resize(
            recorte,
            (128, 128)
        )

        cinza = cv2.cvtColor(
            imagem,
            cv2.COLOR_BGR2GRAY
        )

        cinza = cv2.GaussianBlur(
            cinza,
            (3, 3),
            0
        )

        # Gradientes ajudam a comparar estrutura,
        # bordas e textura do objeto.

        gradiente_x = cv2.Sobel(
            cinza,
            cv2.CV_32F,
            1,
            0,
            ksize=3
        )

        gradiente_y = cv2.Sobel(
            cinza,
            cv2.CV_32F,
            0,
            1,
            ksize=3
        )

        magnitude = cv2.magnitude(
            gradiente_x,
            gradiente_y
        )

        magnitude = cv2.normalize(
            magnitude,
            None,
            0,
            255,
            cv2.NORM_MINMAX
        )

        magnitude = magnitude.astype(
            np.uint8
        )

        histograma = cv2.calcHist(
            [magnitude],
            [0],
            None,
            [64],
            [0, 256]
        )

        cv2.normalize(
            histograma,
            histograma
        )

        return histograma

    except Exception:

        return None


# ============================================================
# ASSINATURA DE FORMA
# ============================================================

def gerar_assinatura_forma(
    bbox
):

    x1, y1, x2, y2 = bbox

    largura = max(
        1,
        x2 - x1
    )

    altura = max(
        1,
        y2 - y1
    )

    proporcao = (
        largura / altura
    )

    return {
        "largura":
            float(largura),

        "altura":
            float(altura),

        "proporcao":
            float(proporcao),
    }


# ============================================================
# ASSINATURA COMPLETA
# ============================================================

def gerar_assinatura_visual(
    frame,
    bbox
):

    recorte = recortar_objeto(
        frame,
        bbox
    )

    if recorte is None:
        return None

    return {
        "cor":
            gerar_assinatura_cor(
                recorte
            ),

        "textura":
            gerar_assinatura_textura(
                recorte
            ),

        "forma":
            gerar_assinatura_forma(
                bbox
            ),
    }


# ============================================================
# NORMALIZAR CORRELAÇÃO
# ============================================================

def normalizar_correlacao(
    valor
):

    # HISTCMP_CORREL pode retornar de -1 até 1.
    # Convertemos para 0 até 1.

    valor = (
        valor + 1.0
    ) / 2.0

    return float(
        max(
            0.0,
            min(
                1.0,
                valor
            )
        )
    )


# ============================================================
# COMPARAR HISTOGRAMAS
# ============================================================

def comparar_histogramas(
    histograma_a,
    histograma_b
):

    if (
        histograma_a is None
        or
        histograma_b is None
    ):
        return 0.0

    try:

        valor = cv2.compareHist(
            histograma_a,
            histograma_b,
            cv2.HISTCMP_CORREL
        )

        return normalizar_correlacao(
            float(valor)
        )

    except Exception:

        return 0.0


# ============================================================
# COMPARAR FORMATO
# ============================================================

def comparar_forma(
    forma_a,
    forma_b
):

    if (
        forma_a is None
        or
        forma_b is None
    ):
        return 0.0

    proporcao_a = max(
        forma_a["proporcao"],
        0.01
    )

    proporcao_b = max(
        forma_b["proporcao"],
        0.01
    )

    menor = min(
        proporcao_a,
        proporcao_b
    )

    maior = max(
        proporcao_a,
        proporcao_b
    )

    similaridade = (
        menor / maior
    )

    return float(
        max(
            0.0,
            min(
                1.0,
                similaridade
            )
        )
    )


# ============================================================
# COMPARAR ASSINATURAS
# ============================================================

def comparar_assinaturas(
    assinatura_a,
    assinatura_b
):

    if (
        assinatura_a is None
        or
        assinatura_b is None
    ):

        return {
            "total": 0.0,
            "cor": 0.0,
            "textura": 0.0,
            "forma": 0.0,
        }

    similaridade_cor = comparar_histogramas(
        assinatura_a.get(
            "cor"
        ),
        assinatura_b.get(
            "cor"
        )
    )

    similaridade_textura = comparar_histogramas(
        assinatura_a.get(
            "textura"
        ),
        assinatura_b.get(
            "textura"
        )
    )

    similaridade_forma = comparar_forma(
        assinatura_a.get(
            "forma"
        ),
        assinatura_b.get(
            "forma"
        )
    )

    total = (
        similaridade_cor
        * PESO_COR
        +
        similaridade_textura
        * PESO_TEXTURA
        +
        similaridade_forma
        * PESO_FORMA
    )

    return {
        "total":
            float(total),

        "cor":
            float(
                similaridade_cor
            ),

        "textura":
            float(
                similaridade_textura
            ),

        "forma":
            float(
                similaridade_forma
            ),
    }


# ============================================================
# ASSOCIAÇÃO É CONFIÁVEL?
# ============================================================

def associacao_confiavel(
    resultado
):

    if resultado is None:
        return False

    if (
        resultado["total"]
        < LIMIAR_SIMILARIDADE_GLOBAL
    ):
        return False

    if (
        resultado["cor"]
        < LIMIAR_COR_MINIMO
    ):
        return False

    if (
        resultado["textura"]
        < LIMIAR_TEXTURA_MINIMO
    ):
        return False

    if (
        resultado["forma"]
        < LIMIAR_FORMA_MINIMO
    ):
        return False

    return True


# ============================================================
# CRIAR NOVO OBJETO GLOBAL
# ============================================================

def criar_novo_objeto_global(
    proximo_id,
    camera_id,
    bbox,
    assinatura
):

    global_id = (
        f"OBJETO_{proximo_id:03d}"
    )

    objeto_global = {

        "id":
            global_id,

        "numero":
            proximo_id,

        "nome":
            f"Objeto {proximo_id}",

        "cameras": [
            camera_id
        ],

        "deteccoes": {
            str(camera_id):
                bbox
        },

        # Mantemos uma assinatura por câmera.
        # Isso é melhor do que comparar sempre
        # somente com a primeira visão do objeto.

        "assinaturas": {
            str(camera_id):
                assinatura
        },

        "maquinario":
            None,
    }

    return (
        global_id,
        objeto_global
    )


# ============================================================
# MELHOR COMPARAÇÃO COM OBJETO GLOBAL
# ============================================================

def comparar_com_objeto_global(
    assinatura,
    objeto_global
):

    melhor_resultado = {
        "total": 0.0,
        "cor": 0.0,
        "textura": 0.0,
        "forma": 0.0,
    }

    assinaturas = objeto_global.get(
        "assinaturas",
        {}
    )

    for assinatura_referencia in (
        assinaturas.values()
    ):

        resultado = comparar_assinaturas(
            assinatura,
            assinatura_referencia
        )

        if (
            resultado["total"]
            >
            melhor_resultado["total"]
        ):

            melhor_resultado = (
                resultado
            )

    return melhor_resultado


# ============================================================
# CRIAR OBJETOS GLOBAIS
# ============================================================

def criar_objetos_globais(
    frames_originais
):

    objetos_globais = {}

    proximo_id = 1

    # ========================================================
    # PERCORRER CÂMERAS
    # ========================================================

    for camera, frame in frames_originais:

        camera_id = (
            camera.camera_id
        )

        objetos_camera = getattr(
            camera,
            "objetos",
            []
        )

        for objeto in objetos_camera:

            bbox = objeto.get(
                "bbox"
            )

            if not bbox:
                continue

            assinatura = gerar_assinatura_visual(
                frame,
                bbox
            )

            melhor_global = None

            melhor_resultado = {
                "total": 0.0,
                "cor": 0.0,
                "textura": 0.0,
                "forma": 0.0,
            }

            # =================================================
            # PROCURAR OBJETO GLOBAL COMPATÍVEL
            # =================================================

            for (
                global_id,
                objeto_global
            ) in objetos_globais.items():

                # Uma câmera não pode adicionar duas
                # detecções ao mesmo objeto global.

                if (
                    camera_id
                    in objeto_global[
                        "cameras"
                    ]
                ):
                    continue

                resultado = comparar_com_objeto_global(
                    assinatura,
                    objeto_global
                )

                if (
                    resultado["total"]
                    >
                    melhor_resultado["total"]
                ):

                    melhor_resultado = (
                        resultado
                    )

                    melhor_global = (
                        global_id
                    )

            # =================================================
            # MESMO OBJETO FÍSICO
            # =================================================

            if (
                melhor_global is not None
                and
                associacao_confiavel(
                    melhor_resultado
                )
            ):

                objeto_global = (
                    objetos_globais[
                        melhor_global
                    ]
                )

                if (
                    camera_id
                    not in objeto_global[
                        "cameras"
                    ]
                ):

                    objeto_global[
                        "cameras"
                    ].append(
                        camera_id
                    )

                objeto_global[
                    "deteccoes"
                ][
                    str(camera_id)
                ] = bbox

                objeto_global[
                    "assinaturas"
                ][
                    str(camera_id)
                ] = assinatura

                objeto[
                    "id_global"
                ] = melhor_global

                objeto[
                    "numero_global"
                ] = objeto_global[
                    "numero"
                ]

                objeto[
                    "nome_global"
                ] = objeto_global[
                    "nome"
                ]

                objeto[
                    "similaridade_global"
                ] = melhor_resultado[
                    "total"
                ]

            # =================================================
            # NOVO OBJETO FÍSICO
            # =================================================

            else:

                (
                    global_id,
                    novo_global
                ) = criar_novo_objeto_global(
                    proximo_id,
                    camera_id,
                    bbox,
                    assinatura
                )

                objetos_globais[
                    global_id
                ] = novo_global

                objeto[
                    "id_global"
                ] = global_id

                objeto[
                    "numero_global"
                ] = proximo_id

                objeto[
                    "nome_global"
                ] = (
                    f"Objeto {proximo_id}"
                )

                objeto[
                    "similaridade_global"
                ] = 1.0

                proximo_id += 1

    # ========================================================
    # ORGANIZAR CÂMERAS
    # ========================================================

    for objeto_global in (
        objetos_globais.values()
    ):

        objeto_global[
            "cameras"
        ] = sorted(
            set(
                objeto_global[
                    "cameras"
                ]
            )
        )

    return objetos_globais


# ============================================================
# PREPARAR PARA SALVAR
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
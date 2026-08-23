import cv2
import math
import os
import numpy as np
import torch

from ultralytics import YOLO

import config

from analise_ambiente import (
    analisar_frame,
    desenhar_objetos
)

from objetos_globais import (
    criar_objetos_globais,
    preparar_objetos_para_salvar
)


# ============================================================
# ESTADO
# ============================================================

estado_sistema = (
    config.obter_estado_inicial()
)


# ============================================================
# CONFIGURAÇÕES
# ============================================================

MAX_INDICES_CAMERA = getattr(
    config,
    "MAX_CAMERAS",
    66
)

LIMITE_FALHAS_CAPTURA = 10

INTERVALO_ANALISE_AMBIENTE = 10

FRAMES_ANTES_CONFIGURACAO = 30


# ============================================================
# INTERFACE DE CONFIGURAÇÃO
# ============================================================

NOME_JANELA_CONFIG = (
    "Configuracao Inicial"
)

clique_mouse = None


# ============================================================
# EPI - CLASSES
# ============================================================

EPIS_PRESENCA = {

    "Helmet":
        "Capacete",

    "Glass":
        "Óculos",

    "Mask":
        "Máscara",

    "Glove":
        "Luvas",

    "Ear Protectors":
        "Protetor auricular",

    "Safety Vest":
        "Colete",
}


EPIS_AUSENCIA = {

    "Without Helmet":
        "Capacete",

    "Without Glass":
        "Óculos",

    "Without Mask":
        "Máscara",

    "Without Glove":
        "Luvas",

    "Without Ear Protectors":
        "Protetor auricular",

    "Without Safety Vest":
        "Colete",
}


# ============================================================
# MODELO DE EPI
# ============================================================

modelo_epi = None


def carregar_modelo_epi():

    global modelo_epi

    if modelo_epi is not None:

        return modelo_epi

    caminho = getattr(
        config,
        "PATH_MODELO",
        "best.pt"
    )

    if not os.path.exists(
        caminho
    ):

        print()
        print(
            f"⚠️ Modelo de EPI não encontrado: "
            f"{caminho}"
        )

        return None

    try:

        modelo_epi = YOLO(
            caminho
        )

        print()
        print(
            "=========================================="
        )
        print(
            " MODELO DE EPI CARREGADO"
        )
        print(
            "=========================================="
        )

        print(
            caminho
        )

        print(
            "=========================================="
        )
        print()

        return modelo_epi

    except Exception as erro:

        print(
            f"❌ Erro ao carregar modelo de EPI: "
            f"{erro}"
        )

        modelo_epi = None

        return None


# ============================================================
# DEVICE
# ============================================================

if torch.cuda.is_available():

    DEVICE = 0

else:

    DEVICE = "cpu"


# ============================================================
# EVENTO DO MOUSE
# ============================================================

def evento_mouse(
    evento,
    x,
    y,
    flags,
    parametro
):

    global clique_mouse

    if evento == cv2.EVENT_LBUTTONDOWN:

        clique_mouse = (
            x,
            y
        )


# ============================================================
# VERIFICAR CLIQUE
# ============================================================

def ponto_dentro(
    ponto,
    caixa
):

    if ponto is None:

        return False

    x, y = ponto

    x1, y1, x2, y2 = caixa

    return (
        x1 <= x <= x2
        and
        y1 <= y <= y2
    )


# ============================================================
# DESENHAR BOTÃO
# ============================================================

def desenhar_botao(
    tela,
    texto,
    caixa,
    selecionado=False
):

    x1, y1, x2, y2 = caixa

    if selecionado:

        cor = (
            50,
            125,
            60
        )

    else:

        cor = (
            55,
            55,
            55
        )

    cv2.rectangle(
        tela,
        (x1, y1),
        (x2, y2),
        cor,
        -1
    )

    cv2.rectangle(
        tela,
        (x1, y1),
        (x2, y2),
        (140, 140, 140),
        1
    )

    cv2.putText(
        tela,
        texto,
        (
            x1 + 12,
            y1 + 27
        ),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.50,
        (255, 255, 255),
        1,
        cv2.LINE_AA
    )


# ============================================================
# CLASSE DA CÂMERA
# ============================================================

class CameraSistema:

    def __init__(
        self,
        camera_id,
        fonte=None,
        nome=None
    ):

        self.camera_id = camera_id

        self.fonte = (
            camera_id
            if fonte is None
            else fonte
        )

        self.nome = (
            nome
            if nome
            else f"Camera {camera_id + 1:02d}"
        )

        self.cap = None

        self.ativa = False

        self.ultimo_frame = None

        self.falhas_consecutivas = 0

        self.objetos = []

        self.total_objetos = 0


    # ========================================================
    # ABRIR
    # ========================================================

    def abrir(self):

        self.liberar()

        try:

            if isinstance(
                self.fonte,
                int
            ):

                self.cap = cv2.VideoCapture(
                    self.fonte,
                    cv2.CAP_DSHOW
                )

            else:

                self.cap = cv2.VideoCapture(
                    self.fonte
                )

        except Exception:

            self.cap = None

            return False

        if (
            self.cap is None
            or not self.cap.isOpened()
        ):

            if self.cap is not None:

                self.cap.release()

            self.cap = None

            return False

        self.cap.set(
            cv2.CAP_PROP_FRAME_WIDTH,
            getattr(
                config,
                "LARGURA_CAM",
                640
            )
        )

        self.cap.set(
            cv2.CAP_PROP_FRAME_HEIGHT,
            getattr(
                config,
                "ALTURA_CAM",
                480
            )
        )

        sucesso, frame = (
            self.cap.read()
        )

        if (
            not sucesso
            or frame is None
            or frame.size == 0
        ):

            self.cap.release()

            self.cap = None

            return False

        self.ultimo_frame = frame

        self.ativa = True

        self.falhas_consecutivas = 0

        print(
            f"✅ {self.nome} encontrada "
            f"(indice {self.camera_id})"
        )

        return True


    # ========================================================
    # GRAB
    # ========================================================

    def grab(self):

        if (
            self.cap is None
            or not self.ativa
        ):

            return False

        try:

            sucesso = self.cap.grab()

        except Exception:

            sucesso = False

        if not sucesso:

            self.falhas_consecutivas += 1

        return sucesso


    # ========================================================
    # RETRIEVE
    # ========================================================

    def retrieve(self):

        if (
            self.cap is None
            or not self.ativa
        ):

            return None

        try:

            sucesso, frame = (
                self.cap.retrieve()
            )

        except Exception:

            sucesso = False
            frame = None

        if (
            not sucesso
            or frame is None
            or frame.size == 0
        ):

            self.falhas_consecutivas += 1

            return None

        self.falhas_consecutivas = 0

        self.ultimo_frame = frame

        return frame


    # ========================================================
    # PERDEU CONEXÃO
    # ========================================================

    def perdeu_conexao(self):

        return (
            self.falhas_consecutivas
            >= LIMITE_FALHAS_CAPTURA
        )


    # ========================================================
    # LIBERAR
    # ========================================================

    def liberar(self):

        if self.cap is not None:

            try:

                self.cap.release()

            except Exception:

                pass

        self.cap = None

        self.ativa = False


# ============================================================
# DESCOBRIR CÂMERAS
# ============================================================

def descobrir_cameras():

    cameras = {}

    print()
    print(
        "=========================================="
    )
    print(
        " PROCURANDO CAMERAS DISPONIVEIS"
    )
    print(
        "=========================================="
    )

    for camera_id in range(
        MAX_INDICES_CAMERA
    ):

        dados = getattr(
            config,
            "CAMERAS",
            {}
        ).get(
            camera_id,
            {}
        )

        fonte = dados.get(
            "fonte",
            camera_id
        )

        nome = dados.get(
            "nome",
            f"Camera {camera_id + 1:02d}"
        )

        camera = CameraSistema(
            camera_id,
            fonte,
            nome
        )

        if camera.abrir():

            cameras[
                camera_id
            ] = camera

    print(
        "=========================================="
    )

    print(
        f"Total de cameras encontradas: "
        f"{len(cameras)}"
    )

    print(
        "=========================================="
    )
    print()

    return cameras


# ============================================================
# CAPTURA SINCRONIZADA
# ============================================================

def capturar_frames_sincronizados(
    cameras
):

    for camera in cameras.values():

        if camera.ativa:

            camera.grab()

    frames = []

    remover = []

    for (
        camera_id,
        camera
    ) in list(
        cameras.items()
    ):

        frame = camera.retrieve()

        if frame is None:

            if camera.perdeu_conexao():

                remover.append(
                    camera_id
                )

                continue

            if camera.ultimo_frame is not None:

                frame = (
                    camera.ultimo_frame.copy()
                )

            else:

                continue

        frames.append(
            (
                camera,
                frame
            )
        )

    for camera_id in remover:

        camera = cameras.get(
            camera_id
        )

        if camera:

            print(
                f"⚠️ {camera.nome} "
                "desconectada."
            )

            camera.liberar()

        cameras.pop(
            camera_id,
            None
        )

    return frames


# ============================================================
# ANALISAR AMBIENTE
# ============================================================

def analisar_ambiente_cameras(
    frames
):

    resultado = []

    for (
        camera,
        frame
    ) in frames:

        try:

            objetos = analisar_frame(
                frame,
                camera.camera_id
            )

        except Exception as erro:

            print(
                f"Erro analisando "
                f"{camera.nome}: {erro}"
            )

            objetos = []

        camera.objetos = objetos

        camera.total_objetos = len(
            objetos
        )

        frame_visual = (
            desenhar_objetos(
                frame,
                objetos
            )
        )

        resultado.append(
            (
                camera,
                frame_visual
            )
        )

    return resultado


# ============================================================
# DESENHAR OBJETOS EXISTENTES
# ============================================================

def desenhar_objetos_existentes(
    frames
):

    resultado = []

    for (
        camera,
        frame
    ) in frames:

        frame_visual = (
            desenhar_objetos(
                frame,
                camera.objetos
            )
        )

        resultado.append(
            (
                camera,
                frame_visual
            )
        )

    return resultado


# ============================================================
# SELECIONAR MAQUINÁRIOS
# ============================================================

def selecionar_maquinarios(
    objetos_globais
):

    global clique_mouse

    clique_mouse = None

    selecionados = set()

    cv2.namedWindow(
        NOME_JANELA_CONFIG
    )

    cv2.setMouseCallback(
        NOME_JANELA_CONFIG,
        evento_mouse
    )

    while True:

        altura = max(
            550,
            180
            + len(
                objetos_globais
            ) * 55
        )

        altura = min(
            altura,
            850
        )

        tela = np.zeros(
            (
                altura,
                760,
                3
            ),
            dtype=np.uint8
        )

        tela[:] = (
            28,
            28,
            28
        )

        cv2.putText(
            tela,
            "ANALISE DO AMBIENTE",
            (30, 42),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.72,
            (255, 255, 255),
            2,
            cv2.LINE_AA
        )

        cv2.putText(
            tela,
            "Quais objetos sao maquinarios?",
            (30, 80),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.56,
            (0, 220, 255),
            2,
            cv2.LINE_AA
        )

        botoes = {}

        y = 110

        for (
            objeto_id,
            objeto
        ) in objetos_globais.items():

            cameras_texto = ", ".join(
                [
                    f"CAM {camera + 1:02d}"
                    for camera
                    in objeto.get(
                        "cameras",
                        []
                    )
                ]
            )

            texto = (
                f"{objeto['nome']} "
                f"({cameras_texto})"
            )

            caixa = (
                30,
                y,
                720,
                y + 42
            )

            botoes[
                objeto_id
            ] = caixa

            desenhar_botao(
                tela,
                texto,
                caixa,
                objeto_id
                in selecionados
            )

            y += 52

            if y > altura - 100:

                break

        confirmar = (
            500,
            altura - 65,
            720,
            altura - 20
        )

        desenhar_botao(
            tela,
            "CONFIRMAR",
            confirmar,
            True
        )

        cv2.imshow(
            NOME_JANELA_CONFIG,
            tela
        )

        tecla = (
            cv2.waitKey(20)
            & 0xFF
        )

        if tecla == ord("q"):

            return None

        if clique_mouse is None:

            continue

        clique = clique_mouse

        clique_mouse = None

        for (
            objeto_id,
            caixa
        ) in botoes.items():

            if ponto_dentro(
                clique,
                caixa
            ):

                if (
                    objeto_id
                    in selecionados
                ):

                    selecionados.remove(
                        objeto_id
                    )

                else:

                    selecionados.add(
                        objeto_id
                    )

        if ponto_dentro(
            clique,
            confirmar
        ):

            break

    for (
        objeto_id,
        objeto
    ) in objetos_globais.items():

        objeto[
            "maquinario"
        ] = (
            objeto_id
            in selecionados
        )

    return objetos_globais


# ============================================================
# SELECIONAR EPIs
# ============================================================

def selecionar_epis():

    global clique_mouse

    clique_mouse = None

    selecionados = set()

    epis = getattr(
        config,
        "EPIS_DISPONIVEIS",
        []
    )

    while True:

        tela = np.zeros(
            (
                610,
                760,
                3
            ),
            dtype=np.uint8
        )

        tela[:] = (
            28,
            28,
            28
        )

        cv2.putText(
            tela,
            "CONFIGURACAO DE EPIs",
            (30, 42),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.72,
            (255, 255, 255),
            2,
            cv2.LINE_AA
        )

        cv2.putText(
            tela,
            "Quais EPIs sao obrigatorios?",
            (30, 80),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.56,
            (0, 220, 255),
            2,
            cv2.LINE_AA
        )

        botoes = {}

        y = 120

        for epi in epis:

            caixa = (
                30,
                y,
                720,
                y + 45
            )

            botoes[
                epi
            ] = caixa

            if epi in selecionados:

                prefixo = "[X]"

            else:

                prefixo = "[ ]"

            desenhar_botao(
                tela,
                f"{prefixo}  {epi}",
                caixa,
                epi in selecionados
            )

            y += 58

        confirmar = (
            500,
            535,
            720,
            580
        )

        desenhar_botao(
            tela,
            "CONFIRMAR",
            confirmar,
            True
        )

        cv2.imshow(
            NOME_JANELA_CONFIG,
            tela
        )

        tecla = (
            cv2.waitKey(20)
            & 0xFF
        )

        if tecla == ord("q"):

            return None

        if clique_mouse is None:

            continue

        clique = clique_mouse

        clique_mouse = None

        for (
            epi,
            caixa
        ) in botoes.items():

            if ponto_dentro(
                clique,
                caixa
            ):

                if epi in selecionados:

                    selecionados.remove(
                        epi
                    )

                else:

                    selecionados.add(
                        epi
                    )

        if ponto_dentro(
            clique,
            confirmar
        ):

            break

    return list(
        selecionados
    )


# ============================================================
# CONFIGURAR AMBIENTE
# ============================================================

def configurar_ambiente(
    frames_originais
):

    global estado_sistema

    print()
    print(
        "Agrupando objetos entre as cameras..."
    )

    objetos_globais = (
        criar_objetos_globais(
            frames_originais
        )
    )

    if not objetos_globais:

        print(
            "⚠️ Nenhum objeto detectado."
        )

        return False

    print(
        f"Objetos globais: "
        f"{len(objetos_globais)}"
    )

    # ========================================================
    # MAQUINÁRIOS
    # ========================================================

    objetos_globais = (
        selecionar_maquinarios(
            objetos_globais
        )
    )

    if objetos_globais is None:

        return False

    objetos_salvar = (
        preparar_objetos_para_salvar(
            objetos_globais
        )
    )

    if not config.salvar_configuracao_ambiente(
        objetos_salvar
    ):

        print(
            "❌ Erro ao salvar ambiente."
        )

        return False

    config.AMBIENTE_CALIBRADO = True

    config.OBJETOS_GLOBAIS = (
        objetos_salvar
    )

    # ========================================================
    # EPIs
    # ========================================================

    estado_sistema = (
        config.ESTADO_CONFIGURACAO_EPI
    )

    epis = selecionar_epis()

    if epis is None:

        return False

    if not config.salvar_configuracao_epis(
        epis
    ):

        print(
            "❌ Erro ao salvar EPIs."
        )

        return False

    config.EPIS_CONFIGURADOS = True

    config.EPIS_OBRIGATORIOS = epis

    # ========================================================
    # MONITORAMENTO
    # ========================================================

    estado_sistema = (
        config.ESTADO_MONITORAMENTO
    )

    carregar_modelo_epi()

    try:

        cv2.destroyWindow(
            NOME_JANELA_CONFIG
        )

    except Exception:

        pass

    print()
    print(
        "=========================================="
    )
    print(
        " CONFIGURACAO CONCLUIDA"
    )
    print(
        "=========================================="
    )

    print(
        f"EPIs obrigatorios: "
        f"{epis}"
    )

    print(
        "Estado: MONITORAMENTO"
    )

    print(
        "=========================================="
    )
    print()

    return True


# ============================================================
# ANALISAR EPIs EM UM FRAME
# ============================================================

def analisar_epis_frame(
    frame
):

    obrigatorios = getattr(
        config,
        "EPIS_OBRIGATORIOS",
        []
    )

    status = {

        epi: False

        for epi in obrigatorios
    }

    if not obrigatorios:

        return status

    modelo = carregar_modelo_epi()

    if modelo is None:

        return status

    try:

        resultados = modelo.predict(
            frame,
            conf=getattr(
                config,
                "CONFIDENCIA_MINIMA",
                0.5
            ),
            imgsz=getattr(
                config,
                "TAMANHO_IMAGEM",
                640
            ),
            device=DEVICE,
            verbose=False
        )

    except Exception as erro:

        print(
            f"⚠️ Erro na análise de EPI: "
            f"{erro}"
        )

        return status

    classes = set()

    for resultado in resultados:

        if resultado.boxes is None:

            continue

        for box in resultado.boxes:

            classe_id = int(
                box.cls[0]
            )

            nome = resultado.names[
                classe_id
            ]

            classes.add(
                nome
            )

    for epi in obrigatorios:

        classe_presenca = None

        classe_ausencia = None

        for (
            classe,
            nome
        ) in EPIS_PRESENCA.items():

            if nome == epi:

                classe_presenca = classe

                break

        for (
            classe,
            nome
        ) in EPIS_AUSENCIA.items():

            if nome == epi:

                classe_ausencia = classe

                break

        # Ausência explícita tem prioridade.
        if (
            classe_ausencia is not None
            and classe_ausencia in classes
        ):

            status[
                epi
            ] = False

        elif (
            classe_presenca is not None
            and classe_presenca in classes
        ):

            status[
                epi
            ] = True

        else:

            status[
                epi
            ] = False

    return status


# ============================================================
# ANALISAR EPIs EM TODAS AS CÂMERAS
# ============================================================

def analisar_epis_cameras(
    frames
):

    obrigatorios = getattr(
        config,
        "EPIS_OBRIGATORIOS",
        []
    )

    # --------------------------------------------------------
    # Guarda presença e ausência por todas as câmeras.
    # --------------------------------------------------------

    encontrou_presenca = {

        epi: False
        for epi in obrigatorios
    }

    encontrou_ausencia = {

        epi: False
        for epi in obrigatorios
    }

    modelo = carregar_modelo_epi()

    if (
        modelo is None
        or not frames
    ):

        return {

            epi: False
            for epi in obrigatorios
        }

    for (
        camera,
        frame
    ) in frames:

        try:

            resultados = modelo.predict(
                frame,
                conf=getattr(
                    config,
                    "CONFIDENCIA_MINIMA",
                    0.5
                ),
                imgsz=getattr(
                    config,
                    "TAMANHO_IMAGEM",
                    640
                ),
                device=DEVICE,
                verbose=False
            )

        except Exception as erro:

            print(
                f"⚠️ Erro EPI "
                f"{camera.nome}: "
                f"{erro}"
            )

            continue

        classes = set()

        for resultado in resultados:

            if resultado.boxes is None:

                continue

            for box in resultado.boxes:

                classe_id = int(
                    box.cls[0]
                )

                nome_classe = (
                    resultado.names[
                        classe_id
                    ]
                )

                classes.add(
                    nome_classe
                )

        for epi in obrigatorios:

            for (
                classe,
                nome
            ) in EPIS_PRESENCA.items():

                if (
                    nome == epi
                    and classe in classes
                ):

                    encontrou_presenca[
                        epi
                    ] = True

            for (
                classe,
                nome
            ) in EPIS_AUSENCIA.items():

                if (
                    nome == epi
                    and classe in classes
                ):

                    encontrou_ausencia[
                        epi
                    ] = True

    status = {}

    for epi in obrigatorios:

        # Ausência explícita tem prioridade.
        if encontrou_ausencia[
            epi
        ]:

            status[
                epi
            ] = False

        elif encontrou_presenca[
            epi
        ]:

            status[
                epi
            ] = True

        else:

            status[
                epi
            ] = False

    return status


# ============================================================
# CALCULAR SEVERIDADE
# ============================================================

def calcular_severidade_epi(
    status_epis
):

    if not status_epis:

        return "NORMAL"

    faltando = any(
        not presente
        for presente
        in status_epis.values()
    )

    if faltando:

        return "ALTA"

    return "NORMAL"


# ============================================================
# PREPARAR FRAME PARA GRADE
# ============================================================

def preparar_frame(
    camera,
    frame,
    largura,
    altura
):

    frame = cv2.resize(
        frame,
        (
            largura,
            altura
        )
    )

    cv2.rectangle(
        frame,
        (0, 0),
        (largura, 40),
        (25, 25, 25),
        -1
    )

    cv2.putText(
        frame,
        camera.nome,
        (12, 27),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.58,
        (255, 255, 255),
        2,
        cv2.LINE_AA
    )

    return frame


# ============================================================
# CRIAR GRADE
# ============================================================

def criar_grade(
    frames
):

    quantidade = len(
        frames
    )

    if quantidade == 0:

        return None

    if quantidade == 1:

        colunas = 1

        largura = 600

        altura = 450

    elif quantidade <= 4:

        colunas = 2

        largura = 480

        altura = 360

    else:

        colunas = 3

        largura = 380

        altura = 285

    linhas = math.ceil(
        quantidade
        / colunas
    )

    imagens = []

    for (
        camera,
        frame
    ) in frames:

        imagens.append(
            preparar_frame(
                camera,
                frame,
                largura,
                altura
            )
        )

    while (
        len(imagens)
        < linhas * colunas
    ):

        imagens.append(
            np.zeros(
                (
                    altura,
                    largura,
                    3
                ),
                dtype=np.uint8
            )
        )

    grade_linhas = []

    indice = 0

    for _ in range(
        linhas
    ):

        grade_linhas.append(
            np.hstack(
                imagens[
                    indice:
                    indice + colunas
                ]
            )
        )

        indice += colunas

    return np.vstack(
        grade_linhas
    )


# ============================================================
# PAINEL CENTRAL
# ============================================================

def criar_painel(
    altura,
    cameras,
    status_epis=None,
    operador="Buscando Biometria...",
    severidade="NORMAL"
):

    largura = getattr(
        config,
        "LARGURA_PAINEL_CENTRAL",
        330
    )

    painel = np.zeros(
        (
            altura,
            largura,
            3
        ),
        dtype=np.uint8
    )

    painel[:] = (
        28,
        28,
        28
    )

    # ========================================================
    # CABEÇALHO
    # ========================================================

    cv2.putText(
        painel,
        "STATUS DOS EPIs",
        (20, 38),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.62,
        (255, 255, 255),
        2,
        cv2.LINE_AA
    )

    cv2.line(
        painel,
        (20, 55),
        (
            largura - 20,
            55
        ),
        (80, 80, 80),
        1
    )

    # ========================================================
    # OPERADOR
    # ========================================================

    cv2.putText(
        painel,
        "OPERADOR",
        (20, 90),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.40,
        (160, 160, 160),
        1,
        cv2.LINE_AA
    )

    operador_tela = str(
        operador
    )

    if len(
        operador_tela
    ) > 28:

        operador_tela = (
            operador_tela[:28]
            + "..."
        )

    cv2.putText(
        painel,
        operador_tela,
        (20, 120),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.48,
        (255, 255, 255),
        1,
        cv2.LINE_AA
    )

    # ========================================================
    # SEVERIDADE
    # ========================================================

    cv2.putText(
        painel,
        "SEVERIDADE",
        (20, 160),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.40,
        (160, 160, 160),
        1,
        cv2.LINE_AA
    )

    if severidade == "NORMAL":
        cor_severidade = (0, 200, 0)
    elif severidade == "CRITICA":
        cor_severidade = (0, 0, 255)
    else:
        cor_severidade = (0, 80, 255)

    cv2.putText(
        painel,
        severidade,
        (20, 190),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.52,
        cor_severidade,
        2,
        cv2.LINE_AA
    )

    cv2.line(
        painel,
        (20, 212),
        (largura - 20, 212),
        (80, 80, 80),
        1
    )

    # ========================================================
    # ESTADO
    # ========================================================

    cv2.putText(
        painel,
        "ESTADO",
        (20, 245),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.40,
        (160, 160, 160),
        1,
        cv2.LINE_AA
    )

    if estado_sistema == config.ESTADO_CALIBRACAO_AMBIENTE:
        texto_estado = "ANALISE DO AMBIENTE"
        cor_estado = (0, 220, 255)

    elif estado_sistema == config.ESTADO_CONFIGURACAO_EPI:
        texto_estado = "CONFIGURACAO EPI"
        cor_estado = (0, 220, 255)

    else:
        texto_estado = "MONITORAMENTO"
        cor_estado = (0, 200, 0)

    cv2.putText(
        painel,
        texto_estado,
        (20, 275),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.45,
        cor_estado,
        2,
        cv2.LINE_AA
    )

    cv2.line(
        painel,
        (20, 300),
        (largura - 20, 300),
        (80, 80, 80),
        1
    )

    # ========================================================
    # EPIs
    # ========================================================

    cv2.putText(
        painel,
        "EPIs OBRIGATORIOS",
        (20, 335),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.42,
        (160, 160, 160),
        1,
        cv2.LINE_AA
    )

    y = 375

    epis_obrigatorios = getattr(
        config,
        "EPIS_OBRIGATORIOS",
        []
    )

    if not epis_obrigatorios:
        cv2.putText(
            painel,
            "Nenhum EPI configurado",
            (20, y),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.42,
            (150, 150, 150),
            1,
            cv2.LINE_AA
        )
        return painel

    if status_epis is None:
        status_epis = {}

    for epi in epis_obrigatorios:
        presente = status_epis.get(epi, False)

        if presente:
            texto_status = "OK"
            cor_status = (0, 200, 0)
        else:
            texto_status = "FALTA"
            cor_status = (0, 0, 255)

        cv2.putText(
            painel,
            epi,
            (20, y),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.46,
            (255, 255, 255),
            1,
            cv2.LINE_AA
        )

        tamanho, _ = cv2.getTextSize(
            texto_status,
            cv2.FONT_HERSHEY_SIMPLEX,
            0.45,
            2
        )

        x_status = largura - tamanho[0] - 25

        cv2.putText(
            painel,
            texto_status,
            (x_status, y),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.45,
            cor_status,
            2,
            cv2.LINE_AA
        )

        cv2.line(
            painel,
            (20, y + 15),
            (largura - 20, y + 15),
            (65, 65, 65),
            1
        )

        y += 48

        if y > altura - 20:
            break

    return painel


# ============================================================
# MAIN
# ============================================================

def main():

    global estado_sistema

    cameras = descobrir_cameras()

    contador_frames = 0
    configuracao_iniciada = False

    if estado_sistema == config.ESTADO_MONITORAMENTO:
        carregar_modelo_epi()

    try:

        while True:

            contador_frames += 1

            frames = (
                capturar_frames_sincronizados(cameras)
                if cameras
                else []
            )

            status_epis = {}
            operador = "Buscando Biometria..."
            severidade = "NORMAL"

            # =================================================
            # CALIBRACAO
            # =================================================

            if estado_sistema == config.ESTADO_CALIBRACAO_AMBIENTE:

                if frames:

                    nova_analise = (
                        contador_frames == 1
                        or contador_frames % INTERVALO_ANALISE_AMBIENTE == 0
                    )

                    if nova_analise:
                        frames_visuais = analisar_ambiente_cameras(frames)
                    else:
                        frames_visuais = desenhar_objetos_existentes(frames)

                    if (
                        contador_frames >= FRAMES_ANTES_CONFIGURACAO
                        and not configuracao_iniciada
                    ):

                        tem_objeto = any(
                            camera.total_objetos > 0
                            for camera in cameras.values()
                        )

                        if tem_objeto:

                            configuracao_iniciada = True

                            frames_config = capturar_frames_sincronizados(
                                cameras
                            )

                            analisar_ambiente_cameras(
                                frames_config
                            )

                            sucesso = configurar_ambiente(
                                frames_config
                            )

                            if not sucesso:
                                configuracao_iniciada = False

                else:
                    frames_visuais = []

            # =================================================
            # MONITORAMENTO
            # =================================================

            elif estado_sistema == config.ESTADO_MONITORAMENTO:

                frames_visuais = frames

                if frames:
                    status_epis = analisar_epis_cameras(frames)
                    severidade = calcular_severidade_epi(
                        status_epis
                    )

            # =================================================
            # CONFIGURACAO DE EPI
            # =================================================

            else:
                frames_visuais = frames

            # =================================================
            # GRADE
            # =================================================

            grade = criar_grade(
                frames_visuais
            )

            if grade is not None:

                painel = criar_painel(
                    grade.shape[0],
                    cameras,
                    status_epis=status_epis,
                    operador=operador,
                    severidade=severidade
                )

                tela = np.hstack(
                    (
                        grade,
                        painel
                    )
                )

            else:

                tela = np.zeros(
                    (
                        500,
                        900,
                        3
                    ),
                    dtype=np.uint8
                )

                cv2.putText(
                    tela,
                    "PROCURANDO CAMERAS...",
                    (250, 250),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.8,
                    (0, 220, 255),
                    2,
                    cv2.LINE_AA
                )

            cv2.imshow(
                getattr(
                    config,
                    "NOME_JANELA",
                    "FIAP x SPI Challenge 2026"
                ),
                tela
            )

            tecla = cv2.waitKey(1) & 0xFF

            if tecla == ord("q"):
                break

    finally:

        for camera in list(
            cameras.values()
        ):
            camera.liberar()

        cv2.destroyAllWindows()


# ============================================================
# EXECUCAO
# ============================================================

if __name__ == "__main__":
    main()

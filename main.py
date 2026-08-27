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

from decision_engine import (
    processar_incidente,
    atualizar_incidentes_ausentes,
    criar_chave_incidente
)

from notificacoes import (
    atualizar_notificacoes,
    encerrar_notificacoes
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
# ESTABILIZACAO TEMPORAL DOS EPIs
# ============================================================

# Poucos frames para aceitar que o EPI apareceu.
FRAMES_CONFIRMAR_EPI_PRESENTE = 3

# Mais frames para aceitar uma ausência explícita.
FRAMES_CONFIRMAR_EPI_AUSENTE = 8

# Se o modelo não detectar nem presença nem ausência,
# preservamos o último estado por um tempo para evitar
# oscilação frame a frame.
FRAMES_SEM_EVIDENCIA_PARA_AUSENCIA = 25

estado_temporal_epis = {}

# Detalhes da última inferência por câmera.
# Usado para escolher a câmera/frame da foto de prova.
detalhes_epis_cameras = {}


# ============================================================
# INTERFACE DE CONFIGURAÇÃO
# ============================================================

NOME_JANELA_CONFIG = (
    "Configuracao Inicial"
)

clique_mouse = None
rolagem_mouse = 0


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
    global rolagem_mouse

    if evento == cv2.EVENT_LBUTTONDOWN:

        clique_mouse = (
            x,
            y
        )

    elif evento == cv2.EVENT_MOUSEWHEEL:

        try:
            delta = cv2.getMouseWheelDelta(
                flags
            )
        except Exception:
            delta = flags

        if delta > 0:
            rolagem_mouse = -1
        elif delta < 0:
            rolagem_mouse = 1


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

        # True para RTSP/HTTP; False para câmera USB.
        self.tipo_rede = not isinstance(
            self.fonte,
            int
        )


    # ========================================================
    # ABRIR
    # ========================================================

    def abrir(self):

        self.liberar()

        try:

            # =================================================
            # USB
            # =================================================

            if not self.tipo_rede:

                self.cap = cv2.VideoCapture(
                    self.fonte,
                    cv2.CAP_DSHOW
                )

            # =================================================
            # WIFI / IP / RTSP / HTTP
            # =================================================

            else:

                # Preferência para RTSP via TCP.
                # Ajuda a evitar perda/corrupção de frames
                # em streams de rede.
                if str(
                    self.fonte
                ).lower().startswith(
                    "rtsp://"
                ):

                    os.environ[
                        "OPENCV_FFMPEG_CAPTURE_OPTIONS"
                    ] = (
                        "rtsp_transport;tcp"
                    )

                self.cap = cv2.VideoCapture(
                    self.fonte,
                    cv2.CAP_FFMPEG
                )

                # Fallback caso o backend FFmpeg explícito
                # não consiga abrir determinada câmera.
                if not self.cap.isOpened():

                    self.cap.release()

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

        # Buffer mínimo para reduzir atraso em câmera de rede.
        if self.tipo_rede:

            try:

                self.cap.set(
                    cv2.CAP_PROP_BUFFERSIZE,
                    1
                )

            except Exception:

                pass

        else:

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

        # Para validar a câmera usamos read().
        # É a mesma forma que funcionou no teste isolado
        # do stream RTSP.
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

        tipo_fonte = (
            "WIFI/IP"
            if self.tipo_rede
            else "USB"
        )

        print(
            f"✅ {self.nome} encontrada "
            f"({tipo_fonte})"
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

        # Em streams RTSP/HTTP usamos read() diretamente
        # no retrieve(). Isso evita problemas observados
        # com grab/retrieve em alguns decodificadores.
        if self.tipo_rede:

            return True

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

            if self.tipo_rede:

                sucesso, frame = (
                    self.cap.read()
                )

            else:

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
# ABRIR CÂMERAS A PARTIR DE UMA CONFIGURAÇÃO
# ============================================================

def abrir_cameras_configuradas(
    configuracoes,
    modo
):

    cameras = {}

    for camera_id, dados in configuracoes.items():

        if not dados.get(
            "ativa",
            True
        ):
            continue

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

    return cameras


# ============================================================
# DESCOBRIR CÂMERAS
# ============================================================

def descobrir_cameras():

    modo = getattr(
        config,
        "MODO_CAMERAS",
        "usb"
    ).lower()

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

    # ========================================================
    # WIFI / IP TEM PRIORIDADE
    # ========================================================

    if modo == "wifi":

        print(
            "Modo configurado: WIFI / IP"
        )

        print(
            "Tentando abrir somente as cameras "
            "salvas em camera_wifi/cameras_wifi.json"
        )

        configuracoes_wifi = getattr(
            config,
            "CAMERAS",
            {}
        )

        cameras = abrir_cameras_configuradas(
            configuracoes_wifi,
            "wifi"
        )

        if cameras:

            print(
                "=========================================="
            )

            print(
                f"Total de cameras WiFi/IP abertas: "
                f"{len(cameras)}"
            )

            print(
                "=========================================="
            )
            print()

            return cameras

        # ----------------------------------------------------
        # WIFI EXISTE NO JSON, MAS NENHUMA ABRIU
        # ----------------------------------------------------

        print()
        print(
            "⚠️ Nenhuma camera WiFi/IP configurada "
            "conseguiu abrir."
        )

        resposta = input(
            "Deseja usar cameras USB como fallback? "
            "[S/n]: "
        ).strip().lower()

        if resposta not in (
            "",
            "s",
            "sim",
            "y",
            "yes"
        ):

            print()
            print(
                "Fallback USB cancelado."
            )
            print()

            return {}

        print()
        print(
            "Usando fallback USB..."
        )

        if hasattr(
            config,
            "criar_cameras_usb"
        ):

            configuracoes_usb = (
                config.criar_cameras_usb()
            )

        else:

            configuracoes_usb = {

                camera_id: {
                    "nome":
                        f"Camera {camera_id + 1:02d}",

                    "fonte":
                        camera_id,

                    "tipo":
                        "usb",

                    "ativa":
                        True,
                }

                for camera_id in range(
                    MAX_INDICES_CAMERA
                )
            }

        cameras = abrir_cameras_configuradas(
            configuracoes_usb,
            "usb"
        )

        print(
            "=========================================="
        )

        print(
            f"Total de cameras USB encontradas: "
            f"{len(cameras)}"
        )

        print(
            "=========================================="
        )
        print()

        return cameras

    # ========================================================
    # USB PADRÃO
    # ========================================================

    print(
        "Modo configurado: USB"
    )

    if hasattr(
        config,
        "criar_cameras_usb"
    ):

        configuracoes_usb = (
            config.criar_cameras_usb()
        )

    else:

        configuracoes_usb = getattr(
            config,
            "CAMERAS",
            {}
        )

    cameras = abrir_cameras_configuradas(
        configuracoes_usb,
        "usb"
    )

    print(
        "=========================================="
    )

    print(
        f"Total de cameras USB encontradas: "
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
    global rolagem_mouse

    clique_mouse = None
    rolagem_mouse = 0

    selecionados = set()

    itens = sorted(
        objetos_globais.items(),
        key=lambda item: item[1].get("numero", 999999)
    )

    largura_tela = 760
    altura_tela = 600
    topo_lista = 115
    rodape = 100
    altura_item = 52

    x_lista_inicio = 30
    x_lista_fim = 690
    x_barra_inicio = 710
    x_barra_fim = 728

    area_lista = altura_tela - topo_lista - rodape
    itens_por_pagina = max(1, area_lista // altura_item)
    max_offset = max(0, len(itens) - itens_por_pagina)
    offset = 0

    cv2.namedWindow(NOME_JANELA_CONFIG, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(NOME_JANELA_CONFIG, largura_tela, altura_tela)
    cv2.setMouseCallback(NOME_JANELA_CONFIG, evento_mouse)

    while True:

        if rolagem_mouse != 0:
            offset += rolagem_mouse
            offset = max(0, min(max_offset, offset))
            rolagem_mouse = 0

        tela = np.zeros(
            (altura_tela, largura_tela, 3),
            dtype=np.uint8
        )
        tela[:] = (28, 28, 28)

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
            (30, 78),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.56,
            (0, 220, 255),
            2,
            cv2.LINE_AA
        )

        cv2.putText(
            tela,
            "Role o mouse, use W/S ou clique na barra",
            (30, 103),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.42,
            (170, 170, 170),
            1,
            cv2.LINE_AA
        )

        botoes = {}
        visiveis = itens[offset:offset + itens_por_pagina]
        y = topo_lista

        for objeto_id, objeto in visiveis:

            cameras_texto = ", ".join(
                f"CAM {camera + 1:02d}"
                for camera in objeto.get("cameras", [])
            )

            nome_global = objeto.get("nome", objeto_id)
            texto = f"{nome_global}  |  {cameras_texto}"

            caixa = (
                x_lista_inicio,
                y,
                x_lista_fim,
                y + 42
            )

            botoes[objeto_id] = caixa

            desenhar_botao(
                tela,
                texto,
                caixa,
                objeto_id in selecionados
            )

            y += altura_item

        # Barra de rolagem visível.
        y_barra_inicio = topo_lista
        y_barra_fim = topo_lista + area_lista - 5

        cv2.rectangle(
            tela,
            (x_barra_inicio, y_barra_inicio),
            (x_barra_fim, y_barra_fim),
            (65, 65, 65),
            -1
        )

        if len(itens) > itens_por_pagina:

            altura_trilho = y_barra_fim - y_barra_inicio

            altura_cursor = max(
                45,
                int(
                    altura_trilho
                    * itens_por_pagina
                    / len(itens)
                )
            )

            espaco_cursor = max(
                1,
                altura_trilho - altura_cursor
            )

            proporcao = (
                offset / max_offset
                if max_offset > 0
                else 0
            )

            y_cursor = (
                y_barra_inicio
                + int(proporcao * espaco_cursor)
            )

            cv2.rectangle(
                tela,
                (x_barra_inicio + 2, y_cursor),
                (x_barra_fim - 2, y_cursor + altura_cursor),
                (180, 180, 180),
                -1
            )

        inicio = offset + 1 if itens else 0
        fim = min(len(itens), offset + itens_por_pagina)

        cv2.putText(
            tela,
            f"Objetos {inicio}-{fim} de {len(itens)}",
            (30, altura_tela - 52),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.43,
            (170, 170, 170),
            1,
            cv2.LINE_AA
        )

        # Fixo no rodapé da janela.
        confirmar = (
            500,
            altura_tela - 75,
            720,
            altura_tela - 25
        )

        desenhar_botao(
            tela,
            "CONFIRMAR",
            confirmar,
            True
        )

        cv2.imshow(NOME_JANELA_CONFIG, tela)

        tecla = cv2.waitKey(20) & 0xFF

        if tecla == ord("q"):
            return None

        if tecla in (ord("s"), 84):
            offset = min(max_offset, offset + 1)

        elif tecla in (ord("w"), 82):
            offset = max(0, offset - 1)

        if clique_mouse is None:
            continue

        clique = clique_mouse
        clique_mouse = None

        for objeto_id, caixa in botoes.items():

            if ponto_dentro(clique, caixa):

                if objeto_id in selecionados:
                    selecionados.remove(objeto_id)
                else:
                    selecionados.add(objeto_id)

        # Clique na barra move a lista.
        if (
            x_barra_inicio <= clique[0] <= x_barra_fim
            and y_barra_inicio <= clique[1] <= y_barra_fim
            and max_offset > 0
        ):

            proporcao = (
                (clique[1] - y_barra_inicio)
                / max(1, y_barra_fim - y_barra_inicio)
            )

            offset = int(round(proporcao * max_offset))
            offset = max(0, min(max_offset, offset))

        if ponto_dentro(clique, confirmar):
            break

    for objeto_id, objeto in objetos_globais.items():
        objeto["maquinario"] = objeto_id in selecionados

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

    global detalhes_epis_cameras

    obrigatorios = list(
        getattr(
            config,
            "EPIS_OBRIGATORIOS",
            []
        )
    )

    if not obrigatorios:

        detalhes_epis_cameras = {}

        return {}

    modelo = carregar_modelo_epi()

    if (
        modelo is None
        or not frames
    ):

        return {
            epi: estado_temporal_epis.get(
                epi,
                {}
            ).get(
                "status",
                False
            )
            for epi in obrigatorios
        }

    # --------------------------------------------------------
    # Evidência agregada entre todas as câmeras.
    #
    # Regra principal:
    # se QUALQUER câmera enxergar o EPI presente,
    # a presença vence a ausência de outra câmera.
    # --------------------------------------------------------

    presenca_global = {
        epi: False
        for epi in obrigatorios
    }

    ausencia_explicita_global = {
        epi: False
        for epi in obrigatorios
    }

    detalhes_epis_cameras = {}

    for camera, frame in frames:

        detalhes_camera = {
            "camera":
                camera,

            "frame":
                frame,

            "presentes":
                set(),

            "ausentes":
                set(),

            "confiancas_presenca":
                {},

            "confiancas_ausencia":
                {},
        }

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

            detalhes_epis_cameras[
                camera.camera_id
            ] = detalhes_camera

            continue

        for resultado in resultados:

            if resultado.boxes is None:
                continue

            for box in resultado.boxes:

                classe_id = int(
                    box.cls[0]
                )

                nome_classe = str(
                    resultado.names[
                        classe_id
                    ]
                )

                confianca = 0.0

                try:

                    confianca = float(
                        box.conf[0]
                    )

                except Exception:

                    pass

                # --------------------------------------------
                # PRESENÇA
                # --------------------------------------------

                if nome_classe in EPIS_PRESENCA:

                    epi = EPIS_PRESENCA[
                        nome_classe
                    ]

                    if epi in obrigatorios:

                        detalhes_camera[
                            "presentes"
                        ].add(
                            epi
                        )

                        detalhes_camera[
                            "confiancas_presenca"
                        ][epi] = max(
                            confianca,
                            detalhes_camera[
                                "confiancas_presenca"
                            ].get(
                                epi,
                                0.0
                            )
                        )

                        presenca_global[
                            epi
                        ] = True

                # --------------------------------------------
                # AUSÊNCIA EXPLÍCITA
                # --------------------------------------------

                if nome_classe in EPIS_AUSENCIA:

                    epi = EPIS_AUSENCIA[
                        nome_classe
                    ]

                    if epi in obrigatorios:

                        detalhes_camera[
                            "ausentes"
                        ].add(
                            epi
                        )

                        detalhes_camera[
                            "confiancas_ausencia"
                        ][epi] = max(
                            confianca,
                            detalhes_camera[
                                "confiancas_ausencia"
                            ].get(
                                epi,
                                0.0
                            )
                        )

                        ausencia_explicita_global[
                            epi
                        ] = True

        detalhes_epis_cameras[
            camera.camera_id
        ] = detalhes_camera

    status_final = {}

    for epi in obrigatorios:

        estado = estado_temporal_epis.setdefault(
            epi,
            {
                "status":
                    False,

                "frames_presente":
                    0,

                "frames_ausente":
                    0,

                "frames_sem_evidencia":
                    0,
            }
        )

        tem_presenca = presenca_global[
            epi
        ]

        # Se uma câmera detectou presença, ela vence.
        tem_ausencia_explicita = (
            not tem_presenca
            and
            ausencia_explicita_global[
                epi
            ]
        )

        if tem_presenca:

            estado[
                "frames_presente"
            ] += 1

            estado[
                "frames_ausente"
            ] = 0

            estado[
                "frames_sem_evidencia"
            ] = 0

            if (
                estado[
                    "frames_presente"
                ]
                >= FRAMES_CONFIRMAR_EPI_PRESENTE
            ):

                estado[
                    "status"
                ] = True

        elif tem_ausencia_explicita:

            estado[
                "frames_ausente"
            ] += 1

            estado[
                "frames_presente"
            ] = 0

            estado[
                "frames_sem_evidencia"
            ] = 0

            if (
                estado[
                    "frames_ausente"
                ]
                >= FRAMES_CONFIRMAR_EPI_AUSENTE
            ):

                estado[
                    "status"
                ] = False

        else:

            # Nenhuma evidência confiável neste frame.
            # Não mudamos imediatamente o status.
            estado[
                "frames_sem_evidencia"
            ] += 1

            estado[
                "frames_presente"
            ] = max(
                0,
                estado[
                    "frames_presente"
                ] - 1
            )

            estado[
                "frames_ausente"
            ] = max(
                0,
                estado[
                    "frames_ausente"
                ] - 1
            )

            # Se estava em uso e desapareceu por bastante
            # tempo em TODAS as câmeras, passa a ausente.
            if (
                estado[
                    "status"
                ]
                and
                estado[
                    "frames_sem_evidencia"
                ]
                >= FRAMES_SEM_EVIDENCIA_PARA_AUSENCIA
            ):

                estado[
                    "status"
                ] = False

        status_final[
            epi
        ] = bool(
            estado[
                "status"
            ]
        )

    return status_final

# ============================================================
# INCIDENTES DE EPI
# ============================================================

def processar_incidentes_epis(
    status_epis,
    frames,
    operador
):

    obrigatorios = list(
        getattr(
            config,
            "EPIS_OBRIGATORIOS",
            []
        )
    )

    ambiente = getattr(
        config,
        "NOME_AMBIENTE",
        "Ambiente Principal"
    )

    # Até a biometria ser integrada ao main,
    # usamos uma matrícula estável para não criar
    # uma chave diferente a cada frame.
    matricula = "DESCONHECIDO"

    chaves_detectadas = set()

    if not frames:

        atualizar_incidentes_ausentes(
            chaves_detectadas
        )

        return

    for epi in obrigatorios:

        presente = bool(
            status_epis.get(
                epi,
                False
            )
        )

        if presente:
            continue

        # ----------------------------------------------------
        # Escolhe preferencialmente uma câmera que tenha
        # detectado explicitamente a ausência deste EPI.
        # Se não houver, usa a primeira câmera disponível.
        # ----------------------------------------------------

        camera_escolhida = None
        frame_escolhido = None
        melhor_confianca = -1.0

        for (
            camera_id,
            detalhes
        ) in detalhes_epis_cameras.items():

            if epi in detalhes.get(
                "ausentes",
                set()
            ):

                confianca = detalhes.get(
                    "confiancas_ausencia",
                    {}
                ).get(
                    epi,
                    0.0
                )

                if confianca > melhor_confianca:

                    camera_escolhida = detalhes.get(
                        "camera"
                    )

                    frame_escolhido = detalhes.get(
                        "frame"
                    )

                    melhor_confianca = confianca

        if camera_escolhida is None:

            camera_escolhida, frame_escolhido = (
                frames[0]
            )

        camera_id = getattr(
            camera_escolhida,
            "camera_id",
            None
        )

        camera_nome = getattr(
            camera_escolhida,
            "nome",
            "Camera"
        )

        chave = criar_chave_incidente(
            camera_id,
            matricula,
            epi
        )

        chaves_detectadas.add(
            chave
        )

        processar_incidente(
            camera_id=camera_id,
            camera_nome=camera_nome,
            ambiente=ambiente,
            matricula=matricula,
            operador=operador,
            tipo_infracao=epi,
            severidade="ALTA",
            frame=frame_escolhido
        )

    # Remove/reset incidentes que deixaram de existir.
    atualizar_incidentes_ausentes(
        chaves_detectadas
    )


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
        (altura, largura, 3),
        dtype=np.uint8
    )

    painel[:] = (28, 28, 28)

    # ========================================================
    # CABECALHO
    # ========================================================

    cv2.putText(
        painel,
        "STATUS DOS EPIs",
        (16, 28),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.58,
        (255, 255, 255),
        2,
        cv2.LINE_AA
    )

    cv2.line(
        painel,
        (16, 40),
        (largura - 16, 40),
        (80, 80, 80),
        1
    )

    # ========================================================
    # OPERADOR
    # ========================================================

    cv2.putText(
        painel,
        "OPERADOR",
        (16, 62),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.34,
        (160, 160, 160),
        1,
        cv2.LINE_AA
    )

    operador_tela = str(operador)

    if len(operador_tela) > 30:
        operador_tela = operador_tela[:30] + "..."

    cv2.putText(
        painel,
        operador_tela,
        (16, 84),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.42,
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
        (16, 108),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.34,
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
        (16, 132),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.46,
        cor_severidade,
        2,
        cv2.LINE_AA
    )

    # ========================================================
    # ESTADO
    # ========================================================

    cv2.putText(
        painel,
        "ESTADO",
        (16, 158),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.34,
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
        (16, 182),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.42,
        cor_estado,
        2,
        cv2.LINE_AA
    )

    cv2.line(
        painel,
        (16, 196),
        (largura - 16, 196),
        (80, 80, 80),
        1
    )

    # ========================================================
    # EPIs OBRIGATORIOS
    # ========================================================

    cv2.putText(
        painel,
        "EPIs OBRIGATORIOS",
        (16, 218),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.34,
        (160, 160, 160),
        1,
        cv2.LINE_AA
    )

    epis_obrigatorios = list(
        getattr(
            config,
            "EPIS_OBRIGATORIOS",
            []
        )
    )

    if status_epis is None:
        status_epis = {}

    y = 246

    if not epis_obrigatorios:

        cv2.putText(
            painel,
            "Nenhum EPI selecionado",
            (16, y),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.38,
            (150, 150, 150),
            1,
            cv2.LINE_AA
        )

        return painel

    # Ajusta automaticamente o espacamento conforme a altura.
    espaco_disponivel = max(
        1,
        altura - y - 8
    )

    passo = min(
        38,
        max(
            22,
            espaco_disponivel // max(
                1,
                len(epis_obrigatorios)
            )
        )
    )

    for epi in epis_obrigatorios:

        if y > altura - 8:
            break

        presente = bool(
            status_epis.get(
                epi,
                False
            )
        )

        if presente:
            texto_status = "EM USO"
            cor_epi = (0, 200, 0)
        else:
            texto_status = "NAO EM USO"
            cor_epi = (0, 0, 255)

        # Nome do EPI na propria cor do status.
        cv2.putText(
            painel,
            epi,
            (16, y),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.39,
            cor_epi,
            2,
            cv2.LINE_AA
        )

        tamanho_status, _ = cv2.getTextSize(
            texto_status,
            cv2.FONT_HERSHEY_SIMPLEX,
            0.34,
            1
        )

        x_status = largura - tamanho_status[0] - 16

        cv2.putText(
            painel,
            texto_status,
            (x_status, y),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.34,
            cor_epi,
            1,
            cv2.LINE_AA
        )

        cv2.line(
            painel,
            (16, y + 8),
            (largura - 16, y + 8),
            (60, 60, 60),
            1
        )

        y += passo

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
                    status_epis = analisar_epis_cameras(
                        frames
                    )

                    severidade = calcular_severidade_epi(
                        status_epis
                    )

                    processar_incidentes_epis(
                        status_epis,
                        frames,
                        operador
                    )

                    atualizar_notificacoes(
                        status_epis=status_epis,
                        frames=frames,
                        operador=operador,
                        severidade=severidade
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

        try:
            encerrar_notificacoes()
        except Exception as erro:
            print(
                f"⚠️ Erro ao encerrar notificações: {erro}"
            )

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
